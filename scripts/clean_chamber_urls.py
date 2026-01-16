"""
Clean up Chamber of Commerce URLs from existing events.

This script removes 'evcal_lmlink' meta field containing Chamber URLs
from existing events that were uploaded with the old unsafe logic.

Usage:
    python clean_chamber_urls.py
    
Environment Variables:
    WP_SITE_URL - WordPress site URL
    WP_USERNAME - WordPress admin username
    WP_APP_PASSWORD - WordPress Application Password
"""

import os
import sys
import requests
from requests.auth import HTTPBasicAuth
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

from env_loader import load_env
load_env()

# WordPress Configuration
WP_SITE_URL = os.getenv("WP_SITE_URL", "https://sandbox.envisionperdido.org").rstrip('/')
WP_USERNAME = os.getenv("WP_USERNAME", "")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD", "")

API_BASE = f"{WP_SITE_URL}/wp-json/wp/v2"
AUTH = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)

# Blocked domains that should NOT appear in evcal_lmlink
BLOCKED_DOMAINS = ['perdidochamber.com', 'business.perdidochamber.com']


def log(message):
    """Print a log message with timestamp."""
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)


def get_all_events(page=1, per_page=100):
    """Fetch all events from WordPress.
    
    Args:
        page: Page number (1-indexed)
        per_page: Items per page (max 100)
    
    Returns:
        List of event objects
    """
    url = f"{API_BASE}/ajde_events"
    params = {
        'per_page': per_page,
        'page': page,
        '_fields': 'id,title,meta'
    }
    
    try:
        response = requests.get(url, params=params, auth=AUTH, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        log(f"ERROR: Failed to fetch events from page {page}: {e}")
        return []


def clean_event_url(event_id, evcal_lmlink):
    """Remove or clean the evcal_lmlink meta field for an event.
    
    Args:
        event_id: WordPress event post ID
        evcal_lmlink: Current value of evcal_lmlink
    
    Returns:
        True if cleaned successfully, False otherwise
    """
    url = f"{API_BASE}/ajde_events/{event_id}"
    
    # Send request to remove the meta field by setting it to empty
    patch_data = {
        'meta': {
            'evcal_lmlink': ''  # Empty string removes the field
        }
    }
    
    try:
        response = requests.post(
            url,
            json=patch_data,
            auth=AUTH,
            timeout=30
        )
        response.raise_for_status()
        log(f"CLEANED: Event ID {event_id} - removed Chamber URL: {evcal_lmlink}")
        return True
    except requests.RequestException as e:
        log(f"ERROR: Failed to clean event {event_id}: {e}")
        return False


def main():
    """Main cleanup routine."""
    log("Starting Chamber URL cleanup...")
    log(f"WordPress Site: {WP_SITE_URL}")
    log(f"Blocked domains: {', '.join(BLOCKED_DOMAINS)}")
    log("")
    
    total_events = 0
    events_with_chamber_urls = 0
    cleaned_count = 0
    
    page = 1
    while True:
        events = get_all_events(page=page)
        
        if not events:
            break
        
        for event in events:
            total_events += 1
            event_id = event.get('id')
            title = event.get('title', {}).get('rendered', 'Unknown')
            meta = event.get('meta', {})
            evcal_lmlink = meta.get('evcal_lmlink', '')
            
            # Check if URL contains blocked domain
            if evcal_lmlink:
                is_blocked = any(
                    domain in evcal_lmlink.lower()
                    for domain in BLOCKED_DOMAINS
                )
                
                if is_blocked:
                    events_with_chamber_urls += 1
                    log(f"FOUND: Event {event_id} ({title})")
                    log(f"  URL: {evcal_lmlink}")
                    
                    # Clean it
                    if clean_event_url(event_id, evcal_lmlink):
                        cleaned_count += 1
        
        page += 1
    
    log("")
    log("=== Cleanup Summary ===")
    log(f"Total events scanned: {total_events}")
    log(f"Events with Chamber URLs found: {events_with_chamber_urls}")
    log(f"Events cleaned: {cleaned_count}")
    log("")
    
    if events_with_chamber_urls == 0:
        log("✓ No Chamber URLs found. Your site is clean!")
    else:
        log(f"✓ Cleaned {cleaned_count}/{events_with_chamber_urls} events")
        if cleaned_count < events_with_chamber_urls:
            log("⚠ Some events could not be cleaned. Check logs above.")


if __name__ == "__main__":
    main()
