"""
WordPress EventON Calendar Uploader

This script uploads classified community events to the WordPress calendar
using the WordPress REST API.

EventON uses a custom post type called 'ajde_events'.
"""

import requests
import pandas as pd
import json
from datetime import datetime
from pathlib import Path
import os
import sys
from requests.auth import HTTPBasicAuth
import mimetypes
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables
from env_loader import load_env
load_env()

# WordPress Configuration
WORDPRESS_CONFIG = {
    "site_url": os.getenv("WP_SITE_URL", "https://sandbox.envisionperdido.org"),
    "username": os.getenv("WP_USERNAME", ""),  # WordPress admin username
    "app_password": os.getenv("WP_APP_PASSWORD", ""),  # WordPress Application Password
}

def log(message):
    """Print timestamped log message."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

class WordPressEventUploader:
    """Handle uploading events to WordPress EventON calendar."""
    
    def __init__(self, site_url, username, app_password, max_workers=5):
        self.site_url = site_url.rstrip('/')
        self.api_base = f"{self.site_url}/wp-json/wp/v2"
        self.auth = HTTPBasicAuth(username, app_password)
        self.session = requests.Session()
        self.max_workers = max_workers
        
    def test_connection(self):
        """Test WordPress API connection and authentication."""
        log("Testing WordPress API connection...")
        
        try:
            # Test basic API access
            response = self.session.get(f"{self.api_base}/users/me", auth=self.auth)
            
            if response.status_code == 200:
                user_data = response.json()
                log(f"OK: Connected as: {user_data.get('name', 'Unknown')}")
                return True
            elif response.status_code == 401:
                log("ERROR: Authentication failed! Check username and app password.")
                return False
            else:
                log(f"ERROR: API error: {response.status_code}")
                return False
                
        except Exception as e:
            log(f"ERROR: Connection error: {e}")
            return False
    
    def get_event_locations(self):
        """Get existing event locations from WordPress."""
        try:
            response = self.session.get(
                f"{self.api_base}/event_location",
                auth=self.auth
            )
            if response.status_code == 200:
                return {loc['name']: loc['id'] for loc in response.json()}
            return {}
        except Exception as e:
            log(f"Warning: Could not fetch locations: {e}")
            return {}
    
    def create_or_get_location(self, location_name):
        """Create a new location or get existing location ID."""
        if not location_name or pd.isna(location_name):
            return None
        
        # Check existing locations
        locations = self.get_event_locations()
        if location_name in locations:
            return locations[location_name]
        
        # Create new location
        try:
            response = self.session.post(
                f"{self.api_base}/event_location",
                auth=self.auth,
                json={"name": location_name}
            )
            if response.status_code == 201:
                return response.json()['id']
        except Exception as e:
            log(f"Warning: Could not create location '{location_name}': {e}")
        
        return None
    
    def parse_event_metadata(self, event_row):
        """Parse event data into EventON metadata format."""
        metadata = {}
        
        # Event start and end times
        # NOTE: EventON ignores hour/min/ampm fields and uses only evcal_srow epoch
        # EventON interprets the epoch as local time (not UTC), so we store the "local epoch"
        # i.e., the timestamp of the local time treating it as if it were UTC
        if pd.notna(event_row.get('start')):
            start_dt = pd.to_datetime(event_row['start'])
            start_local = start_dt  # Keep original for display
            try:
                from zoneinfo import ZoneInfo
                local_tz = ZoneInfo(os.getenv("SITE_TIMEZONE", "America/Chicago"))
                # Treat naive as local time
                if start_dt.tzinfo is None:
                    start_dt = start_dt.replace(tzinfo=local_tz)
                # WORKAROUND: Store "local epoch" - epoch of local time treating as UTC
                # Remove timezone info and get timestamp (treats as UTC)
                local_naive = start_dt.replace(tzinfo=None)
                metadata['evcal_srow'] = str(int(local_naive.timestamp()))
            except Exception:
                # Fallback: use naive timestamp
                metadata['evcal_srow'] = str(int(pd.Timestamp(start_dt).timestamp()))
            # Use local time for display fields (though EventON ignores these)
            metadata['evcal_start_date'] = start_local.strftime('%Y-%m-%d')
            metadata['evcal_start_time_hour'] = start_local.strftime('%I')
            metadata['evcal_start_time_min'] = start_local.strftime('%M')
            metadata['evcal_start_time_ampm'] = start_local.strftime('%p').lower()
        
        if pd.notna(event_row.get('end')):
            end_dt = pd.to_datetime(event_row['end'])
            end_local = end_dt  # Keep original for display
            try:
                from zoneinfo import ZoneInfo
                local_tz = ZoneInfo(os.getenv("SITE_TIMEZONE", "America/Chicago"))
                if end_dt.tzinfo is None:
                    end_dt = end_dt.replace(tzinfo=local_tz)
                # WORKAROUND: Store "local epoch"
                local_naive = end_dt.replace(tzinfo=None)
                metadata['evcal_erow'] = str(int(local_naive.timestamp()))
            except Exception:
                metadata['evcal_erow'] = str(int(pd.Timestamp(end_dt).timestamp()))
            # Use local time for display fields
            metadata['evcal_end_date'] = end_local.strftime('%Y-%m-%d')
            metadata['evcal_end_time_hour'] = end_local.strftime('%I')
            metadata['evcal_end_time_min'] = end_local.strftime('%M')
            metadata['evcal_end_time_ampm'] = end_local.strftime('%p').lower()
        
        # Location
        if pd.notna(event_row.get('location')):
            location_id = self.create_or_get_location(str(event_row['location']))
            if location_id:
                metadata['event_location'] = location_id
        
        # URL
        if pd.notna(event_row.get('url')):
            metadata['evcal_lmlink'] = str(event_row['url'])
        
        # EventON specific settings for better display
        metadata['_evcal_exlink_option'] = '1'  # Open link in new window
        metadata['_evcal_exlink_target'] = 'yes'  # Enable external link
        metadata['evo_hide_endtime'] = 'no'  # Show end time
        metadata['evo_year_long'] = 'no'  # Not a year-long event
        metadata['_evo_featured_img'] = 'no'  # Don't show featured image in event details popup
        
        return metadata
    
    def upload_image(self, image_path_or_url, title=None):
        """
        Upload an image to WordPress media library.
        
        Args:
            image_path_or_url: Local file path or URL to image
            title: Optional title for the image
            
        Returns:
            Media ID if successful, None otherwise
        """
        try:
            # Determine if it's a URL or local file
            if image_path_or_url.startswith('http://') or image_path_or_url.startswith('https://'):
                # Download image from URL
                response = requests.get(image_path_or_url, timeout=30)
                response.raise_for_status()
                image_data = response.content
                # Extract filename from URL
                filename = image_path_or_url.split('/')[-1].split('?')[0]
                if not filename or '.' not in filename:
                    filename = 'event_image.jpg'
            else:
                # Read local file
                with open(image_path_or_url, 'rb') as f:
                    image_data = f.read()
                filename = os.path.basename(image_path_or_url)
            
            # Determine MIME type
            mime_type, _ = mimetypes.guess_type(filename)
            if not mime_type:
                mime_type = 'image/jpeg'  # Default fallback
            
            # Upload to WordPress media library
            headers = {
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Type': mime_type
            }
            
            response = self.session.post(
                f"{self.api_base}/media",
                auth=self.auth,
                headers=headers,
                data=image_data
            )
            
            if response.status_code == 201:
                media_data = response.json()
                media_id = media_data['id']
                
                # Optionally update title
                if title:
                    self.session.post(
                        f"{self.api_base}/media/{media_id}",
                        auth=self.auth,
                        json={'title': title}
                    )
                
                log(f"   Uploaded image: {filename} (Media ID: {media_id})")
                return media_id
            else:
                log(f"   Warning: Failed to upload image: {response.status_code}")
                return None
                
        except Exception as e:
            log(f"   Warning: Error uploading image: {e}")
            return None
    
    def create_event(self, event_row, image_column='image_url'):
        """Create a single event in WordPress."""
        try:
            # Prepare event data
            title = event_row.get('title', 'Untitled Event')
            description = event_row.get('description', '')
            
            # Parse metadata
            metadata = self.parse_event_metadata(event_row)
            
            # Handle featured image for calendar thumbnail display ONLY
            if image_column in event_row and pd.notna(event_row[image_column]):
                image_source = event_row[image_column]
                featured_media_id = self.upload_image(image_source, title=title)
                
                if featured_media_id:
                    # Store ONLY in _thumbnail_id for EventON calendar tiles
                    # Do NOT set featured_media to avoid showing in popup
                    metadata['_thumbnail_id'] = str(featured_media_id)
            
            # Create post data - description only, no featured_media
            post_data = {
                'title': title,
                'content': description if pd.notna(description) else '',
                'status': 'draft',
                'type': 'ajde_events',
                'meta': metadata
            }
            
            # Send to WordPress
            response = self.session.post(
                f"{self.api_base}/ajde_events",
                auth=self.auth,
                json=post_data
            )
            
            if response.status_code == 201:
                event_data = response.json()
                log(f"OK: Created event: {title} (ID: {event_data['id']})")
                return event_data['id']
            else:
                log(f"ERROR: Failed to create event '{title}': {response.status_code}")
                log(f"   Response: {response.text[:200]}")
                return None
                
        except Exception as e:
            log(f"ERROR: Error creating event '{event_row.get('title', 'Unknown')}': {e}")
            return None
    
    def upload_events_from_csv(self, csv_path, dry_run=True, max_workers=None):
        """Upload events from CSV file in parallel."""
        log(f"Loading events from {csv_path}...")
        
        df = pd.read_csv(csv_path)
        log(f"Found {len(df)} events to upload")
        
        if dry_run:
            log("DRY RUN MODE - No events will be created")
            log("Review the following events:")
            for idx, row in df.iterrows():
                log(f"  - {row.get('title', 'Untitled')} ({row.get('start', 'No date')})")
            log(f"\nTo actually upload, run with dry_run=False")
            return []
        
        # Convert DataFrame rows to list for parallel processing
        events_list = [row for idx, row in df.iterrows()]
        workers = max_workers or self.max_workers
        
        # Upload events in parallel
        created_ids = self._create_events_parallel(events_list, workers)
        
        log(f"Upload complete: {len(created_ids)}/{len(df)} events created")
        return created_ids
    
    def _create_events_parallel(self, events_list, max_workers):
        """Create multiple events in parallel using thread pool."""
        created_ids = []
        total = len(events_list)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all event creation tasks
            future_to_event = {
                executor.submit(self.create_event, event): event
                for event in events_list
            }
            
            # Process completed creations as they finish
            for i, future in enumerate(as_completed(future_to_event), 1):
                try:
                    event_id = future.result()
                    if event_id:
                        created_ids.append(event_id)
                    
                    # Progress update every 5 events or on final completion
                    if i % 5 == 0 or i == total:
                        log(f"Progress: {i}/{total} events created")
                except Exception as e:
                    log(f"Error in event creation task: {e}")
        
        return created_ids
    
    def publish_events(self, event_ids, max_workers=None):
        """Publish events that were created as drafts in parallel."""
        log(f"Publishing {len(event_ids)} events...")
        
        workers = max_workers or self.max_workers
        published = self._publish_events_parallel(event_ids, workers)
        
        log(f"Published {published}/{len(event_ids)} events")
        return published
    
    def _publish_events_parallel(self, event_ids, max_workers):
        """Publish multiple events in parallel using thread pool."""
        published_count = 0
        total = len(event_ids)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all publish tasks
            future_to_event_id = {
                executor.submit(self._publish_single_event, event_id): event_id
                for event_id in event_ids
            }
            
            # Process completed publishes as they finish
            for i, future in enumerate(as_completed(future_to_event_id), 1):
                try:
                    if future.result():
                        published_count += 1
                    
                    # Progress update every 5 events or on final completion
                    if i % 5 == 0 or i == total:
                        log(f"Progress: {i}/{total} events published")
                except Exception as e:
                    log(f"Error in publish task: {e}")
        
        return published_count
    
    def _publish_single_event(self, event_id):
        """Publish a single event (helper for parallel publishing)."""
        try:
            response = self.session.post(
                f"{self.api_base}/ajde_events/{event_id}",
                auth=self.auth,
                json={'status': 'publish'}
            )
            return response.status_code == 200
        except Exception as e:
            log(f"Error publishing event {event_id}: {e}")
            return False

def setup_wordpress_credentials():
    """Interactive setup for WordPress credentials."""
    print("\n" + "="*80)
    print("WORDPRESS CREDENTIALS SETUP")
    print("="*80)
    print("\nYou need WordPress Application Password for authentication.")
    print("To create one:")
    print("1. Log into WordPress admin")
    print("2. Go to Users → Profile")
    print("3. Scroll to 'Application Passwords'")
    print("4. Enter a name (e.g., 'Event Uploader') and click 'Add New'")
    print("5. Copy the generated password (it will look like: 'xxxx xxxx xxxx xxxx xxxx xxxx')")
    print("\n" + "="*80)
    
    site_url = input("\nWordPress Site URL (default: https://sandbox.envisionperdido.org): ").strip()
    if not site_url:
        site_url = "https://sandbox.envisionperdido.org"
    
    username = input("WordPress Username: ").strip()
    app_password = input("Application Password: ").strip()
    
    # Save to environment variables (for this session)
    os.environ["WP_SITE_URL"] = site_url
    os.environ["WP_USERNAME"] = username
    os.environ["WP_APP_PASSWORD"] = app_password
    
    print("\nCredentials set for this session.")
    print("To make permanent, add to your environment variables or .env file:")
    print(f"  WP_SITE_URL={site_url}")
    print(f"  WP_USERNAME={username}")
    print(f"  WP_APP_PASSWORD=<your_password>")
    
    return site_url, username, app_password

def main():
    """Main upload workflow."""
    print("\n" + "="*80)
    print("WORDPRESS CALENDAR UPLOADER")
    print("="*80)
    
    # Check for credentials
    if not WORDPRESS_CONFIG['username'] or not WORDPRESS_CONFIG['app_password']:
        log("WordPress credentials not found in environment variables.")
        site_url, username, app_password = setup_wordpress_credentials()
    else:
        site_url = WORDPRESS_CONFIG['site_url']
        username = WORDPRESS_CONFIG['username']
        app_password = WORDPRESS_CONFIG['app_password']
        log(f"Using credentials from environment for {username}")
    
    # Create uploader
    uploader = WordPressEventUploader(site_url, username, app_password)
    
    # Test connection
    if not uploader.test_connection():
        log("Cannot continue without valid WordPress connection.")
        return
    
    # Find latest calendar upload file
    base_dir = Path(__file__).parent.parent
    # Check new organized path first, fall back to legacy
    output_dir = base_dir / "output" / "pipeline"
    if not output_dir.exists():
        output_dir = base_dir / "pipeline_output"
    
    if not output_dir.exists():
        log(f"Output directory not found: {output_dir}")
        log("Please run the automated pipeline first to generate events.")
        return
    
    # Find most recent calendar upload file
    csv_files = list(output_dir.glob("calendar_upload_*.csv"))
    if not csv_files:
        log("No calendar upload files found.")
        log("Please run the automated pipeline first.")
        return
    
    latest_csv = max(csv_files, key=lambda p: p.stat().st_mtime)
    log(f"Using file: {latest_csv.name}")
    
    # Upload events (dry run first)
    print("\n" + "="*80)
    print("DRY RUN - Reviewing events before upload")
    print("="*80)
    uploader.upload_events_from_csv(latest_csv, dry_run=True)
    
    # Confirm upload
    print("\n" + "="*80)
    response = input("Upload these events to WordPress? (yes/no): ").strip().lower()
    
    if response == 'yes':
        print("\n" + "="*80)
        print("UPLOADING TO WORDPRESS")
        print("="*80)
        created_ids = uploader.upload_events_from_csv(latest_csv, dry_run=False)
        
        if created_ids:
            response = input(f"\n{len(created_ids)} events created as DRAFTS. Publish them? (yes/no): ").strip().lower()
            if response == 'yes':
                uploader.publish_events(created_ids)
                log("OK: Upload complete! Check your WordPress calendar.")
            else:
                log("Events saved as drafts. You can publish them manually in WordPress.")
    else:
        log("Upload cancelled.")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    main()
