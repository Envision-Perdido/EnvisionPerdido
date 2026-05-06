#!/usr/bin/env python3
"""Compatibility shim — delegates to :mod:`scripts.scrapers.multi_calendar`.

.. deprecated::
    Import directly from scripts.scrapers.multi_calendar instead.
    This file will be removed in a future release.
"""

import warnings

warnings.warn(
    "scripts.scrapers.multi_calendar_scraper is deprecated. "
    "Use 'from scripts.scrapers.multi_calendar import scrape_sources' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from scripts.scrapers.multi_calendar import (  # noqa: F401, E402
    DetailSelectors,
    ListingSelectors,
    ScraperError,
    SourceConfig,
    load_config,
    scrape_sources,
)
from scripts.scrapers.multi_calendar.scraper import (  # noqa: F401, E402
    build_parser,
    main,
    normalize_and_dedupe,
    save_outputs,
    weak_label,
)

if __name__ == "__main__":
    raise SystemExit(main())
