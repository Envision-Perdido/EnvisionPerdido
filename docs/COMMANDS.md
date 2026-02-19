# Delete all events

Windows (PowerShell):

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows\run_delete_all_events.ps1
```

macOS / Linux (zsh / bash):

Before running, set WordPress credentials in your shell (example for zsh):

```zsh
export WP_SITE_URL="https://sandbox.example.org"
export WP_USERNAME="your_wp_username"
export WP_APP_PASSWORD="xxxx xxxx xxxx xxxx xxxx xxxx"
```

Run the cross-platform Python deleter:

```zsh
python scripts/maintenance/delete_all_events.py
```

This will prompt for an explicit confirmation string `DELETE ALL` before performing destructive deletion.

# run pipeline

Windows (PowerShell):

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows\run_pipeline.ps1
```

macOS / Linux (zsh / bash):

```zsh
python scripts/automated_pipeline.py
```