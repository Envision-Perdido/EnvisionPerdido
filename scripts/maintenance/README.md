# Maintenance Scripts

This directory contains administrative and maintenance scripts for managing the WordPress calendar and event data.

## Event Management

- **delete_all_events.py** - Bulk delete all events with safety confirmations (use `--dry-run` and `--yes` flags)
- **delete_test_events.py** - Clean up test/duplicate events by ID range
- **fix_event_times.py** - Reconstruct local datetime from meta fields & update evcal_srow/evcal_erow

## WordPress Configuration

- **set_wordpress_timezone.py** - Configure WordPress timezone to America/Chicago via REST API
- **query_eventon_options.py** - Query WordPress settings (timezone, date format)
- **dump_all_meta.py** - Export all EventON meta fields from a specific event

## Usage

These scripts should be used with caution as they modify data:

```bash
# Delete all events (with safety checks)
python scripts/maintenance/delete_all_events.py --dry-run

# Set WordPress timezone
python scripts/maintenance/set_wordpress_timezone.py

# Fix event times after timezone changes
python scripts/maintenance/fix_event_times.py

# Query EventON options
python scripts/maintenance/query_eventon_options.py
```

**⚠️ Warning:** Always use `--dry-run` flags when available and test on a staging environment first!

All scripts require WordPress credentials (WP_SITE_URL, WP_USERNAME, WP_APP_PASSWORD) to be set in environment variables.
