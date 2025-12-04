#!/usr/bin/env python3
"""
Test storing events with LOCAL timezone epoch instead of UTC
This might be what EventON expects when WordPress timezone is set
"""
import os
import sys
import requests
import base64
from datetime import datetime
from zoneinfo import ZoneInfo

def load_env():
    """Load environment from env.ps1"""
    env = {}
    env_path = "scripts/windows/env.ps1"
    try:
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if "=" in line:
                        key, val = line.split("=", 1)
                        key = key.replace("$env:", "").strip()
                        val = val.strip().strip('"').strip("'")
                        env[key] = val
    except FileNotFoundError:
        print(f"Error: {env_path} not found")
        sys.exit(1)
    return env

def test_epoch_approaches():
    env = load_env()
    
    WP_URL = env.get("WP_SITE_URL", "https://sandbox.envisionperdido.org").rstrip("/")
    WP_USER = env.get("WP_USERNAME")
    WP_APP_PASSWORD = env.get("WP_APP_PASSWORD")
    
    # Create Basic Auth header
    credentials = base64.b64encode(f"{WP_USER}:{WP_APP_PASSWORD}".encode()).decode()
    headers = {
        "Authorization": f"Basic {credentials}",
        "Content-Type": "application/json"
    }
    
    # Get an existing event to test with
    print("Fetching first event to test...")
    response = requests.get(f"{WP_URL}/wp-json/wp/v2/ajde_events?per_page=1", 
                           headers=headers, verify=False)
    
    if response.status_code != 200 or not response.json():
        print("No events found")
        return
    
    event = response.json()[0]
    event_id = event['id']
    event_title = event['title']['rendered']
    
    print(f"\nTesting with event: {event_title} (ID: {event_id})")
    print(f"Current evcal_srow: {event['meta'].get('evcal_srow', 'N/A')}")
    print(f"Current evcal_start_time_hour: {event['meta'].get('evcal_start_time_hour', 'N/A')}")
    
    # The event is currently Dec 31 at 7 PM CST
    # UTC epoch for Dec 31, 2025 @ 7 PM CST = 1767229200
    # Local "fake" epoch treating 7 PM as UTC = 1767211200
    
    cst = ZoneInfo("America/Chicago")
    
    # Target: Dec 31, 2025 @ 7 PM CST
    target_dt = datetime(2025, 12, 31, 19, 0, 0, tzinfo=cst)
    
    # Method 1: Correct UTC epoch (current approach)
    utc_epoch = int(target_dt.timestamp())
    
    # Method 2: Local "fake" epoch (treat local time as UTC seconds)
    local_fake_epoch = int(target_dt.replace(tzinfo=None).timestamp())
    
    print(f"\nTarget time: Dec 31, 2025 @ 7 PM CST")
    print(f"Method 1 - UTC epoch: {utc_epoch} (should display 7 PM if WP timezone applied)")
    print(f"Method 2 - Local fake epoch: {local_fake_epoch} (might display 7 PM if EventON ignores WP tz)")
    
    # Verify current approach
    print(f"\nCurrent approach uses: {utc_epoch}")
    print(f"If EventON displays this as 1 AM UTC, try using: {local_fake_epoch}")
    
    # Print CSV format for reference
    print(f"\nFor CSV upload with Method 2, use:")
    print(f"evcal_srow: {local_fake_epoch}")
    print(f"evcal_start_time_hour: 07")
    print(f"evcal_start_time_min: 00")
    print(f"evcal_start_time_ampm: pm")

if __name__ == "__main__":
    test_epoch_approaches()
