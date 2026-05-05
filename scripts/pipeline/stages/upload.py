"""Stage 5 — Upload events to WordPress via REST API."""

from __future__ import annotations

import os
from pathlib import Path

from scripts.tooling.logger import get_logger

logger = get_logger(__name__)


def upload_to_wordpress(csv_path: Path) -> tuple[list | None, int | None]:
    """Upload events from *csv_path* to the configured WordPress site.

    Reads ``WP_SITE_URL``, ``WP_USERNAME``, and ``WP_APP_PASSWORD`` from
    the environment.

    Args:
        csv_path: Path to the CSV file produced by the export stage.

    Returns:
        ``(created_ids, published_count)`` on success, or
        ``(None, None)`` when credentials are missing or connection fails.
    """
    from scripts.pipeline.wordpress_uploader import WordPressEventUploader  # lazy

    site_url = os.getenv("WP_SITE_URL", "")
    username = os.getenv("WP_USERNAME", "")
    app_password = os.getenv("WP_APP_PASSWORD", "")

    if not username or not app_password:
        logger.error("WordPress credentials not configured (WP_USERNAME / WP_APP_PASSWORD).")
        return None, None

    logger.info("Connecting to WordPress at %s...", site_url)
    uploader = WordPressEventUploader(site_url, username, app_password)

    if not uploader.test_connection():
        logger.error("WordPress connection failed.")
        return None, None

    logger.info("Uploading events from %s...", csv_path)
    created_ids = uploader.upload_events_from_csv(csv_path, dry_run=False)

    if not created_ids:
        logger.info("No events were uploaded.")
        return [], 0

    logger.info("Publishing %d events...", len(created_ids))
    published = uploader.publish_events(created_ids)

    return created_ids, published
