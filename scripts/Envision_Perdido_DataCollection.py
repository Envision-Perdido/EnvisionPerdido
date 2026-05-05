#!/usr/bin/env python3
"""Compatibility wrapper for moved scraper module.

DEPRECATED: Import directly from scripts.scrapers.perdido_chamber_scraper.
This wrapper will be removed in a future release.
"""
import warnings

warnings.warn(
    "scripts.Envision_Perdido_DataCollection is deprecated. "
    "Use 'scripts.scrapers.perdido_chamber_scraper' directly.",
    DeprecationWarning,
    stacklevel=2,
)

from scripts.scrapers.perdido_chamber_scraper import *  # noqa: F401,F403

if __name__ == "__main__":
    import runpy

    runpy.run_module("scripts.scrapers.perdido_chamber_scraper", run_name="__main__")

if __name__ == "__main__":
	import runpy

	runpy.run_module("scripts.scrapers.perdido_chamber_scraper", run_name="__main__")
