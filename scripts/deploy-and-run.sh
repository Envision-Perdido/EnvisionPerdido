#!/bin/bash
# EnvisionPerdido Deploy and Run Script
# Purpose: Deploy pipeline on remote server and run with make.com integration
# Usage: ./scripts/deploy-and-run.sh [REPO_DIR] [DRY_RUN]
# Examples:
#   ./scripts/deploy-and-run.sh . true           # Dry-run in current dir
#   ./scripts/deploy-and-run.sh /home/ubuntu/ep false  # Full run in /home/ubuntu/ep

set -e

REPO_DIR="${1:-.}"
DRY_RUN="${2:-true}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_info "EnvisionPerdido Deploy and Run Script"
log_info "Repository: $REPO_DIR"
log_info "Dry Run: $DRY_RUN"

# Navigate to repo directory
if [ ! -d "$REPO_DIR" ]; then
    log_error "Repository directory not found: $REPO_DIR"
    exit 1
fi

cd "$REPO_DIR"
log_info "Working directory: $(pwd)"

# Check if .env exists
if [ ! -f .env ]; then
    log_error ".env file not found at $(pwd)/.env"
    log_error "Please create .env from .env.example:"
    log_error "  cp .env.example .env"
    log_error "  nano .env  # Edit with your credentials"
    exit 1
fi

log_info "✓ .env file found"

# Check if venv exists, create if not
if [ ! -d .venvEnvisionPerdido ]; then
    log_warn "Virtual environment not found. Creating..."
    python3 -m venv .venvEnvisionPerdido
    . .venvEnvisionPerdido/bin/activate
    pip install --upgrade pip --quiet
    pip install -r requirements.txt --quiet
    log_info "✓ Virtual environment created and dependencies installed"
else
    . .venvEnvisionPerdido/bin/activate
    log_info "✓ Virtual environment activated"
fi

# Load environment variables
source scripts/load_env.sh

# Verify required environment variables
required_vars=("WP_SITE_URL" "WP_USERNAME" "WP_APP_PASSWORD" "SENDER_EMAIL" "RECIPIENT_EMAIL")
missing_vars=()

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -gt 0 ]; then
    log_error "Missing required environment variables:"
    for var in "${missing_vars[@]}"; do
        log_error "  - $var"
    done
    exit 1
fi

log_info "✓ Required environment variables present"

# Verify model artifacts exist
log_info "Verifying model artifacts..."

if [ ! -f data/artifacts/event_classifier_model.pkl ]; then
    log_error "Model artifact missing: data/artifacts/event_classifier_model.pkl"
    exit 1
fi

if [ ! -f data/artifacts/event_vectorizer.pkl ]; then
    log_error "Model artifact missing: data/artifacts/event_vectorizer.pkl"
    exit 1
fi

log_info "✓ Model artifacts verified"

# Create output directories if they don't exist
mkdir -p output/pipeline output/logs

# Run pipeline
log_info "Starting pipeline execution..."
log_info "DRY_RUN=$DRY_RUN, AUTO_UPLOAD will be set accordingly"

if [ "$DRY_RUN" = "true" ]; then
    log_info "Running in DRY RUN mode (AUTO_UPLOAD=false)"
    log_warn "Events will be classified but NOT uploaded to WordPress"
    export AUTO_UPLOAD=false
else
    log_info "Running full pipeline with uploads enabled"
    # AUTO_UPLOAD will use the value from .env (or false if not set)
fi

# Run the pipeline and capture exit code
if python scripts/automated_pipeline.py; then
    log_info "✓ Pipeline completed successfully"
    log_info "Outputs:"
    log_info "  CSV: output/pipeline/calendar_upload_*.csv"
    log_info "  Logs: output/logs/automated_pipeline_*.log"
    
    # List the most recent files for verification
    if [ "$(ls -1 output/pipeline/calendar_upload_*.csv 2>/dev/null | wc -l)" -gt 0 ]; then
        latest_csv=$(ls -t output/pipeline/calendar_upload_*.csv | head -1)
        log_info "Latest CSV: $(basename $latest_csv)"
    fi
    
    if [ "$(ls -1 output/logs/automated_pipeline_*.log 2>/dev/null | wc -l)" -gt 0 ]; then
        latest_log=$(ls -t output/logs/automated_pipeline_*.log | head -1)
        log_info "Latest log: $(basename $latest_log)"
    fi
    
    exit 0
else
    log_error "Pipeline failed with exit code $?"
    log_error "Check output/logs/ for details"
    exit 1
fi
