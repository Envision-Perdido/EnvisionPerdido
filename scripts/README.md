# Scripts Directory

This directory contains all Python automation scripts for the EnvisionPerdido calendar system.

## 📁 Directory Structure

### Main Scripts (Root Level)

**Core Pipeline:**
- `automated_pipeline.py` - Compatibility wrapper for pipeline orchestrator
- `Envision_Perdido_DataCollection.py` - Compatibility wrapper for the Perdido Chamber scraper
- `wren_haven_scraper.py` - Compatibility wrapper for Wren Haven scraper
- `multi_calendar_scraper.py` - Compatibility wrapper for the multi-source scraper CLI
- `wordpress_uploader.py` - Compatibility wrapper for WordPress uploader
- `health_check.py` - Compatibility wrapper for health checks

**Utilities:**
- `logger.py` - Compatibility wrapper for structured logging utilities
- `env_loader.py` - Compatibility wrapper for environment loading
- `event_normalizer.py` - Compatibility wrapper for event normalization
- `venue_registry.py` - Compatibility wrapper for venue resolution
- `tag_taxonomy.py` - Compatibility wrapper for tag taxonomy
- `browser_bootstrap.py` - Compatibility wrapper for bootstrap helpers

**Machine Learning:**
- `svm_train_from_file.py` - Compatibility wrapper for SVM training
- `svm_tag_events.py` - Compatibility wrapper for SVM tagging
- `auto_label_and_train.py` - Compatibility wrapper for automated training
- `events_to_labelset.py` - Compatibility wrapper for labelset generation
- `consolidate_training_data.py` - Compatibility wrapper for dataset consolidation
- `retrain_end_to_end.py` - Compatibility wrapper for chained retraining + evaluation report
- `audit_datasets.py` - Compatibility wrapper for dataset audits
- `modelViewer.py` - Compatibility wrapper for model inspection

**Setup & Deployment:**
- `run_pipeline_with_smoketest.py` - Compatibility wrapper with safety checks
- `setup_image_mapper.py` - Compatibility wrapper for image mapping setup

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
python scripts/automated_pipeline.py
```

Upload events to WordPress:
```bash
python scripts/wordpress_uploader.py
```

Run with safety checks (recommended):
```bash
python scripts/run_pipeline_with_smoketest.py
```

Scrape and consolidate multi-source events for labeling:
```bash
python scripts/multi_calendar_scraper.py --config data/community_calendar_sources.json --target-events 10000
```

Run end-to-end retraining with recall-target threshold policy:
```bash
python scripts/retrain_end_to_end.py \
	--target-class1-recall 0.92 \
	--min-class1-precision 0.68 \
	--review-margin 0.40
```

## 📖 Documentation

See [docs/INDEX.md](../docs/INDEX.md) for complete documentation links.
