"""
Test script to validate that "Learn more" links are not using Chamber URLs.

This script:
1. Creates test events with Chamber URLs
2. Verifies they are rejected by the uploader
3. Scans existing events to ensure no Chamber URLs are present
4. Reports on the state of your WordPress site

Usage:
    python test_chamber_url_guard.py
"""

import os
import sys
import pandas as pd
import requests
from requests.auth import HTTPBasicAuth
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

from env_loader import load_env
load_env()

# Import the uploader
from wordpress_uploader import WordPressUploader

# Test configuration
TEST_EVENT_DATA = [
    {
        'title': '[TEST] Event with Chamber URL',
        'description': 'This is a test event with a Chamber URL in the url field.',
        'start': '2025-01-20T14:00:00',
        'end': '2025-01-20T15:00:00',
        'location': 'Test Venue',
        'url': 'https://business.perdidochamber.com/events/details/test-event-12345',
        'uid': 'test-chamber-url-guard-001',
        'tags': '["test"]'
    },
    {
        'title': '[TEST] Event with internal URL',
        'description': 'This is a test event with an internal/safe URL.',
        'start': '2025-01-21T14:00:00',
        'end': '2025-01-21T15:00:00',
        'location': 'Test Venue',
        'url': 'https://sandbox.envisionperdido.org/events/test-internal/',
        'uid': 'test-internal-url-guard-002',
        'tags': '["test"]'
    },
    {
        'title': '[TEST] Event with no URL',
        'description': 'This is a test event with no URL - should use internal permalink.',
        'start': '2025-01-22T14:00:00',
        'end': '2025-01-22T15:00:00',
        'location': 'Test Venue',
        'uid': 'test-no-url-guard-003',
        'tags': '["test"]'
    }
]


def log(message):
    """Print a log message."""
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)


def test_url_rejection():
    """Test that Chamber URLs are rejected during upload."""
    log("=" * 60)
    log("TEST: URL Rejection for Chamber Domains")
    log("=" * 60)
    
    # Create DataFrame from test data
    df = pd.DataFrame(TEST_EVENT_DATA)
    
    # Initialize uploader
    uploader = WordPressUploader()
    
    log("\nTesting URL field validation...")
    for idx, row in df.iterrows():
        title = row.get('title', 'Unknown')
        url = row.get('url', '(no URL)')
        
        # Parse metadata to see what gets stored
        metadata = uploader.parse_event_metadata(row)
        evcal_lmlink = metadata.get('evcal_lmlink', '(not set)')
        
        log(f"\nEvent {idx + 1}: {title}")
        log(f"  Input URL: {url}")
        log(f"  Stored evcal_lmlink: {evcal_lmlink}")
        
        # Verify: Chamber URLs should NOT be in metadata
        if 'perdidochamber.com' in url.lower():
            if evcal_lmlink == '(not set)':
                log("  ✓ PASS: Chamber URL was correctly rejected")
            else:
                log(f"  ✗ FAIL: Chamber URL was stored! Value: {evcal_lmlink}")
        
        # Verify: Internal URLs should be stored
        elif 'sandbox.envisionperdido.org' in url.lower():
            if evcal_lmlink == url:
                log("  ✓ PASS: Internal URL was correctly stored")
            else:
                log(f"  ✗ FAIL: Internal URL was not stored correctly")
        
        # Verify: Missing URL should not set evcal_lmlink
        elif '(no URL)' in url:
            if evcal_lmlink == '(not set)':
                log("  ✓ PASS: No URL field - evcal_lmlink not set (will use permalink)")
            else:
                log(f"  ✗ FAIL: evcal_lmlink should not be set for missing URLs")


def scan_existing_events():
    """Scan existing WordPress events for Chamber URLs."""
    log("\n" + "=" * 60)
    log("SCAN: Existing WordPress Events")
    log("=" * 60)
    
    WP_SITE_URL = os.getenv("WP_SITE_URL", "https://sandbox.envisionperdido.org").rstrip('/')
    WP_USERNAME = os.getenv("WP_USERNAME", "")
    WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD", "")
    
    API_BASE = f"{WP_SITE_URL}/wp-json/wp/v2"
    AUTH = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    
    BLOCKED_DOMAINS = ['perdidochamber.com', 'business.perdidochamber.com']
    
    try:
        log(f"\nFetching events from: {WP_SITE_URL}")
        
        # Fetch events with chamber URLs
        url = f"{API_BASE}/ajde_events"
        response = requests.get(
            url,
            params={'per_page': 100, '_fields': 'id,title,meta'},
            auth=AUTH,
            timeout=30
        )
        response.raise_for_status()
        events = response.json()
        
        log(f"Total events on site: {len(events)}")
        
        chamber_url_count = 0
        unsafe_events = []
        
        for event in events:
            event_id = event.get('id')
            title = event.get('title', {}).get('rendered', 'Unknown')[:50]
            meta = event.get('meta', {})
            evcal_lmlink = meta.get('evcal_lmlink', '')
            
            if evcal_lmlink:
                is_blocked = any(
                    domain in evcal_lmlink.lower()
                    for domain in BLOCKED_DOMAINS
                )
                
                if is_blocked:
                    chamber_url_count += 1
                    unsafe_events.append({
                        'id': event_id,
                        'title': title,
                        'url': evcal_lmlink
                    })
        
        log(f"\nEvents with Chamber URLs: {chamber_url_count}")
        
        if chamber_url_count == 0:
            log("✓ GOOD: No events with Chamber URLs found!")
        else:
            log(f"⚠ WARNING: Found {chamber_url_count} events with Chamber URLs:")
            for event in unsafe_events[:10]:  # Show first 10
                log(f"  - ID {event['id']}: {event['title']}")
                log(f"    URL: {event['url']}")
            if len(unsafe_events) > 10:
                log(f"  ... and {len(unsafe_events) - 10} more")
            log("\nRun 'python clean_chamber_urls.py' to remove these URLs")
    
    except requests.RequestException as e:
        log(f"ERROR: Could not connect to WordPress: {e}")
        log("Make sure WP_SITE_URL, WP_USERNAME, and WP_APP_PASSWORD are set")


def main():
    """Run all tests."""
    log("\n" + "=" * 60)
    log("CHAMBER URL SAFETY TEST SUITE")
    log("=" * 60)
    
    test_url_rejection()
    scan_existing_events()
    
    log("\n" + "=" * 60)
    log("TEST COMPLETE")
    log("=" * 60)


if __name__ == "__main__":
    main()
