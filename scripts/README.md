# Scripts Directory

This directory contains all Python automation scripts for the EnvisionPerdido calendar system.

## 📁 Directory Structure

### Main Scripts (Root Level)

**Core Pipeline:**
- `pipeline/automated_pipeline.py` - Main pipeline orchestrator
- `scrapers/perdido_chamber_scraper.py` - Perdido Chamber scraper implementation
- `scrapers/wren_haven_scraper.py` - Wren Haven scraper implementation
- `scrapers/multi_calendar_scraper.py` - Multi-source scraper CLI implementation
- `pipeline/wordpress_uploader.py` - WordPress uploader
- `pipeline/health_check.py` - Health checks

**Utilities:**
- `logger.py` - Compatibility wrapper for structured logging utilities
- `env_loader.py` - Compatibility wrapper for environment loading
- `event_normalizer.py` - Compatibility wrapper for event normalization
- `venue_registry.py` - Compatibility wrapper for venue resolution
- `tag_taxonomy.py` - Compatibility wrapper for tag taxonomy
- `browser_bootstrap.py` - Compatibility wrapper for bootstrap helpers

**Machine Learning:**
- `ml/svm_train_from_file.py` - SVM training
- `ml/svm_tag_events.py` - SVM tagging
- `analytics/svm_analytics.py` - SVM analytics graphs + markdown report
- `ml/auto_label_and_train.py` - Automated training
- `ml/events_to_labelset.py` - Labelset generation
- `ml/consolidate_training_data.py` - Dataset consolidation
- `ml/retrain_end_to_end.py` - Chained retraining + evaluation report
- `ml/audit_datasets.py` - Dataset audits
- `ml/modelViewer.py` - Model inspection

**Setup & Deployment:**
- `pipeline/run_pipeline_with_smoketest.py` - Safety checks wrapper
- `tooling/setup_image_mapper.py` - Image mapping setup

**Shell scripts (compatibility wrappers — originals in subfolders):**
- `deploy-and-run.sh` → `ops/deploy-and-run.sh`
- `load_env.sh` → `ops/load_env.sh`
- `verify_security.sh` → `ops/verify_security.sh`
- `verify-setup.sh` → `ops/verify-setup.sh`
- `new-branch.sh` → `dev/new-branch.sh`
- `new-branch.ps1` → `dev/new-branch.ps1`
- `run_delete_all_events.sh` → `maintenance/run_delete_all_events.sh`

### Subdirectories

- **[pipeline/](pipeline/)** - Pipeline execution, health checks, uploads, and pipeline utilities
- **[ml/](ml/)** - Training, labeling, dataset consolidation, and model utilities
- **[tooling/](tooling/)** - Shared utilities (env loading, logging, normalization, taxonomy, bootstrap)
- **[scrapers/](scrapers/)** - Source scraping implementations (Perdido, Wren Haven, multi-source)
- **[ops/](ops/)** - Operational shell scripts: deployment, env loading, and setup verification
- **[dev/](dev/)** - Developer tooling: debugging scripts and git branch helpers
- **[maintenance/](maintenance/)** - Administrative and maintenance scripts
- **[windows/](windows/)** - Windows-specific batch files and PowerShell scripts
- **[macos/](macos/)** - macOS-specific shell scripts

## 🚀 Quick Start

Run the main pipeline:
```bash
python scripts/pipeline/automated_pipeline.py
```

Upload events to WordPress:
```bash
python scripts/pipeline/wordpress_uploader.py
```

Run with safety checks (recommended):
```bash
python scripts/pipeline/run_pipeline_with_smoketest.py
```

Scrape and consolidate multi-source events for labeling:
```bash
python scripts/multi_calendar_scraper.py --config data/community_calendar_sources.json --target-events 10000
```

Run end-to-end retraining with recall-target threshold policy:
```bash
python scripts/ml/retrain_end_to_end.py \
	--target-class1-recall 0.92 \
	--min-class1-precision 0.68 \
	--review-margin 0.40
```

Generate SVM analytics report and graphs:
```bash
python scripts/analytics/svm_analytics.py
```

## 📖 Documentation

See [docs/INDEX.md](../docs/INDEX.md) for complete documentation links.
