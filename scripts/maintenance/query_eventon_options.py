#!/usr/bin/env python3
"""Query WordPress options for EventON timezone settings"""
import requests
import base64
import json

env = {}
with open('scripts/windows/env.ps1', 'r') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, val = line.split('=', 1)
            key = key.replace('$env:', '').strip()
            val = val.strip().strip('"').strip("'")
            env[key] = val

WP_URL = env.get('WP_SITE_URL').rstrip('/')
creds = base64.b64encode(f"{env.get('WP_USERNAME')}:{env.get('WP_APP_PASSWORD')}".encode()).decode()
headers = {'Authorization': f'Basic {creds}'}

# Get WordPress settings
r = requests.get(f'{WP_URL}/wp-json/wp/v2/settings', headers=headers, verify=False)
if r.status_code == 200:
    settings = r.json()
    print('WordPress Settings:')
    print(f"  timezone_string: {settings.get('timezone_string', 'N/A')}")
    print(f"  gmt_offset: {settings.get('gmt_offset', 'N/A')}")
    print(f"  date_format: {settings.get('date_format', 'N/A')}")
    print(f"  time_format: {settings.get('time_format', 'N/A')}")
    
    # Check for EventON settings - might be in options
    print("\nLooking for EventON-specific settings in response...")
    eventon_keys = [k for k in settings.keys() if 'eventon' in k.lower() or 'evcal' in k.lower()]
    if eventon_keys:
        for key in eventon_keys:
            print(f"  {key}: {settings[key]}")
    else:
        print("  (none found in REST settings)")
else:
    print(f"Error: {r.status_code}")
    print(r.text[:500])
