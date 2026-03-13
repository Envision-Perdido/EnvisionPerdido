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

import pandas as pd
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent
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

def load_and_consolidate():
    """Load all event data and consolidate."""
    
    all_events = []
    
    print("[Loading] Reading event CSVs...")
    
    # 1. Load raw data
    for csv_file in sorted(RAW_DIR.glob("*.csv")):
        try:
            df = pd.read_csv(csv_file)
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
            print(f"  Loaded: {csv_file.name} ({len(df)} events)")
            all_events.append(df)
        except Exception as e:
            print(f"  ERROR reading {csv_file.name}: {e}")
    
    # 3. Load labeled data
    for csv_file in sorted(LABELED_DIR.glob("*.csv")):
        try:
            df = pd.read_csv(csv_file)
            print(f"  Loaded: {csv_file.name} ({len(df)} events)")
            all_events.append(df)
        except Exception as e:
            print(f"  ERROR reading {csv_file.name}: {e}")
    
    if not all_events:
        print("[ERROR] No event CSVs found!")
        return None
    
    # Combine all
    combined = pd.concat(all_events, ignore_index=True, sort=False)
    print(f"\n[Consolidating] Total events before dedup: {len(combined)}")
    
    # Deduplicate
    combined["_event_key"] = combined.apply(normalize_event, axis=1)
    combined = combined.drop_duplicates(subset=["_event_key"], keep="first")
    combined = combined.drop(columns=["_event_key"])
    
    print(f"[Consolidating] Total events after dedup: {len(combined)}")
    
    # Count labeled
    labeled_count = combined["is_community_event"].notna().sum() if "is_community_event" in combined.columns else 0
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
            print("  python scripts/auto_label_and_train.py")
        elif labeled >= 300:
            print(f"~ Moderate data ({labeled} events). Would benefit from more labels.")
            print("  Consider manually reviewing ~50-100 uncertain events first,")
            print("  then retrain for better calibration.")
        else:
            print(f"✗ Too few labeled events ({labeled}). Need more manual labeling.")
            print("  1. Review pipeline outputs manually")
            print("  2. Mark community vs non-community")
            print("  3. Save with 'is_community_event' column")
            print("  4. Then retrain")
        print()
