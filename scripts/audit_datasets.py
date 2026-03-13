#!/usr/bin/env python3
"""Audit available datasets for consolidation."""

from pathlib import Path

import pandas as pd

base = Path(__file__).parent.parent

print("=" * 80)
print("DATA AUDIT FOR CONSOLIDATION")
print("=" * 80)

print("\nRAW DATA FILES:")
for f in sorted(base.glob("data/raw/*.csv")):
    df = pd.read_csv(f)
    print(f"  {f.name:40s} {len(df):5d} rows")

print("\nPROCESSED DATA FILES:")
for f in sorted(base.glob("data/processed/*.csv")):
    df = pd.read_csv(f)
    has_label = "is_community_event" in df.columns
    label_info = " [labeled]" if has_label else ""
    print(f"  {f.name:40s} {len(df):5d} rows{label_info}")

print("\nLABELED DATA FILES:")
for f in sorted(base.glob("data/labeled/*.csv")):
    df = pd.read_csv(f)
    has_label = "is_community_event" in df.columns
    label_info = " [labeled]" if has_label else ""
    print(f"  {f.name:40s} {len(df):5d} rows{label_info}")

print("\n" + "=" * 80)
print("RECOMMENDATION:")
print("=" * 80)

# Load key files
try:
    combined = pd.read_csv(base / "data/processed/combined_events_auto.csv")
    labeled = pd.read_csv(base / "data/labeled/perdido_events_2025_labeled.csv")

    print("\nCurrent training data:")
    print(f"  combined_events_auto.csv: {len(combined)} events")
    print(f"  perdido_events_2025_labeled.csv: {len(labeled)} labeled events")

    # Check if we have additional events to consolidate
    raw_2025 = pd.read_csv(base / "data/raw/perdido_events_2025.csv")
    print("\nAdditional data available:")
    print(f"  perdido_events_2025.csv: {len(raw_2025)} events (potentially more data)")

    total_potential = len(combined) + len(raw_2025) - len(labeled)
    print("\nConsolidation opportunity:")
    print(f"  Total potential events: ~{total_potential} (before dedup)")
    print("\nTo improve model:")
    print("  1. Run pipeline monthly and save to data/raw/")
    print("  2. Consolidate all CSVs from Sept-Mar into one dataset")
    print("  3. Manually label ~50-100 uncertain events (confidence 0.4-0.6)")
    print("  4. Retrain with 600+ diverse events for better calibration")

except Exception as e:
    print(f"Error reading files: {e}")

print()
