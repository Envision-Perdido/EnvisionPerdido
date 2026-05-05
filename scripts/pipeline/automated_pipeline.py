"""
Automated Community Event Classification Pipeline — Orchestrator

Runs the pipeline end-to-end by delegating each concern to a stage module:

    Stage 1 · scrape   – fetch raw events from external sources
    Stage 2 · classify – SVM classification + confidence flagging
    Stage 2b· enrich   – enrichment, venue/tag filtering, image assignment
    Stage 3 · export   – export to CSV for upload
    Stage 4 · notify   – email review digest (and post-upload confirmation)
    Stage 5 · upload   – WordPress REST API upload

Each stage module lives under ``scripts/pipeline/stages/``.  This file is
intentionally kept thin — it only owns orchestration logic, shared constants
that haven't yet been migrated to a dedicated config module, and the legacy
``build_features()`` compat shim used by the classify stage for old model
formats.
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Path setup (must run before any project imports)
# ---------------------------------------------------------------------------

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# ---------------------------------------------------------------------------
# Environment loading
# ---------------------------------------------------------------------------

from env_loader import load_env, validate_env_config  # noqa: E402

load_env()

# ---------------------------------------------------------------------------
# Logger / metrics
# ---------------------------------------------------------------------------

from logger import PipelineMetrics, get_logger  # noqa: E402
from scripts.ml.training_support import build_text_features, normalize_event_text_series  # noqa: E402

# ---------------------------------------------------------------------------
# Optional enhancement module
# ---------------------------------------------------------------------------

try:
    from regenerate_descriptions import enhance_event_descriptions  # noqa: E402
except (ImportError, SystemExit):
    enhance_event_descriptions = None

# ---------------------------------------------------------------------------
# Stage modules
# ---------------------------------------------------------------------------

from scripts.pipeline.stages import classify as classify_stage  # noqa: E402
from scripts.pipeline.stages import enrich as enrich_stage  # noqa: E402
from scripts.pipeline.stages import export as export_stage  # noqa: E402
from scripts.pipeline.stages import notify as notify_stage  # noqa: E402
from scripts.pipeline.stages import scrape as scrape_stage  # noqa: E402
from scripts.pipeline.stages import upload as upload_stage  # noqa: E402

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).parent.parent.parent
OUTPUT_DIR = BASE_DIR / "output" / "pipeline"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.75"))

# ---------------------------------------------------------------------------
# Backward-compatibility shims (kept for external callers / legacy tests)
# ---------------------------------------------------------------------------


def build_features(df: pd.DataFrame) -> list[str]:
    """Text-only feature builder — compat shim for legacy model format.

    .. deprecated::
        New code should use
        ``scripts.ml.training_support.build_text_features`` or
        ``build_structured_features`` directly.
    """
    return build_text_features(df)


def log(message: str) -> None:
    """Timestamped log shim — use ``get_logger(__name__)`` in new code."""
    _logger = get_logger()
    if "ERROR" in message or "CRITICAL" in message:
        _logger.error(message)
    elif "Warning" in message or "WARN" in message:
        _logger.warning(message)
    else:
        _logger.info(message)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the complete automated community event pipeline."""
    pipeline_logger = get_logger(log_dir=str(BASE_DIR / "output" / "logs"))
    metrics = PipelineMetrics()

    validate_env_config()

    log("=" * 80)
    log("AUTOMATED COMMUNITY EVENT CLASSIFICATION PIPELINE")
    log("=" * 80)

    pipeline_start = time.time()

    try:
        # ------------------------------------------------------------------
        # Step 1 · Scrape
        # ------------------------------------------------------------------
        step_start = time.time()
        events, scrape_errors = scrape_stage.scrape_events(
            include_sources=["perdido_chamber", "wren_haven"]
        )
        log(f"\nStep 1 (Scraping) completed in {time.time() - step_start:.1f}s")

        for error in scrape_errors:
            pipeline_logger.warning(error)
            metrics.add_error(error)

        if not events:
            log("No events scraped. Exiting.")
            metrics.add_error("Scraper returned zero events")
            pipeline_logger.info(metrics.get_summary())
            return

        metrics.add_scraped(len(events))
        events_df = pd.DataFrame(events)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        raw_csv = OUTPUT_DIR / f"scraped_events_{timestamp}.csv"
        events_df.to_csv(raw_csv, index=False)
        log(f"Raw data saved to {raw_csv}")

        # ------------------------------------------------------------------
        # Step 2 · Classify
        # ------------------------------------------------------------------
        step_start = time.time()
        log("\nStep 2: Classifying events...")
        classified_df = classify_stage.classify_events(events_df)
        log(f"Step 2 (Classification) completed in {time.time() - step_start:.1f}s")

        if classified_df is None:
            metrics.add_error("Classification step failed")
            pipeline_logger.info(metrics.get_summary())
            return

        metrics.add_classified(len(classified_df))

        # ------------------------------------------------------------------
        # Step 2b · Enrich + filter
        # ------------------------------------------------------------------
        step_start = time.time()
        log("\nStep 2b: Enriching and filtering events...")
        classified_df, _ = enrich_stage.enrich_and_filter(classified_df)
        classified_df = enrich_stage.assign_event_images(classified_df)
        log(f"Step 2b (Enrich) completed in {time.time() - step_start:.1f}s")

        # ------------------------------------------------------------------
        # Step 3 · Optionally enhance descriptions via OpenAI
        # ------------------------------------------------------------------
        step_start = time.time()
        log("\nStep 3: Enhancing event descriptions with OpenAI...")
        if os.getenv("OPENAI_API_KEY") and enhance_event_descriptions:
            try:
                openai_dry_run = os.getenv("OPENAI_DRY_RUN", "false").lower() == "true"
                openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
                openai_use_batch = os.getenv("OPENAI_USE_BATCH", "false").lower() == "true"
                openai_top_n = int(os.getenv("OPENAI_TOP_N", "100"))
                openai_min_confidence = float(os.getenv("OPENAI_MIN_CONFIDENCE", "0.75"))

                events_list = classified_df.to_dict("records")
                for event in events_list:
                    if "Title" not in event and "title" in event:
                        event["Title"] = event["title"]
                    if "Description" not in event and "description" in event:
                        event["Description"] = event["description"]

                original_descriptions = [
                    event.get("description") or event.get("Description")
                    for event in events_list
                ]

                enhanced_events = enhance_event_descriptions(
                    events_list,
                    dry_run=openai_dry_run,
                    model=openai_model,
                    use_batch=openai_use_batch,
                    top_n=openai_top_n,
                    min_confidence=openai_min_confidence,
                    use_cache=True,
                    save_cache=True,
                )

                changed_count = 0
                for idx, event in enumerate(enhanced_events):
                    if "Title" in event and not event.get("title"):
                        event["title"] = event["Title"]
                    new_desc = event.get("Description") or event.get("description")
                    orig_desc = original_descriptions[idx] if idx < len(original_descriptions) else None
                    if new_desc is not None and new_desc != orig_desc:
                        changed_count += 1
                    if new_desc is not None:
                        event["description"] = new_desc

                classified_df = pd.DataFrame(enhanced_events)
                log(f"Enhanced {changed_count} descriptions in {time.time() - step_start:.1f}s")
                metrics.add_enhanced(changed_count)
            except Exception as exc:
                log(f"Warning: Description enhancement failed: {exc}")
                pipeline_logger.warning("OpenAI enhancement error: %s", exc)
        else:
            log("[SKIP] Step 3 (Enhancement): no OPENAI_API_KEY or module unavailable")

        # ------------------------------------------------------------------
        # Step 4 · Filter to community events
        # ------------------------------------------------------------------
        step_start = time.time()
        log("\nStep 4: Filtering community events...")
        community_events = classified_df[classified_df["is_community_event"] == 1].copy()

        if "needs_review" in classified_df.columns:
            metrics.add_needs_review(int(classified_df["needs_review"].sum()))

        # Remove events with implausibly long durations (> 60 days)
        if (
            len(community_events) > 0
            and "start" in community_events.columns
            and "end" in community_events.columns
        ):
            start_dt = pd.to_datetime(community_events["start"], errors="coerce")
            end_dt = pd.to_datetime(community_events["end"], errors="coerce")
            duration = (end_dt - start_dt).dt.days
            mask = duration.fillna(0) <= 60
            filtered_out = (~mask).sum()
            community_events = community_events[mask].copy()
            if filtered_out > 0:
                log(f"Filtered out {filtered_out} events with duration > 60 days")

        log(f"Step 4 (Filtering) completed in {time.time() - step_start:.1f}s")
        log(f"Found {len(community_events)} community events")

        # ------------------------------------------------------------------
        # Step 5 · Export
        # ------------------------------------------------------------------
        step_start = time.time()
        log("\nStep 5: Exporting events for calendar...")
        calendar_csv = export_stage.export_for_calendar(community_events, format="csv")
        log(f"Step 5 (Export) completed in {time.time() - step_start:.1f}s")

        # ------------------------------------------------------------------
        # Step 6 · Email review digest
        # ------------------------------------------------------------------
        step_start = time.time()
        sender = os.getenv("SENDER_EMAIL", "")
        if sender and sender != "your_email@example.com":
            log("\nStep 6: Sending email notification...")
            notify_stage.send_review_email(community_events, classified_df, calendar_csv)
            log(f"Step 6 (Email) completed in {time.time() - step_start:.1f}s")
        else:
            log("Email not configured. Skipping email notification.")
            log(f"Review file manually at: {calendar_csv}")

        # ------------------------------------------------------------------
        # Step 7 · Upload to WordPress (if enabled)
        # ------------------------------------------------------------------
        auto_upload = os.getenv("AUTO_UPLOAD", "true").lower() in {"true", "1", "yes"}

        if auto_upload and len(community_events) > 0:
            step_start = time.time()
            log("\n" + "=" * 80)
            log("Step 7: AUTO-UPLOAD ENABLED — Uploading to WordPress...")
            log("=" * 80)

            created_ids, published_count = upload_stage.upload_to_wordpress(calendar_csv)
            log(f"Step 7 (Upload) completed in {time.time() - step_start:.1f}s")

            if created_ids and published_count:
                log(f"Successfully published {published_count} events to calendar")
                metrics.add_uploaded(published_count)
                notify_stage.send_upload_confirmation(community_events, created_ids, published_count)
            elif created_ids is not None:
                log("Upload completed but some events may not have published")
                metrics.add_uploaded(len(created_ids))
            else:
                log("Upload failed — check WordPress credentials and connection")
                metrics.add_error("WordPress upload failed")
        else:
            log("\n" + "=" * 80)
            log("AUTO_UPLOAD disabled — manual upload required")
            log(f"Use: uv run python scripts/pipeline/wordpress_uploader.py {calendar_csv}")
            log("=" * 80)

        # ------------------------------------------------------------------
        # Final summary
        # ------------------------------------------------------------------
        total = time.time() - pipeline_start
        log("\n" + "=" * 80)
        log("PIPELINE COMPLETE!")
        log(f"Total execution time: {total:.1f}s ({total / 60:.1f} minutes)")
        log("=" * 80)
        pipeline_logger.info(metrics.get_summary())

    except Exception as exc:
        log(f"CRITICAL ERROR: {exc}")
        metrics.add_error(str(exc))
        pipeline_logger.error("Pipeline failed: %s", exc)
        pipeline_logger.info(metrics.get_summary())
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()

