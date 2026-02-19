#!/usr/bin/env bash
set -euo pipefail

# Wrapper: run the automated pipeline then the evcal_srow smoke-test.
# Safer defaults: force AUTO_UPLOAD=false unless the caller overrides it.

# If the caller explicitly set AUTO_UPLOAD in the environment, respect it.
if [ -z "${AUTO_UPLOAD+x}" ]; then
  export AUTO_UPLOAD="false"
fi

# Allow overriding SITE_TIMEZONE externally; default to America/Chicago
: "${SITE_TIMEZONE:=America/Chicago}"

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"

PY_WRAPPER="$BASE_DIR/scripts/run_with_venv.sh"

run_python() {
  local script="$1"; shift
  if [ -x "$PY_WRAPPER" ]; then
    "$PY_WRAPPER" "$script" "$@"
  else
    python "$script" "$@"
  fi
}

echo "[run] AUTO_UPLOAD=$AUTO_UPLOAD SITE_TIMEZONE=${SITE_TIMEZONE}"

echo "[run] Running pipeline (safe defaults: AUTO_UPLOAD=false)..."
run_python scripts/automated_pipeline.py

echo "[run] Running evcal_srow smoke-test against latest CSV..."
run_python scripts/dev/check_evcal_srow.py

echo "[run] Done."
