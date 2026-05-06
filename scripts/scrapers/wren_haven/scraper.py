"""Parse, normalize, and public scrape API for Wren Haven events."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from bs4 import BeautifulSoup

from scripts.scrapers.wren_haven.fetch import fetch_events_html

SOURCE_NAME = "wren_haven_homestead"


# ---------------------------------------------------------------------------
# Parse
# ---------------------------------------------------------------------------


def parse_events_from_html(html: str) -> list[dict[str, Any]]:
    """Extract raw event dicts from rendered Wix calendar HTML.

    .. note::
        The actual Wix widget structure must be reverse-engineered from a
        live render.  The current implementation is a documented stub that
        returns an empty list until the selectors are confirmed.
    """
    soup = BeautifulSoup(html, "html.parser")
    widget = soup.find(attrs={"data-hook": "EVENTS_ROOT_NODE"})
    if not widget:
        return []
    # TODO: parse event cards from widget once live HTML structure is known.
    return []


# ---------------------------------------------------------------------------
# Normalize
# ---------------------------------------------------------------------------


def normalize_event(raw_event: dict[str, Any]) -> dict[str, Any] | None:
    """Map a raw Wren Haven event dict to the standard event schema.

    Returns *None* if the event has no usable title.
    """
    title = raw_event.get("title") or raw_event.get("name")
    if not title or not str(title).strip():
        return None
    title = str(title).strip()

    start = raw_event.get("start") or raw_event.get("startDate") or raw_event.get("begin")
    end = raw_event.get("end") or raw_event.get("endDate") or raw_event.get("finish")

    def _parse_dt(value: Any) -> datetime | None:
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                return None
        return value if isinstance(value, datetime) else None

    start_dt = _parse_dt(start)
    end_dt = _parse_dt(end)

    location = raw_event.get("location") or raw_event.get("venue") or raw_event.get("place")
    location = str(location).strip() if location else None

    url = raw_event.get("url") or raw_event.get("link")
    url = str(url).strip() if url else None

    description = raw_event.get("description") or raw_event.get("summary")
    description = str(description).strip() if description else None

    uid = raw_event.get("uid") or raw_event.get("id")
    if not uid and start_dt:
        uid = f"{SOURCE_NAME}_{title}_{start_dt.isoformat()}"

    category = raw_event.get("category") or "Community Event"

    return {
        "title": title,
        "start": start_dt,
        "end": end_dt,
        "location": location,
        "url": url,
        "description": description,
        "uid": uid,
        "category": category,
        "source": SOURCE_NAME,
    }


# ---------------------------------------------------------------------------
# Public scrape API
# ---------------------------------------------------------------------------


def scrape_wren_haven(
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    force_refresh: bool = False,
) -> list[dict[str, Any]]:
    """Scrape events from Wren Haven Homestead and return normalized dicts.

    Args:
        start_date: Optional lower-bound date filter.
        end_date: Optional upper-bound date filter.
        force_refresh: When *True*, bypass the HTML cache.

    Raises:
        RuntimeError: If the page cannot be fetched.
    """
    html = fetch_events_html(force_refresh=force_refresh)
    raw_events = parse_events_from_html(html)

    normalized = [n for r in raw_events if (n := normalize_event(r)) is not None]

    if start_date or end_date:

        def _in_range(event: dict[str, Any]) -> bool:
            es = event.get("start")
            if not isinstance(es, datetime):
                return False
            es_naive = es.replace(tzinfo=None) if es.tzinfo else es
            start_ok = not start_date or es_naive >= start_date
            end_ok = not end_date or es_naive <= end_date
            return start_ok and end_ok

        normalized = [e for e in normalized if _in_range(e)]

    return normalized


def get_events(
    year: int | None = None,
    month: int | None = None,
) -> list[dict[str, Any]]:
    """Pipeline-compatible interface: return events for one calendar month.

    Args:
        year: Target year (default: current year).
        month: Target month (default: current month).
    """
    if year is None:
        year = datetime.now().year
    if month is None:
        month = datetime.now().month

    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = datetime(year, month + 1, 1) - timedelta(days=1)

    return scrape_wren_haven(start_date=start_date, end_date=end_date)
