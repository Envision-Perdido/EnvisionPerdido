# Delete all events
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows\run_delete_all_events.ps1

# run pipeline
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows\run_pipeline.ps1