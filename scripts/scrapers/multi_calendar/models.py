"""Data models and config loading for the multi-calendar scraper."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


DEFAULT_CONFIG = Path("data/community_calendar_sources.json")

COMMUNITY_KW = (
    r"(festival|parade|market|farmers|community|workshop|class|volunteer|fundraiser|"
    r"family|youth|meetup|open house|concert|library|park|veterans|food truck|gallery|"
    r"art\b|craft\b|charity|cleanup|nonprofit|school)"
)

NONCOMM_KW = (
    r"(board meeting|committee|sponsor|leads? group|b2b|webinar|"
    r"business networking|members only)"
)


class ScraperError(Exception):
    """Raised when a scraper encounters an unrecoverable error."""


@dataclass
class ListingSelectors:
    event_link_selector: str
    next_page_selector: str | None = None


@dataclass
class DetailSelectors:
    title_selector: str
    date_selector: str | None = None
    end_date_selector: str | None = None
    location_selector: str | None = None
    description_selector: str | None = None
    category_selector: str | None = None


@dataclass
class SourceConfig:
    name: str
    start_urls: list[str]
    allowed_domains: list[str]
    listing: ListingSelectors
    detail: DetailSelectors
    enabled: bool = True


def load_config(path: Path = DEFAULT_CONFIG) -> list[SourceConfig]:
    """Parse *path* (JSON) into a list of :class:`SourceConfig` objects."""
    if not path.exists():
        raise ScraperError(f"Config file not found: {path}")

    raw = json.loads(path.read_text(encoding="utf-8"))
    sources_raw = raw.get("sources", [])
    if not sources_raw:
        raise ScraperError("Config contains no sources")

    sources: list[SourceConfig] = []
    for src in sources_raw:
        listing = ListingSelectors(**src["listing"])
        detail = DetailSelectors(**src["detail"])
        sources.append(
            SourceConfig(
                name=src["name"],
                start_urls=src["start_urls"],
                allowed_domains=src.get("allowed_domains", []),
                listing=listing,
                detail=detail,
                enabled=src.get("enabled", True),
            )
        )

    return sources
