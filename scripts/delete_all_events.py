"""
Delete all events from WordPress EventON calendar.

Usage:
  python scripts/delete_all_events.py

Requires env vars: WP_SITE_URL, WP_USERNAME, WP_APP_PASSWORD
"""

import os
from datetime import datetime
import requests
from requests.auth import HTTPBasicAuth

SITE = os.getenv("WP_SITE_URL", "https://sandbox.envisionperdido.org").rstrip("/")
AUTH = HTTPBasicAuth(os.getenv("WP_USERNAME", ""), os.getenv("WP_APP_PASSWORD", ""))
API = f"{SITE}/wp-json/wp/v2"


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def fetch_all_events():
    """Fetch all events from WordPress."""
    all_events = []
    page = 1
    
    while True:
        try:
            r = requests.get(
                f"{API}/ajde_events",
                params={
                    "per_page": 100,
                    "page": page,
                    "status": "any",
                    "orderby": "id",
                    "order": "desc"
                },
                auth=AUTH,
                timeout=30,
            )
            
            if r.status_code == 200:
                events = r.json()
                if not events:
                    break
                all_events.extend(events)
                log(f"Fetched page {page}: {len(events)} events")
                page += 1
            else:
                log(f"Error fetching events: {r.status_code}")
                break
                
        except Exception as e:
            log(f"Error fetching events: {e}")
            break
    
    return all_events


def delete_event(event_id: int, force: bool = True) -> bool:
    """Delete a single event."""
    try:
        r = requests.delete(
            f"{API}/ajde_events/{event_id}",
            params={"force": "true"} if force else {},
            auth=AUTH,
            timeout=30,
        )
        
        if r.status_code in (200, 204):
            return True
        else:
            log(f"Failed to delete event {event_id}: {r.status_code}")
            return False
            
    except Exception as e:
        log(f"Error deleting event {event_id}: {e}")
        return False


def main():
    log("Starting WordPress event deletion...")
    
    if not (os.getenv("WP_USERNAME") and os.getenv("WP_APP_PASSWORD")):
        log("ERROR: WordPress credentials missing in environment.")
        return
    
    # Fetch all events
    log("Fetching all events...")
    events = fetch_all_events()
    
    if not events:
        log("No events found to delete.")
        return
    
    log(f"Found {len(events)} events to delete.")
    
    # Confirm deletion
    print("\n" + "="*80)
    print("WARNING: This will permanently delete ALL events from WordPress!")
    print("="*80)
    response = input(f"Delete all {len(events)} events? (type 'DELETE ALL' to confirm): ").strip()
    
    if response != "DELETE ALL":
        log("Deletion cancelled.")
        return
    
    # Delete all events
    log("\nDeleting events...")
    deleted = 0
    
    for event in events:
        event_id = event.get("id")
        event_title = event.get("title", {}).get("rendered", "Unknown")
        
        if delete_event(event_id):
            deleted += 1
            if deleted % 10 == 0:
                log(f"Progress: {deleted}/{len(events)} deleted")
    
    log(f"\nDone! Deleted {deleted}/{len(events)} events.")


if __name__ == "__main__":
    main()
