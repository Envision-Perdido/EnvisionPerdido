#!/usr/bin/env python3
"""
Test DELETE operations on EventON events

The supervisor reported: DELETE attempts return HTTP 401 with error "rest_not_authorized"

This test will:
1. Find a test event
2. Attempt to DELETE it
3. Report back the exact error

DO NOT RUN ON PRODUCTION - only on sandbox!
"""

import base64
import io
import os
import sys
from pathlib import Path

import requests

# Fix Unicode on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

sys.path.insert(0, str(Path(__file__).parent))
from env_loader import load_env


def test_delete_operation():
    """Test DELETE capability"""
    load_env(verbose=False)

    site_url = os.environ.get("WP_SITE_URL", "").rstrip("/")
    username = os.environ.get("WP_USERNAME", "")
    app_password = os.environ.get("WP_APP_PASSWORD", "")

    creds_b64 = base64.b64encode(f"{username}:{app_password}".encode()).decode()
    headers = {"Authorization": f"Basic {creds_b64}"}

    print("=" * 70)
    print("DELETE OPERATION TEST")
    print("=" * 70)
    print()
    print(f"User: {username}")
    print(f"Site: {site_url}")
    print()

    # Step 1: Get list of events
    print("STEP 1: Fetching events...")
    try:
        response = requests.get(
            f"{site_url}/wp-json/wp/v2/ajde_events?per_page=100&status=any",
            headers=headers,
            verify=False,
            timeout=10,
        )

        if response.status_code != 200:
            print(f"❌ Failed to fetch events: {response.status_code}")
            return

        events = response.json()
        print(f"✅ Found {len(events)} events")

        if not events:
            print("⚠️  No events to test DELETE on")
            return

        # Get first event
        event = events[0]
        event_id = event["id"]
        event_title = event["title"]["rendered"]

        print(f"✅ Target event: {event_title} (ID: {event_id})")
        print()

    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return

    # Step 2: Attempt DELETE
    print("STEP 2: Attempting DELETE...")
    print(f"DELETE /wp-json/wp/v2/ajde_events/{event_id}")
    print()

    try:
        response = requests.delete(
            f"{site_url}/wp-json/wp/v2/ajde_events/{event_id}",
            headers=headers,
            verify=False,
            timeout=10,
        )

        print(f"Status: {response.status_code}")
        print()

        if response.status_code == 200:
            print("✅ DELETE SUCCESSFUL!")
            result = response.json()
            print(f"   Event deleted: {result.get('title', {}).get('rendered', 'Unknown')}")

        elif response.status_code == 401:
            print("❌ HTTP 401 - NOT AUTHORIZED")
            error = response.json()
            print(f"   Error Code: {error.get('code')}")
            print(f"   Message: {error.get('message')}")
            print()
            print("POSSIBLE CAUSES:")
            print("  1. User doesn't have 'delete_ajde_events' capability")
            print("  2. EventON REST API helper plugin not installed")
            print("  3. App password doesn't have delete permissions")

        elif response.status_code == 403:
            print("❌ HTTP 403 - FORBIDDEN")
            error = response.json()
            print(f"   Error: {error.get('message')}")
            print()
            print("This means the event exists but you can't delete it.")
            print("Check your user role permissions for EventON events.")

        elif response.status_code == 404:
            print("❌ HTTP 404 - NOT FOUND")
            print("   Event with ID {event_id} doesn't exist")

        else:
            print(f"❌ HTTP {response.status_code}")
            print(f"   Response: {response.text[:300]}")

        print()
        print("=" * 70)
        print("FULL RESPONSE HEADERS")
        print("=" * 70)
        for key, val in response.headers.items():
            print(f"{key}: {val}")

        print()
        print("=" * 70)
        print("FULL RESPONSE BODY")
        print("=" * 70)
        print(response.text)

    except Exception as e:
        print(f"❌ Exception: {str(e)}")


if __name__ == "__main__":
    test_delete_operation()
