"""Stage 3 — Export classified events to disk (CSV, JSON, iCal)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from scripts.tooling.logger import get_logger

logger = get_logger(__name__)

_BASE_DIR = Path(__file__).parent.parent.parent.parent  # …/EnvisionPerdido
OUTPUT_DIR = _BASE_DIR / "output" / "pipeline"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def export_for_calendar(
    community_events_df: pd.DataFrame,
    format: str = "csv",  # noqa: A002
) -> Path | None:
    """Export community events to a file ready for calendar upload.

    Args:
        community_events_df: Enriched community events DataFrame.
        format: ``'csv'`` (default), ``'json'``, or ``'ical'`` (not yet
            implemented).

    Returns:
        Path to the output file, or ``None`` on error / unsupported format.
    """
    logger.info("Exporting %d events (format=%s)...", len(community_events_df), format)

    image_count = int(
        community_events_df.get("image_url", pd.Series())
        .apply(lambda x: pd.notna(x))
        .sum()
    )
    logger.info("Events with images: %d/%d", image_count, len(community_events_df))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    df = community_events_df.copy()

    if format == "csv":
        path = OUTPUT_DIR / f"calendar_upload_{timestamp}.csv"
        df.to_csv(path, index=False)
        logger.info("CSV export saved to %s", path)
        return path

    if format == "json":
        path = OUTPUT_DIR / f"calendar_upload_{timestamp}.json"
        df.to_json(path, orient="records", indent=2)
        logger.info("JSON export saved to %s", path)
        return path

    if format == "ical":
        logger.warning("iCal export is not yet implemented.")
        return None

    logger.error("Unsupported export format: %s", format)
    return None
