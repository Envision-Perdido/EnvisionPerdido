#!/usr/bin/env python3
"""
WordPress Authentication Diagnostic

Tests whether your credentials allow EDIT privileges as required for:
- status=any queries (see all event statuses, not just published)
- DELETE operations on events
- POST operations (create/update events)

The supervisor's diagnosis: The API shows published events fine,
but DELETE/status=any fail with 401 "rest_not_authorized".
This means you're NOT properly authenticated with EDIT privileges.

Solution: Generate a new app password in WordPress.
"""

import base64
import os
import sys
from pathlib import Path

import requests

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

from env_loader import load_env


def test_authentication():
    """Test if user is properly authenticated"""
    load_env(verbose=False)

    site_url = os.environ.get("WP_SITE_URL", "").rstrip("/")
    username = os.environ.get("WP_USERNAME", "")
    app_password = os.environ.get("WP_APP_PASSWORD", "")

    if not all([site_url, username, app_password]):
        print(" Missing credentials in environment!")
        return False

    # Create Basic Auth header
    creds_str = f"{username}:{app_password}"
    creds_b64 = base64.b64encode(creds_str.encode()).decode()
    headers = {"Authorization": f"Basic {creds_b64}"}

    print("=" * 70)
    print("WORDPRESS AUTHENTICATION DIAGNOSTIC")
    print("=" * 70)
    print()
    print(f"Testing credentials for user: {username}")
    print(f"WordPress Site: {site_url}")
    print()

    # Test 1: /users/me (requires proper authentication with Basic Auth)
    print(" TEST 1: /wp-json/wp/v2/users/me")
    print("   (Verifies Basic Auth is working)")
    print("   " + "-" * 60)

    try:
        response = requests.get(
            f"{site_url}/wp-json/wp/v2/users/me", headers=headers, verify=False, timeout=10
        )

        if response.status_code == 200:
            user = response.json()
            print(f"    STATUS: {response.status_code} OK")
            print(f"    Authenticated as: {user.get('name', 'Unknown')}")
            print(f"    User ID: {user.get('id')}")
            print(f"    Email: {user.get('email')}")

            # Check capabilities
            caps = user.get("capabilities", {})
            has_edit = "edit_posts" in caps or "edit_ajde_events" in caps
            print(f"    Has EDIT capability: {has_edit}")
            test1_pass = True
        else:
            print(f"    STATUS: {response.status_code}")
            error_resp = response.json()
            print(f"    Error: {error_resp.get('code', 'UNKNOWN')}")
            print(f"    Message: {error_resp.get('message', 'No message')}")
            test1_pass = False

    except Exception as e:
        print(f"    Exception: {str(e)}")
        test1_pass = False

    print()

    # Test 2: GET published events (should work)
    print("📋 TEST 2: GET /wp-json/wp/v2/ajde_events (published)")
    print("   (Should work with or without auth)")
    print("   " + "-" * 60)

    try:
        response = requests.get(
            f"{site_url}/wp-json/wp/v2/ajde_events?per_page=5",
            headers=headers,
            verify=False,
            timeout=10,
        )

        if response.status_code == 200:
            events = response.json()
            print(f"    STATUS: {response.status_code} OK")
            print(f"    Found {len(events)} published events")
        else:
            print(f"    STATUS: {response.status_code}")

    except Exception as e:
        print(f"    Exception: {str(e)}")
        #test2_pass = False

    print()

    # Test 3: GET with status=any (requires EDIT privileges)
    print(" TEST 3: GET /wp-json/wp/v2/ajde_events?status=any")
    print("   (Requires EDIT privileges - this is where it likely fails)")
    print("   " + "-" * 60)

    try:
        response = requests.get(
            f"{site_url}/wp-json/wp/v2/ajde_events?per_page=5&status=any",
            headers=headers,
            verify=False,
            timeout=10,
        )

        if response.status_code == 200:
            events = response.json()
            print(f"   STATUS: {response.status_code} OK")
            print("    Can access ALL statuses (drafts, published, etc)")
            print(f"   Found {len(events)} events")
            test3_pass = True
        elif response.status_code == 400:
            error_resp = response.json()
            print(f"    STATUS: {response.status_code}")
            print(f"    Error Code: {error_resp.get('code')}")
            print(f"    Message: {error_resp.get('message')}")
            print("   ➜ This means you don't have EDIT privileges")
            test3_pass = False
        else:
            print(f"    STATUS: {response.status_code}")
            print(f"    Response: {response.text[:200]}")
            test3_pass = False

    except Exception as e:
        print(f"    Exception: {str(e)}")
        test3_pass = False

    print()
    print("=" * 70)
    print("DIAGNOSIS")
    print("=" * 70)
    print()

    if test1_pass:
        print(" Your credentials ARE properly authenticated!")
        print()
        if test3_pass:
            print(" You have EDIT privileges - can see all statuses")
            print(" You should be able to DELETE events")
            return True
        else:
            print("  But you DON'T have EDIT privileges for EventON events")
            print()
            print("POSSIBLE CAUSES:")
            print("  1. Your user doesn't have 'edit_ajde_events' capability")
            print("  2. Your app password doesn't grant edit permissions")
            print("  3. The EventON plugin isn't properly configured")
            print()
            print("SOLUTIONS:")
            print("  1. Check WordPress user role has 'edit_ajde_events'")
            print("  2. Generate a NEW application password")
            print("  3. Verify EventON plugin is activated")
            return False
    else:
        print(" Your credentials are NOT properly authenticated!")
        print()
        print("Your user/app password combination is invalid.")
        print()
        print("SOLUTION:")
        print("  1. Go to: https://sandbox.envisionperdido.org/wp-admin/profile.php")
        print("  2. Scroll to 'Application Passwords'")
        print("  3. Enter an app name (e.g., 'EventON Upload')")
        print("  4. Click 'Create Application Password'")
        print("  5. Copy the generated 24-character password")
        print("  6. Update: scripts/windows/env.ps1")
        print("  7. Run this test again")
        print()
        return False


if __name__ == "__main__":
    success = test_authentication()
    sys.exit(0 if success else 1)
