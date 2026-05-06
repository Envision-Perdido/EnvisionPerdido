#!/usr/bin/env python3
"""Compatibility shim for perdido_chamber_scraper — DEPRECATED.

.. deprecated::
    Import directly from ``scripts.scrapers.perdido_chamber`` instead.
    The layer structure (fetch, parse, scraper, output) is now in
    ``scripts/scrapers/perdido_chamber/`` directory.

This wrapper will be removed in a future release.
"""

import os
import sys
import warnings

warnings.warn(
    "scripts.scrapers.perdido_chamber_scraper is deprecated. "
    "Use 'from scripts.scrapers.perdido_chamber import scrape_month' instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export for backward compatibility
from scripts.scrapers.perdido_chamber import (  # noqa: F401, E402
    save_events_csv,
    save_events_json,
    scrape_month,
)

# Public API
__all__ = ["scrape_month", "save_events_json", "save_events_csv"]


if __name__ == "__main__":
    """Standalone runner for testing.
    
    Usage:
        python scripts/scrapers/perdido_chamber_scraper.py [OUTPUT_DIR]
    
    Scrapes all months in 2025 and saves to JSON and CSV files.
    """
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    os.makedirs(out_dir, exist_ok=True)

    print("[runner] Starting scrape for all months in 2025...", flush=True)

    all_events = []
    for month in range(1, 13):
        month_str = f"2025-{month:02d}-01"
        month_url = f"https://business.perdidochamber.com/events/calendar/{month_str}"
        print(f"[runner] Scraping {month_url}", flush=True)
        try:
            events = scrape_month(month_url)
            print(f"[runner] Scraped {len(events)} events from {month_url}", flush=True)
            all_events.extend(events)
        except Exception as e:
            print(f"[runner] Error scraping {month_url}: {e}", flush=True)

    print(f"[runner] Total events scraped: {len(all_events)}", flush=True)

    json_path = os.path.join(out_dir, "perdido_events_2025.json")
    csv_path = os.path.join(out_dir, "perdido_events_2025.csv")

    save_events_json(all_events, json_path)
    save_events_csv(all_events, csv_path)

    print(f"[runner] Wrote:\n  - {json_path}\n  - {csv_path}", flush=True)
    print("[done]", flush=True)
