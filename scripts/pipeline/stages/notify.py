"""Stage 4 — Email notification (review digest and upload confirmation)."""

from __future__ import annotations

import os
import smtplib
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import pandas as pd

from scripts.tooling.logger import get_logger

logger = get_logger(__name__)

CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.75"))


def _email_config() -> dict:
    """Read SMTP credentials from environment at call-time (not at import)."""
    return {
        "smtp_server": os.getenv("SMTP_SERVER", "smtp.gmail.com"),
        "smtp_port": int(os.getenv("SMTP_PORT", "587")),
        "sender_email": os.getenv("SENDER_EMAIL", ""),
        "sender_password": os.getenv("EMAIL_PASSWORD", ""),
        "recipient_email": os.getenv("RECIPIENT_EMAIL", ""),
    }


# ---------------------------------------------------------------------------
# HTML template builders
# ---------------------------------------------------------------------------


def generate_review_html(
    community_events_df: pd.DataFrame,
    stats: dict,
    confidence_threshold: float = CONFIDENCE_THRESHOLD,
) -> str:
    """Build the HTML body for the classification-review email."""
    rows: list[str] = []
    for _, event in community_events_df.iterrows():
        confidence = float(event.get("confidence", 0))
        conf_class = "high-confidence" if confidence >= confidence_threshold else "low-confidence"
        row_class = "review-needed" if event.get("needs_review") else ""
        status = "Review Needed" if event.get("needs_review") else "High Confidence"
        start_date = (
            pd.to_datetime(event["start"]).strftime("%b %d, %Y %I:%M %p")
            if pd.notna(event.get("start"))
            else "N/A"
        )
        location = event.get("location") or "N/A"
        if pd.isna(location):
            location = "N/A"
        rows.append(
            f'<tr class="{row_class}">'
            f"<td><strong>{event['title']}</strong></td>"
            f"<td>{start_date}</td>"
            f"<td>{location}</td>"
            f'<td class="{conf_class}">{confidence:.1%}</td>'
            f"<td>{status}</td>"
            "</tr>"
        )

    return f"""<!DOCTYPE html>
<html>
<head>
  <style>
    body{{font-family:Arial,sans-serif;max-width:900px;margin:20px auto}}
    h1{{color:#2c3e50}} h2{{color:#34495e;margin-top:30px}}
    .stats{{background:#ecf0f1;padding:15px;border-radius:5px;margin:20px 0}}
    .stat-item{{display:inline-block;margin-right:30px}}
    .stat-number{{font-size:24px;font-weight:bold;color:#3498db}}
    table{{width:100%;border-collapse:collapse;margin-top:20px}}
    th{{background:#3498db;color:white;padding:10px;text-align:left}}
    td{{padding:10px;border-bottom:1px solid #ddd}}
    tr:hover{{background:#f5f5f5}}
    .high-confidence{{color:#27ae60;font-weight:bold}}
    .low-confidence{{color:#e74c3c;font-weight:bold}}
    .review-needed{{background:#fff3cd}}
  </style>
</head>
<body>
  <h1>Community Event Classification Review</h1>
  <p>Run Date: {datetime.now().strftime("%B %d, %Y at %I:%M %p")}</p>
  <div class="stats">
    <div class="stat-item"><div class="stat-number">{stats["total_events"]}</div><div>Total Scraped</div></div>
    <div class="stat-item"><div class="stat-number">{stats["community_events"]}</div><div>Community Events</div></div>
    <div class="stat-item"><div class="stat-number">{stats["non_community_events"]}</div><div>Non-Community</div></div>
    <div class="stat-item"><div class="stat-number">{stats["needs_review"]}</div><div>Need Review</div></div>
  </div>
  <h2>Community Events for Calendar Upload</h2>
  <table>
    <thead><tr><th>Title</th><th>Date</th><th>Location</th><th>Confidence</th><th>Status</th></tr></thead>
    <tbody>{"".join(rows)}</tbody>
  </table>
  <h2>Next Steps</h2>
  <p>1. Review the events above, especially those flagged for review.</p>
  <p>2. Download the attached CSV for detailed information.</p>
  <p>3. Once approved, use the upload script to publish events to the calendar.</p>
  <p style="margin-top:30px;color:#7f8c8d;font-size:12px;">
    Automated email from the Community Event Classification System.
  </p>
</body>
</html>"""


def generate_confirmation_html(
    community_events_df: pd.DataFrame,
    created_ids: list,
    published_count: int,
) -> str:
    """Build the HTML body for the post-upload confirmation email."""
    rows: list[str] = []
    for _, event in community_events_df.iterrows():
        start_date = (
            pd.to_datetime(event["start"]).strftime("%b %d, %Y %I:%M %p")
            if pd.notna(event.get("start"))
            else "N/A"
        )
        location = event.get("location") or "N/A"
        if pd.isna(location):
            location = "N/A"
        rows.append(
            f"<tr><td><strong>{event['title']}</strong></td>"
            f"<td>{start_date}</td><td>{location}</td>"
            f"<td>{float(event.get('confidence', 0)):.1%}</td></tr>"
        )

    return f"""<!DOCTYPE html>
<html>
<head>
  <style>
    body{{font-family:Arial,sans-serif;margin:20px}}
    h1{{color:#2c3e50}} h2{{color:#34495e;margin-top:30px}}
    .summary{{background:#ecf0f1;padding:15px;border-radius:5px;margin:20px 0}}
    table{{border-collapse:collapse;width:100%;margin-top:20px}}
    th{{background:#3498db;color:white;padding:12px;text-align:left}}
    td{{padding:10px;border-bottom:1px solid #ddd}}
    tr:hover{{background:#f5f5f5}}
    .success{{color:#27ae60;font-weight:bold}}
  </style>
</head>
<body>
  <h1>Community Events Published to Calendar</h1>
  <div class="summary">
    <h2>Upload Summary</h2>
    <p><strong>Events Uploaded:</strong> {len(created_ids)}</p>
    <p><strong>Successfully Published:</strong> <span class="success">{published_count}</span></p>
    <p><strong>Date:</strong> {datetime.now().strftime("%B %d, %Y at %I:%M %p")}</p>
  </div>
  <h2>Published Events</h2>
  <table>
    <thead><tr><th>Title</th><th>Start Date</th><th>Location</th><th>Confidence</th></tr></thead>
    <tbody>{"".join(rows)}</tbody>
  </table>
  <p style="margin-top:30px;color:#7f8c8d;font-size:12px;">
    Automated confirmation from the Community Event Classification System.
  </p>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Delivery helpers
# ---------------------------------------------------------------------------


def _send(subject: str, html: str, cfg: dict, attachment: Path | None = None) -> bool:
    if not (cfg["sender_email"] and cfg["sender_password"] and cfg["recipient_email"]):
        logger.warning("Email not fully configured; skipping send.")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = cfg["sender_email"]
    msg["To"] = cfg["recipient_email"]
    msg.attach(MIMEText(html, "html"))

    if attachment is not None:
        try:
            with open(attachment, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f'attachment; filename="{attachment.name}"',
                )
                msg.attach(part)
        except OSError as exc:
            logger.warning("Could not attach %s: %s", attachment, exc)

    try:
        with smtplib.SMTP(cfg["smtp_server"], cfg["smtp_port"]) as server:
            server.starttls()
            server.login(cfg["sender_email"], cfg["sender_password"])
            server.send_message(msg)
        logger.info("Email sent to %s.", cfg["recipient_email"])
        return True
    except smtplib.SMTPException as exc:
        logger.error("Failed to send email: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def send_review_email(
    community_events_df: pd.DataFrame,
    all_events_df: pd.DataFrame,
    csv_path: Path,
) -> bool:
    """Send the classification-review digest email with a CSV attachment."""
    logger.info("Preparing review email...")
    cfg = _email_config()
    stats = {
        "total_events": len(all_events_df),
        "community_events": len(community_events_df),
        "non_community_events": len(all_events_df) - len(community_events_df),
        "needs_review": int(community_events_df.get("needs_review", pd.Series()).sum()),
    }
    html = generate_review_html(community_events_df, stats)
    subject = f"Community Event Review - {stats['community_events']} Events Found"
    return _send(subject, html, cfg, attachment=csv_path)


def send_upload_confirmation(
    community_events_df: pd.DataFrame,
    created_ids: list,
    published_count: int,
) -> bool:
    """Send the post-upload confirmation email."""
    logger.info("Sending upload confirmation email...")
    cfg = _email_config()
    html = generate_confirmation_html(community_events_df, created_ids, published_count)
    subject = f"Calendar Updated - {published_count} Community Events Published"
    return _send(subject, html, cfg)
