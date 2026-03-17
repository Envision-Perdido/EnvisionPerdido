#!/usr/bin/env bash
# Backward-compatibility wrapper — actual script moved to scripts/ops/
exec "$(dirname "$0")/ops/verify_security.sh" "$@"
