#!/usr/bin/env python3
"""Compatibility wrapper for moved scraper module.

DEPRECATED: Import directly from scripts.scrapers.multi_calendar_scraper.
This wrapper will be removed in a future release.
"""
import warnings

warnings.warn(
    "scripts.multi_calendar_scraper is deprecated. "
    "Use 'scripts.scrapers.multi_calendar_scraper' directly.",
    DeprecationWarning,
    stacklevel=2,
)

from scripts.scrapers.multi_calendar_scraper import *  # noqa: F401,F403

if __name__ == "__main__":
    from scripts.scrapers.multi_calendar_scraper import main

    raise SystemExit(main())
