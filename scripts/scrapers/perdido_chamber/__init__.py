"""Perdido Chamber event scraper — decomposed layer structure.

Layer organization:
- models: Constants and configuration
- fetch: HTTP fetching with retry logic
- parse: HTML and ICS parsing
- scraper: Main orchestration
- output: JSON/CSV export

Public API:
    from scripts.scrapers.perdido_chamber import scrape_month, save_events_json, save_events_csv
"""

from .output import save_events_csv, save_events_json
from .scraper import scrape_month

__all__ = ["scrape_month", "save_events_json", "save_events_csv"]
