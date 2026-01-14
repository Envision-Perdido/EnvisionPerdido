# Windows Environment Setup Guide

## Current Status: ✓ FIXED

All systems are now operational on Windows.

## What Was Fixed

### 1. **VS Code Python Path**
- **Issue**: Python interpreter was set to macOS path (`/Users/jacob/...`)
- **Fixed**: Updated `.vscode/settings.json` to use Windows venv path
  ```json
  "python.defaultInterpreterPath": "${workspaceFolder}/.venvEnvisionPerdido/Scripts/python.exe"
  ```

### 2. **Environment Variable Loading**
- **Issue**: Python scripts couldn't access WordPress credentials
- **Fixed**: Created `env_loader.py` utility that reads `scripts/windows/env.ps1` in Python scripts
- **Updated**: `automated_pipeline.py`, `wordpress_uploader.py`, `check_wp_timezone.py`

### 3. **VS Code IntelliSense**
- **Issue**: Red squiggly lines for imports (false errors)
- **Fix**: Reload VS Code or restart Python extension
  - Press `Ctrl+Shift+P` → "Python: Clear Cache"
  - Or simply reload VS Code window

## Quick Start (Fresh Start)

```powershell
cd C:\Users\scott\UWF-Code\EnvisionPerdido

# Activate venv
.\.venvEnvisionPerdido\Scripts\Activate.ps1

# Test API connection
python scripts/check_wp_timezone.py

# Test scraper
python scripts/Envision_Perdido_DataCollection.py

# Run full pipeline
python scripts/automated_pipeline.py
```

## Environment Variables

All credentials are in `scripts/windows/env.ps1`:
- `WP_SITE_URL`: WordPress site URL
- `WP_USERNAME`: WordPress username
- `WP_APP_PASSWORD`: Application password
- `SMTP_SERVER`, `SENDER_EMAIL`, etc.: Email config

**Note**: The `env_loader.py` module automatically loads these when Python scripts run.

## Credential Management

### Update WordPress Credentials
Edit `scripts/windows/env.ps1`:
```powershell
$env:WP_SITE_URL   = "https://your-site.com"
$env:WP_USERNAME   = "your_user"
$env:WP_APP_PASSWORD = "your_app_password"
```

### Update Email Credentials
```powershell
$env:SMTP_SERVER   = "smtp.gmail.com"
$env:SENDER_EMAIL  = "your_email@gmail.com"
$env:EMAIL_PASSWORD = "your_app_password"  # Gmail App Password
```

## API Authentication

All scripts that need API access automatically load credentials via `env_loader.py`. 

**Testing API Connection**:
```powershell
python scripts/check_wp_timezone.py
```

**Expected Output** (✓ if working):
```
WordPress Site Info:
  Name: Community Calendar
  Timezone: America/Chicago
  GMT Offset: -6
```

## Scripts Using Environment Variables

These scripts automatically load credentials:
- `automated_pipeline.py` - Full pipeline
- `wordpress_uploader.py` - Event upload
- `check_wp_timezone.py` - API test
- `health_check.py` - Monitoring
- `delete_all_events.py` - Bulk delete

## PowerShell Scripts

Windows Task Scheduler uses `.ps1` files in `scripts/windows/`:
```powershell
# These automatically source env.ps1
.\scripts\windows\run_pipeline.ps1
.\scripts\windows\run_health_check.ps1
```

## Dependency List

All required packages are installed:
```
beautifulsoup4       - Web scraping
icalendar           - ICS parsing
pandas              - Data processing
requests            - HTTP requests
scikit-learn        - ML classification
joblib              - Model persistence
numpy               - Numerical computing
pytz, zoneinfo      - Timezone handling
```

Verify installation:
```powershell
pip list
```

## Troubleshooting

### "Invalid credentials" error
1. Check `scripts/windows/env.ps1` has correct credentials
2. Test with: `python scripts/check_wp_timezone.py`
3. Verify WordPress app password is correct (not regular password)

### Import errors in VS Code
1. Restart Python extension: `Ctrl+Shift+P` → "Python: Clear Cache"
2. Reload VS Code window: `Ctrl+K Ctrl+R`
3. Check interpreter path: `Ctrl+Shift+P` → "Python: Select Interpreter"
   - Should show: `.venvEnvisionPerdido/Scripts/python.exe`

### Scripts fail to load environment
1. Ensure `scripts/windows/env.ps1` exists
2. Check file has `$env:KEY = "value"` format
3. `env_loader.py` is in `scripts/` directory

### API connection timeout
1. Check WordPress site is online
2. Verify `WP_SITE_URL` in `env.ps1` is correct
3. Try: `python scripts/check_wp_timezone.py -v`

## File Locations

```
EnvisionPerdido/
├── scripts/
│   ├── env_loader.py              ← Loads env.ps1 into Python
│   ├── automated_pipeline.py       ← Uses env_loader
│   ├── wordpress_uploader.py       ← Uses env_loader
│   ├── check_wp_timezone.py        ← API test
│   └── windows/
│       ├── env.ps1                ← Credentials (NOT in git)
│       ├── run_pipeline.ps1        ← PowerShell runner
│       └── run_health_check.ps1
├── .vscode/
│   └── settings.json               ← Python interpreter path (FIXED)
└── .venvEnvisionPerdido/           ← Virtual environment
    └── Scripts/python.exe          ← Actual Python executable
```

## Next Steps

1. **Verify everything works**:
   ```powershell
   python scripts/check_wp_timezone.py
   ```

2. **Test pipeline** (with dry-run):
   ```powershell
   $env:AUTO_UPLOAD = "false"
   python scripts/automated_pipeline.py
   ```

3. **Schedule with Task Scheduler** (already set up):
   ```powershell
   Get-ScheduledTask -TaskName EnvisionPerdido* | Get-ScheduledTaskInfo
   ```

## Questions?

- **Script won't run?** → Check venv is activated
- **API won't connect?** → Check credentials in `env.ps1`
- **Imports not recognized?** → Reload VS Code + restart Python extension
- **Task Scheduler issues?** → Check logs in `output/logs/`
