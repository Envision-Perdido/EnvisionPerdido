# Pipeline Entry Points

Main executable workflows for the Envision Perdido event management system.

## Scripts (3)

- `automated_pipeline.py` — Full pipeline execution
  - Scrapes events from all configured sources
  - Classifies events using trained SVM model
  - Exports results to CSV
  - Sends email notifications
  - Optionally uploads to WordPress
  
  Usage:
  ```bash
  python scripts/pipelines/automated_pipeline.py
  ```
  
  Environment variables:
  - `AUTO_UPLOAD` — Auto-upload to WordPress (default: false)
  - `SITE_TIMEZONE` — WordPress timezone (default: America/Chicago)

- `wordpress_uploader.py` — Interactive event uploader
  - Reads from latest CSV export
  - Performs dry-run for review
  - Creates events as drafts
  - Optionally publishes events
  - Supports image assignment
  
  Usage:
  ```bash
  python scripts/pipelines/wordpress_uploader.py
  ```
  
  Environment variables:
  - `WP_SITE_URL` — WordPress site URL
  - `WP_USERNAME` — WordPress username
  - `WP_APP_PASSWORD` — WordPress Application Password

- `run_pipeline_with_smoketest.py` — Safe pipeline wrapper
  - Runs full pipeline with validation
  - Enforces safe defaults (AUTO_UPLOAD=false)
  - Validates evcal_srow epoch calculations
  - Cross-platform (Windows, macOS, Linux)
  
  Usage:
  ```bash
  python scripts/pipelines/run_pipeline_with_smoketest.py
  ```

## Quick Start

**Run the full pipeline with validation:**
```bash
python scripts/pipelines/run_pipeline_with_smoketest.py
```

**Upload events to WordPress (interactive):**
```bash
python scripts/pipelines/wordpress_uploader.py
```

## Integration

These entry points integrate:
- **Scrapers** — Data collection from multiple sources
- **ML scripts** — Event classification using trained model
- **Data processing** — Normalization and enrichment
- **Core utilities** — Logging, config, health checks
- **WordPress API** — Event upload and publication

## Workflow

Typical pipeline workflow:
```
automated_pipeline.py
  ├─ Scrape events (scrapers/)
  ├─ Classify (ml/)
  ├─ Normalize & enrich (data_processing/)
  ├─ Export to CSV (output/pipeline/)
  ├─ Send email (core/logger)
  └─ Optional auto-upload (wordpress_uploader.py)

wordpress_uploader.py
  ├─ Dry-run review
  ├─ Create as drafts
  ├─ Optionally publish
  └─ Report results
```

## Safe Defaults

These entry points follow safety-first principles:
- ✅ `AUTO_UPLOAD=false` by default (requires explicit confirmation)
- ✅ Dry-run before actual operations
- ✅ Interactive confirmation for destructive operations
- ✅ Comprehensive logging and error reporting
- ✅ Email confirmation of all changes

## Monitoring

All pipelines produce:
- **Logs** — Detailed execution logs in `output/logs/`
- **Exports** — CSV files in `output/pipeline/`
- **Email confirmations** — Timestamped results
- **Dry-run reports** — Full impact analysis before upload
