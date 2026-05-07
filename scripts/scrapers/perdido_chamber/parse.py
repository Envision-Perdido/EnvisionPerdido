"""HTML and ICS parsing layer for Perdido Chamber scraper.

Handles BeautifulSoup HTML parsing and iCalendar parsing.
"""

import importlib
import os
import re
from typing import TYPE_CHECKING
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

from .models import BASE, SOURCE_NAME

# Handle optional BeautifulSoup dependency
if TYPE_CHECKING:
    from bs4 import BeautifulSoup
else:
    try:
        _bs = importlib.import_module("bs4")
        BeautifulSoup = getattr(_bs, "BeautifulSoup")
    except (ImportError, AttributeError):
        BeautifulSoup = None

# Handle optional icalendar dependency
try:
    _ical = importlib.import_module("icalendar")
    Calendar = getattr(_ical, "Calendar")
except (ImportError, AttributeError):
    Calendar = None


def find_ics_links_in_html(soup) -> str | None:
    """Find iCalendar download link on an event detail page.

    Handles both old and new GrowthZone link formats:
    - New format: /events/addtocalendar/{slug}?format=ICal
    - Old format: /events/ical/{slug}.ics

    Args:
        soup: BeautifulSoup parsed HTML object.

    Returns:
        URL to ICS file, or None if not found.
    """
    # Try new format first: "Add to iCal Calendar" link in modal
    ical_link = soup.select_one('a[href*="addtocalendar"][href*="format=ICal"]')
    if ical_link and ical_link.get("href"):
        return urljoin(BASE, ical_link["href"])

    # Fallback to old format: direct .ics link
    anchor = soup.find("a", string=re.compile(r"Add to Calendar\s*-\s*iCal", re.IGNORECASE))
    if anchor and anchor.get("href"):
        return urljoin(BASE, anchor["href"])

    # Fallback to any direct .ics link
    generic = soup.select_one('a[href$=".ics"]')
    if generic and generic.get("href"):
        return urljoin(BASE, generic["href"])

    return None


def parse_html_for_event_links(html: str) -> list[str]:
    """Parse calendar month view HTML for event detail links.

    Args:
        html: HTML content of calendar page

    Returns:
        List of unique event detail URLs
    """
    if BeautifulSoup is None:
        raise RuntimeError("BeautifulSoup is required to parse HTML; install beautifulsoup4")

    soup = BeautifulSoup(html, "html.parser")

    # Collect event detail links
    event_links = []
    for anchor in soup.select('a[href*="/events/details"]'):
        href = anchor.get("href")
        if href:
            event_links.append(urljoin(BASE, href))

    # Remove duplicates while preserving order
    seen, unique_links = set(), []
    for link in event_links:
        if link not in seen:
            seen.add(link)
            unique_links.append(link)

    return unique_links


def parse_html_for_ics_link(html: str) -> str | None:
    """Parse event detail HTML for ICS download link.

    Args:
        html: HTML content of event page

    Returns:
        URL to ICS file, or None if not found
    """
    if BeautifulSoup is None:
        return None

    soup = BeautifulSoup(html, "html.parser")
    return find_ics_links_in_html(soup)


def parse_ics_to_dict(ics_content: bytes, source_ics: str, source_page: str | None = None) -> list[dict]:
    """Parse iCalendar content into normalized event dictionaries.

    Args:
        ics_content: Raw ICS file content (bytes)
        source_ics: URL where the ICS was fetched from (for provenance)
        source_page: Event page URL (optional, for provenance)

    Returns:
        List of normalized event dictionaries
    """
    if Calendar is None:
        print("Cannot parse ICS because 'icalendar' package is not installed.")
        return []

    try:
        cal = Calendar.from_ical(ics_content)
    except Exception as e:
        print(f"Error parsing ICS content from {source_ics}: {e}")
        return []

    events = []
    for component in cal.walk():
        # Some implementations require checking .name
        if getattr(component, "name", "").upper() != "VEVENT":
            continue

        event = {
            "title": _text_or_none(component.get("SUMMARY")),
            "description": _text_or_none(component.get("DESCRIPTION")),
            "location": _text_or_none(component.get("LOCATION")),
            "start": _dt_to_iso(component.get("DTSTART")),
            "end": _dt_to_iso(component.get("DTEND")),
            "url": _text_or_none(component.get("URL")),
            "uid": _text_or_none(component.get("UID")),
            "category": _normalize_categories(component.get("CATEGORIES")),
            "last_modified": _dt_to_iso(component.get("LAST-MODIFIED")),
            "created": _dt_to_iso(component.get("CREATED")),
            "source": SOURCE_NAME,
            # Provenance
            "source_ics": source_ics,
            "source_page": source_page,
        }
        events.append(event)

    return events


def _text_or_none(val) -> str | None:
    """Convert value to string or None."""
    return str(val) if val is not None else None


def _normalize_categories(category_value) -> list[str] | None:
    """Normalize iCalendar CATEGORIES value to list of strings."""
    if category_value is None:
        return None

    try:
        # Try to extract categories list
        return list(category_value.cats)
    except (AttributeError, TypeError):
        # Fallback: convert to single-item list
        category_str = _text_or_none(category_value)
        return [category_str] if category_str else None


def _dt_to_iso(dt_value) -> str | None:
    """Convert iCalendar datetime to ISO format string.

    Handles date or datetime with or without timezone, converting to configured timezone.
    """
    if not dt_value:
        return None

    # iCalendar stores time as vDDDTypes; .dt can be date or datetime
    dt = getattr(dt_value, "dt", dt_value)

    try:
        # If it's a datetime with timezone, convert to SITE_TIMEZONE
        if hasattr(dt, "tzinfo") and dt.tzinfo is not None:
            local_tz = ZoneInfo(os.getenv("SITE_TIMEZONE", "America/Chicago"))
            dt = dt.astimezone(local_tz)
            # Return naive local time (remove timezone)
            return dt.replace(tzinfo=None).isoformat()

        # If it's a date or naive datetime, return as-is
        if hasattr(dt, "isoformat"):
            return dt.isoformat()

        # Fallback: convert to string
        return str(dt)
    except Exception:
        return str(dt)
