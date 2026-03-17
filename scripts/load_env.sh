#!/usr/bin/env bash
# Backward-compatibility wrapper — actual script moved to scripts/ops/
# This file supports both `source scripts/load_env.sh` and direct execution.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/ops/load_env.sh"
