#!/usr/bin/env python3
"""
Test if changing evcal_start_time_hour changes the display
This will help us determine if EventON is using these fields at all
"""

import base64
import os

import pytest
import requests

# By default skip tests that interact with a live WordPress site. To run them set:
#   RUN_LIVE_SITE_TESTS=1
# This avoids accidental network calls or destructive updates during CI or local runs.
if not os.environ.get("RUN_LIVE_SITE_TESTS"):
    pytest.skip(
        "Skipping live-site tests (set RUN_LIVE_SITE_TESTS=1 to enable)", allow_module_level=True
    )


# Load credentials for live site tests. Priority order:
# 1) Environment variables: WP_SITE_URL, WP_USERNAME, WP_APP_PASSWORD
# 2) A local secrets file: ~/.secrets/envision_env.ps1 (PowerShell-style lines)
# 3) Fallback to scripts/windows/env.ps1 if it exists (not recommended for secrets)
env = {}


def _load_from_ps1(path):
    out = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    key = key.replace("$env:", "").strip()
                    val = val.strip().strip('"').strip("'")
                    out[key] = val
    except FileNotFoundError:
        return {}
    return out


# 1) from env vars
env["WP_SITE_URL"] = os.environ.get("WP_SITE_URL")
env["WP_USERNAME"] = os.environ.get("WP_USERNAME")
env["WP_APP_PASSWORD"] = os.environ.get("WP_APP_PASSWORD")

# 2) from ~/.secrets/envision_env.ps1
if not all([env.get("WP_SITE_URL"), env.get("WP_USERNAME"), env.get("WP_APP_PASSWORD")]):
    secrets_file = os.path.expanduser("~/.secrets/envision_env.ps1")
    env_secrets = _load_from_ps1(secrets_file)
    for k, v in env_secrets.items():
        env.setdefault(k, v)

# 3) fallback to scripts/windows/env.ps1 (only if present locally)
if not all([env.get("WP_SITE_URL"), env.get("WP_USERNAME"), env.get("WP_APP_PASSWORD")]):
    env_local = _load_from_ps1("scripts/windows/env.ps1")
    for k, v in env_local.items():
        env.setdefault(k, v)

if not all([env.get("WP_SITE_URL"), env.get("WP_USERNAME"), env.get("WP_APP_PASSWORD")]):
    raise RuntimeError(
        "Live-site test enabled but WP credentials not found in env vars or ~/.secrets/envision_env.ps1"
    )

WP_URL = env.get("WP_SITE_URL").rstrip("/")
creds = base64.b64encode(f"{env.get('WP_USERNAME')}:{env.get('WP_APP_PASSWORD')}".encode()).decode()
headers = {"Authorization": f"Basic {creds}"}

# Test: Change one event's hour to 19 (7 PM 24-hour format)
# If EventON displays it as 7 PM, it's reading this field
# If still 1 AM, it's ignoring this field

event_id = 1432

print(f"Testing event {event_id}...")
print("\nStep 1: Current value")
r = requests.get(f"{WP_URL}/wp-json/wp/v2/ajde_events/{event_id}", headers=headers, verify=False)
if r.status_code == 200:
    event = r.json()
    print(f"  evcal_start_time_hour: {event['meta'].get('evcal_start_time_hour')}")
    print("  Currently displays on calendar as: 1 AM")

print("\nStep 2: Try setting hour to 19 (24-hour format)...")
data = {"meta": {"evcal_start_time_hour": "19"}}
r = requests.post(
    f"{WP_URL}/wp-json/wp/v2/ajde_events/{event_id}", headers=headers, json=data, verify=False
)
if r.status_code == 200:
    print("  Updated to 19")
    print("  Please check: Does event now show 7 PM or still 1 AM?")
else:
    print(f"  Error: {r.status_code} - {r.text[:200]}")

print("\nStep 3: If still 1 AM after update:")
print("  → EventON is ignoring hour/min/ampm fields")
print("  → EventON must have its own timezone config")
print("\nStep 4: If changed to 7 PM (19:00):")
print("  → EventON is using the hour field (24-hour format)")
print("  → Need to always store as '19' for 7 PM instead of '07' pm")
