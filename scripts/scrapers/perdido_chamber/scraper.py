"""Scraper orchestration for Perdido Chamber events.

Main entry point that coordinates fetching and parsing.
"""

import re
import time
from urllib.parse import urlparse

from . import fetch, parse
from .models import BASE, DEFAULT_RATE_LIMIT, SOURCE_NAME


def get_ics_url_from_event_page(event_url: str, pause_seconds: float = 0.1) -> str | None:
    """Fetch the ICS URL from an event detail page.

    Tries multiple approaches:
    1. New format (GrowthZone 2025+): /events/addtocalendar/{slug}?format=ICal
    2. Old format (legacy): /events/ical/{slug}.ics
    3. HTML parsing: Search page for available ICS link

    Args:
        event_url: URL of event detail page
        pause_seconds: Time to wait between requests (rate limiting)

    Returns:
        ICS URL, or None if not found
    """
    # Extract slug from event URL: /events/details/[slug]
    match = re.search(r"/events/details/([^/]+)", urlparse(event_url).path)
    if not match:
        print(f"Could not extract event slug from {event_url}")
        return None

    event_slug = match.group(1)

    # Try new format first: /events/addtocalendar/{slug}?format=ICal
    new_format_url = f"{BASE}/events/addtocalendar/{event_slug}?format=ICal"
    try:
        time.sleep(pause_seconds)
        status = fetch.get_page_headers(new_format_url, timeout=15)
        if status == 200:
            return new_format_url
    except Exception:
        pass

    # Try old format: /events/ical/{slug}.ics
    old_format_url = f"{BASE}/events/ical/{event_slug}.ics"
    try:
        time.sleep(pause_seconds)
        status = fetch.get_page_headers(old_format_url, timeout=15)
        if status == 200:
            return old_format_url
    except Exception:
        pass

    # Fallback: fetch event page and search HTML for ICS link
    try:
        time.sleep(pause_seconds)
        html = fetch.get_page_html(event_url, timeout=30)
        return parse.parse_html_for_ics_link(html)
    except Exception as e:
        print(f"Error fetching event page {event_url}: {e}")
        return None


def scrape_month(month_url: str, pause_seconds: float = DEFAULT_RATE_LIMIT) -> list[dict]:
    """Scrape all events from a Perdido Chamber calendar month view.

    Fetches the month view, extracts event detail URLs, and retrieves ICS files
    for each event. Handles rate limiting and errors gracefully.

    Args:
        month_url: URL to Perdido Chamber calendar month view
        pause_seconds: Time to wait between requests (rate limiting, default 0.4s)

    Returns:
        List of normalized event dictionaries
    """
    all_events: list[dict] = []
    errors: list[str] = []

    # Fetch and parse month view to get event URLs
    try:
        html = fetch.get_page_html(month_url)
        event_pages = parse.parse_html_for_event_links(html)
    except Exception as e:
        print(f"Error fetching event URLs from {month_url}: {e}")
        return all_events

    print(f"Found {len(event_pages)} event pages in month view.")

    # Fetch each event's ICS file and parse events
    seen_ics: set[str] = set()
    for i, page_url in enumerate(event_pages, 1):
        try:
            ics_url = get_ics_url_from_event_page(page_url, pause_seconds=pause_seconds)
            if not ics_url:
                errors.append(f"No ICS link found on event page {page_url}")
                time.sleep(pause_seconds)
                continue

            if ics_url in seen_ics:
                time.sleep(pause_seconds)
                continue

            seen_ics.add(ics_url)

            # Fetch ICS content
            try:
                time.sleep(pause_seconds)
                ics_content = fetch.fetch_ics_content(ics_url)
            except Exception as e:
                errors.append(f"Error fetching ICS from {ics_url}: {e}")
                continue

            # Parse ICS to events
            events = parse.parse_ics_to_dict(
                ics_content, source_ics=ics_url, source_page=page_url
            )
            all_events.extend(events)

        except Exception as e:
            errors.append(f"Error processing event page {page_url}: {e}")
        finally:
            time.sleep(pause_seconds)

    print(f"Scraped {len(all_events)} events with {len(errors)} errors.")
    if errors:
        for msg in errors[:5]:
            print(f"  - {msg}")
        if len(errors) > 5:
            print(f"  ... and {len(errors) - 5} more errors.")

    return all_events
