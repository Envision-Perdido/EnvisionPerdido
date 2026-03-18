#!/usr/bin/env python3
"""
Consolidate all event data from Sept 2025 onwards for model retraining.

This script:
1. Loads all available event CSVs (raw, processed, labeled)
2. Deduplicates by title + date + location
3. Merges with existing labels
4. Creates a consolidated training dataset
5. Reports statistics for retraining decision
"""

from pathlib import Path

import pandas as pd

from scripts.ml.training_support import ensure_source_column

BASE_DIR = Path(__file__).parent.parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
LABELED_DIR = BASE_DIR / "data" / "labeled"
OUTPUT_FILE = BASE_DIR / "data" / "processed" / "consolidated_training_data.csv"


def normalize_event(row):
    """Normalize event for deduplication."""
    title = str(row.get("title", "")).strip().lower()
    start = str(row.get("start", "")).strip()
    location = str(row.get("location", "")).strip().lower()
    return f"{title}|{start}|{location}"


def has_authoritative_label(row) -> int:
    """Return 1 when row has an explicit 0/1 label, else 0."""
    label = str(row.get("label", "")).strip().replace(".0", "")
    if label in {"0", "1"}:
        return 1

    legacy = str(row.get("is_community_event", "")).strip().replace(".0", "")
    return 1 if legacy in {"0", "1"} else 0


def load_and_consolidate():
    """Load all event data and consolidate."""

    all_events = []

    print("[Loading] Reading event CSVs...")

    # 1. Load raw data
    for csv_file in sorted(RAW_DIR.glob("*.csv")):
        try:
            df = pd.read_csv(csv_file)
            df["_source_file"] = csv_file.name
            print(f"  Loaded: {csv_file.name} ({len(df)} events)")
            all_events.append(df)
        except Exception as e:
            print(f"  ERROR reading {csv_file.name}: {e}")

    # 2. Load processed data
    for csv_file in sorted(PROCESSED_DIR.glob("*.csv")):
        if csv_file.name == "consolidated_training_data.csv":
            continue  # Skip output file if it exists
        try:
            df = pd.read_csv(csv_file)
            df["_source_file"] = csv_file.name
            print(f"  Loaded: {csv_file.name} ({len(df)} events)")
            all_events.append(df)
        except Exception as e:
            print(f"  ERROR reading {csv_file.name}: {e}")

    # 3. Load labeled data
    for csv_file in sorted(LABELED_DIR.glob("*.csv")):
        try:
            df = pd.read_csv(csv_file)
            df["_source_file"] = csv_file.name
            print(f"  Loaded: {csv_file.name} ({len(df)} events)")
            all_events.append(df)
        except Exception as e:
            print(f"  ERROR reading {csv_file.name}: {e}")

    if not all_events:
        print("[ERROR] No event CSVs found!")
        return None

    # Combine all
    combined = pd.concat(all_events, ignore_index=True, sort=False)
    combined = ensure_source_column(combined)
    print(f"\n[Consolidating] Total events before dedup: {len(combined)}")

    # Deduplicate. Keep rows with authoritative labels first so labels are not
    # lost when raw/unlabeled duplicates exist.
    combined["_has_label"] = combined.apply(has_authoritative_label, axis=1)
    combined = combined.sort_values("_has_label", ascending=False)
    combined["_event_key"] = combined.apply(normalize_event, axis=1)
    combined = combined.drop_duplicates(subset=["_event_key"], keep="first")
    combined = combined.drop(columns=["_event_key", "_has_label"])

    print(f"[Consolidating] Total events after dedup: {len(combined)}")

    # Count labeled (support both newer label and legacy is_community_event fields)
    if "label" in combined.columns:
        labels = combined["label"].astype(str).str.replace(".0", "", regex=False)
        labeled_count = labels.isin(["0", "1"]).sum()
    elif "is_community_event" in combined.columns:
        labels = combined["is_community_event"].astype(str).str.replace(".0", "", regex=False)
        labeled_count = labels.isin(["0", "1"]).sum()
    else:
        labeled_count = 0
    unlabeled_count = len(combined) - labeled_count

    print(f"[Status] Labeled events: {labeled_count}")
    print(f"[Status] Unlabeled events: {unlabeled_count}")

    # Save consolidated dataset
    combined.to_csv(OUTPUT_FILE, index=False)
    print(f"\n[Saved] Consolidated dataset: {OUTPUT_FILE}")
    print(f"        Total events: {len(combined)}")

    return combined, labeled_count, unlabeled_count


if __name__ == "__main__":
    print("=" * 80)
    print("CONSOLIDATE TRAINING DATA")
    print("=" * 80)
    print()

    result = load_and_consolidate()

    if result:
        df, labeled, unlabeled = result
        print()
        print("=" * 80)
        print("NEXT STEPS:")
        print("=" * 80)
        print(f"\n1. You now have {len(df)} total events consolidated")
        print(f"2. {labeled} are labeled for training")
        print(f"3. {unlabeled} events still need manual review")
        print()
        print("RECOMMENDED ACTION:")
        print("-" * 80)
        if labeled >= 500:
            print(f"✓ Sufficient data! Retrain model with {labeled} labeled events:")
            print(
                "  python scripts/ml/svm_train_from_file.py --input "
                "data/processed/consolidated_training_data.csv "
                "--model-path data/artifacts/event_classifier_model.pkl"
            )
        elif labeled >= 300:
            print(f"~ Moderate data ({labeled} events). Would benefit from more labels.")
            print("  Consider manually reviewing ~50-100 uncertain events first,")
            print("  then retrain for better calibration.")
        else:
            print(f"✗ Too few labeled events ({labeled}). Need more manual labeling.")
            print("  1. Review pipeline outputs manually")
            print("  2. Mark community vs non-community")
            print("  3. Save with 'label' column (0 or 1)")
            print("  4. Then retrain")
        print()
