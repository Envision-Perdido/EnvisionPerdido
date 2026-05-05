"""Stage 2b — Event enrichment, venue/tag filtering, and image assignment."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd

from scripts.tooling.logger import get_logger

logger = get_logger(__name__)

_BASE_DIR = Path(__file__).parent.parent.parent.parent  # …/EnvisionPerdido
IMAGE_CONFIG_PATH = _BASE_DIR / "data" / "image_keyword_config.json"
IMAGES_DIR = _BASE_DIR / "data" / "event_images"


def enrich_and_filter(
    events_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Enrich events with tags/venue data then apply business-rule filters.

    Args:
        events_df: Classified events DataFrame (output of classify stage).

    Returns:
        ``(kept_df, filtered_df)`` — *filtered_df* is logged for audit
        purposes and discarded by the orchestrator.
    """
    from scripts import event_normalizer  # lazy; avoids circular import at module load

    logger.info("Enriching events with tags, paid/free status, and venue information...")
    enriched = event_normalizer.enrich_events_dataframe(events_df)
    logger.info("Enrichment complete.")

    kept_df, filtered_df = event_normalizer.filter_events_dataframe(enriched)
    if len(filtered_df) > 0:
        logger.info("Filtered out %d events:", len(filtered_df))
        for _, event in filtered_df.iterrows():
            logger.info(
                "  FILTERED: %s at %s — %s",
                event.get("title", "Unknown"),
                event.get("location", "Unknown"),
                event.get("filter_reason", "Unknown"),
            )

    return kept_df, filtered_df


def assign_event_images(events_df: pd.DataFrame) -> pd.DataFrame:
    """Assign a keyword-scored stock image to each event.

    Reads ``data/image_keyword_config.json`` and scores each event's text
    against keyword→weight mappings.  The highest-scoring image above the
    configured minimum threshold is assigned; events with no qualifying match
    get ``image_url = None``.

    Args:
        events_df: Events DataFrame.

    Returns:
        Same DataFrame with ``image_url`` column added.
    """
    if not IMAGE_CONFIG_PATH.exists():
        logger.warning("Image config not found (%s); skipping image assignment.", IMAGE_CONFIG_PATH)
        events_df = events_df.copy()
        events_df["image_url"] = None
        return events_df

    with open(IMAGE_CONFIG_PATH) as f:
        config = json.load(f)

    images_config = config.get("images", {})
    min_threshold = config.get("config", {}).get("min_score_threshold", 0)

    if not images_config:
        logger.warning("No images configured in %s; skipping.", IMAGE_CONFIG_PATH)
        events_df = events_df.copy()
        events_df["image_url"] = None
        return events_df

    image_specs = [
        (fname, list(kw.keys()), list(kw.values()))
        for fname, data in images_config.items()
        if (kw := data.get("keywords", {}))
    ]

    event_text = (
        events_df.get("title", pd.Series()).fillna("").astype(str).str.lower()
        + " "
        + events_df.get("description", pd.Series()).fillna("").astype(str).str.lower()
        + " "
        + events_df.get("location", pd.Series()).fillna("").astype(str).str.lower()
        + " "
        + events_df.get("category", pd.Series()).fillna("").astype(str).str.lower()
    )

    assigned: list[str | None] = []
    for text in event_text:
        best_image: str | None = None
        best_score = -1
        for fname, keywords, weights in image_specs:
            score = sum(w for kw, w in zip(keywords, weights) if kw.lower() in text)
            if score > best_score:
                best_score = score
                best_image = fname
        if best_score >= min_threshold and best_score > 0 and best_image is not None:
            assigned.append(str(os.path.abspath(IMAGES_DIR / best_image)))
        else:
            assigned.append(None)

    events_df = events_df.copy()
    events_df["image_url"] = assigned
    assigned_count = sum(1 for img in assigned if img is not None)
    logger.info(
        "Image assignment complete: %d/%d events assigned images.",
        assigned_count,
        len(events_df),
    )
    return events_df
