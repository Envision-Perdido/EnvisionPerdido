# Scripts Directory

This directory contains the automation pipeline, machine learning utilities, and helper scripts for the Envision Perdido event management system.

## Structure

### Root Level - Main Entry Points (3)

**Pipeline executables:**
- `automated_pipeline.py` — Full pipeline: scrape → classify → export → email → (optional) upload
- `wordpress_uploader.py` — Interactive uploader (dry-run → create drafts → publish)
- `run_pipeline_with_smoketest.py` — Cross-platform safe pipeline execution with validation

### ml/ - Machine Learning & Classification (4)

SVM-based event classification:
- `svm_train_from_file.py` — Train SVM model from labeled event data
- `svm_tag_events.py` — Classify events using trained model
- `auto_label_and_train.py` — Auto-label new events and retrain
- `smart_label_helper.py` — Interactive labeling assistant

See [ml/README.md](ml/README.md) for details.

### data_processing/ - Normalization & Enrichment (6)

Event data cleaning and preparation:
- `event_normalizer.py` — Normalize and enrich event data
- `events_to_labelset.py` — Convert events to training sets
- `clean_chamber_urls.py` — Remove unsafe URLs from events
- `fix_event_times.py` — Fix and standardize event times
- `fill_recurring_labels.py` — Propagate labels in series
- `merge_and_propagate_labels.py` — Merge manual/predicted labels

See [data_processing/README.md](data_processing/README.md) for details.

### scrapers/ - Data Collection (3)

Web scrapers and data source integrations:
- `Envision_Perdido_DataCollection.py` — Perdido Chamber scraper
- `wren_haven_scraper.py` — Wren Haven events scraper
- `google_sheets_source.py` — Google Sheets event submissions

See [scrapers/README.md](scrapers/README.md) for details.

### core/ - Core Utilities (5)

Shared utilities and modules:
- `env_loader.py` — Cross-platform environment configuration
- `logger.py` — Structured logging system
- `health_check.py` — System health verification
- `tag_taxonomy.py` — Controlled tag vocabulary
- `venue_registry.py` — Known venues database

See [core/README.md](core/README.md) for details.

### deployment/ - Cloud Integration (3)

AWS Lambda and Make.com deployment:
- `make_cloud_pipeline.py` — AWS Lambda handler for Make.com
- `make_deploy_helper.py` — Lambda deployment preparation
- `make_health_check.py` — CI/CD health checks

See [deployment/README.md](deployment/README.md) for details.

### config/ - Configuration Files (2)

Environment and secrets templates:
- `make_env_secrets.json` — Example secrets (DO NOT COMMIT)
- `make_env_template.json` — Configuration template

See [config/README.md](config/README.md) for details.

### dev/ - Testing & Development (17)

Testing, debugging, and development utilities. See [dev/README.md](dev/README.md).

### maintenance/ - Administrative (7)

Administrative operations for managing deployed systems. See [maintenance/README.md](maintenance/README.md).

### windows/ & macos/ - Platform-Specific

Platform-specific runners and environment setup scripts.

### dev/ (Testing & Debugging)

Testing, debugging, and experimental scripts:
- `check_eventon_settings.py` — Verify EventON plugin settings
- `debug_event_meta.py` — Debug event metadata issues
- `test_wp_auth.py` — Test WordPress authentication
- `test_local_epoch.py` — Test epoch time calculations
- `test_hour_format.py` — Test time format handling
- `test_event_summary_generation.py` — Test event summary generation
- `test_epoch_approaches.py` — Test different epoch computation methods
- `check_meta_format.py` — Verify event metadata format
- `check_wp_timezone.py` — Verify WordPress timezone settings
- `test_chamber_url_guard.py` — Test URL validation logic
- `test_delete_operation.py` — Test event deletion workflows

Run these locally with your test environment or against sandbox WordPress installations.

### maintenance/ (Administrative)

Administrative and maintenance scripts for managing deployed systems:
- `delete_all_events.py` — Delete all events (use cautiously, typically for testing)
- `delete_test_events.py` — Delete test/staging events by tag or date
- `dump_all_meta.py` — Export all event metadata for analysis
- `query_eventon_options.py` — Query EventON plugin option values
- `set_wordpress_timezone.py` — Configure WordPress timezone settings
- `validate_google_sheets_integration.py` — Verify Google Sheets sync status

These scripts are typically used directly via command line or scheduled tasks.

### windows/ (Windows-Specific Scripts)

Windows batch/PowerShell runner and setup scripts:
- `run_pipeline.ps1` — Run pipeline with PowerShell
- `run_pipeline_with_smoketest.ps1` — Safe pipeline with validation
- `run_delete_all_events.ps1` — Delete events runner
- `run_fix_event_times.ps1` — Fix event times runner
- `run_health_check.ps1` — Health check runner
- `env.ps1`, `env.ps1.template` — Environment setup for Windows
- `setup_scheduled_tasks.ps1` — Configure Windows scheduled tasks

### macos/ (macOS/Linux-Specific Scripts)

Shell scripts for macOS and Linux:
- `run_pipeline_with_smoketest.sh` — Safe pipeline execution wrapper
- `run_with_venv.sh` — Virtual environment activation wrapper
- `env.sh`, `env.sh.template` — Environment setup for macOS/Linux

## Quick Start

**Full pipeline (safe-by-default):**
```bash
export AUTO_UPLOAD=false
export SITE_TIMEZONE="America/Chicago"
python scripts/automated_pipeline.py
```

**Training a new classifier:**
```bash
python scripts/ml/svm_train_from_file.py --input data/labeled/events.csv --output data/artifacts/
```

**WordPress upload (interactive):**
```bash
python scripts/wordpress_uploader.py
```

**System health check:**
```bash
python scripts/core/health_check.py
```

## Organization Summary

```
scripts/                    (Total: 61+ scripts organized)
├── automated_pipeline.py   (3 main entry points)
├── wordpress_uploader.py
├── run_pipeline_with_smoketest.py
│
├── ml/                     (4 ML/classification scripts)
├── data_processing/        (6 data pipeline scripts)
├── scrapers/               (3 web scraper scripts)
├── core/                   (5 utility modules)
├── deployment/             (3 AWS Lambda scripts)
├── config/                 (2 config templates)
│
├── dev/                    (17 test/debug scripts)
├── maintenance/            (7 admin scripts)
├── windows/                (9 Windows scripts)
└── macos/                  (5 macOS/Linux scripts)
```

## Environment Variables

See [Configuration & Environment Variables](../.github/copilot-instructions.md#configuration--environment-variables) in the main project docs.

Key variables:
- `WP_SITE_URL`, `WP_USERNAME`, `WP_APP_PASSWORD` (WordPress)
- `SENDER_EMAIL`, `EMAIL_PASSWORD`, `SMTP_SERVER` (Email)
- `AUTO_UPLOAD` (default false for safety)
- `SITE_TIMEZONE` (default `America/Chicago`)

## Safety & Best Practices

- Always test against a **sandbox WordPress installation** before production
- Use `AUTO_UPLOAD=false` by default (required for safe testing)
- Run `run_pipeline_with_smoketest.sh` for validated pipeline execution
- Review dry-run output before confirming destructive operations
- Keep `maintenance/` scripts reserved for administrative use only

See [Safe WordPress Testing Checklist](../.github/copilot-instructions.md#safe-wordpress-testing-checklist) for detailed guidelines.
