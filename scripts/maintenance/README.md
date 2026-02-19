# Maintenance & Administrative Scripts

This directory contains administrative utilities (6+ scripts) for managing deployed Envision Perdido systems.

## Administrative Scripts

**Deletion & Cleanup:**
- `delete_all_events.py` — Delete all events from WordPress (use **extremely cautiously**, typically only for complete resets)
- `delete_test_events.py` — Delete test or staging events by tag, date range, or other criteria
- `run_delete_all_events.sh` — Shell wrapper for delete operation (macOS/Linux)

**Inspection & Export:**
- `dump_all_meta.py` — Export all event metadata for analysis, backup, or auditing

## WordPress Administration

**Settings & Configuration:**
- `set_wordpress_timezone.py` — Configure WordPress timezone offset and settings
- `query_eventon_options.py` — Query and inspect EventON plugin option values

## Integration Validation

- `validate_google_sheets_integration.py` — Verify Google Sheets sync status and connectivity

## Usage

**Check EventON options:**
```bash
python maintenance/query_eventon_options.py
```

**Export all events for audit:**
```bash
python maintenance/dump_all_meta.py --output audit_$(date +%Y%m%d).csv
```

**Set WordPress timezone:**
```bash
python maintenance/set_wordpress_timezone.py --timezone "America/Chicago"
```

**Delete test events:**
```bash
python maintenance/delete_test_events.py --tag "test" --dry-run
python maintenance/delete_test_events.py --tag "test" --confirm
```

**Validate Google Sheets:**
```bash
python maintenance/validate_google_sheets_integration.py
```

## ⚠️ Important Safety Notes

- **`delete_all_events.py` is destructive** — It will remove all events. Use only for:
  - Complete system resets
  - Testing against sandbox installations
  - Always confirm with `--dry-run` first
  
- **Always test with `--dry-run` before executing deletions:**
  ```bash
  python maintenance/delete_test_events.py --tag "test" --dry-run
  ```

- **These scripts should only run against:**
  - Sandbox WordPress installations during testing
  - Production systems with explicit approval and backup

- **Never enable `AUTO_UPLOAD` when running maintenance scripts**

- **Backup your database before running deletion scripts**

## Scheduled Use

These scripts can be scheduled for maintenance tasks:

**Windows (PowerShell scheduled task):**
```powershell
$action = New-ScheduledTaskAction -Execute "python" -Argument "scripts/maintenance/validate_google_sheets_integration.py"
$trigger = New-ScheduledTaskTrigger -Daily -At 2AM
Register-ScheduledTask -TaskName "Envision-Validation" -Action $action -Trigger $trigger
```

**macOS/Linux (cron job):**
```bash
# Daily at 2 AM
0 2 * * * cd /path/to/EnvisionPerdido && python scripts/maintenance/validate_google_sheets_integration.py
```

## Related Documentation

- [Safe WordPress Testing Checklist](../docs/WORDPRESS_INTEGRATION_GUIDE.md)
- [Copilot Instructions - Safety Guidelines](../.github/copilot-instructions.md#safety--non-goals)
