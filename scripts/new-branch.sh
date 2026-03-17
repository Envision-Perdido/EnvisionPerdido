#!/usr/bin/env bash
# Backward-compatibility wrapper — actual script moved to scripts/dev/
exec "$(dirname "$0")/dev/new-branch.sh" "$@"
