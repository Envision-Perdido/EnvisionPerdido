#!/usr/bin/env python3
"""
Quick reference: Add Wren Haven Homestead events to the automated pipeline.

This script demonstrates the common use cases for the Wren Haven scraper.
"""

# ============================================================================
# BASIC USAGE - Add Wren Haven to Monthly Scraping
# ============================================================================

from scripts.automated_pipeline import scrape_events
import pandas as pd

# Scrape from BOTH Perdido Chamber AND Wren Haven
all_events = scrape_events(
    year=2025,
    month=3,
    include_sources=['perdido_chamber', 'wren_haven']  # <-- Add 'wren_haven'
)

# Result: List of event dicts, combined from both sources
# Each event has: title, start, end, location, url, description, uid, category
print(f"Scraped {len(all_events)} total events from 2 sources")

# ============================================================================
# DIRECT SCRAPER USAGE
# ============================================================================

from scripts.wren_haven_scraper import scrape_wren_haven

# Option 1: Scrape all events (no date filter)
events = scrape_wren_haven()
print(f"Wren Haven events: {len(events)}")

# Option 2: Scrape specific date range
events = scrape_wren_haven(
    start_date='2025-03-01',
    end_date='2025-03-31'
)
print(f"March 2025 events: {len(events)}")

# Option 3: Force re-bootstrap (ignore 24h cache)
events = scrape_wren_haven(force_bootstrap=True)

# ============================================================================
# CACHE MANAGEMENT
# ============================================================================

from scripts.browser_bootstrap import clear_bootstrap_cache

# Clear cache for Wren Haven (forces next scrape to re-bootstrap)
clear_bootstrap_cache('wren_haven_homestead', 'www.wrenhavenhomestead.com')

# Clear ALL cached bootstrap artifacts
clear_bootstrap_cache()

# ============================================================================
# TESTING - MANUAL VERIFICATION
# ============================================================================

# Option 1: Run unit tests (no network)
# Command: python -m pytest tests/test_wren_haven_scraper.py -v

# Option 2: Manual endpoint discovery (with browser window visible)
from scripts.browser_bootstrap import bootstrap_json_api

artifacts = bootstrap_json_api(
    url="https://www.wrenhavenhomestead.com/events",
    previous_month_selector="button[aria-label='Previous month']",
    source_name="wren_haven_homestead",
    headless=False  # <-- Open browser to watch bootstrap
)

if artifacts:
    print(f"Discovered API endpoint: {artifacts['endpoint']}")
    print(f"Method: {artifacts['method']}")
    print(f"Headers: {artifacts['headers']}")
else:
    print("Bootstrap failed - check browser output above")

# ============================================================================
# INTEGRATION WITH ENRICHMENT PIPELINE
# ============================================================================

from scripts.automated_pipeline import (
    scrape_events,
    assign_event_images,
    classify_events
)
from scripts.event_normalizer import enrich_events_dataframe, filter_events_dataframe

# Scrape from multiple sources
raw_events = scrape_events(include_sources=['perdido_chamber', 'wren_haven'])

# Convert to DataFrame for enrichment
df = pd.DataFrame(raw_events)
print(f"Before enrichment: {len(df)} events")

# Apply standard enrichment pipeline (works on all sources)
df = enrich_events_dataframe(df)  # Detect paid/free, category enrichment
df = assign_event_images(df)      # Assign images by keyword matching
df = classify_events(df)          # SVM classification

# Filter (keep only community events)
community_df, other_df = filter_events_dataframe(df)
print(f"After classification: {len(community_df)} community events")

# Export for calendar upload
csv_path = "output/pipeline/calendar_upload.csv"
community_df.to_csv(csv_path, index=False)

# ============================================================================
# TROUBLESHOOTING
# ============================================================================

# If bootstrap fails:
# 1. Make sure Playwright is installed:
#    pip install playwright
#    playwright install chromium

# 2. Check if Wren Haven button selector still exists:
#    Open https://www.wrenhavenhomestead.com/events in browser
#    Inspect the "Previous month" button
#    Update selector if changed in code

# 3. Force re-bootstrap:
#    clear_bootstrap_cache('wren_haven_homestead', 'www.wrenhavenhomestead.com')
#    scrape_wren_haven(force_bootstrap=True)

# 4. Increase bootstrap timeout:
#    from scripts.browser_bootstrap import bootstrap_json_api
#    artifacts = bootstrap_json_api(
#        url="https://www.wrenhavenhomestead.com/events",
#        timeout_seconds=60  # <-- Increased from default 30
#    )

# ============================================================================
# PRODUCTION USAGE - SCHEDULED PIPELINE
# ============================================================================

# In scripts/automated_pipeline.py, main() function:
# Change this:
#     all_events = scrape_events()
#
# To this:
#     all_events = scrape_events(
#         include_sources=['perdido_chamber', 'wren_haven']
#     )

# Then run pipeline as usual:
#     python scripts/automated_pipeline.py
#
# First run takes ~5-10 seconds (Playwright bootstrap)
# Subsequent runs take ~2-3 seconds (use cached auth)
# Every 24 hours, cache refreshes automatically

if __name__ == "__main__":
    print(__doc__)
