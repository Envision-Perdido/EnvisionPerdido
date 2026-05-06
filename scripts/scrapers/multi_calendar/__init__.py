"""multi_calendar sub-package — public API.

Import surface that the rest of the codebase should use::

    from scripts.scrapers.multi_calendar import scrape_sources, SourceConfig
"""

from scripts.scrapers.multi_calendar.models import (  # noqa: F401
    DetailSelectors,
    ListingSelectors,
    ScraperError,
    SourceConfig,
    load_config,
)
from scripts.scrapers.multi_calendar.scraper import scrape_sources  # noqa: F401

__all__ = [
    "DetailSelectors",
    "ListingSelectors",
    "ScraperError",
    "SourceConfig",
    "load_config",
    "scrape_sources",
]
