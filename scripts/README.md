# Scripts Directory

This directory contains the automation pipeline, machine learning utilities, and helper scripts for the Envision Perdido event management system.

## Structure

### Root Level (23 Core Scripts + Utilities)

**Main Entry Points:**
- `automated_pipeline.py` — Full pipeline: scrape → classify → export → email → (optional) upload
- `wordpress_uploader.py` — Interactive uploader (dry-run → create drafts → publish)
- `Envision_Perdido_DataCollection.py` — Scraper and ICS parsing

**Machine Learning & Classification:**
- `svm_train_from_file.py` — Train the event classifier SVM model from labeled data
- `auto_label_and_train.py` — Automated labeling and model retraining
- `svm_tag_events.py` — Tag/classify events using trained SVM model

**Data Processing & Normalization:**
- `event_normalizer.py` — Normalize and standardize event data
- `events_to_labelset.py` — Convert events into labeled training sets
- `fill_recurring_labels.py` — Propagate labels across recurring events
- `fix_event_times.py` — Fix and standardize event times
- `clean_chamber_urls.py` — Clean and validate chamber/venue URLs

**Integration & Data Sources:**
- `google_sheets_source.py` — Google Sheets integration and syncing
- `venue_registry.py` — Manage venue and organization data
- `wren_haven_scraper.py` — Scraper for Wren Haven events

**Utilities:**
- `env_loader.py` — Environment variable loading and configuration
- `logger.py` — Centralized logging configuration
- `smart_label_helper.py` — Helper utilities for labeling workflows
- `tag_taxonomy.py` — Taxonomy and tag management

**Deployment & Health:**
- `make_cloud_pipeline.py` — MAKE.COM (CloudMIG) workflow integration
- `make_deploy_helper.py` — Deployment helper utilities
- `make_health_check.py` — Deployment health verification
- `health_check.py` — General system health checks

**Wrappers & Runners:**
- `run_pipeline_with_smoketest.py` — Safe pipeline execution with validation
- `run_pipeline_with_smoketest.sh` — Shell wrapper for safe pipeline runs
- `run_with_venv.sh` — Virtual environment activation wrapper

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

Windows batch/PowerShell scripts:
- Environment setup (`env.ps1`, `env.ps1.template`)
- Wrappers and runners (`run_*.ps1`, `run_*.bat`)
- Deployment helpers (`setup_scheduled_tasks.ps1`)

### macos/ (macOS-Specific Scripts)

macOS/Linux shell scripts:
- Environment setup (`env.sh`, `env.sh.template`)
- Platform-specific utilities

## Quick Start

**Full pipeline (safe-by-default):**
```bash
export AUTO_UPLOAD=false
python scripts/automated_pipeline.py
```

**Training a new classifier:**
```bash
python scripts/svm_train_from_file.py --input data/labeled/events.csv --output data/artifacts/
```

**WordPress upload (interactive):**
```bash
python scripts/wordpress_uploader.py
```

**Health check:**
```bash
python scripts/health_check.py
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
