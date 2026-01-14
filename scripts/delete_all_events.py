"""Delete all events from WordPress EventON calendar.

Usage:
    python scripts/delete_all_events.py [--dry-run] [--yes]

Options:
    --dry-run   Print the list of events that would be deleted and exit.
    --yes       Skip the interactive "DELETE ALL" prompt (use with caution).

Requires env vars: WP_SITE_URL, WP_USERNAME, WP_APP_PASSWORD
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import argparse
import base64
import requests
from requests.auth import HTTPBasicAuth

# Add scripts directory to path and load environment
sys.path.insert(0, str(Path(__file__).parent))
from env_loader import load_env
load_env()

SITE = os.getenv("WP_SITE_URL", "https://sandbox.envisionperdido.org").rstrip("/")
AUTH = HTTPBasicAuth(os.getenv("WP_USERNAME", ""), os.getenv("WP_APP_PASSWORD", ""))
API = f"{SITE}/wp-json/wp/v2"

# When set, use an explicit Authorization header (Basic base64) instead of
# requests' auth=HTTPBasicAuth. This is an explicit, temporary workaround for
# environments where an intermediary (proxy/WAF) strips Basic auth supplied
# via the requests lib. Default is False; enable with the CLI flag
# --explicit-auth or the env var DELETE_USE_EXPLICIT_AUTH=1
USE_EXPLICIT_AUTH = False


def _explicit_auth_header():
    """Return dict of Authorization header (Basic base64(username:password))."""
    user = os.getenv("WP_USERNAME", "")
    pwd = os.getenv("WP_APP_PASSWORD", "")
    token = base64.b64encode(f"{user}:{pwd}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {token}"}


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def fetch_all_events(debug: bool = False):
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
                if debug:
                    print(f"DEBUG: GET {r.url}\nResponse status: {r.status_code}\nResponse body (truncated):\n{str(r.text)[:1000]}\n--- end debug ---")

                try:
                    events = r.json()
                except Exception:
                    # Unexpected non-json response
                    log("Warning: response not JSON")
                    events = []

                # If the response is a dict, try to inspect keys for event list
                if isinstance(events, dict):
                    # Common API patterns: {"data": [...]} or similar
                    # Try to find a key that contains a list of events
                    candidate = None
                    for k, v in events.items():
                        if isinstance(v, list):
                            candidate = v
                            if debug:
                                print(f"DEBUG: found list under key '{k}' with {len(v)} items")
                            break
                    if candidate is not None:
                        events = candidate
                    else:
                        # No list found
                        events = []

                if not events:
                    break

                all_events.extend(events)
                log(f"Fetched page {page}: {len(events)} events")
                page += 1
            else:
                # Some WP installations (or EventON endpoints) forbid the `status` param.
                # If we received a 400 with a message indicating the `status` param is invalid,
                # retry the request without the `status` parameter.
                log(f"Error fetching events: {r.status_code}")
                if debug:
                    print(f"DEBUG: GET {r.url}\nResponse status: {r.status_code}\n{r.text}")

                try:
                    j = r.json()
                    # Check common error shapes for forbidden status
                    msg = j.get('message', '') if isinstance(j, dict) else ''
                    params = j.get('data', {}).get('params', {}) if isinstance(j, dict) else {}
                    forbidden_status = False
                    if 'Status is forbidden' in msg or params.get('status'):
                        forbidden_status = True
                except Exception:
                    forbidden_status = False

                if forbidden_status:
                    # Retry without the 'status' parameter
                    if debug:
                        print("DEBUG: Retrying without 'status' parameter...")
                    try:
                        r2 = requests.get(
                            f"{API}/ajde_events",
                            params={
                                "per_page": 100,
                                "page": page,
                                "orderby": "id",
                                "order": "desc"
                            },
                            auth=AUTH,
                            timeout=30,
                        )
                        if r2.status_code == 200:
                            try:
                                events = r2.json()
                            except Exception:
                                log("Warning: retry response not JSON")
                                events = []

                            if isinstance(events, dict):
                                # extract list if nested
                                candidate = None
                                for k, v in events.items():
                                    if isinstance(v, list):
                                        candidate = v
                                        break
                                if candidate is not None:
                                    events = candidate
                                else:
                                    events = []

                            if not events:
                                break

                            all_events.extend(events)
                            log(f"Fetched page {page}: {len(events)} events (after retry without status)")
                            page += 1
                            continue
                        else:
                            log(f"Retry without status failed: {r2.status_code}")
                            if debug:
                                print(f"DEBUG: GET {r2.url}\nResponse status: {r2.status_code}\n{r2.text}")
                            break
                    except Exception as e:
                        log(f"Retry without status error: {e}")
                        break

                # Not a forbidden-status case; break out
                break
                
        except Exception as e:
            log(f"Error fetching events: {e}")
            break
    
    return all_events


def delete_event(event_id: int, force: bool = True) -> bool:
    """Delete a single event."""
    try:
        # Choose whether to send auth via requests' auth= or via an explicit
        # Authorization header. The explicit header is only used when
        # USE_EXPLICIT_AUTH is True (controlled by CLI or env var).
        if USE_EXPLICIT_AUTH:
            headers = _explicit_auth_header()
            r = requests.delete(
                f"{API}/ajde_events/{event_id}",
                params={"force": "true"} if force else {},
                headers=headers,
                timeout=30,
            )
        else:
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
            # Print response body when debug enabled to help diagnose 401/403 issues
            try:
                if os.getenv('DELETE_DEBUG', '').lower() in {'1','true','yes'}:
                    print(f"DEBUG DELETE {event_id} response:\n{r.text}")
            except Exception:
                pass
            return False
            
    except Exception as e:
        log(f"Error deleting event {event_id}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Delete all events from WordPress EventON calendar")
    parser.add_argument('--dry-run', action='store_true', help='List events that would be deleted and exit')
    parser.add_argument('--yes', action='store_true', help="Skip interactive confirmation (USE WITH CAUTION)")
    parser.add_argument('--debug', action='store_true', help='Print debug HTTP responses and shapes')
    parser.add_argument('--explicit-auth', action='store_true', help='Use explicit Authorization header (temporary workaround)')
    args = parser.parse_args()

    log("Starting WordPress event deletion...")

    if not (os.getenv("WP_USERNAME") and os.getenv("WP_APP_PASSWORD")):
        log("ERROR: WordPress credentials missing in environment.")
        return
    # Honor CLI flag or environment variable to enable explicit Authorization header
    global USE_EXPLICIT_AUTH
    env_flag = os.getenv('DELETE_USE_EXPLICIT_AUTH', '').lower() in {'1', 'true', 'yes'}
    USE_EXPLICIT_AUTH = args.explicit_auth or env_flag
    if USE_EXPLICIT_AUTH:
        log("NOTICE: Using explicit Authorization header for DELETE requests (temporary workaround).")
    
    # Fetch all events
    log("Fetching all events...")
    events = fetch_all_events(debug=args.debug)

    if not events:
        log("No events found to delete.")
        return

    log(f"Found {len(events)} events to delete.")

    if args.dry_run:
        print("\nDRY RUN: The following events would be deleted:\n")
        for ev in events:
            eid = ev.get('id')
            title = ev.get('title', {}).get('rendered', 'Unknown')
            print(f" - {eid}: {title}")
        print(f"\nTotal: {len(events)} events")
        return

    # Confirm deletion
    print("\n" + "="*80)
    print("WARNING: This will permanently delete ALL events from WordPress!")
    print("="*80)
    if not args.yes:
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
