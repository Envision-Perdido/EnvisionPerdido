"""Stage 1 — Scrape raw events from configured sources."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from scripts.tooling.logger import get_logger

logger = get_logger(__name__)


def _log(msg: str) -> None:
    logger.info(msg)


def scrape_events(
    year: int | None = None,
    month: int | None = None,
    include_sources: list[str] | None = None,
) -> tuple[list[dict], list[str]]:
    """Scrape events from all configured sources in parallel.

    Args:
        year: Year to scrape (default: current year).
        month: Month to scrape (default: current month).
        include_sources: Source names to include.
            Supported values: ``'perdido_chamber'``, ``'wren_haven'``.
            Default: ``['perdido_chamber', 'wren_haven']``.

    Returns:
        ``(events_list, errors_list)`` where *events_list* is the combined
        list of raw event dicts and *errors_list* collects any per-source
        failure messages.
    """
    if include_sources is None:
        include_sources = ["perdido_chamber", "wren_haven"]

    if year is None:
        year = datetime.now().year
    if month is None:
        month = datetime.now().month

    all_events: list[dict] = []
    errors: list[str] = []
    scraping_tasks: list[tuple[str, str | None]] = []

    if "perdido_chamber" in include_sources:
        base_url = "https://business.perdidochamber.com/events/calendar"
        for m in range(month, min(month + 2, 13)):
            month_str = f"{year}-{m:02d}-01"
            scraping_tasks.append(("perdido_chamber", f"{base_url}/{month_str}"))

    if "wren_haven" in include_sources:
        scraping_tasks.append(("wren_haven", None))

    _log(f"Running {len(scraping_tasks)} scraping task(s) in parallel...")
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(_scrape_single_source, source, url): (source, url)
            for source, url in scraping_tasks
        }
        for i, future in enumerate(as_completed(futures), 1):
            source, url = futures[future]
            try:
                events, error = future.result()
                all_events.extend(events)
                if error:
                    errors.append(error)
                elapsed = time.time() - start_time
                _log(
                    f"  [{i}/{len(scraping_tasks)}] {source} completed: "
                    f"{len(events)} events ({elapsed:.1f}s elapsed)"
                )
            except Exception as exc:
                msg = f"Error scraping {source} {url or ''}: {exc}"
                _log(f"ERROR: {msg}")
                errors.append(msg)

    elapsed = time.time() - start_time
    _log(f"Total events scraped: {len(all_events)} in {elapsed:.1f}s")
    if errors:
        _log(f"Encountered {len(errors)} scraper error(s)")

    return all_events, errors


def _scrape_single_source(
    source: str, url: str | None
) -> tuple[list[dict], str | None]:
    """Scrape a single source (runs in thread pool).

    Args:
        source: ``'perdido_chamber'`` or ``'wren_haven'``.
        url: URL to fetch, or ``None`` for sources that discover it internally.

    Returns:
        ``(events, error_message)`` — *error_message* is ``None`` on success.
    """
    try:
        if source == "perdido_chamber":
            from scripts.scrapers.perdido_chamber_scraper import scrape_month

            return scrape_month(url), None

        if source == "wren_haven":
            try:
                from scripts.scrapers.wren_haven_scraper import scrape_wren_haven

                return scrape_wren_haven(), None
            except ImportError as exc:
                return [], (
                    f"wren_haven_scraper not available "
                    f"(Playwright not installed?): {exc}"
                )
    except Exception as exc:
        return [], f"Error scraping {source}: {exc}"

    return [], f"Unknown source: {source}"
