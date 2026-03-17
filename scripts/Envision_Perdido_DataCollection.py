#!/usr/bin/env python3
"""Compatibility wrapper for moved scraper module."""

from scripts.scrapers.perdido_chamber_scraper import *  # noqa: F401,F403

if __name__ == "__main__":
	import runpy

	runpy.run_module("scripts.scrapers.perdido_chamber_scraper", run_name="__main__")
