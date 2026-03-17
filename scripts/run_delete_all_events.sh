#!/usr/bin/env bash
# Backward-compatibility wrapper — actual script moved to scripts/maintenance/
exec "$(dirname "$0")/maintenance/run_delete_all_events.sh" "$@"
