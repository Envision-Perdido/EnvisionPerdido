# Development & Testing Scripts

This directory contains scripts used for testing, debugging, and development purposes. These scripts are not part of the main production pipeline.

## Testing Scripts

- **test_wp_auth.py** - Diagnose WordPress authentication & EDIT privilege issues
- **test_hour_format.py** - Pytest-based test for EventON hour field display
- **test_local_epoch.py** - Pytest-based test for local timezone epoch storage
- **test_delete_operation.py** - Debug HTTP 401 errors on DELETE operations
- **test_epoch_approaches.py** - Compare UTC vs local epoch calculations

## Debugging Scripts

- **debug_event_meta.py** - Query & display all EventON meta fields from live site
- **check_evcal_srow.py** - Smoke test validating epoch calculations against stored values (also used in CI)

## Usage

These scripts are typically run manually for development and troubleshooting:

```bash
# Test authentication
python scripts/dev/test_wp_auth.py

# Check epoch calculations
python scripts/dev/check_evcal_srow.py

# Debug event metadata
python scripts/dev/debug_event_meta.py
```

Note: Some test scripts require WordPress credentials (WP_SITE_URL, WP_USERNAME, WP_APP_PASSWORD) to be set in environment variables.
