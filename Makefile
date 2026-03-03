.PHONY: setup install test lint run-pipeline run-uploader dry-run verify help regenerate-descriptions regenerate-descriptions-dry-run

# Default target
.DEFAULT_GOAL := help

# Determine OS
UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Linux)
    ACTIVATE := . .venvEnvisionPerdido/bin/activate
else ifeq ($(UNAME_S),Darwin)
    ACTIVATE := . .venvEnvisionPerdido/bin/activate
else
    ACTIVATE := . .venvEnvisionPerdido\Scripts\activate
endif

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
	@echo "  make regenerate-descriptions-dry-run   Preview description enhancement"
	@echo "  make regenerate-descriptions          Enhance descriptions with OpenAI"
	@echo ""
	@echo "Examples:"
	@echo "  make setup && make verify && make dry-run"
	@echo "  make run-pipeline       # Full automation (requires AUTO_UPLOAD env var)"

# Create virtual environment and install dependencies
setup:
	@echo "[INFO] Creating virtual environment..."
	python3 -m venv .venvEnvisionPerdido
	@echo "[INFO] Installing dependencies..."
	$(ACTIVATE) && pip install --upgrade pip && pip install -r requirements.txt
	@echo "[✓] Setup complete! Run 'make verify' to check configuration."

# Install dependencies into existing venv
install:
	@if [ ! -d .venvEnvisionPerdido ]; then \
		echo "[ERROR] Virtual environment not found. Run 'make setup' first."; \
		exit 1; \
	fi
	@echo "[INFO] Installing dependencies..."
	$(ACTIVATE) && pip install --upgrade pip && pip install -r requirements.txt
	@echo "[✓] Dependencies installed."

# Run tests
test:
	@if [ ! -d .venvEnvisionPerdido ]; then \
		echo "[ERROR] Virtual environment not found. Run 'make setup' first."; \
		exit 1; \
	fi
	@echo "[INFO] Running pytest suite..."
	$(ACTIVATE) && python -m pytest tests/ -v

# Run linter
lint:
	@if [ ! -d .venvEnvisionPerdido ]; then \
		echo "[ERROR] Virtual environment not found. Run 'make setup' first."; \
		exit 1; \
	fi
	@echo "[INFO] Running ruff linter..."
	$(ACTIVATE) && ruff check scripts/

# Verify setup
verify:
	@if [ ! -d .venvEnvisionPerdido ]; then \
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
	$(ACTIVATE) && AUTO_UPLOAD=false python scripts/automated_pipeline.py

# Full pipeline (requires explicit AUTO_UPLOAD setting)
run-pipeline: verify
	@echo "[INFO] Running full pipeline with uploads..."
	$(ACTIVATE) && python scripts/automated_pipeline.py

# Interactive uploader
run-uploader: verify
	@echo "[INFO] Starting interactive WordPress uploader..."
	@echo "[INFO] Uploader will run in dry-run mode first. Review before uploading."
	$(ACTIVATE) && python scripts/wordpress_uploader.py

# Regenerate descriptions with OpenAI (dry-run preview)
regenerate-descriptions-dry-run:
	@if [ ! -d .venvEnvisionPerdido ]; then \
		echo "[ERROR] Virtual environment not found. Run 'make setup' first."; \
		exit 1; \
	fi
	@echo "[INFO] DRY RUN: Previewing description regeneration (no API calls)..."
	$(ACTIVATE) && python scripts/regenerate_descriptions.py --dry-run --model gpt-4o-mini

# Regenerate descriptions with OpenAI (full enhancement)
regenerate-descriptions: verify
	@if [ -z "$$OPENAI_API_KEY" ]; then \
		echo "[ERROR] OPENAI_API_KEY environment variable not set"; \
		exit 1; \
	fi
	@echo "[INFO] Regenerating event descriptions with OpenAI..."
	$(ACTIVATE) && python scripts/regenerate_descriptions.py --model gpt-4o-mini

.SILENT: help
