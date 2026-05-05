#!/usr/bin/env python3
"""Compatibility wrapper for moved scraper module.

DEPRECATED: Import directly from scripts.scrapers.wren_haven_scraper.
This wrapper will be removed in a future release.
"""
import warnings

warnings.warn(
    "scripts.wren_haven_scraper is deprecated. "
    "Use 'scripts.scrapers.wren_haven_scraper' directly.",
    DeprecationWarning,
    stacklevel=2,
)

from scripts.scrapers.wren_haven_scraper import *  # noqa: F401,F403

if __name__ == "__main__":
    import runpy

    runpy.run_module("scripts.scrapers.wren_haven_scraper", run_name="__main__")

if __name__ == "__main__":
	import runpy

	runpy.run_module("scripts.scrapers.wren_haven_scraper", run_name="__main__")
