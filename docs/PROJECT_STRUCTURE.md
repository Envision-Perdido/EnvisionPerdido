# EnvisionPerdido Project Structure

```
EnvisionPerdido/
├── docs/                              # All documentation
│   ├── QUICKSTART.md
│   ├── SETUP_GUIDE.md
│   ├── WORDPRESS_INTEGRATION_GUIDE.md
│   └── EVENTON_PLUGIN_INSTALL.md
│
├── scripts/                           # Python automation scripts
│   ├── automated_pipeline.py          # Main pipeline: scrape → classify → email
│   ├── wordpress_uploader.py          # Upload events to WordPress
│   ├── health_check.py                # Health check for calendar/API
│   ├── Envision_Perdido_DataCollection.py  # Perdido Chamber scraper
│   ├── wren_haven_scraper.py          # Wren Haven Homestead scraper
│   ├── event_normalizer.py            # Event enrichment and normalization
│   ├── logger.py                      # Structured logging
│   ├── env_loader.py                  # Cross-platform env loader
│   ├── venue_registry.py              # Venue name resolution
│   ├── browser_bootstrap.py           # Playwright API discovery helper
│   ├── auto_label_and_train.py        # ML training utilities
│   ├── svm_train_from_file.py         # Train SVM model
│   ├── svm_tag_events.py              # Apply SVM model
│   ├── smart_label_helper.py          # Predict with confidence scores
│   ├── events_to_labelset.py          # Convert to training format
│   ├── merge_and_propagate_labels.py  # Label management
│   ├── fill_recurring_labels.py       # Propagate recurring labels
│   ├── dev/                           # Testing and debugging scripts
│   │   ├── test_*.py                  # Various test scripts
│   │   ├── debug_*.py                 # Debugging utilities
│   │   └── check_evcal_srow.py        # Epoch validation smoke test
│   ├── maintenance/                   # Administrative scripts
│   │   ├── delete_*.py                # Event deletion scripts
│   │   ├── fix_*.py                   # Data repair scripts
│   │   ├── set_*.py                   # Configuration scripts
│   │   └── query_*.py                 # Data query scripts
│   └── windows/                       # Windows-specific runners
│       └── run_health_check.bat
│
├── data/                              # All data files (ignored in git)
│   ├── raw/                           # Raw scraped data (perdido_events*.csv, *.json)
│   ├── labeled/                       # Labeled training data (*_labeled.csv)
│   ├── processed/                     # Intermediate processed data (combined_events*.csv)
│   └── artifacts/                     # Model artifacts (*.pkl files)
│       ├── event_classifier_model.pkl
│       └── event_vectorizer.pkl
│
├── output/                            # Generated outputs (ignored in git)
│   ├── pipeline/                      # Pipeline outputs (calendar_upload_*.csv, scraped_events_*.csv)
│   └── logs/                          # Log files
│
├── plugins/                           # WordPress plugins
│   ├── eventon-rest-api-meta.php      # EventON REST API meta fields plugin
│   └── builds/                        # Built plugin ZIPs (ignored in git)
│       └── eventon-rest-api-meta.zip
│
├── notebooks/                         # Jupyter notebooks
│   └── EVP_SVM.ipynb                  # SVM experimentation notebook
│
├── .venvEnvisionPerdido/              # Python virtual environment (ignored in git)
│
├── Envision_Perdido_DataCollection.py # Main scraper module
├── requirements.txt                   # Python dependencies
├── .gitignore                         # Git ignore rules
└── README.md                          # This file
```

## Quick Navigation

### Running the Pipeline
```powershell
cd C:\Users\scott\UWF-Code\EnvisionPerdido
.\.venvEnvisionPerdido\Scripts\Activate.ps1
python scripts\automated_pipeline.py
```

### Uploading Events
```powershell
python scripts\wordpress_uploader.py
```

### Health Check
```powershell
python scripts\health_check.py
```

### Documentation
- **Documentation Index**: `docs/INDEX.md`
- **Getting Started**: `docs/QUICKSTART.md`
- **Setup Instructions**: `docs/CROSS_PLATFORM_SETUP.md`
- **WordPress Integration**: `docs/WORDPRESS_INTEGRATION_GUIDE.md`
- **Plugin Installation**: `docs/EVENTON_PLUGIN_INSTALL.md`

## File Organization Rules

### Data Files
- **Raw scraped data** → `data/raw/` (perdido_events*.csv, *.json)
- **Labeled training data** → `data/labeled/` (*_labeled.csv)
- **Processed/combined** → `data/processed/` (combined_events*.csv)
- **Model files (.pkl)** → `data/artifacts/`

### Output Files
- **Pipeline outputs** (calendar CSVs) → `output/pipeline/`
- **Log files** → `output/logs/`

### Scripts
- **Python automation** → `scripts/`
- **Windows batch files** → `scripts/windows/`

### Plugins
- **WordPress plugins** → `plugins/`
- **Built ZIPs** → `plugins/builds/`

## Git Ignore Summary
- All `output/` contents (CSVs, logs)
- All `data/` contents (event CSVs, JSON)
- Plugin builds (`plugins/builds/`)
- Virtual environment (`.venvEnvisionPerdido/`)
- Ad-hoc debug scripts (`check_*.py`, `compare_events.py`, etc.)

## System Overview

**Purpose**: Automated community event classification and calendar publishing

**Workflow**:
1. Scrape events from Perdido Chamber website
2. Classify using trained SVM model (96.47% accuracy)
3. Send email review with community events
4. Upload approved events to WordPress EventON calendar
5. Health check monitors system integrity

**Key Components**:
- **Scraper**: `Envision_Perdido_DataCollection.py`
- **Model**: `data/artifacts/event_classifier_model.pkl` + `event_vectorizer.pkl`
- **Pipeline**: `scripts/automated_pipeline.py`
- **Uploader**: `scripts/wordpress_uploader.py`
- **Health Check**: `scripts/health_check.py`
- **WordPress Plugin**: `plugins/eventon-rest-api-meta.php`

## Next Steps

1. **Schedule automation**: Set up weekly Task Scheduler jobs
2. **Persist credentials**: Set environment variables for email and WordPress
3. **Monitor health**: Enable weekly health check emails
4. **Optional optimizations**: Tune confidence thresholds, add more training data

For detailed instructions, see `docs/QUICKSTART.md`.
