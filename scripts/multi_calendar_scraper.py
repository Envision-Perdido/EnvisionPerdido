#!/usr/bin/env python3
"""Compatibility wrapper for moved scraper module."""

from scripts.scrapers.multi_calendar_scraper import *  # noqa: F401,F403

if __name__ == "__main__":
    from scripts.scrapers.multi_calendar_scraper import main

    raise SystemExit(main())
