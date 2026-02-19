# Development & Testing Scripts

This directory contains debugging, testing, and development utility scripts for local development and validation.

## Testing & Debugging Scripts (14)

**EventON & WordPress Testing:**
- `check_eventon_settings.py` — Verify EventON plugin configuration and capabilities
- `check_wp_timezone.py` — Validate WordPress timezone settings
- `test_wp_auth.py` — Test WordPress API authentication and credentials
- `test_delete_operation.py` — Test event deletion workflows and safety checks

**Time & Data Format Testing:**
- `test_local_epoch.py` — Test epoch time calculation (critical for correct event dates)
- `test_hour_format.py` — Test time formatting (12-hour vs 24-hour)
- `test_epoch_approaches.py` — Compare different epoch computation methods

**Feature Testing:**
- `test_event_summary_generation.py` — Test event summary generation and formatting
- `test_chamber_url_guard.py` — Test URL validation and chamber URL guard logic

**Debugging & Utilities:**
- `debug_event_meta.py` — Inspect and debug event metadata structure
- `check_meta_format.py` — Verify event metadata format compliance
- `browser_bootstrap.py` — Bootstrap/test browser automation utilities
- `modelViewer.py` — Inspect and debug model artifacts
- `setup_image_mapper.py` — Image mapping configuration and testing

## Git Development Utilities

- `new-branch.sh` — Create and setup new feature branches (macOS/Linux compatible)
- `new-branch.ps1` — Create and setup new feature branches (PowerShell)

## Usage

**Test metadata format:**
```bash
python dev/check_meta_format.py data/artifacts/last_export.csv
```

**Debug metadata issues:**
```bash
python dev/debug_event_meta.py --event-id 12345
```

**Test epoch calculations:**
```bash
python dev/test_local_epoch.py --timezone "America/Chicago"
```

**Validate authentication:**
```bash
python dev/test_wp_auth.py
```

## Important Notes

- These scripts are **for local testing and debugging only**
- Always test against a **sandbox WordPress installation** first
- Never enable `AUTO_UPLOAD` when running tests
- Use `test_delete_operation.py` to validate destructive operations before production use
- Check `test_epoch_approaches.py` output carefully before deploying timezone changes

## Running in Development

Set environment variables for testing:
```bash
export AUTO_UPLOAD=false
export SITE_TIMEZONE="America/Chicago"
python dev/test_local_epoch.py
```

For Windows (PowerShell):
```powershell
$env:AUTO_UPLOAD = "false"
$env:SITE_TIMEZONE = "America/Chicago"
python dev\test_local_epoch.py
```
