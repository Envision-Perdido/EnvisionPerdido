"""HTTP fetch layer for the multi-calendar scraper.

Responsible for:
- Creating a reusable :class:`requests.Session`
- Collecting event-page URLs from listing pages (pagination-aware)
- Fetching and lightly parsing individual event detail pages
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from scripts.scrapers.multi_calendar.models import SourceConfig


def new_session(user_agent: str) -> requests.Session:
    """Return a :class:`requests.Session` pre-configured with *user_agent*."""
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
    )
    return s


def is_allowed(url: str, allowed_domains: list[str]) -> bool:
    """Return *True* if *url*'s hostname matches any entry in *allowed_domains*."""
    if not allowed_domains:
        return True
    host = (urlparse(url).hostname or "").lower()
    for domain in allowed_domains:
        d = domain.lower().strip()
        if host == d or host.endswith(f".{d}"):
            return True
    return False


def extract_text(soup: BeautifulSoup, selector: str | None) -> str | None:
    """Return stripped text from the first element matching *selector*, or *None*."""
    if not selector:
        return None
    node = soup.select_one(selector)
    if not node:
        return None
    text = node.get_text(" ", strip=True)
    return text if text else None


def extract_event_links(
    session: requests.Session,
    source: SourceConfig,
    timeout: int,
    request_delay: float,
    max_listing_pages: int,
    max_links_per_source: int,
) -> list[str]:
    """Walk *source*'s listing pages and return candidate event URLs."""
    links: list[str] = []
    seen_pages: set[str] = set()
    seen_links: set[str] = set()

    for start_url in source.start_urls:
        page_url = start_url
        pages = 0

        while page_url and page_url not in seen_pages and pages < max_listing_pages:
            seen_pages.add(page_url)
            pages += 1

            try:
                resp = session.get(page_url, timeout=timeout)
                resp.raise_for_status()
            except Exception as exc:
                print(f"[{source.name}] listing fetch failed: {page_url} ({exc})")
                break

            soup = BeautifulSoup(resp.text, "html.parser")

            for a in soup.select(source.listing.event_link_selector):
                href = a.get("href")
                if not href:
                    continue
                url = urljoin(page_url, href)
                if not is_allowed(url, source.allowed_domains):
                    continue
                if url in seen_links:
                    continue
                seen_links.add(url)
                links.append(url)
                if len(links) >= max_links_per_source:
                    break

            if len(links) >= max_links_per_source:
                break

            next_url = None
            if source.listing.next_page_selector:
                next_node = soup.select_one(source.listing.next_page_selector)
                if next_node and next_node.get("href"):
                    next_url = urljoin(page_url, next_node["href"])

            page_url = next_url
            if request_delay > 0:
                time.sleep(request_delay)

    return links


def scrape_event_detail(
    session: requests.Session,
    source: SourceConfig,
    event_url: str,
    timeout: int,
) -> dict[str, Any] | None:
    """Fetch *event_url* and return a raw event dict, or *None* on failure."""
    try:
        resp = session.get(event_url, timeout=timeout)
        resp.raise_for_status()
    except Exception as exc:
        print(f"[{source.name}] detail fetch failed: {event_url} ({exc})")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    title = extract_text(soup, source.detail.title_selector)
    if not title:
        return None

    date_text = extract_text(soup, source.detail.date_selector)
    end_date_text = extract_text(soup, source.detail.end_date_selector)

    return {
        "event_id": None,
        "title": title,
        "description": extract_text(soup, source.detail.description_selector),
        "location": extract_text(soup, source.detail.location_selector),
        "start": _parse_datetime(date_text),
        "end": _parse_datetime(end_date_text),
        "url": event_url,
        "category": extract_text(soup, source.detail.category_selector),
        "source": source.name,
        "scraped_at": datetime.now(UTC).isoformat(),
    }


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------


def _parse_datetime(raw_value: str | None) -> str | None:
    """Best-effort parse of *raw_value* into an ISO-8601 string."""
    if not raw_value:
        return None
    candidate = raw_value.strip()
    if not candidate:
        return None

    import pandas as pd  # lazy — only needed at call time

    dt = pd.to_datetime(candidate, errors="coerce", utc=False)
    if pd.isna(dt):
        return candidate
    if hasattr(dt, "to_pydatetime"):
        return dt.to_pydatetime().isoformat()
    return str(dt)
