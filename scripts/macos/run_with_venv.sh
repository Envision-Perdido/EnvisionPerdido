#!/usr/bin/env bash
# Helper to run project scripts using a reusable venv stored in the user's home.
# Adjust VENV_PATH if you created the venv elsewhere.

set -euo pipefail

VENV_PATH="$HOME/.virtualenvs/envisionperdido"
PYTHON="$VENV_PATH/bin/python"

if [ ! -x "$PYTHON" ]; then
  echo "Error: python not found in venv at $PYTHON"
  echo "Create the venv by running: python3 -m venv $VENV_PATH && $PYTHON -m pip install -r \"$(pwd)/requirements.txt\""
  exit 2
fi

if [ "$#" -eq 0 ]; then
  echo "Usage: $0 <script> [args...]"
  echo "Example: $0 scripts/modelViewer.py"
  exit 0
fi

SCRIPT="$1"
shift || true

exec "$PYTHON" "$SCRIPT" "$@"
