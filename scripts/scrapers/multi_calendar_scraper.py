#!/usr/bin/env python3
"""
Multi-source community calendar scraper using BeautifulSoup.

Goal:
- Crawl multiple calendar listing pages
- Extract event detail links
- Scrape normalized event fields from detail pages
- Consolidate into one DataFrame-ready dataset for labeling

Outputs:
- data/raw/community_multi_source_events_<timestamp>.csv
- data/raw/community_multi_source_events_<timestamp>.json
- data/labeled/community_multi_source_labelset_<timestamp>.csv

Usage:
    python scripts/multi_calendar_scraper.py \
        --config data/community_calendar_sources.json \
        --target-events 10000
"""

from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup

DEFAULT_CONFIG = Path("data/community_calendar_sources.json")

COMMUNITY_KW = (
    r"(festival|parade|market|farmers|community|workshop|class|volunteer|fundraiser|"
    r"family|youth|meetup|open house|concert|library|park|veterans|food truck|gallery|"
    r"art\\b|craft\\b|charity|cleanup|nonprofit|school)"
)

NONCOMM_KW = (
    r"(board meeting|committee|sponsor|leads? group|b2b|webinar|"
    r"business networking|members only)"
)


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


class ScraperError(Exception):
    pass


def _load_config(path: Path) -> list[SourceConfig]:
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


def _new_session(user_agent: str) -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
    )
    return s


def _is_allowed(url: str, allowed_domains: list[str]) -> bool:
    if not allowed_domains:
        return True
    host = (urlparse(url).hostname or "").lower()
    for domain in allowed_domains:
        d = domain.lower().strip()
        if host == d or host.endswith(f".{d}"):
            return True
    return False


def _extract_text(soup: BeautifulSoup, selector: str | None) -> str | None:
    if not selector:
        return None
    node = soup.select_one(selector)
    if not node:
        return None
    text = node.get_text(" ", strip=True)
    return text if text else None


def _extract_event_links(
    session: requests.Session,
    source: SourceConfig,
    timeout: int,
    request_delay: float,
    max_listing_pages: int,
    max_links_per_source: int,
) -> list[str]:
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
                if not _is_allowed(url, source.allowed_domains):
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


def _parse_datetime(raw_value: str | None) -> str | None:
    if not raw_value:
        return None

    candidate = raw_value.strip()
    if not candidate:
        return None

    # Prefer pandas parser for broad date support.
    dt = pd.to_datetime(candidate, errors="coerce", utc=False)
    if pd.isna(dt):
        return candidate

    if hasattr(dt, "to_pydatetime"):
        return dt.to_pydatetime().isoformat()
    return str(dt)


def _scrape_event_detail(
    session: requests.Session,
    source: SourceConfig,
    event_url: str,
    timeout: int,
) -> dict[str, Any] | None:
    try:
        resp = session.get(event_url, timeout=timeout)
        resp.raise_for_status()
    except Exception as exc:
        print(f"[{source.name}] detail fetch failed: {event_url} ({exc})")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    title = _extract_text(soup, source.detail.title_selector)
    if not title:
        return None

    date_text = _extract_text(soup, source.detail.date_selector)
    end_date_text = _extract_text(soup, source.detail.end_date_selector)

    event = {
        "event_id": None,
        "title": title,
        "description": _extract_text(soup, source.detail.description_selector),
        "location": _extract_text(soup, source.detail.location_selector),
        "start": _parse_datetime(date_text),
        "end": _parse_datetime(end_date_text),
        "url": event_url,
        "category": _extract_text(soup, source.detail.category_selector),
        "source": source.name,
        "scraped_at": datetime.now(UTC).isoformat(),
    }

    return event


def _weak_label(df: pd.DataFrame) -> pd.DataFrame:
    text = (df["title"].fillna("") + " " + df["description"].fillna("")).str.lower()
    df["weak_label"] = pd.NA
    df.loc[text.str.contains(COMMUNITY_KW, regex=True, na=False), "weak_label"] = 1
    df.loc[text.str.contains(NONCOMM_KW, regex=True, na=False), "weak_label"] = 0
    df["label"] = ""
    return df


def _normalize_and_dedupe(records: list[dict[str, Any]]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame(
            columns=[
                "event_id",
                "title",
                "description",
                "location",
                "start",
                "end",
                "url",
                "category",
                "source",
                "scraped_at",
            ]
        )

    df = pd.DataFrame(records)
    for c in ["title", "description", "location", "start", "url", "source"]:
        if c not in df.columns:
            df[c] = ""

    # Prefer URL dedupe, then fallback to title+start+source signature.
    df["_dedupe_key"] = df["url"].fillna("")
    missing_url = df["_dedupe_key"].eq("")
    fallback = (
        df["title"].fillna("").str.lower().str.strip()
        + "|"
        + df["start"].fillna("").astype(str).str.strip()
        + "|"
        + df["source"].fillna("").astype(str).str.strip()
    )
    df.loc[missing_url, "_dedupe_key"] = fallback[missing_url]

    df = df.drop_duplicates(subset=["_dedupe_key"]).copy()
    df = df.drop(columns=["_dedupe_key"])

    if "event_id" not in df.columns:
        df["event_id"] = None

    missing_id = df["event_id"].isna() | df["event_id"].eq("")
    generated_ids = (
        df["source"].fillna("source")
        + "::"
        + df["title"].fillna("").str.lower().str.replace(r"\\s+", "-", regex=True)
        + "::"
        + df["start"].fillna("").astype(str)
    )
    df.loc[missing_id, "event_id"] = generated_ids[missing_id]

    return df


def scrape_sources(
    sources: list[SourceConfig],
    target_events: int,
    max_listing_pages: int,
    max_links_per_source: int,
    timeout: int,
    request_delay: float,
    user_agent: str,
) -> pd.DataFrame:
    session = _new_session(user_agent=user_agent)
    all_records: list[dict[str, Any]] = []

    for source in sources:
        if not source.enabled:
            print(f"[{source.name}] skipped (enabled=false)")
            continue
        print(f"\\n[{source.name}] collecting event links...")
        links = _extract_event_links(
            session=session,
            source=source,
            timeout=timeout,
            request_delay=request_delay,
            max_listing_pages=max_listing_pages,
            max_links_per_source=max_links_per_source,
        )
        print(f"[{source.name}] found {len(links)} candidate event URLs")

        source_count = 0
        for i, link in enumerate(links, 1):
            event = _scrape_event_detail(session, source, link, timeout)
            if event:
                all_records.append(event)
                source_count += 1

            if request_delay > 0:
                time.sleep(request_delay)

            if len(all_records) >= target_events:
                print(f"Reached target event count: {target_events}")
                break

            if i % 50 == 0:
                print(
                    f"[{source.name}] progress: {i}/{len(links)} links checked, "
                    f"{source_count} events extracted"
                )

        print(f"[{source.name}] extracted {source_count} events")

        if len(all_records) >= target_events:
            break

    df = _normalize_and_dedupe(all_records)
    df = _weak_label(df)
    return df


def _save_outputs(df: pd.DataFrame, output_dir: Path, label_dir: Path) -> tuple[Path, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    label_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = output_dir / f"community_multi_source_events_{ts}.csv"
    json_path = output_dir / f"community_multi_source_events_{ts}.json"
    lbl_path = label_dir / f"community_multi_source_labelset_{ts}.csv"

    df.to_csv(csv_path, index=False)
    df.to_json(json_path, orient="records", indent=2)

    label_cols = ["event_id", "title", "description", "start", "location", "url", "source", "weak_label", "label"]
    labelset = df[[c for c in label_cols if c in df.columns]].copy()
    labelset.to_csv(lbl_path, index=False)

    return csv_path, json_path, lbl_path


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Scrape multiple community calendars with BeautifulSoup and consolidate "
            "events into a training-friendly dataset"
        )
    )
    p.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    p.add_argument("--target-events", type=int, default=10000)
    p.add_argument("--max-listing-pages", type=int, default=30)
    p.add_argument("--max-links-per-source", type=int, default=5000)
    p.add_argument("--timeout", type=int, default=25)
    p.add_argument("--request-delay", type=float, default=0.2)
    p.add_argument(
        "--user-agent",
        default=(
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
    )
    p.add_argument("--output-dir", type=Path, default=Path("data/raw"))
    p.add_argument("--label-dir", type=Path, default=Path("data/labeled"))
    return p


def main() -> int:
    args = build_parser().parse_args()

    sources = _load_config(args.config)
    print(f"Loaded {len(sources)} calendar source definitions from {args.config}")

    df = scrape_sources(
        sources=sources,
        target_events=args.target_events,
        max_listing_pages=args.max_listing_pages,
        max_links_per_source=args.max_links_per_source,
        timeout=args.timeout,
        request_delay=args.request_delay,
        user_agent=args.user_agent,
    )

    if df.empty:
        print("No events scraped. Check selectors and source URLs in your config.")
        return 1

    csv_path, json_path, lbl_path = _save_outputs(df, args.output_dir, args.label_dir)

    print("\nDone.")
    print(f"Consolidated events: {len(df)}")
    print(f"CSV: {csv_path}")
    print(f"JSON: {json_path}")
    print(f"Labelset: {lbl_path}")

    community_guess = int((df["weak_label"] == 1).sum())
    noncommunity_guess = int((df["weak_label"] == 0).sum())
    unlabeled_guess = len(df) - community_guess - noncommunity_guess

    print("\nWeak-label distribution:")
    print(f"  community-like: {community_guess}")
    print(f"  non-community-like: {noncommunity_guess}")
    print(f"  unknown: {unlabeled_guess}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
