#!/usr/bin/env python3
"""
Integration Example: Using Google Sheets as an Event Source

This script demonstrates how to use the Google Sheets integration
with the Community Calendar pipeline.

Setup:
1. Set up Google Sheets credentials (see docs/GOOGLE_SHEETS_SETUP.md)
2. Set environment variables:
   - SHEETS_SPREADSHEET_ID
   - GOOGLE_APPLICATION_CREDENTIALS or GOOGLE_SHEETS_SA_JSON_B64
3. Run: python examples/google_sheets_integration_example.py
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts import google_sheets_source
from scripts.automated_pipeline import scrape_events


def example_1_fetch_sheets_only():
    """Example 1: Fetch events from Google Sheets only."""
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Fetch Events from Google Sheets Only")
    print("=" * 70)
    
    events, errors = google_sheets_source.get_events_from_sheets()
    
    if errors:
        print(f"\n⚠️  Warnings/Errors ({len(errors)}):")
        for error in errors:
            print(f"  - {error}")
    
    print(f"\n✓ Fetched {len(events)} events from Google Sheets")
    for event in events:
        print(f"  - {event['title']} ({event['start']})")


def example_2_dry_run():
    """Example 2: Dry run mode (no API calls)."""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Dry Run Mode (Config validation only)")
    print("=" * 70)
    
    events, errors = google_sheets_source.get_events_from_sheets(dry_run=True)
    
    print("✓ Dry run completed (no API calls made)")
    print(f"  Config status: {'Valid' if not errors else 'Invalid'}")


def example_3_custom_mapping():
    """Example 3: Custom column mapping."""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Custom Column Mapping")
    print("=" * 70)
    
    # If your sheet uses different column names
    custom_mapping = {
        'title': ['event_title', 'subject'],
        'location': ['venue_name'],
        'start': ['event_date'],
    }
    
    events, errors = google_sheets_source.get_events_from_sheets(
        column_mapping=custom_mapping
    )
    
    print(f"✓ Fetched {len(events)} events with custom mapping")


def example_4_integrated_pipeline():
    """Example 4: Integrated with full pipeline (multiple sources)."""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Multi-Source Pipeline (Sheets + Chamber + Wren Haven)")
    print("=" * 70)
    
    # Include Google Sheets alongside other sources
    events, errors = scrape_events(
        include_sources=['perdido_chamber', 'wren_haven', 'google_sheets']
    )
    
    if errors:
        print(f"\n⚠️  Warnings/Errors ({len(errors)}):")
        for error in errors[:5]:  # Show first 5 errors
            print(f"  - {error}")
        if len(errors) > 5:
            print(f"  ... and {len(errors) - 5} more")
    
    print(f"\n✓ Total events from all sources: {len(events)}")
    
    # Count by source
    sources = {}
    for event in events:
        source = event.get('source', 'unknown')
        sources[source] = sources.get(source, 0) + 1
    
    print("\nEvents by source:")
    for source, count in sorted(sources.items()):
        print(f"  - {source}: {count} events")


def example_5_error_handling():
    """Example 5: Error handling when credentials missing."""
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Error Handling (Missing Credentials)")
    print("=" * 70)
    
    # Clear credentials temporarily
    original_creds = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    original_b64 = os.environ.get('GOOGLE_SHEETS_SA_JSON_B64')
    
    if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
        del os.environ['GOOGLE_APPLICATION_CREDENTIALS']
    if 'GOOGLE_SHEETS_SA_JSON_B64' in os.environ:
        del os.environ['GOOGLE_SHEETS_SA_JSON_B64']
    
    events, errors = google_sheets_source.get_events_from_sheets()
    
    print(f"Events returned: {len(events)}")
    print(f"Errors captured: {len(errors)}")
    if errors:
        print(f"Error message: {errors[0]}")
    
    # Restore credentials
    if original_creds:
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = original_creds
    if original_b64:
        os.environ['GOOGLE_SHEETS_SA_JSON_B64'] = original_b64


def main():
    """Run integration examples."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + " Google Sheets Integration Examples ".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "=" * 68 + "╝")
    
    # Check if credentials are configured
    if not os.getenv('SHEETS_SPREADSHEET_ID'):
        print("\n❌ SHEETS_SPREADSHEET_ID not set")
        print("\nTo run these examples:")
        print("  1. See docs/GOOGLE_SHEETS_SETUP.md for setup instructions")
        print("  2. Set SHEETS_SPREADSHEET_ID environment variable")
        print("  3. Set GOOGLE_APPLICATION_CREDENTIALS or GOOGLE_SHEETS_SA_JSON_B64")
        print("  4. Run this script again")
        return
    
    if not (os.getenv('GOOGLE_APPLICATION_CREDENTIALS') or 
            os.getenv('GOOGLE_SHEETS_SA_JSON_B64')):
        print("\n❌ Credentials not configured")
        print("\nSet one of:")
        print("  - GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json")
        print("  - GOOGLE_SHEETS_SA_JSON_B64=base64-encoded-json")
        return
    
    # Run examples
    try:
        example_1_fetch_sheets_only()
    except ImportError:
        print("\n❌ Example 1 requires google-auth-httplib2 and google-api-python-client")
        print("   Install with: pip install google-auth google-auth-httplib2 google-api-python-client")
    except Exception as e:
        print(f"\n❌ Example 1 failed: {e}")
    
    try:
        example_2_dry_run()
    except Exception as e:
        print(f"\n❌ Example 2 failed: {e}")
    
    try:
        example_3_custom_mapping()
    except ImportError:
        pass
    except Exception as e:
        print(f"\n❌ Example 3 failed: {e}")
    
    try:
        example_4_integrated_pipeline()
    except Exception as e:
        print(f"\n❌ Example 4 failed: {e}")
    
    try:
        example_5_error_handling()
    except Exception as e:
        print(f"\n❌ Example 5 failed: {e}")
    
    print("\n" + "=" * 70)
    print("Examples completed!")
    print("=" * 70 + "\n")


if __name__ == '__main__':
    main()
