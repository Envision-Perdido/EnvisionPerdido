"""Orchestration, normalization, export, and CLI for the multi-calendar scraper.

This is the thinnest meaningful layer: it wires together the fetch and model
layers and owns the only concern that didn't fit elsewhere — weak labeling
(a lightweight pre-classification heuristic used to seed the training
labelset, not a real ML step).
"""

from __future__ import annotations

import argparse
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from scripts.scrapers.multi_calendar.fetch import (
    extract_event_links,
    new_session,
    scrape_event_detail,
)
from scripts.scrapers.multi_calendar.models import (
    COMMUNITY_KW,
    DEFAULT_CONFIG,
    NONCOMM_KW,
    SourceConfig,
    load_config,
)


# ---------------------------------------------------------------------------
# Normalization / deduplication
# ---------------------------------------------------------------------------


def normalize_and_dedupe(records: list[dict[str, Any]]) -> pd.DataFrame:
    """Deduplicate *records* and ensure all expected columns are present."""
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
        + df["title"].fillna("").str.lower().str.replace(r"\s+", "-", regex=True)
        + "::"
        + df["start"].fillna("").astype(str)
    )
    df.loc[missing_id, "event_id"] = generated_ids[missing_id]

    return df


# ---------------------------------------------------------------------------
# Weak labeling (heuristic pre-classification for labelset seeding)
# ---------------------------------------------------------------------------


def weak_label(df: pd.DataFrame) -> pd.DataFrame:
    """Assign ``weak_label`` (1=community, 0=non-community, NA=unknown)."""
    text = (df["title"].fillna("") + " " + df["description"].fillna("")).str.lower()
    df["weak_label"] = pd.NA
    df.loc[text.str.contains(COMMUNITY_KW, regex=True, na=False), "weak_label"] = 1
    df.loc[text.str.contains(NONCOMM_KW, regex=True, na=False), "weak_label"] = 0
    df["label"] = ""
    return df


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


def save_outputs(
    df: pd.DataFrame, output_dir: Path, label_dir: Path
) -> tuple[Path, Path, Path]:
    """Write CSV, JSON, and labelset CSV to *output_dir* / *label_dir*."""
    output_dir.mkdir(parents=True, exist_ok=True)
    label_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = output_dir / f"community_multi_source_events_{ts}.csv"
    json_path = output_dir / f"community_multi_source_events_{ts}.json"
    lbl_path = label_dir / f"community_multi_source_labelset_{ts}.csv"

    df.to_csv(csv_path, index=False)
    df.to_json(json_path, orient="records", indent=2)

    label_cols = [
        "event_id",
        "title",
        "description",
        "start",
        "location",
        "url",
        "source",
        "weak_label",
        "label",
    ]
    labelset = df[[c for c in label_cols if c in df.columns]].copy()
    labelset.to_csv(lbl_path, index=False)

    return csv_path, json_path, lbl_path


# ---------------------------------------------------------------------------
# Main scrape orchestrator
# ---------------------------------------------------------------------------


def scrape_sources(
    sources: list[SourceConfig],
    target_events: int,
    max_listing_pages: int,
    max_links_per_source: int,
    timeout: int,
    request_delay: float,
    user_agent: str,
) -> pd.DataFrame:
    """Scrape all enabled *sources* and return a clean, labeled DataFrame."""
    session = new_session(user_agent=user_agent)
    all_records: list[dict[str, Any]] = []

    for source in sources:
        if not source.enabled:
            print(f"[{source.name}] skipped (enabled=false)")
            continue
        print(f"\n[{source.name}] collecting event links...")
        links = extract_event_links(
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
            event = scrape_event_detail(session, source, link, timeout)
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

    df = normalize_and_dedupe(all_records)
    df = weak_label(df)
    return df


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


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

    sources = load_config(args.config)
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

    csv_path, json_path, lbl_path = save_outputs(df, args.output_dir, args.label_dir)

    print("\nDone.")
    print(f"Consolidated events: {len(df)}")
    print(f"CSV:      {csv_path}")
    print(f"JSON:     {json_path}")
    print(f"Labelset: {lbl_path}")

    community_guess = int((df["weak_label"] == 1).sum())
    noncommunity_guess = int((df["weak_label"] == 0).sum())
    unlabeled_guess = len(df) - community_guess - noncommunity_guess

    print("\nWeak-label distribution:")
    print(f"  community-like:     {community_guess}")
    print(f"  non-community-like: {noncommunity_guess}")
    print(f"  unknown:            {unlabeled_guess}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
