# Scripts Directory

This directory contains all Python automation scripts for the EnvisionPerdido calendar system.

## 📁 Directory Structure

### Main Scripts (Root Level)

**Core Pipeline:**
- `automated_pipeline.py` - Main orchestrator: scrape → classify → email → upload
- `Envision_Perdido_DataCollection.py` - Perdido Chamber event scraper
- `wren_haven_scraper.py` - Wren Haven Homestead event scraper
- `wordpress_uploader.py` - Upload events to WordPress EventON calendar
- `health_check.py` - Monitor system health and send alerts

**Utilities:**
- `logger.py` - Structured logging with JSON output
- `env_loader.py` - Cross-platform environment variable loader
- `event_normalizer.py` - Event enrichment and normalization
- `venue_registry.py` - Venue name resolution
- `tag_taxonomy.py` - Event tag vocabulary
- `browser_bootstrap.py` - Playwright helper for API discovery

**Machine Learning:**
- `svm_train_from_file.py` - Train SVM classifier
- `svm_tag_events.py` - Apply trained model to tag events
- `auto_label_and_train.py` - Automated training pipeline
- `smart_label_helper.py` - Predict labels with confidence scores
- `fill_recurring_labels.py` - Propagate labels across series
- `merge_and_propagate_labels.py` - Merge and propagate labels
- `events_to_labelset.py` - Convert events to training format
- `modelViewer.py` - Inspect trained models

**Setup & Deployment:**
- `run_pipeline_with_smoketest.py` - Pipeline wrapper with safety checks
- `setup_image_mapper.py` - Initialize image mapping directories

### Subdirectories

- **[dev/](dev/)** - Testing and debugging scripts
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

## 📖 Documentation

See [docs/INDEX.md](../docs/INDEX.md) for complete documentation links.
