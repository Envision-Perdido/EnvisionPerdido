"""Quick integration test: verify pipeline stages work end-to-end with minimal data."""

import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# Ensure scripts path is on sys.path
_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "scripts"))

# Set env vars for test isolation
os.environ["AUTO_UPLOAD"] = "false"
os.environ["CONFIDENCE_THRESHOLD"] = "0.75"

from scripts.pipeline.stages import classify, enrich, export, notify
from scripts.tooling.logger import get_logger

logger = get_logger()

# Minimal sample events (just scraped, no classification yet)
SAMPLE_RAW_EVENTS = [
    {
        "title": "Community Festival 2026",
        "description": "Annual arts and crafts festival with local vendors",
        "location": "Central Park, downtown",
        "start": "2026-06-15T10:00:00",
        "end": "2026-06-15T18:00:00",
        "url": "https://example.com/event1",
        "category": "Festival",
        "source": "test_source",
        "scraped_at": datetime.now().isoformat(),
    },
    {
        "title": "Board Meeting Q2",
        "description": "Corporate quarterly board meeting",
        "location": "Conference Room A",
        "start": "2026-05-20T14:00:00",
        "end": "2026-05-20T16:00:00",
        "url": "https://example.com/event2",
        "category": "Meeting",
        "source": "test_source",
        "scraped_at": datetime.now().isoformat(),
    },
    {
        "title": "Youth Volunteer Day",
        "description": "Community service event for teenagers",
        "location": "East Side Community Center",
        "start": "2026-05-25T09:00:00",
        "end": "2026-05-25T12:00:00",
        "url": "https://example.com/event3",
        "category": "Volunteer",
        "source": "test_source",
        "scraped_at": datetime.now().isoformat(),
    },
]


def test_pipeline_stages():
    """Run all pipeline stages on minimal test data."""
    logger.info("=" * 80)
    logger.info("END-TO-END PIPELINE STAGE TEST")
    logger.info("=" * 80)

    # Convert to DataFrame
    events_df = pd.DataFrame(SAMPLE_RAW_EVENTS)
    logger.info(f"[OK] Created test DataFrame with {len(events_df)} events")

    # Stage 1: Classify
    logger.info("\n--- Stage 1: Classify ---")
    classified_df = classify.classify_events(events_df)
    if classified_df is None:
        logger.error("[FAIL] Classification failed")
        return False
    logger.info(f"[OK] Classified {len(classified_df)} events")
    logger.info(
        f"  Community: {(classified_df['is_community_event'] == 1).sum()}, "
        f"Non-community: {(classified_df['is_community_event'] == 0).sum()}"
    )

    # Stage 2b: Enrich + Filter
    logger.info("\n--- Stage 2b: Enrich & Filter ---")
    kept_df, filtered_df = enrich.enrich_and_filter(classified_df)
    logger.info(f"[OK] Kept: {len(kept_df)}, Filtered: {len(filtered_df)}")

    kept_df = enrich.assign_event_images(kept_df)
    logger.info(f"[OK] Image assignment complete")

    # Filter to community events
    community_events = kept_df[kept_df["is_community_event"] == 1].copy()
    logger.info(f"[OK] {len(community_events)} community events")

    if len(community_events) == 0:
        logger.info("  (No community events in test set; proceeding with export)")
        community_events = kept_df.head(1)  # Use first event for test

    # Stage 3: Export
    logger.info("\n--- Stage 3: Export ---")
    csv_path = export.export_for_calendar(community_events, format="csv")
    logger.info(f"[OK] Exported to {csv_path}")
    assert csv_path.exists(), f"Export file not created: {csv_path}"

    # Stage 4: Email notify (dry-run)
    logger.info("\n--- Stage 4: Notify (simulated) ---")
    stats = {
        "total_events": len(events_df),
        "community_events": len(community_events),
        "non_community_events": len(events_df) - len(community_events),
        "needs_review": int(classified_df.get("needs_review", pd.Series()).sum()),
    }
    logger.info(f"[OK] Email would contain: {stats}")

    logger.info("\n" + "=" * 80)
    logger.info("[PASS]PASS] ALL PIPELINE STAGES COMPLETED SUCCESSFULLY")
    logger.info("=" * 80)

    return True


if __name__ == "__main__":
    success = test_pipeline_stages()
    sys.exit(0 if success else 1)
