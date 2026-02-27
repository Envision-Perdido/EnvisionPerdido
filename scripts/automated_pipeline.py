"""
Automated Community Event Classification Pipeline

This script runs the complete pipeline:
1. Scrape events from the chamber website
2. Classify events as community/non-community using trained SVM
3. Format results for review
4. Send email notification with results
5. Prepare events for calendar upload

Run this script on a schedule (weekly/monthly) for hands-off operation.
"""

import json
import os
import smtplib
import sys
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Tuple

import joblib
import numpy as np
import pandas as pd

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
from env_loader import load_env, validate_env_config

load_env()
# Import logger and metrics
from logger import PipelineMetrics, get_logger

# Import scraper and normalizer modules
from scripts import Envision_Perdido_DataCollection, event_normalizer

# Configuration
BASE_DIR = Path(__file__).parent.parent
MODEL_PATH = BASE_DIR / "data" / "artifacts" / "event_classifier_model.pkl"
VECTORIZER_PATH = BASE_DIR / "data" / "artifacts" / "event_vectorizer.pkl"
IMAGE_CONFIG_PATH = BASE_DIR / "data" / "image_keyword_config.json"
IMAGES_DIR = BASE_DIR / "data" / "event_images"
# Organized output path
OUTPUT_DIR = BASE_DIR / "output" / "pipeline"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Model caching for performance
_MODEL_CACHE = {"model": None, "vectorizer": None}


def load_model_and_vectorizer():
    """Load model and vectorizer with caching.

    Returns:
        Tuple[object | None, object | None]: Tuple of (model,
            vectorizer), or (None, None) if files not found.
    """
    global _MODEL_CACHE

    if _MODEL_CACHE["model"] is None or _MODEL_CACHE["vectorizer"] is None:
        if not MODEL_PATH.exists() or not VECTORIZER_PATH.exists():
            log("ERROR: Model files not found! Please train the model first.")
            return None, None

        _MODEL_CACHE["model"] = joblib.load(MODEL_PATH)
        _MODEL_CACHE["vectorizer"] = joblib.load(VECTORIZER_PATH)

    return _MODEL_CACHE["model"], _MODEL_CACHE["vectorizer"]


# Email configuration (set these as environment variables for security)
EMAIL_CONFIG = {
    "smtp_server": os.getenv("SMTP_SERVER", "smtp.gmail.com"),
    "smtp_port": int(os.getenv("SMTP_PORT", "587")),
    "sender_email": os.getenv("SENDER_EMAIL", ""),
    "sender_password": os.getenv("EMAIL_PASSWORD", ""),
    "recipient_email": os.getenv("RECIPIENT_EMAIL", ""),
}


def log(message):
    """Print timestamped log message (DEPRECATED - use logger instead).

    This function is deprecated. New code should use the global logger object instead.
    It's kept for backward compatibility with existing log() calls in the pipeline.
    """
    # For now, we'll still support the old log() calls by delegating to the logger
    # This allows gradual migration to the new logging system
    logger = get_logger()
    # Determine log level based on message content
    if "ERROR" in message or "CRITICAL" in message:
        logger.error(message)
    elif "Warning" in message or "WARN" in message:
        logger.warning(message)
    else:
        logger.info(message)


def build_features(df: pd.DataFrame) -> list[str]:
    """Build text features from event data using vectorized operations.

    Args:
        df: DataFrame with 'title', 'description', 'location',
            'category' columns.

    Returns:
        List of concatenated feature strings.
    """
    title = df.get("title", pd.Series()).fillna("").astype(str)
    description = df.get("description", pd.Series()).fillna("").astype(str)
    location = df.get("location", pd.Series()).fillna("").astype(str)
    category = df.get("category", pd.Series()).fillna("").astype(str)

    features = (
        (title + " " + description + " " + location + " " + category).str.split().str.join(" ")
    )
    return features.tolist()


def classify_events_batch(
    events_df: pd.DataFrame,
    model: object,
    vectorizer: object,
    batch_size: int = 500,
    verbose: bool = True,
) -> Tuple[np.ndarray, np.ndarray]:
    """Classify events in batches for better memory efficiency.

    Uses batch processing to vectorize and classify events, reducing peak memory
    usage and enabling progress reporting.

    Args:
        events_df: DataFrame with event data.
        model: Trained classifier.
        vectorizer: TfidfVectorizer.
        batch_size: Number of events per batch (default: 500).
        verbose: Whether to log progress (default: True).

    Returns:
        Tuple of (predictions, confidence_scores) arrays.
    """
    n_events = len(events_df)
    all_predictions = np.zeros(n_events, dtype=int)
    all_confidences = np.zeros(n_events, dtype=float)

    for i in range(0, n_events, batch_size):
        end_idx = min(i + batch_size, n_events)
        batch = events_df.iloc[i:end_idx]

        # Build features for batch
        X_text = build_features(batch)
        X = vectorizer.transform(X_text)

        # Predict on batch
        batch_predictions = model.predict(X)
        all_predictions[i:end_idx] = batch_predictions

        # Get confidence scores (use decision_function for SVM)
        if hasattr(model, "decision_function"):
            decision_scores = model.decision_function(X)
            # Convert decision function to confidence-like score (sigmoid transform)
            # For binary classification, values range approximately [-inf, +inf]
            # Normalize to [0, 1] using sigmoid
            batch_confidences = 1 / (1 + np.exp(-decision_scores))
        else:
            # Fallback if decision_function not available
            batch_confidences = np.ones(len(batch_predictions)) * 0.5

        all_confidences[i:end_idx] = batch_confidences

        if verbose and (i + batch_size) % (batch_size * 5) == 0:
            log(f"  Progress: {min(i + batch_size, n_events)}/{n_events} events classified")

    return all_predictions, all_confidences


def scrape_events(
    year: int | None = None, month: int | None = None, include_sources: list[str] | None = None
) -> tuple[list[dict], list]:
    """Scrape events from all configured sources.

    Args:
        year: Year to scrape (default current year).
        month: Month to scrape (default current month).
        include_sources: List of source names to include. Options:
            'perdido_chamber', 'wren_haven'. Default:
            ['perdido_chamber'] (for backward compatibility).

    Returns:
        Tuple of (events_list, errors_list):
            - events_list: List of event dictionaries from all sources
            - errors_list: List of errors encountered during scraping
    """
    log("Starting event scraping...")

    if include_sources is None:
        include_sources = ["perdido_chamber"]

    if year is None:
        year = datetime.now().year
    if month is None:
        month = datetime.now().month

    all_events = []
    errors = []

    # Scrape Perdido Chamber (original source)
    if "perdido_chamber" in include_sources:
        log("Scraping Perdido Chamber...")
        for m in range(month, min(month + 2, 13)):
            month_str = f"{year}-{m:02d}-01"
            base_url = "https://business.perdidochamber.com/events/calendar"
            month_url = f"{base_url}/{month_str}"
            log(f"Scraping {month_url}...")

            try:
                events = Envision_Perdido_DataCollection.scrape_month(month_url)
                log(f"Scraped {len(events)} events from {month_url}")
                all_events.extend(events)
            except Exception as e:  # pylint: disable=broad-except
                error_msg = f"Error scraping Perdido Chamber {month_url}: {e}"
                log(f"ERROR: {error_msg}")
                errors.append(error_msg)

    # Scrape Wren Haven (if enabled)
    if "wren_haven" in include_sources:
        log("Scraping Wren Haven Homestead...")
        try:
            from scripts import wren_haven_scraper

            events = wren_haven_scraper.scrape_wren_haven()
            log(f"Scraped {len(events)} events from Wren Haven")
            all_events.extend(events)
        except ImportError as e:
            error_msg = (
                f"Warning: wren_haven_scraper not available (Playwright not installed?): {e}"
            )
            log(error_msg)
            errors.append(error_msg)
        except Exception as e:  # pylint: disable=broad-except
            error_msg = f"Error scraping Wren Haven: {e}"
            log(f"ERROR: {error_msg}")
            errors.append(error_msg)

    log(f"Total events scraped from all sources: {len(all_events)}")
    if errors:
        log(f"Encountered {len(errors)} scraper error(s)")

    return all_events, errors


def assign_event_images(events_df: pd.DataFrame) -> pd.DataFrame:
    """Assign images to events based on weighted keyword scoring.

    Uses vectorized text operations and pre-processed keyword data for
    efficient scoring. Assigns the highest-scoring image to each event.

    Args:
        events_df: DataFrame with event data.

    Returns:
        DataFrame with 'image_url' column added (absolute path or None).
    """
    if not IMAGE_CONFIG_PATH.exists():
        log("Warning: Image config not found, skipping image assignment")
        events_df["image_url"] = None
        return events_df

    log("Assigning images based on keyword scoring...")

    # Load image keyword configuration
    with open(IMAGE_CONFIG_PATH) as f:
        config = json.load(f)

    images_config = config.get("images", {})
    min_threshold = config.get("config", {}).get("min_score_threshold", 0)

    if not images_config:
        log("Warning: No images configured, skipping image assignment")
        events_df["image_url"] = None
        return events_df

    # Pre-process image configurations: create list of (image_file, keywords_list, weights_list)
    image_specs = []
    for image_file, image_data in images_config.items():
        keywords = image_data.get("keywords", {})
        if keywords:
            image_specs.append((image_file, list(keywords.keys()), list(keywords.values())))

    # Build event text once for all comparisons using vectorized operations
    event_text = (
        events_df.get("title", pd.Series()).fillna("").astype(str).str.lower()
        + " "
        + events_df.get("description", pd.Series()).fillna("").astype(str).str.lower()
        + " "
        + events_df.get("location", pd.Series()).fillna("").astype(str).str.lower()
        + " "
        + events_df.get("category", pd.Series()).fillna("").astype(str).str.lower()
    )

    # Score all images for all events at once
    assigned_images = []
    for idx, text in enumerate(event_text):
        best_image = None
        best_score = -1

        # Score each image
        for image_file, keywords, weights in image_specs:
            score = sum(
                weight for keyword, weight in zip(keywords, weights) if keyword.lower() in text
            )

            if score > best_score:
                best_score = score
                best_image = image_file

        # Apply threshold
        if best_score >= min_threshold and best_score > 0:
            image_path = os.path.abspath(os.path.join(IMAGES_DIR, best_image))
            assigned_images.append(image_path)
        else:
            assigned_images.append(None)

    events_df["image_url"] = assigned_images

    # Report statistics
    assigned_count = sum(1 for img in assigned_images if img is not None)
    log(f"Image assignment complete: {assigned_count}/{len(events_df)} events assigned images")

    return events_df


def classify_events(events_df: pd.DataFrame) -> pd.DataFrame | None:
    """Classify events using trained SVM model.

    Uses cached model loading and batch processing for efficiency.
    Adds confidence scores and review flags.

    Args:
        events_df: DataFrame with event data.

    Returns:
        DataFrame with classification columns added, or None on error.
    """
    log("Loading trained model...")

    model, vectorizer = load_model_and_vectorizer()
    if model is None or vectorizer is None:
        return None

    log(f"Classifying {len(events_df)} events (using batch processing)...")

    # Use batch classification for better memory efficiency
    predictions, confidence = classify_events_batch(
        events_df, model, vectorizer, batch_size=500, verbose=True
    )

    events_df["is_community_event"] = predictions
    events_df["confidence"] = confidence

    # Add review flag for low confidence predictions
    events_df["needs_review"] = events_df["confidence"] < 0.75

    community_count = predictions.sum()
    log(
        f"Classification complete: {community_count} community events, {len(events_df) - community_count} non-community events"
    )

    # Enrich events with tags, paid/free status, venue resolution
    log("Enriching events with tags, paid/free status, and venue information...")
    events_df = event_normalizer.enrich_events_dataframe(events_df)
    log("Enrichment complete. Added tags, event types, and venue data.")

    # Apply filters (Brandon Styles @ OWA, etc.)
    kept_df, filtered_df = event_normalizer.filter_events_dataframe(events_df)
    if len(filtered_df) > 0:
        log(f"Filtered out {len(filtered_df)} events:")
        for _, event in filtered_df.iterrows():
            log(
                f"  - FILTERED: {event.get('title', 'Unknown')} at {event.get('location', 'Unknown')} - Reason: {event.get('filter_reason', 'Unknown')}"
            )

    # Continue with kept events only
    events_df = kept_df

    # Assign images based on keyword scoring
    events_df = assign_event_images(events_df)

    return events_df


def generate_review_html(community_events_df: pd.DataFrame, stats: dict) -> str:
    """Generate HTML email for event review.

    Args:
        community_events_df: DataFrame of community events.
        stats: Dictionary with statistics (total_events, etc.).

    Returns:
        HTML string for email body.
    """

    html_parts = [
        f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 900px; margin: 20px auto; }}
            h1 {{ color: #2c3e50; }}
            h2 {{ color: #34495e; margin-top: 30px; }}
            .stats {{ background: #ecf0f1; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            .stat-item {{ display: inline-block; margin-right: 30px; }}
            .stat-number {{ font-size: 24px; font-weight: bold; color: #3498db; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th {{ background: #3498db; color: white; padding: 10px; text-align: left; }}
            td {{ padding: 10px; border-bottom: 1px solid #ddd; }}
            tr:hover {{ background: #f5f5f5; }}
            .high-confidence {{ color: #27ae60; font-weight: bold; }}
            .low-confidence {{ color: #e74c3c; font-weight: bold; }}
            .review-needed {{ background: #fff3cd; }}
        </style>
    </head>
    <body>
        <h1>Community Event Classification Review</h1>
        <p>Run Date: {datetime.now().strftime("%B %d, %Y at %I:%M %p")}</p>

        <div class="stats">
            <div class="stat-item">
                <div class="stat-number">{stats["total_events"]}</div>
                <div>Total Events Scraped</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{stats["community_events"]}</div>
                <div>Community Events</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{stats["non_community_events"]}</div>
                <div>Non-Community Events</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{stats["needs_review"]}</div>
                <div>Need Review</div>
            </div>
        </div>

        <h2>Community Events for Calendar Upload</h2>
        <p>The following events have been classified as community events. Please review before uploading to the calendar.</p>

        <table>
            <thead>
                <tr>
                    <th>Title</th>
                    <th>Date</th>
                    <th>Location</th>
                    <th>Confidence</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
    """
    ]

    # Build rows more efficiently
    for _, event in community_events_df.iterrows():
        confidence = event["confidence"]
        confidence_class = "high-confidence" if confidence >= 0.75 else "low-confidence"
        row_class = "review-needed" if event["needs_review"] else ""
        status = "Review Needed" if event["needs_review"] else "High Confidence"

        start_date = (
            pd.to_datetime(event["start"]).strftime("%b %d, %Y %I:%M %p")
            if pd.notna(event["start"])
            else "N/A"
        )
        location = event.get("location", "N/A")
        if pd.isna(location):
            location = "N/A"

        html_parts.append(
            '                <tr class="{}">\n'
            "                    <td><strong>{}</strong></td>\n"
            "                    <td>{}</td>\n"
            "                    <td>{}</td>\n"
            '                    <td class="{}">{:.1%}</td>\n'
            "                    <td>{}</td>\n"
            "                </tr>".format(
                row_class,
                event["title"],
                start_date,
                location,
                confidence_class,
                confidence,
                status,
            )
        )

    html_parts.append("""
            </tbody>
        </table>

        <h2>Next Steps</h2>
        <p>1. Review the events listed above, especially those marked for review.</p>
        <p>2. Download the attached CSV file for detailed information.</p>
        <p>3. Once approved, use the upload script to publish events to the calendar.</p>

        <p style="margin-top: 30px; color: #7f8c8d; font-size: 12px;">
            This is an automated email from the Community Event Classification System.
        </p>
    </body>
    </html>
    """)

    return "\n".join(html_parts)


def send_email_notification(
    community_events_df: pd.DataFrame, all_events_df: pd.DataFrame, csv_path: Path
) -> bool:
    """Send email notification with classified events.

    Args:
        community_events_df: DataFrame of community events.
        all_events_df: DataFrame of all events (for statistics).
        csv_path: Path to CSV export file to attach.

    Returns:
        True if email sent successfully, False otherwise.
    """
    log("Preparing email notification...")

    # Calculate statistics
    stats = {
        "total_events": len(all_events_df),
        "community_events": len(community_events_df),
        "non_community_events": len(all_events_df) - len(community_events_df),
        "needs_review": community_events_df["needs_review"].sum(),
    }

    # Generate HTML email
    html_content = generate_review_html(community_events_df, stats)

    # Create email message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Community Event Review - {stats['community_events']} Events Found"
    msg["From"] = EMAIL_CONFIG["sender_email"]
    msg["To"] = EMAIL_CONFIG["recipient_email"]

    # Attach HTML
    msg.attach(MIMEText(html_content, "html"))

    # Attach CSV file
    try:
        with open(csv_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
            encoders.encode_base64(part)
            filename = csv_path.name
            part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
            msg.attach(part)
    except OSError as e:  # File access errors
        log(f"Warning: Could not attach CSV file: {e}")

    # Send email
    try:
        recipient = EMAIL_CONFIG["recipient_email"]
        log(f"Sending email to {recipient}...")
        smtp_server = EMAIL_CONFIG["smtp_server"]
        smtp_port = EMAIL_CONFIG["smtp_port"]
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            sender_email = EMAIL_CONFIG["sender_email"]
            sender_password = EMAIL_CONFIG["sender_password"]
            server.login(sender_email, sender_password)
            server.send_message(msg)
        log("Email sent successfully!")
        return True
    except smtplib.SMTPException as e:
        log(f"ERROR: Failed to send email: {e}")
        log("Please check your email configuration and credentials.")
        return False


def export_for_calendar(community_events_df: pd.DataFrame, format: str = "csv") -> Path | None:
    """Export community events in format ready for calendar upload.

    Uses automated keyword-based image assignment from classification.

    Args:
        community_events_df: DataFrame of community events.
        format: Export format ('csv', 'json', 'ical'). Default: 'csv'.

    Returns:
        Path to exported file, or None on error.
    """
    log(f"Exporting events for calendar upload (format: {format})...")

    # Use automated image assignments from classification
    df = community_events_df.copy()

    # Log image assignment statistics
    image_urls = df.get("image_url", [None] * len(df))
    events_with_images = sum(1 for img in image_urls if pd.notna(img))
    log(f"Automated keyword-based image assignments: {events_with_images} events with images")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if format == "csv":
        output_path = OUTPUT_DIR / f"calendar_upload_{timestamp}.csv"
        df.to_csv(output_path, index=False)
        log(f"CSV export saved to {output_path}")
        return output_path

    elif format == "json":
        output_path = OUTPUT_DIR / f"calendar_upload_{timestamp}.json"
        df.to_json(output_path, orient="records", indent=2)
        log(f"JSON export saved to {output_path}")
        return output_path

    elif format == "ical":
        # TODO: Implement iCal export for calendar systems that accept .ics files
        log("iCal export not yet implemented")
        return None

    return None


def upload_to_wordpress(csv_path: Path) -> tuple[list | None, int]:
    """Upload events to WordPress and return results.

    Args:
        csv_path: Path to CSV file with events.

    Returns:
        Tuple of (created_ids list or None, published_count).
    """
    from scripts import wordpress_uploader

    # Get WordPress credentials from environment
    site_url = os.getenv("WP_SITE_URL", "")
    username = os.getenv("WP_USERNAME", "")
    app_password = os.getenv("WP_APP_PASSWORD", "")

    if not username or not app_password:
        log("ERROR: WordPress credentials not configured")
        return None, None

    log("Connecting to WordPress...")
    uploader = wordpress_uploader.WordPressEventUploader(site_url, username, app_password)

    if not uploader.test_connection():
        log("ERROR: WordPress connection failed")
        return None, None

    log("Uploading events to WordPress...")
    created_ids = uploader.upload_events_from_csv(csv_path, dry_run=False)

    if not created_ids:
        log("No events were uploaded")
        return [], 0

    log(f"Publishing {len(created_ids)} events...")
    published = uploader.publish_events(created_ids)

    return created_ids, published


def send_upload_confirmation_email(
    community_events_df: pd.DataFrame, created_ids: list, published_count: int
) -> bool:
    """Send confirmation email with upload results.

    Args:
        community_events_df: DataFrame of community events.
        created_ids: List of created event IDs.
        published_count: Number of events published.

    Returns:
        True if email sent successfully, False otherwise.
    """
    log("Sending upload confirmation email...")

    # Generate HTML for confirmation using list join for efficiency
    html_parts = [
        f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1 {{ color: #2c3e50; }}
            h2 {{ color: #34495e; margin-top: 30px; }}
            .summary {{ background-color: #ecf0f1; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
            th {{ background-color: #3498db; color: white; padding: 12px; text-align: left; }}
            td {{ padding: 10px; border-bottom: 1px solid #ddd; }}
            tr:hover {{ background-color: #f5f5f5; }}
            .success {{ color: #27ae60; font-weight: bold; }}
        </style>
    </head>
    <body>
    <h1>Community Events Published to Calendar</h1>

        <div class="summary">
            <h2>Upload Summary</h2>
            <p><strong>Total Events Uploaded:</strong> {len(created_ids)}</p>
            <p><strong>Successfully Published:</strong> <span class="success">{published_count}</span></p>
            <p><strong>Upload Date:</strong> {datetime.now().strftime("%B %d, %Y at %I:%M %p")}</p>
        </div>

        <h2>Published Events</h2>
        <table>
            <thead>
                <tr>
                    <th>Title</th>
                    <th>Start Date</th>
                    <th>Location</th>
                    <th>Confidence</th>
                </tr>
            </thead>
            <tbody>
    """
    ]

    # Add event rows
    for _, event in community_events_df.iterrows():
        start_date = (
            pd.to_datetime(event["start"]).strftime("%b %d, %Y %I:%M %p")
            if pd.notna(event["start"])
            else "N/A"
        )
        location = event.get("location", "N/A")
        if pd.isna(location):
            location = "N/A"
        confidence = event.get("confidence", 0)

        html_parts.append(
            "                <tr>\n"
            "                    <td><strong>{}</strong></td>\n"
            "                    <td>{}</td>\n"
            "                    <td>{}</td>\n"
            "                    <td>{:.1%}</td>\n"
            "                </tr>".format(event["title"], start_date, location, confidence)
        )

    html_parts.append("""
            </tbody>
        </table>

        <p style="margin-top: 30px;">
            View your calendar events online.
        </p>

        <p style="margin-top: 30px; color: #7f8c8d; font-size: 12px;">
            This is an automated confirmation from the Community Event Classification System.
        </p>
    </body>
    </html>
    """)

    html = "\n".join(html_parts)

    # Create email message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Calendar Updated - {published_count} Community Events Published"
    msg["From"] = EMAIL_CONFIG["sender_email"]
    msg["To"] = EMAIL_CONFIG["recipient_email"]
    msg.attach(MIMEText(html, "html"))

    # Send email
    try:
        smtp_server = EMAIL_CONFIG["smtp_server"]
        smtp_port = EMAIL_CONFIG["smtp_port"]
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            sender_email = EMAIL_CONFIG["sender_email"]
            sender_password = EMAIL_CONFIG["sender_password"]
            server.login(sender_email, sender_password)
            server.send_message(msg)
        log("Upload confirmation email sent successfully!")
        return True
    except smtplib.SMTPException as e:
        log(f"ERROR: Failed to send confirmation email: {e}")
        return False


def main():
    """Run the complete automated pipeline."""
    # Initialize logger and metrics
    logger = get_logger(log_dir=str(BASE_DIR / "output" / "logs"))
    metrics = PipelineMetrics()

    # Validate environment configuration first (fail fast)
    validate_env_config()

    log("=" * 80)
    log("AUTOMATED COMMUNITY EVENT CLASSIFICATION PIPELINE")
    log("=" * 80)

    try:
        # Step 1: Scrape events
        events, scrape_errors = scrape_events(include_sources=["perdido_chamber", "wren_haven"])

        # Log scraper errors and add to metrics
        for error in scrape_errors:
            logger.warning(error)
            metrics.add_error(error)

        if not events:
            log("No events scraped. Exiting.")
            metrics.add_error("Scraper returned zero events")
            logger.info(metrics.get_summary())
            return

        metrics.add_scraped(len(events))

        # Convert to DataFrame
        events_df = pd.DataFrame(events)

        # Save raw scraped data
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        raw_csv = OUTPUT_DIR / f"scraped_events_{timestamp}.csv"
        events_df.to_csv(raw_csv, index=False)
        log(f"Raw data saved to {raw_csv}")

        # Step 2: Classify events
        classified_df = classify_events(events_df)
        if classified_df is None:
            metrics.add_error("Classification step failed")
            logger.info(metrics.get_summary())
            return

        metrics.add_classified(len(classified_df))

        # Step 3: Filter community events and remove unreasonably long events
        community_events = classified_df[classified_df["is_community_event"] == 1].copy()

        # Track events needing review (confidence < 0.75)
        if "confidence" in classified_df.columns:
            needs_review = len(classified_df[classified_df["confidence"] < 0.75])
            metrics.add_needs_review(needs_review)

        # Filter out events longer than 60 days (likely recurring stubs or data errors)
        if (
            len(community_events) > 0
            and "start" in community_events.columns
            and "end" in community_events.columns
        ):
            community_events["_start_dt"] = pd.to_datetime(
                community_events["start"], errors="coerce"
            )
            community_events["_end_dt"] = pd.to_datetime(community_events["end"], errors="coerce")
            community_events["_duration_days"] = (
                community_events["_end_dt"] - community_events["_start_dt"]
            ).dt.days

            before_filter = len(community_events)
            community_events = community_events[
                community_events["_duration_days"].fillna(0) <= 60
            ].copy()
            community_events.drop(columns=["_start_dt", "_end_dt", "_duration_days"], inplace=True)

            filtered_out = before_filter - len(community_events)
            if filtered_out > 0:
                log(f"Filtered out {filtered_out} events with duration > 60 days")

        log(f"Found {len(community_events)} community events")

        # Step 4: Export for calendar
        calendar_csv = export_for_calendar(community_events, format="csv")

        # Step 5: Send email notification
        if EMAIL_CONFIG["sender_email"] != "your_email@example.com":
            send_email_notification(community_events, classified_df, calendar_csv)
        else:
            log("Email not configured. Skipping email notification.")
            log(f"Review file manually at: {calendar_csv}")

        # Step 6: Auto-upload to WordPress (if enabled)
        auto_upload = os.getenv("AUTO_UPLOAD", "true").lower() in {"true", "1", "yes"}

        if auto_upload and len(community_events) > 0:
            log("\n" + "=" * 80)
            log("AUTO-UPLOAD ENABLED - Uploading to WordPress...")
            log("=" * 80)

            created_ids, published_count = upload_to_wordpress(calendar_csv)

            if created_ids and published_count:
                log(f"Successfully published {published_count} events to calendar")
                metrics.add_uploaded(published_count)
                send_upload_confirmation_email(community_events, created_ids, published_count)
            elif created_ids is not None:
                log("Upload completed but some events may not have published")
                metrics.add_uploaded(len(created_ids))
            else:
                log("Upload failed - check WordPress credentials and connection")
                metrics.add_error("WordPress upload failed")
        else:
            log("\n" + "=" * 80)
            log("AUTO_UPLOAD disabled - manual upload required")
            log(f"Use: python scripts/wordpress_uploader.py {calendar_csv}")
            log("=" * 80)

        log("\n" + "=" * 80)
        log("PIPELINE COMPLETE!")
        log("=" * 80)

        # Log final metrics summary
        logger.info(metrics.get_summary())

    except Exception as e:
        log(f"CRITICAL ERROR: {e}")
        metrics.add_error(str(e))
        logger.error(f"Pipeline failed with exception: {e}")
        logger.info(metrics.get_summary())
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
