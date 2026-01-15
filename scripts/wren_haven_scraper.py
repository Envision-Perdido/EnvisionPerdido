"""
Wren Haven Homestead events scraper.

Wren Haven Homestead (https://www.wrenhavenhomestead.com/events) loads events
via a JSON API that requires an Authorization header. This module:

1. Uses Playwright to bootstrap/discover the API endpoint and auth header
2. Caches the auth artifacts (endpoint, headers) for reuse
3. Fetches events via the existing HTTP client with minimal custom mapping
4. Normalizes events into the standard Event model

Reuses:
- Existing Event model and normalization functions
- Existing HTTP client retry/backoff utilities
- Existing venue resolution and paid/free detection
- Existing event enrichment and filtering pipeline
"""

import json
import time
import requests
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path
import os
import sys

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

from browser_bootstrap import bootstrap_json_api, _load_cached_artifacts


# Configuration
SOURCE_NAME = "wren_haven_homestead"
SOURCE_URL = "https://www.wrenhavenhomestead.com/events"
PREVIOUS_MONTH_SELECTOR = "button[aria-label='Previous month']"

# Standard headers (reuses existing pattern)
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# Session (reuses existing pattern)
session = requests.Session()
session.headers.update(DEFAULT_HEADERS)


class WrenHavenScraperError(Exception):
    """Raised when Wren Haven scraping fails."""
    pass


def _bootstrap_or_use_cached(force_refresh: bool = False) -> Dict[str, Any]:
    """
    Get bootstrap artifacts (endpoint, auth headers) from cache or discover via Playwright.
    
    Args:
        force_refresh: If True, ignore cache and re-bootstrap
        
    Returns:
        Dictionary with 'endpoint', 'method', 'headers', 'cookies'
    """
    from urllib.parse import urlparse
    domain = urlparse(SOURCE_URL).netloc
    
    # Try cache first (unless force_refresh)
    if not force_refresh:
        cached = _load_cached_artifacts(SOURCE_NAME, domain)
        if cached:
            return cached
    
    # Bootstrap via Playwright
    print(f"Bootstrapping JSON API endpoint for {SOURCE_NAME}...")
    try:
        artifacts = bootstrap_json_api(
            url=SOURCE_URL,
            previous_month_selector=PREVIOUS_MONTH_SELECTOR,
            source_name=SOURCE_NAME,
            headless=True,
            timeout_seconds=30
        )
        
        if not artifacts or not artifacts.get('endpoint'):
            raise WrenHavenScraperError("Could not discover API endpoint via Playwright")
        
        return artifacts
    except ImportError:
        raise WrenHavenScraperError(
            "Playwright is required for Wren Haven bootstrapping. "
            "Install with: pip install playwright && playwright install"
        )


def _prepare_request_headers(artifacts: Dict[str, Any]) -> Dict[str, str]:
    """
    Prepare HTTP headers for the request, preserving auth and other artifacts.
    
    Reuses existing pattern: merge default headers with discovered headers.
    """
    headers = DEFAULT_HEADERS.copy()
    
    # Add discovered headers (Authorization, Content-Type, etc.)
    if artifacts.get('headers'):
        headers.update(artifacts['headers'])
    
    return headers


def _fetch_events_from_api(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    bootstrap_artifacts: Optional[Dict[str, Any]] = None,
    max_retries: int = 3
) -> List[Dict[str, Any]]:
    """
    Fetch raw events from Wren Haven JSON API.
    
    Reuses existing retry/backoff pattern from requests library.
    
    Args:
        start_date: ISO date string (YYYY-MM-DD), optional filter
        end_date: ISO date string (YYYY-MM-DD), optional filter
        bootstrap_artifacts: Cached endpoint/auth info
        max_retries: Number of retries on failure
        
    Returns:
        List of raw event dictionaries from the API
    """
    
    if bootstrap_artifacts is None:
        bootstrap_artifacts = _bootstrap_or_use_cached()
    
    endpoint = bootstrap_artifacts.get('endpoint')
    method = bootstrap_artifacts.get('method', 'GET')
    headers = _prepare_request_headers(bootstrap_artifacts)
    cookies = bootstrap_artifacts.get('cookies', [])
    body = bootstrap_artifacts.get('body')
    
    if not endpoint:
        raise WrenHavenScraperError("No API endpoint available")
    
    # Build request parameters/body
    params = {}
    request_body = None
    
    if start_date:
        params['start'] = start_date
    if end_date:
        params['end'] = end_date
    
    if method.upper() == 'POST' and body:
        # For POST requests, try to merge filters into body
        try:
            request_body = json.loads(body) if isinstance(body, str) else body
            if start_date:
                request_body['start'] = start_date
            if end_date:
                request_body['end'] = end_date
        except:
            request_body = body
    
    # Reuse existing retry pattern (simple exponential backoff)
    last_error = None
    for attempt in range(max_retries):
        try:
            time.sleep(0.5 * attempt)  # Backoff
            
            kwargs = {
                'headers': headers,
                'timeout': 30
            }
            
            # Add cookies if present
            if cookies:
                cookie_dict = {c['name']: c['value'] for c in cookies}
                kwargs['cookies'] = cookie_dict
            
            if method.upper() == 'POST':
                if request_body:
                    kwargs['json'] = request_body
                response = session.post(endpoint, **kwargs)
            else:
                if params:
                    kwargs['params'] = params
                response = session.get(endpoint, **kwargs)
            
            response.raise_for_status()
            
            data = response.json()
            
            # Handle both direct array and nested structure
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                # Try common keys for event lists
                for key in ['events', 'items', 'results', 'data']:
                    if key in data and isinstance(data[key], list):
                        return data[key]
                # If no standard key, return dict as single item for inspection
                return [data]
            
            return []
        
        except requests.exceptions.RequestException as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
        except json.JSONDecodeError as e:
            raise WrenHavenScraperError(f"API response was not valid JSON: {e}")
        except Exception as e:
            raise WrenHavenScraperError(f"Error fetching events: {e}")
    
    if last_error:
        raise WrenHavenScraperError(f"Failed to fetch events after {max_retries} retries: {last_error}")
    
    return []


def normalize_event(raw_event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a raw Wren Haven event to standard Event model.
    
    Maps Wren Haven fields to standard schema:
        title, start, end, location, url, description, uid, category
    
    Reuses existing normalization approach: map + enrich downstream.
    """
    
    # Extract standard fields (adapt based on actual API response)
    # Common Wren Haven event fields (adjust based on actual API):
    event = {
        'title': raw_event.get('title') or raw_event.get('name', ''),
        'start': raw_event.get('start') or raw_event.get('startDate') or raw_event.get('begin'),
        'end': raw_event.get('end') or raw_event.get('endDate') or raw_event.get('finish'),
        'location': raw_event.get('location') or raw_event.get('venue'),
        'url': raw_event.get('url') or raw_event.get('link'),
        'description': raw_event.get('description') or raw_event.get('summary'),
        'uid': raw_event.get('id') or raw_event.get('uid', ''),
        'category': raw_event.get('category') or raw_event.get('type'),
    }
    
    # Store raw source for debugging
    event['_raw_source'] = SOURCE_NAME
    
    return event


def scrape_wren_haven(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    force_bootstrap: bool = False
) -> List[Dict[str, Any]]:
    """
    Scrape events from Wren Haven Homestead.
    
    Main entry point. Reuses the standard pipeline:
    1. Bootstrap/cache auth (Playwright on first run)
    2. Fetch raw events via HTTP
    3. Normalize to standard schema
    
    Downstream code (enrichment, filtering, classification) reuses existing functions.
    
    Args:
        start_date: ISO date to filter events (YYYY-MM-DD)
        end_date: ISO date to filter events (YYYY-MM-DD)
        force_bootstrap: Re-run Playwright bootstrap even if cached
        
    Returns:
        List of normalized event dictionaries
    """
    
    print(f"Scraping {SOURCE_NAME} from {SOURCE_URL}...")
    
    try:
        # Get auth artifacts (cached or bootstrapped)
        artifacts = _bootstrap_or_use_cached(force_refresh=force_bootstrap)
        
        # Fetch raw events from API
        raw_events = _fetch_events_from_api(
            start_date=start_date,
            end_date=end_date,
            bootstrap_artifacts=artifacts
        )
        
        print(f"Fetched {len(raw_events)} raw events from API")
        
        # Normalize events
        normalized = []
        for raw in raw_events:
            try:
                event = normalize_event(raw)
                if event.get('title'):  # Only keep if has title
                    normalized.append(event)
            except Exception as e:
                print(f"Warning: Could not normalize event {raw.get('id', '?')}: {e}")
        
        print(f"Normalized {len(normalized)} events")
        return normalized
    
    except WrenHavenScraperError as e:
        print(f"Error scraping {SOURCE_NAME}: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error scraping {SOURCE_NAME}: {e}")
        return []


# For integration with automated_pipeline.py
def get_events(year: int = None, month: int = None) -> List[Dict[str, Any]]:
    """
    Get events for a specific month.
    
    Signature matches other sources in the pipeline.
    """
    if year is None:
        year = datetime.now().year
    if month is None:
        month = datetime.now().month
    
    # Compute date range for the month
    from datetime import date
    import calendar
    
    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])
    
    start_date = first_day.isoformat()
    end_date = last_day.isoformat()
    
    return scrape_wren_haven(start_date=start_date, end_date=end_date)


if __name__ == "__main__":
    # Quick test
    events = scrape_wren_haven()
    print(f"\nTotal events: {len(events)}")
    if events:
        print(f"First event: {events[0]}")
