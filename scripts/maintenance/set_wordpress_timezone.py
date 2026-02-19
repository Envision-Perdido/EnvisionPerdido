#!/usr/bin/env python3
"""
Set WordPress timezone to America/Chicago via REST API
"""
import os
import sys
import requests
import base64
from urllib3.exceptions import InsecureRequestWarning

# Suppress SSL warnings for self-signed certs
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

def load_env():
    """Load environment from env.ps1"""
    env = {}
    env_path = "scripts/windows/env.ps1"
    try:
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    # Parse PowerShell format: $env:WP_URL = "value"
                    if "=" in line:
                        key, val = line.split("=", 1)
                        # Extract variable name from $env:NAME format
                        key = key.replace("$env:", "").strip()
                        val = val.strip().strip('"').strip("'")
                        env[key] = val
    except FileNotFoundError:
        print(f"Error: {env_path} not found")
        sys.exit(1)
    return env

def set_wordpress_timezone():
    env = load_env()
    
    WP_URL = env.get("WP_SITE_URL", "https://sandbox.envisionperdido.org").rstrip("/")
    WP_USER = env.get("WP_USERNAME")
    WP_APP_PASSWORD = env.get("WP_APP_PASSWORD")
    
    if not WP_USER or not WP_APP_PASSWORD:
        print("Error: WP_USERNAME or WP_APP_PASSWORD not found in env.ps1")
        sys.exit(1)
    
    # Create Basic Auth header
    credentials = base64.b64encode(f"{WP_USER}:{WP_APP_PASSWORD}".encode()).decode()
    headers = {
        "Authorization": f"Basic {credentials}",
        "Content-Type": "application/json"
    }
    
    # Set timezone to America/Chicago
    url = f"{WP_URL}/wp-json/wp/v2/settings"
    data = {
        "timezone_string": "America/Chicago"
    }
    
    print(f"Setting WordPress timezone to America/Chicago...")
    print(f"URL: {url}")
    
    response = requests.post(url, json=data, headers=headers, verify=False)
    
    if response.status_code == 200:
        print("✓ Successfully set timezone to America/Chicago")
        result = response.json()
        print(f"  Timezone: {result.get('timezone_string', 'N/A')}")
        print(f"  GMT Offset: {result.get('gmt_offset', 'N/A')}")
    else:
        print(f"✗ Error setting timezone: {response.status_code}")
        print(response.text[:500])
        sys.exit(1)

if __name__ == "__main__":
    set_wordpress_timezone()
