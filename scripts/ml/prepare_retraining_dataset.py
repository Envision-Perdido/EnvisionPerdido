#!/usr/bin/env python3
"""
Prepare canonical retraining datasets from multi-calendar scraper outputs.

This script produces two artifacts:
1) A review queue for manual labeling (unlabeled rows only)
2) A canonical labeled training dataset for svm_train_from_file.py

It standardizes common column names across scraper/export variants,
deduplicates records, and prioritizes rows that are most useful to review.
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).parent.parent.parent
DEFAULT_LABELED_DIR = BASE_DIR / "data" / "labeled"
DEFAULT_OUTPUT_DIR = BASE_DIR / "data" / "processed"


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Map common aliases to canonical column names."""
    alias_map = {
        "start_time": "start",
        "end_time": "end",
        "name": "title",
        "summary": "description",
        "venue": "location",
    }

    out = df.copy()
    for old, new in alias_map.items():
        if old in out.columns and new not in out.columns:
            out[new] = out[old]

    # Promote is_community_event into label if label is missing/blank.
    if "label" not in out.columns:
        out["label"] = ""

    if "is_community_event" in out.columns:
        mask_blank_label = out["label"].astype(str).str.strip().eq("")
        out.loc[mask_blank_label, "label"] = out.loc[mask_blank_label, "is_community_event"]

    for col in ["event_id", "title", "description", "location", "start", "end", "url", "category", "source", "weak_label", "label"]:
        if col not in out.columns:
            out[col] = ""

    out["title"] = out["title"].astype(str)
    out["description"] = out["description"].astype(str)
    out["location"] = out["location"].astype(str)
    out["start"] = out["start"].astype(str)
    out["url"] = out["url"].astype(str)
    out["source"] = out["source"].astype(str)

    return out


def _dedupe(df: pd.DataFrame) -> pd.DataFrame:
    """Deduplicate by URL first, then fallback to title/start/source key."""
    out = df.copy()
    out["_dedupe_key"] = out["url"].fillna("").astype(str).str.strip().str.lower()

    missing_url = out["_dedupe_key"].eq("")
    fallback = (
        out["title"].fillna("").str.lower().str.strip()
        + "|"
        + out["start"].fillna("").astype(str).str.strip()
        + "|"
        + out["source"].fillna("").astype(str).str.lower().str.strip()
    )
    out.loc[missing_url, "_dedupe_key"] = fallback[missing_url]

    out = out.drop_duplicates(subset=["_dedupe_key"], keep="first").drop(columns=["_dedupe_key"])
    return out


def _coerce_label(series: pd.Series) -> pd.Series:
    """Normalize labels to integer 0/1 when possible; blank otherwise."""
    values = series.astype(str).str.strip().str.replace(".0", "", regex=False)
    return values.where(values.isin(["0", "1"]), "")


def _coerce_weak_label(series: pd.Series) -> pd.Series:
    values = series.astype(str).str.strip().str.replace(".0", "", regex=False)
    return values.where(values.isin(["0", "1"]), "")


def _assign_review_priority(df: pd.DataFrame) -> pd.Series:
    """
    Priority score for manual review:
    1 = highest priority (unlabeled and no weak label)
    2 = unlabeled with weak label
    3 = already labeled
    """
    labeled = df["label"].astype(str).isin(["0", "1"])
    has_weak = df["weak_label"].astype(str).isin(["0", "1"])

    pr = pd.Series(3, index=df.index, dtype="int64")
    pr.loc[~labeled & has_weak] = 2
    pr.loc[~labeled & ~has_weak] = 1
    return pr


def _load_inputs(files: list[Path]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for path in files:
        try:
            df = pd.read_csv(path)
            df["_source_file"] = path.name
            frames.append(df)
            print(f"Loaded: {path} ({len(df)} rows)")
        except Exception as exc:
            print(f"Skipped: {path} ({exc})")

    if not frames:
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True, sort=False)
    return combined


def _ensure_event_id(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    missing = out["event_id"].astype(str).str.strip().eq("")
    generated = (
        out["source"].fillna("source")
        + "::"
        + out["title"].fillna("").str.lower().str.replace(r"\s+", "-", regex=True)
        + "::"
        + out["start"].fillna("").astype(str)
    )
    out.loc[missing, "event_id"] = generated[missing]
    return out


def build_artifacts(input_files: list[Path], output_dir: Path, review_limit: int | None) -> tuple[Path, Path, int, int, int]:
    combined = _load_inputs(input_files)
    if combined.empty:
        raise SystemExit("No rows loaded from input files")

    normalized = _normalize_columns(combined)
    normalized = _dedupe(normalized)
    normalized = _ensure_event_id(normalized)

    normalized["label"] = _coerce_label(normalized["label"])
    normalized["weak_label"] = _coerce_weak_label(normalized["weak_label"])
    normalized["review_priority"] = _assign_review_priority(normalized)

    # Canonical labeled training data (authoritative labels only)
    labeled = normalized[normalized["label"].isin(["0", "1"])].copy()
    labeled["label"] = labeled["label"].astype(int)

    labeled = labeled[
        [
            "event_id",
            "title",
            "description",
            "location",
            "start",
            "end",
            "url",
            "category",
            "source",
            "label",
            "weak_label",
        ]
    ]

    # Review queue (unlabeled rows), highest-priority first.
    review = normalized[~normalized["label"].isin(["0", "1"])].copy()
    review = review.sort_values(["review_priority", "source", "start", "title"])
    if review_limit is not None and review_limit > 0:
        review = review.head(review_limit)

    review = review[
        [
            "event_id",
            "title",
            "description",
            "location",
            "start",
            "url",
            "source",
            "weak_label",
            "review_priority",
            "label",
            "_source_file",
        ]
    ]

    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    review_path = output_dir / f"review_queue_{ts}.csv"
    training_path = output_dir / f"canonical_labeled_training_{ts}.csv"

    review.to_csv(review_path, index=False)
    labeled.to_csv(training_path, index=False)

    return review_path, training_path, len(normalized), len(review), len(labeled)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare a manual-review queue and canonical labeled training dataset "
            "from multi-calendar scraper outputs"
        )
    )
    parser.add_argument(
        "--inputs",
        nargs="*",
        type=Path,
        help=(
            "Optional explicit input files. If omitted, uses "
            "data/labeled/community_multi_source_labelset_*.csv"
        ),
    )
    parser.add_argument(
        "--input-glob",
        default="community_multi_source_labelset_*.csv",
        help="Glob used in data/labeled when --inputs is not provided",
    )
    parser.add_argument(
        "--labeled-dir",
        type=Path,
        default=DEFAULT_LABELED_DIR,
        help="Directory for discovered input labelset files",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for generated review/training artifacts",
    )
    parser.add_argument(
        "--review-limit",
        type=int,
        default=0,
        help="Optional max rows for review queue (0 means no limit)",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    if args.inputs:
        input_files = [p.expanduser().resolve() for p in args.inputs]
    else:
        labeled_dir = args.labeled_dir.expanduser().resolve()
        input_files = sorted(labeled_dir.glob(args.input_glob))
        if not input_files:
            print(
                "No files matched input glob "
                f"'{args.input_glob}'. Falling back to all CSV files in {labeled_dir}."
            )
            input_files = sorted(labeled_dir.glob("*.csv"))

    if not input_files:
        print("No input files found. Provide --inputs or adjust --input-glob.")
        return 1

    review_limit = args.review_limit if args.review_limit and args.review_limit > 0 else None
    review_path, training_path, total_rows, review_rows, labeled_rows = build_artifacts(
        input_files=input_files,
        output_dir=args.output_dir.expanduser().resolve(),
        review_limit=review_limit,
    )

    print("\nPrepared retraining artifacts")
    print(f"  total normalized rows: {total_rows}")
    print(f"  review queue rows: {review_rows}")
    print(f"  labeled training rows: {labeled_rows}")
    print(f"  review queue: {review_path}")
    print(f"  labeled training: {training_path}")

    if labeled_rows == 0:
        print("\nWarning: no authoritative labels found yet. Label some review rows first.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())