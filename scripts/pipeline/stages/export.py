"""Stage 3 — Export classified events to the external handoff bundle."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from scripts.pipeline.external_handoff_export import export_handoff_bundle
from scripts.tooling.logger import get_logger

logger = get_logger(__name__)

_BASE_DIR = Path(__file__).parent.parent.parent.parent  # …/EnvisionPerdido
OUTPUT_DIR = _BASE_DIR / "output" / "pipeline"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def export_external_handoff(community_events_df: pd.DataFrame) -> Path:
    """Export community events to the external handoff contract bundle."""
    logger.info(f"Exporting {len(community_events_df)} events to external handoff bundle...")

    image_count = int(
        community_events_df.get("image_url", pd.Series())
        .apply(lambda x: pd.notna(x))
        .sum()
    )
    logger.info(f"Events with images: {image_count}/{len(community_events_df)}")

    df = community_events_df.copy()
    path = export_handoff_bundle(df, OUTPUT_DIR)
    logger.info(f"External handoff export saved to {path}")
    return path


def export_for_calendar(
    community_events_df: pd.DataFrame,
    format: str = "csv",  # noqa: A002
) -> Path | None:
    """Backward-compatible alias for callers still using the old export name."""
    if format != "csv":
        logger.warning("Only external handoff JSON export is supported in the main workflow.")
    return export_external_handoff(community_events_df)
