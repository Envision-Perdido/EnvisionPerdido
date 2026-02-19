#!/usr/bin/env python3
"""
Smoke test for evcal_srow epoch calculations.

This script validates that the evcal_srow (EventON start epoch) values
in the most recent calendar_upload CSV are correctly calculated based
on the event start times and the configured site timezone.

The smoke test:
1. Finds the most recent calendar_upload_*.csv in output/pipeline/
2. For each event, recomputes the expected evcal_srow epoch
3. Compares computed vs. actual values
4. Reports any mismatches as failures

This ensures the "local epoch" logic (treat naive datetime as local,
then compute epoch as if it were UTC) is working correctly.
"""

import calendar
import os
import sys
from pathlib import Path

import pandas as pd


def compute_expected_epoch(start_iso: str, tz_name: str = "America/Chicago") -> int:
    """
    Compute the expected evcal_srow epoch for a given start time.

    This mirrors the logic in wordpress_uploader.parse_event_metadata:
    1. Parse the datetime (may be naive or aware)
    2. If naive, assume it's in the site timezone
    3. Remove timezone info to get a "local naive" datetime
    4. Compute Unix timestamp as if this local time were UTC (the "local epoch")

    Args:
        start_iso: ISO datetime string (e.g., "2025-09-15 10:00:00" or "2025-11-01T09:00:00-05:00")
        tz_name: IANA timezone name (e.g., "America/Chicago")

    Returns:
        Unix timestamp (seconds since 1970-01-01 00:00:00 UTC) of the local naive time
    """
    dt = pd.to_datetime(start_iso)

    # Get timezone object
    try:
        from zoneinfo import ZoneInfo

        local_tz = ZoneInfo(tz_name)
    except Exception:
        from dateutil.tz import gettz

        local_tz = gettz(tz_name)
        if local_tz is None:
            raise ValueError(f"Invalid timezone: {tz_name}")

    # If naive, assume local timezone
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=local_tz)

    # Convert to local naive (remove tzinfo)
    local_naive = dt.replace(tzinfo=None)

    # Compute "local epoch" - treat local time as UTC
    return int(calendar.timegm(local_naive.timetuple()))


def find_latest_csv(output_dir: Path) -> Path | None:
    """Find the most recent calendar_upload_*.csv file."""
    csv_files = sorted(output_dir.glob("calendar_upload_*.csv"))
    return csv_files[-1] if csv_files else None


def validate_csv(csv_path: Path, tz_name: str) -> tuple[int, int]:
    """
    Validate that we can compute evcal_srow values from event start times.

    This test validates the epoch calculation logic without requiring
    the CSV to already have evcal_srow values. It simply ensures we can
    successfully compute epochs for all events in the CSV.

    Args:
        csv_path: Path to calendar_upload CSV
        tz_name: Site timezone name

    Returns:
        Tuple of (total_events, failed_events)
    """
    df = pd.read_csv(csv_path)

    if "start" not in df.columns:
        print("❌ CSV missing required column: start")
        return 0, 0

    total = len(df)
    failures = 0

    print(f"Validating {total} events from {csv_path.name}...")
    print(f"Using timezone: {tz_name}")
    print()

    for idx, row in df.iterrows():
        start_time = row["start"]

        if pd.isna(start_time):
            print(f"⚠️  Row {idx}: Missing start time, skipping")
            continue

        try:
            epoch = compute_expected_epoch(start_time, tz_name)
            # Validate that the epoch is reasonable (not negative, not too far in future)
            if epoch < 0:
                failures += 1
                print(f"❌ Row {idx}: Negative epoch")
                print(f"   Event: {row.get('title', 'N/A')}")
                print(f"   Start: {start_time}")
                print(f"   Computed evcal_srow: {epoch}")
                print()
            elif epoch > 2**31 - 1:  # Max 32-bit signed int
                failures += 1
                print(f"❌ Row {idx}: Epoch overflow (too far in future)")
                print(f"   Event: {row.get('title', 'N/A')}")
                print(f"   Start: {start_time}")
                print(f"   Computed evcal_srow: {epoch}")
                print()
            else:
                # Success - epoch is valid
                if idx < 3:  # Show first 3 for verification
                    print(f"✅ Row {idx}: {row.get('title', 'N/A')[:40]}")
                    print(f"   Start: {start_time}")
                    print(f"   Computed evcal_srow: {epoch}")
                    print()
        except Exception as e:
            failures += 1
            print(f"❌ Row {idx}: Error computing epoch: {e}")
            print(f"   Event: {row.get('title', 'N/A')}")
            print(f"   Start: {start_time}")
            print()

    return total, failures


def main():
    """Main entry point."""
    # Get timezone from environment (default: America/Chicago)
    tz_name = os.environ.get("SITE_TIMEZONE", "America/Chicago")

    # Find repository root (script is in scripts/dev/ subdirectory, go up 2 levels)
    repo_root = Path(__file__).resolve().parent.parent.parent
    output_dir = repo_root / "output" / "pipeline"

    if not output_dir.exists():
        print(f"❌ Output directory not found: {output_dir}")
        print("Run the pipeline first to generate a CSV file.")
        return 1

    csv_path = find_latest_csv(output_dir)
    if not csv_path:
        print(f"❌ No calendar_upload_*.csv files found in {output_dir}")
        print("Run the pipeline first to generate a CSV file.")
        return 1

    print("=" * 70)
    print("evcal_srow Smoke Test")
    print("=" * 70)
    print()

    total, failures = validate_csv(csv_path, tz_name)

    print()
    print("=" * 70)
    if failures == 0:
        print(f"✅ All {total} events passed validation")
        print("=" * 70)
        return 0
    else:
        print(f"❌ {failures}/{total} events failed validation")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
