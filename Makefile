.PHONY: setup install test lint run-pipeline run-uploader dry-run verify help regenerate-descriptions regenerate-descriptions-dry-run regenerate-descriptions-sync

# Default target
.DEFAULT_GOAL := help

help:
	@echo "EnvisionPerdido Makefile Targets:"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make setup              Create virtual environment and install dependencies"
	@echo "  make install            Install dependencies into existing venv"
	@echo ""
	@echo "Testing & Validation:"
	@echo "  make test               Run pytest test suite"
	@echo "  make lint               Run ruff linter on scripts/"
	@echo "  make verify             Verify setup (check .env, artifacts, venv)"
	@echo ""
	@echo "Pipeline Execution:"
	@echo "  make dry-run            Run pipeline with AUTO_UPLOAD=false (SAFE)"
	@echo "  make run-pipeline       Execute full pipeline (scrape → classify → upload)"
	@echo "  make run-uploader       Interactive WordPress uploader (dry-run first)"
	@echo ""
	@echo "OpenAI Description Enhancement:"
	@echo "  make regenerate-descriptions-dry-run   Preview enhancement (batch API, cached)"
	@echo "  make regenerate-descriptions-sync      Sync API with immediate results"
	@echo "  make regenerate-descriptions          Batch API (async, cheaper, slower)"
	@echo ""
	@echo "Examples:"
	@echo "  make setup && make verify && make dry-run"
	@echo "  make run-pipeline       # Full automation (requires AUTO_UPLOAD env var)"

# Create virtual environment and install dependencies
setup:
	@if ! command -v uv >/dev/null 2>&1; then \
		echo "[ERROR] uv is not installed. Install from https://docs.astral.sh/uv/getting-started/installation/"; \
		exit 1; \
	fi
	@echo "[INFO] Creating .venv and syncing dependencies with uv..."
	uv sync
	@echo "[✓] Setup complete! Run 'make verify' to check configuration."

# Install dependencies into existing venv
install:
	@if ! command -v uv >/dev/null 2>&1; then \
		echo "[ERROR] uv is not installed. Install from https://docs.astral.sh/uv/getting-started/installation/"; \
		exit 1; \
	fi
	@echo "[INFO] Syncing dependencies..."
	uv sync
	@echo "[✓] Dependencies installed."

# Run tests
test:
	@if [ ! -d .venv ]; then \
		echo "[ERROR] Virtual environment not found. Run 'make setup' first."; \
		exit 1; \
	fi
	@echo "[INFO] Running pytest suite..."
	uv run python -m pytest tests/ -v

# Run linter
lint:
	@if [ ! -d .venv ]; then \
		echo "[ERROR] Virtual environment not found. Run 'make setup' first."; \
		exit 1; \
	fi
	@echo "[INFO] Running ruff linter..."
	uv run ruff check scripts/

# Verify setup
verify:
	@if [ ! -d .venv ]; then \
		echo "[ERROR] Virtual environment not found. Run 'make setup' first."; \
		exit 1; \
	fi
	@if [ ! -f .env ]; then \
		echo "[ERROR] .env file not found. Copy .env.example to .env and fill in values."; \
		exit 1; \
	fi
	@if [ ! -f data/artifacts/event_classifier_model.pkl ]; then \
		echo "[ERROR] Model artifact missing: data/artifacts/event_classifier_model.pkl"; \
		exit 1; \
	fi
	@if [ ! -f data/artifacts/event_vectorizer.pkl ]; then \
		echo "[ERROR] Model artifact missing: data/artifacts/event_vectorizer.pkl"; \
		exit 1; \
	fi
	@echo "[✓] Virtual environment OK"
	@echo "[✓] .env configured"
	@echo "[✓] Model artifacts present"
	@echo "[✓] Setup verified successfully!"

# Dry-run (safe, no uploads)
dry-run: verify
	@echo "[INFO] Running pipeline in DRY RUN mode (AUTO_UPLOAD=false)..."
	@echo "[INFO] Events will be reviewed but NOT uploaded to WordPress"
	AUTO_UPLOAD=false uv run python scripts/pipeline/automated_pipeline.py

# Full pipeline (requires explicit AUTO_UPLOAD setting)
run-pipeline: verify
	@echo "[INFO] Running full pipeline with uploads..."
	uv run python scripts/pipeline/automated_pipeline.py

# Interactive uploader
run-uploader: verify
	@echo "[INFO] Starting interactive WordPress uploader..."
	@echo "[INFO] Uploader will run in dry-run mode first. Review before uploading."
	uv run python scripts/wordpress_uploader.py

# Regenerate descriptions with OpenAI (dry-run preview)
regenerate-descriptions-dry-run:
	@if [ ! -d .venv ]; then \
		echo "[ERROR] Virtual environment not found. Run 'make setup' first."; \
		exit 1; \
	fi
	@echo "[INFO] DRY RUN: Previewing description regeneration (no API calls)..."
	uv run python scripts/regenerate_descriptions.py --dry-run --sync --model gpt-4o-mini

# Regenerate descriptions with OpenAI (full enhancement, batch API for cost savings)
regenerate-descriptions: verify
	@if [ -z "$$OPENAI_API_KEY" ]; then \
		echo "[ERROR] OPENAI_API_KEY environment variable not set"; \
		exit 1; \
	fi
	@echo "[INFO] Regenerating event descriptions with OpenAI (Batch API, cached)..."
	@echo "[INFO] Configuration: top-n=100, min-confidence=0.75, use-cache=true"
	uv run python scripts/regenerate_descriptions.py --batch --top-n 100 --min-confidence 0.75 --model gpt-4o-mini

# Regenerate descriptions with sync API (immediate results, no caching)
regenerate-descriptions-sync: verify
	@if [ -z "$$OPENAI_API_KEY" ]; then \
		echo "[ERROR] OPENAI_API_KEY environment variable not set"; \
		exit 1; \
	fi
	@echo "[INFO] Regenerating event descriptions with OpenAI (Sync API, immediate)..."
	uv run python scripts/regenerate_descriptions.py --sync --top-n 100 --min-confidence 0.75 --model gpt-4o-mini

.SILENT: help
