#!/usr/bin/env python3
"""Compatibility wrapper for moved scraper module."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from scripts.scrapers import wren_haven_scraper as _impl
from scripts.scrapers.wren_haven_scraper import *  # noqa: F401,F403

CACHE_DIR = _impl.CACHE_DIR
CACHE_TTL_HOURS = _impl.CACHE_TTL_HOURS
SOURCE_NAME = _impl.SOURCE_NAME
SOURCE_URL = _impl.SOURCE_URL
WrenHavenScraperError = _impl.WrenHavenScraperError

# Re-export private helpers that are used by the unit tests. Star import does
# not bring underscore-prefixed names into this compatibility wrapper.
_fetch_events_html = _impl._fetch_events_html
_load_cached_html = _impl._load_cached_html
_parse_events_from_html = _impl._parse_events_from_html
_save_cached_html = _impl._save_cached_html

normalize_event = _impl.normalize_event


def scrape_wren_haven(
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    force_refresh: bool = False,
) -> list[dict[str, Any]]:
    """Compatibility wrapper that preserves old patch points for tests."""
    try:
        html = _fetch_events_html(force_refresh=force_refresh)
        raw_events = _parse_events_from_html(html)

        normalized = []
        for raw in raw_events:
            normalized_event = normalize_event(raw)
            if normalized_event:
                normalized.append(normalized_event)

        filtered = normalized
        if start_date or end_date:

            def in_range(event_start: datetime | None) -> bool:
                if not event_start:
                    return False
                if hasattr(event_start, "replace"):
                    event_start = (
                        event_start.replace(tzinfo=None) if event_start.tzinfo else event_start
                    )
                else:
                    return False

                start_ok = not start_date or event_start >= start_date
                end_ok = not end_date or event_start <= end_date
                return start_ok and end_ok

            filtered = [event for event in normalized if in_range(event["start"])]

        return filtered
    except WrenHavenScraperError:
        raise
    except Exception as exc:
        raise WrenHavenScraperError(f"Error scraping Wren Haven: {exc}")


def get_events(year: int | None = None, month: int | None = None) -> list[dict[str, Any]]:
    """Compatibility wrapper that preserves old patch points for tests."""
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


if __name__ == "__main__":
    import runpy

    runpy.run_module("scripts.scrapers.wren_haven_scraper", run_name="__main__")
