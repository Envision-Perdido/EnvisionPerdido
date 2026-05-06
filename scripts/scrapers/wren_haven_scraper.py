"""Compatibility shim — delegates to :mod:`scripts.scrapers.wren_haven`.

.. deprecated::
    Import directly from scripts.scrapers.wren_haven instead.
    This file will be removed in a future release.
"""

import warnings

warnings.warn(
    "scripts.scrapers.wren_haven_scraper is deprecated. "
    "Use 'from scripts.scrapers.wren_haven import scrape_wren_haven, get_events' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from scripts.scrapers.wren_haven import (  # noqa: F401, E402
    get_events,
    normalize_event,
    scrape_wren_haven,
)
from scripts.scrapers.wren_haven.cache import (  # noqa: F401, E402
    CACHE_DIR,
    CACHE_TTL_HOURS,
    load_cached_html,
    save_cached_html,
)
from scripts.scrapers.wren_haven.fetch import (  # noqa: F401, E402
    SOURCE_URL,
    fetch_events_from_api,
    fetch_events_html,
)
