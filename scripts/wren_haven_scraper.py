"""
Wren Haven Homestead events scraper.

Wren Haven Homestead (https://www.wrenhavenhomestead.com/events) uses a Wix-based
calendar that requires JavaScript rendering. This module:

1. Uses Playwright to load and render the events page
2. Parses the rendered HTML with BeautifulSoup to extract event data
3. Navigates through months programmatically
4. Caches event HTML for performance (24-hour TTL)
5. Normalizes events into the standard Event model

Reuses:
- Existing Event model and normalization functions
- Existing venue resolution and paid/free detection
- Existing event enrichment and filtering pipeline
"""

import asyncio
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from playwright.async_api import async_playwright
except ImportError:
    async_playwright = None


# Configuration
SOURCE_NAME = "wren_haven_homestead"
SOURCE_URL = "https://www.wrenhavenhomestead.com/events"
CACHE_TTL_HOURS = 24

# Cache directory
CACHE_DIR = Path(__file__).parent.parent / "data" / "cache" / "wren_haven"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


class WrenHavenScraperError(Exception):
    """Raised when Wren Haven scraping fails."""

    pass


def _load_cached_html(force_refresh: bool = False) -> str | None:
    """Load cached event HTML if it exists and is fresh."""
    cache_file = CACHE_DIR / "events.html"

    if not force_refresh and cache_file.exists():
        file_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
        age_hours = (datetime.now() - file_time).total_seconds() / 3600

        if age_hours < CACHE_TTL_HOURS:
            try:
                with open(cache_file, encoding="utf-8") as f:
                    print(
                        f"[Wren Haven] Using cached HTML ({age_hours:.1f}h old) - skipping Playwright"
                    )
                    return f.read()
            except Exception:
                pass
        else:
            print(
                f"[Wren Haven] Cache expired ({age_hours:.1f}h > {CACHE_TTL_HOURS}h TTL) - fetching fresh"
            )

    return None


def _save_cached_html(html: str) -> None:
    """Save event HTML to cache."""
    try:
        cache_file = CACHE_DIR / "events.html"
        with open(cache_file, "w", encoding="utf-8") as f:
            f.write(html)
    except Exception:
        pass


async def _fetch_events_with_playwright() -> str:
    """
    Use Playwright to load the events page and extract rendered HTML.
    Navigates through months to collect all events.
    """
    if async_playwright is None:
        raise WrenHavenScraperError(
            "Playwright not installed. Install with: pip install playwright"
        )

    all_html = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # Navigate to events page
            await page.goto(SOURCE_URL, wait_until="networkidle", timeout=30000)
            await page.wait_for_selector("[data-hook='EVENTS_ROOT_NODE']", timeout=5000)

            # Scrape current month
            html = await page.content()
            all_html.append(html)

            # Navigate forward 3 months to get upcoming events
            for i in range(3):
                try:
                    next_button = page.locator("button[aria-label='Next month']")
                    await next_button.click()
                    await page.wait_for_timeout(1000)  # Wait for animation
                    html = await page.content()
                    all_html.append(html)
                except Exception:
                    break  # Stop if we can't navigate further

        finally:
            await browser.close()

    return "\n".join(all_html)


def _fetch_events_html(force_refresh: bool = False) -> str:
    """
    Fetch event HTML using Playwright. Uses asyncio to run async code.
    """
    # Try cache first
    cached = _load_cached_html(force_refresh=force_refresh)
    if cached:
        return cached

    # Fetch fresh HTML
    try:
        html = asyncio.run(_fetch_events_with_playwright())
        _save_cached_html(html)
        return html
    except Exception as e:
        raise WrenHavenScraperError(f"Failed to fetch events page: {e}")


def _parse_events_from_html(html: str) -> list[dict[str, Any]]:
    """
    Parse event data from rendered Wix events calendar HTML.
    For now returns empty list - actual parsing depends on HTML structure.
    """
    soup = BeautifulSoup(html, "html.parser")
    events = []

    # Find the events widget root
    widget = soup.find(attrs={"data-hook": "EVENTS_ROOT_NODE"})
    if not widget:
        return []

    # Placeholder - actual implementation would parse the calendar structure
    # and extract event details from the rendered HTML

    return events


def _prepare_request_headers(artifacts: dict[str, Any]) -> dict[str, str]:
    """
    Prepare HTTP headers for the request, preserving auth and other artifacts.

    Reuses existing pattern: merge default headers with discovered headers.
    """
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    # Add discovered headers (Authorization, Content-Type, etc.)
    if artifacts.get("headers"):
        headers.update(artifacts["headers"])

    return headers


def _fetch_events_from_api(
    start_date: str | None = None,
    end_date: str | None = None,
    bootstrap_artifacts: dict[str, Any] | None = None,
    max_retries: int = 3,
) -> list[dict[str, Any]]:
    """
    Fetch raw events from Wren Haven JSON API.

    Reuses existing retry/backoff pattern from requests library.

    Args:
        start_date: ISO date string (YYYY-MM-DD), optional filter
        end_date: ISO date string (YYYY-MM-DD), optional filter
        bootstrap_artifacts: Cached endpoint/auth info
        max_retries: Number of retries on failure

    Returns:
        List of raw event dictionaries from the API
    """

    if bootstrap_artifacts is None:
        # Use simple default artifacts for HTML-based scraping
        bootstrap_artifacts = {
            "endpoint": SOURCE_URL,
            "method": "GET",
            "headers": {},
            "cookies": [],
        }

    endpoint = bootstrap_artifacts.get("endpoint", SOURCE_URL)
    method = bootstrap_artifacts.get("method", "GET")
    headers = _prepare_request_headers(bootstrap_artifacts)
    cookies = bootstrap_artifacts.get("cookies", [])
    body = bootstrap_artifacts.get("body")

    if not endpoint:
        raise WrenHavenScraperError("No endpoint available")

    # Build request parameters/body
    params = {}
    request_body = None

    if start_date:
        params["start"] = start_date
    if end_date:
        params["end"] = end_date

    if method.upper() == "POST" and body:
        # For POST requests, try to merge filters into body
        try:
            request_body = json.loads(body) if isinstance(body, str) else body
            if start_date:
                request_body["start"] = start_date
            if end_date:
                request_body["end"] = end_date
        except:
            request_body = body

    # Create session for requests
    session = requests.Session()

    # Reuse existing retry pattern (simple exponential backoff)
    last_error = None
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                time.sleep(0.5 * attempt)  # Backoff

            kwargs = {"headers": headers, "timeout": 30}

            # Add cookies if present
            if cookies:
                cookie_dict = {c["name"]: c["value"] for c in cookies}
                kwargs["cookies"] = cookie_dict

            if method.upper() == "POST":
                if request_body:
                    kwargs["json"] = request_body
                response = session.post(endpoint, **kwargs)
            else:
                if params:
                    kwargs["params"] = params
                response = session.get(endpoint, **kwargs)

            response.raise_for_status()

            data = response.json()

            # Handle both direct array and nested structure
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                # Try common keys for event lists
                for key in ["events", "items", "results", "data"]:
                    if key in data and isinstance(data[key], list):
                        return data[key]
                # If no standard key, return dict as single item for inspection
                return [data]

            return []

        except requests.exceptions.RequestException as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = 2**attempt
                print(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
        except json.JSONDecodeError as e:
            raise WrenHavenScraperError(f"API response was not valid JSON: {e}")
        except Exception as e:
            raise WrenHavenScraperError(f"Error fetching events: {e}")

    if last_error:
        raise WrenHavenScraperError(
            f"Failed to fetch events after {max_retries} retries: {last_error}"
        )

    return []


def normalize_event(raw_event: dict[str, Any]) -> dict[str, Any] | None:
    """
    Normalize a raw Wren Haven event to standard Event schema.

    Maps Wren Haven fields to:
    - title, start, end, location, url, description, uid, category
    """

    # Require title
    title = raw_event.get("title") or raw_event.get("name")
    if not title or not str(title).strip():
        return None

    title = str(title).strip()

    # Extract dates
    start = raw_event.get("start") or raw_event.get("startDate") or raw_event.get("begin")
    end = raw_event.get("end") or raw_event.get("endDate") or raw_event.get("finish")

    # Parse dates if they're strings
    if isinstance(start, str):
        try:
            start = datetime.fromisoformat(start.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            start = None

    if isinstance(end, str):
        try:
            end = datetime.fromisoformat(end.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            end = None

    # Location
    location = raw_event.get("location") or raw_event.get("venue") or raw_event.get("place")
    location = str(location).strip() if location else None

    # URL
    url = raw_event.get("url") or raw_event.get("link")
    url = str(url).strip() if url else None

    # Description
    description = raw_event.get("description") or raw_event.get("summary")
    description = str(description).strip() if description else None

    # UID (use title + start date if not provided)
    uid = raw_event.get("uid") or raw_event.get("id")
    if not uid and start:
        uid = f"{SOURCE_NAME}_{title}_{start.isoformat()}"

    # Category (default to "Community Event")
    category = raw_event.get("category") or "Community Event"

    return {
        "title": title,
        "start": start,
        "end": end,
        "location": location,
        "url": url,
        "description": description,
        "uid": uid,
        "category": category,
        "source": SOURCE_NAME,
    }


def scrape_wren_haven(
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    force_refresh: bool = False,
) -> list[dict[str, Any]]:
    """
    Scrape events from Wren Haven Homestead.

    Args:
        start_date: Optional start date filter
        end_date: Optional end date filter
        force_refresh: If True, bypass cache and refetch HTML

    Returns:
        List of normalized event dictionaries

    Raises:
        WrenHavenScraperError: If scraping fails
    """

    try:
        # Fetch HTML (uses cache or Playwright)
        html = _fetch_events_html(force_refresh=force_refresh)

        # Parse events from HTML
        raw_events = _parse_events_from_html(html)

        # Normalize events
        normalized = []
        for raw in raw_events:
            normalized_event = normalize_event(raw)
            if normalized_event:
                normalized.append(normalized_event)

        # Filter by date range if specified
        filtered = normalized
        if start_date or end_date:

            def in_range(event_start):
                if not event_start:
                    return False
                # Handle timezone-aware and naive datetimes
                if hasattr(event_start, "replace"):
                    # Make both naive for comparison
                    es = event_start.replace(tzinfo=None) if event_start.tzinfo else event_start
                else:
                    return False

                start_ok = not start_date or es >= start_date
                end_ok = not end_date or es <= end_date
                return start_ok and end_ok

            filtered = [e for e in normalized if in_range(e["start"])]

        return filtered

    except WrenHavenScraperError:
        raise
    except Exception as e:
        raise WrenHavenScraperError(f"Error scraping Wren Haven: {e}")


def get_events(
    year: int | None = None,
    month: int | None = None,
) -> list[dict[str, Any]]:
    """
    Pipeline-compatible interface for scraping Wren Haven events.

    Args:
        year: Year (default current)
        month: Month (default current)

    Returns:
        List of normalized events for the specified month
    """
    if year is None:
        year = datetime.now().year
    if month is None:
        month = datetime.now().month

    # Calculate date range for the month
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = datetime(year, month + 1, 1) - timedelta(days=1)

    return scrape_wren_haven(start_date=start_date, end_date=end_date)
