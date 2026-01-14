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

import sys
import os
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np
import joblib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import json

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
from env_loader import load_env
load_env()
# Import scraper from scripts directory
from scripts.Envision_Perdido_DataCollection import scrape_month, save_events_csv, save_events_json

# Configuration
BASE_DIR = Path(__file__).parent.parent
MODEL_PATH = BASE_DIR / "data" / "artifacts" / "event_classifier_model.pkl"
VECTORIZER_PATH = BASE_DIR / "data" / "artifacts" / "event_vectorizer.pkl"
IMAGE_CONFIG_PATH = BASE_DIR / "data" / "image_keyword_config.json"
IMAGES_DIR = BASE_DIR / "data" / "event_images"
# Organized output path
OUTPUT_DIR = BASE_DIR / "output" / "pipeline"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Email configuration (set these as environment variables for security)
EMAIL_CONFIG = {
    "smtp_server": os.getenv("SMTP_SERVER", "smtp.gmail.com"),
    "smtp_port": int(os.getenv("SMTP_PORT", "587")),
    "sender_email": os.getenv("SENDER_EMAIL", ""),
    "sender_password": os.getenv("EMAIL_PASSWORD", ""),
    "recipient_email": os.getenv("RECIPIENT_EMAIL", ""),
}

def log(message):
    """Print timestamped log message."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def build_features(df):
    """Build text features from event data."""
    features = []
    for _, row in df.iterrows():
        parts = []
        if pd.notna(row.get('title')):
            parts.append(str(row['title']))
        if pd.notna(row.get('description')):
            parts.append(str(row['description']))
        if pd.notna(row.get('location')):
            parts.append(str(row['location']))
        if pd.notna(row.get('category')):
            parts.append(str(row['category']))
        features.append(' '.join(parts))
    return features

def scrape_events(year=None, month=None):
    """Scrape events from the chamber website."""
    log("Starting event scraping...")
    
    if year is None:
        year = datetime.now().year
    if month is None:
        month = datetime.now().month
    
    all_events = []
    
    # Scrape current month and next month
    for m in range(month, min(month + 2, 13)):
        month_str = f"{year}-{m:02d}-01"
        month_url = f"https://business.perdidochamber.com/events/calendar/{month_str}"
        log(f"Scraping {month_url}...")
        
        try:
            from scripts.Envision_Perdido_DataCollection import scrape_month
            events = scrape_month(month_url)
            log(f"Scraped {len(events)} events from {month_url}")
            all_events.extend(events)
        except Exception as e:
            log(f"Error scraping {month_url}: {e}")
    
    log(f"Total events scraped: {len(all_events)}")
    return all_events

def assign_event_images(events_df):
    """
    Assign images to events based on weighted keyword scoring.
    
    Scores each image against event text (title, description, location)
    using keyword weights from configuration file. Assigns the highest-
    scoring image to each event.
    
    Returns:
        DataFrame with 'image_url' column added (absolute path or None)
    """
    if not IMAGE_CONFIG_PATH.exists():
        log("Warning: Image config not found, skipping image assignment")
        events_df['image_url'] = None
        return events_df
    
    log("Assigning images based on keyword scoring...")
    
    # Load image keyword configuration
    with open(IMAGE_CONFIG_PATH, 'r') as f:
        config = json.load(f)
    
    images_config = config.get('images', {})
    min_threshold = config.get('config', {}).get('min_score_threshold', 0)
    
    if not images_config:
        log("Warning: No images configured, skipping image assignment")
        events_df['image_url'] = None
        return events_df
    
    # Process each event
    assigned_images = []
    for _, event in events_df.iterrows():
        # Build event text from all relevant fields
        event_text_parts = []
        if pd.notna(event.get('title')):
            event_text_parts.append(str(event['title']).lower())
        if pd.notna(event.get('description')):
            event_text_parts.append(str(event['description']).lower())
        if pd.notna(event.get('location')):
            event_text_parts.append(str(event['location']).lower())
        if pd.notna(event.get('category')):
            event_text_parts.append(str(event['category']).lower())
        
        event_text = ' '.join(event_text_parts)
        
        # Score each image
        image_scores = {}
        for image_file, image_data in images_config.items():
            score = 0
            keywords = image_data.get('keywords', {})
            
            for keyword, weight in keywords.items():
                if keyword.lower() in event_text:
                    score += weight
            
            image_scores[image_file] = score
        
        # Find best match
        if image_scores:
            best_image = max(image_scores, key=image_scores.get)
            best_score = image_scores[best_image]
            
            # Apply threshold
            if best_score >= min_threshold and best_score > 0:
                image_path = os.path.abspath(os.path.join(IMAGES_DIR, best_image))
                assigned_images.append(image_path)
            else:
                assigned_images.append(None)
        else:
            assigned_images.append(None)
    
    events_df['image_url'] = assigned_images
    
    # Report statistics
    assigned_count = sum(1 for img in assigned_images if img is not None)
    log(f"Image assignment complete: {assigned_count}/{len(events_df)} events assigned images")
    
    return events_df

def classify_events(events_df):
    """Classify events using trained SVM model."""
    log("Loading trained model...")
    
    if not MODEL_PATH.exists() or not VECTORIZER_PATH.exists():
        log("ERROR: Model files not found! Please train the model first.")
        return None
    
    model = joblib.load(MODEL_PATH)
    vectorizer = joblib.load(VECTORIZER_PATH)
    
    log(f"Classifying {len(events_df)} events...")
    
    # Build features and classify
    X_text = build_features(events_df)
    X = vectorizer.transform(X_text)
    
    predictions = model.predict(X)
    probabilities = model.predict_proba(X)
    confidence = np.max(probabilities, axis=1)
    
    events_df['is_community_event'] = predictions
    events_df['confidence'] = confidence
    
    # Add review flag for low confidence predictions
    events_df['needs_review'] = events_df['confidence'] < 0.75
    
    community_count = predictions.sum()
    log(f"Classification complete: {community_count} community events, {len(events_df) - community_count} non-community events")
    
    # Assign images based on keyword scoring
    events_df = assign_event_images(events_df)
    
    return events_df

def generate_review_html(community_events_df, stats):
    """Generate HTML email for event review."""
    
    html = f"""
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
            .button {{ display: inline-block; padding: 10px 20px; background: #3498db; color: white; text-decoration: none; border-radius: 5px; margin: 10px 5px; }}
            .approve {{ background: #27ae60; }}
            .reject {{ background: #e74c3c; }}
        </style>
    </head>
    <body>
        <h1>Community Event Classification Review</h1>
        <p>Run Date: {datetime.now().strftime("%B %d, %Y at %I:%M %p")}</p>
        
        <div class="stats">
            <div class="stat-item">
                <div class="stat-number">{stats['total_events']}</div>
                <div>Total Events Scraped</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{stats['community_events']}</div>
                <div>Community Events</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{stats['non_community_events']}</div>
                <div>Non-Community Events</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{stats['needs_review']}</div>
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
    
    for _, event in community_events_df.iterrows():
        confidence = event['confidence']
        confidence_class = 'high-confidence' if confidence >= 0.75 else 'low-confidence'
        row_class = 'review-needed' if event['needs_review'] else ''
        status = 'Review Needed' if event['needs_review'] else 'High Confidence'
        
        start_date = pd.to_datetime(event['start']).strftime("%b %d, %Y %I:%M %p") if pd.notna(event['start']) else 'N/A'
        location = event.get('location', 'N/A')
        if pd.isna(location):
            location = 'N/A'
        
        html += f"""
                <tr class="{row_class}">
                    <td><strong>{event['title']}</strong></td>
                    <td>{start_date}</td>
                    <td>{location}</td>
                    <td class="{confidence_class}">{confidence:.1%}</td>
                    <td>{status}</td>
                </tr>
        """
    
    html += """
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
    """
    
    return html

def send_email_notification(community_events_df, all_events_df, csv_path):
    """Send email notification with classified events."""
    log("Preparing email notification...")
    
    # Calculate statistics
    stats = {
        'total_events': len(all_events_df),
        'community_events': len(community_events_df),
        'non_community_events': len(all_events_df) - len(community_events_df),
        'needs_review': community_events_df['needs_review'].sum(),
    }
    
    # Generate HTML email
    html_content = generate_review_html(community_events_df, stats)
    
    # Create email message
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"Community Event Review - {stats['community_events']} Events Found"
    msg['From'] = EMAIL_CONFIG['sender_email']
    msg['To'] = EMAIL_CONFIG['recipient_email']
    
    # Attach HTML
    msg.attach(MIMEText(html_content, 'html'))
    
    # Attach CSV file
    try:
        with open(csv_path, 'rb') as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename="{csv_path.name}"')
            msg.attach(part)
    except Exception as e:
        log(f"Warning: Could not attach CSV file: {e}")
    
    # Send email
    try:
        log(f"Sending email to {EMAIL_CONFIG['recipient_email']}...")
        with smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as server:
            server.starttls()
            server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
            server.send_message(msg)
        log("Email sent successfully!")
        return True
    except Exception as e:
        log(f"ERROR: Failed to send email: {e}")
        log("Please check your email configuration and credentials.")
        return False

def export_for_calendar(community_events_df, format='csv'):
    """Export community events in format ready for calendar upload.
    
    Uses automated keyword-based image assignment from classification.
    """
    log(f"Exporting events for calendar upload (format: {format})...")
    
    # Use automated image assignments from classification
    df = community_events_df.copy()
    
    # Log image assignment statistics
    events_with_images = len([x for x in df.get('image_url', [None] * len(df)) if pd.notna(x)])
    log(f"Automated keyword-based image assignments: {events_with_images} events with images")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if format == 'csv':
        output_path = OUTPUT_DIR / f"calendar_upload_{timestamp}.csv"
        df.to_csv(output_path, index=False)
        log(f"CSV export saved to {output_path}")
        return output_path
    
    elif format == 'json':
        output_path = OUTPUT_DIR / f"calendar_upload_{timestamp}.json"
        df.to_json(output_path, orient='records', indent=2)
        log(f"JSON export saved to {output_path}")
        return output_path
    
    elif format == 'ical':
        # TODO: Implement iCal export for calendar systems that accept .ics files
        log("iCal export not yet implemented")
        return None
    
    return None

def upload_to_wordpress(csv_path):
    """Upload events to WordPress and return results."""
    from wordpress_uploader import WordPressEventUploader
    
    # Get WordPress credentials from environment
    site_url = os.getenv("WP_SITE_URL", "")
    username = os.getenv("WP_USERNAME", "")
    app_password = os.getenv("WP_APP_PASSWORD", "")
    
    if not username or not app_password:
        log("ERROR: WordPress credentials not configured")
        return None, None
    
    log("Connecting to WordPress...")
    uploader = WordPressEventUploader(site_url, username, app_password)
    
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

def send_upload_confirmation_email(community_events_df, created_ids, published_count):
    """Send confirmation email with upload results."""
    log("Sending upload confirmation email...")
    
    # Generate HTML for confirmation
    html = f"""
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
    
    # Add event rows
    for _, event in community_events_df.iterrows():
        start_date = pd.to_datetime(event['start']).strftime("%b %d, %Y %I:%M %p") if pd.notna(event['start']) else 'N/A'
        location = event.get('location', 'N/A')
        if pd.isna(location):
            location = 'N/A'
        confidence = event.get('confidence', 0)
        
        html += f"""
                <tr>
                    <td><strong>{event['title']}</strong></td>
                    <td>{start_date}</td>
                    <td>{location}</td>
                    <td>{confidence:.1%}</td>
                </tr>
        """
    
    html += """
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
    """
    
    # Create email message
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"Calendar Updated - {published_count} Community Events Published"
    msg['From'] = EMAIL_CONFIG['sender_email']
    msg['To'] = EMAIL_CONFIG['recipient_email']
    msg.attach(MIMEText(html, 'html'))
    
    # Send email
    try:
        with smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as server:
            server.starttls()
            server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
            server.send_message(msg)
        log("Upload confirmation email sent successfully!")
        return True
    except Exception as e:
        log(f"ERROR: Failed to send confirmation email: {e}")
        return False

def main():
    """Run the complete automated pipeline."""
    log("=" * 80)
    log("AUTOMATED COMMUNITY EVENT CLASSIFICATION PIPELINE")
    log("=" * 80)
    
    try:
        # Step 1: Scrape events
        events = scrape_events()
        if not events:
            log("No events scraped. Exiting.")
            return
        
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
            return
        
        # Step 3: Filter community events and remove unreasonably long events
        community_events = classified_df[classified_df['is_community_event'] == 1].copy()
        
        # Filter out events longer than 60 days (likely recurring stubs or data errors)
        if len(community_events) > 0 and 'start' in community_events.columns and 'end' in community_events.columns:
            community_events['_start_dt'] = pd.to_datetime(community_events['start'], errors='coerce')
            community_events['_end_dt'] = pd.to_datetime(community_events['end'], errors='coerce')
            community_events['_duration_days'] = (community_events['_end_dt'] - community_events['_start_dt']).dt.days
            
            before_filter = len(community_events)
            community_events = community_events[community_events['_duration_days'].fillna(0) <= 60].copy()
            community_events.drop(columns=['_start_dt', '_end_dt', '_duration_days'], inplace=True)
            
            filtered_out = before_filter - len(community_events)
            if filtered_out > 0:
                log(f"Filtered out {filtered_out} events with duration > 60 days")
        
        log(f"Found {len(community_events)} community events")
        
        # Step 4: Export for calendar
        calendar_csv = export_for_calendar(community_events, format='csv')
        
        # Step 5: Send email notification
        if EMAIL_CONFIG['sender_email'] != "your_email@example.com":
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
                send_upload_confirmation_email(community_events, created_ids, published_count)
            elif created_ids is not None:
                log("Upload completed but some events may not have published")
            else:
                log("Upload failed - check WordPress credentials and connection")
        else:
            log("\n" + "=" * 80)
            log("AUTO_UPLOAD disabled - manual upload required")
            log(f"Use: python scripts/wordpress_uploader.py {calendar_csv}")
            log("=" * 80)
        
        log("\n" + "=" * 80)
        log("PIPELINE COMPLETE!")
        log("=" * 80)
        
    except Exception as e:
        log(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
