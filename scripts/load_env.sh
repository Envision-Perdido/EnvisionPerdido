#!/bin/bash
# Load environment variables from .env file
# Usage: source scripts/load_env.sh
# This script is safe for use in make.com or any shell environment

if [ -f .env ]; then
    # Set allexport to automatically export all variables
    set -a
    # Source the .env file (suppress errors for comments and blank lines)
    source .env
    set +a
    echo "[INFO] Environment variables loaded from .env"
else
    echo "[ERROR] .env file not found in current directory: $(pwd)"
    echo "[ERROR] Please create .env from .env.example:"
    echo "  cp .env.example .env"
    echo "  nano .env  # or your preferred editor"
    exit 1
fi
