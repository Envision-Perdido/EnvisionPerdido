# EnvisionPerdido - Automated Community Calendar System

Automated event classification and publishing system for the Envision Perdido non-profit organization community calendar.

## Overview

This system automatically:
1. Scrapes events from the Perdido Chamber website
2. Classifies them as community/non-community using Support Vector Machine (SVM) ML model (96.47% accuracy)
3. Sends email reviews with classified events
4. Uploads approved events to the WordPress EventON calendar
5. Monitors system health with automated checks

## Quick Start

```powershell
# Activate environment
cd path\to\EnvisionPerdido
.\.venvEnvisionPerdido\Scripts\Activate.ps1

# Run the pipeline
python scripts\automated_pipeline.py

# Upload events to WordPress
python scripts\wordpress_uploader.py

# Health check
python scripts\health_check.py
```

## Docker Workflow

Build the containerized runtime:

```bash
docker compose build
```

Run the documented commands inside the container:

```bash
docker compose run --rm app python scripts/automated_pipeline.py
docker compose run --rm app python scripts/wordpress_uploader.py
docker compose run --rm app python scripts/health_check.py
```

Open an interactive shell if you want to run other repo commands manually:

```bash
docker compose run --rm app
```

Generated files persist on the host under `container-data/`:

- `container-data/output/` maps to the app's `output/`
- `container-data/data-cache/` maps to the app's `data/cache/`

## Using Codex In This Repo

If you run `codex` from this repository, there are local reusable skills under `skills/` that map to the main project workflows.

For a novice user, the simplest prompts are:

- "Set up the environment" -> uses `calendar-env-setup`
- "Build the Docker image" -> uses `calendar-docker-build`
- "Run the pipeline" -> uses `calendar-run-pipeline`
- "Upload events to WordPress" -> uses `calendar-wordpress-upload`
- "Run a health check" -> uses `calendar-health-check`
- "Open a shell in the container" -> uses `calendar-shell`

These skills are stored in this repository for portability:

- `skills/calendar-env-setup/`
- `skills/calendar-docker-build/`
- `skills/calendar-run-pipeline/`
- `skills/calendar-wordpress-upload/`
- `skills/calendar-health-check/`
- `skills/calendar-shell/`

If you are not sure what to ask for, start with one of these exact prompts:

```text
Set up the environment for this repo
Build the Docker image
Run the pipeline in Docker
Upload events to WordPress
Run a health check
Open a bash shell in the container
```

## Documentation

All detailed documentation is in the `docs/` folder. See **[docs/INDEX.md](docs/INDEX.md)** for a complete navigation guide.

**Quick Links:**
- **[Quick Start Guide](docs/QUICKSTART.md)** - Get started in 5 minutes
- **[Project Structure](docs/PROJECT_STRUCTURE.md)** - Folder organization and file locations
- **[WordPress Integration](docs/WORDPRESS_INTEGRATION_GUIDE.md)** - Calendar upload workflow
- **[Contributing](CONTRIBUTING.md)** - Development workflow and branching strategy
- **[Critical Issues](CRITICAL_ISSUES.md)** - Known blockers and production issues

## Project Structure

```
EnvisionPerdido/
├── docs/           # All documentation
├── scripts/        # Python automation scripts
├── data/           # Raw, labeled, processed data + model artifacts
├── output/         # Pipeline outputs and logs
├── plugins/        # WordPress plugins
├── notebooks/      # Jupyter notebooks
└── tests/          # Test files
```

See [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md) for the complete structure.

## Key Features

- **96.47% Classification Accuracy** - Trained SVM model on 424 labeled events
- **Fully Automated** - Scrape, classify, email, upload workflow
- **Email Review System** - HTML emails with event statistics and CSV exports
- **WordPress Integration** - Direct upload to EventON calendar via REST API
- **Health Monitoring** - Automated checks with email alerts
- **Organized Structure** - Clean folder organization for easy maintenance

## Requirements

- Python 3.13+ with virtual environment
- WordPress site with EventON plugin
- Gmail account for email notifications (or SMTP server)
- Windows Task Scheduler (for automation)

See `requirements.txt` for Python dependencies.

## Configuration

This repo currently loads local credentials from `scripts/windows/env.ps1`, `scripts/macos/env.sh`, or `~/.secrets/envision_env.*` via `scripts/env_loader.py`. A root `.env` file is gitignored, but it is not automatically loaded by the current code.

Set these environment variables:

```powershell
# WordPress
$env:WP_SITE_URL = "https://your-site.org"
$env:WP_USERNAME = "your_username"
$env:WP_APP_PASSWORD = "your_app_password"

# Email
$env:SMTP_SERVER = "smtp.gmail.com"
$env:SMTP_PORT = "587"
$env:SENDER_EMAIL = "your_email@gmail.com"
$env:EMAIL_PASSWORD = "your_gmail_app_password"
$env:RECIPIENT_EMAIL = "your_email@gmail.com"
```

## Next Steps

1. Review [docs/QUICKSTART.md](docs/QUICKSTART.md)
2. Set up credentials (WordPress + Email)
3. Test the pipeline
4. Schedule automation with Task Scheduler
5. Monitor via health checks

## Support

For detailed instructions, troubleshooting, and advanced configuration, see the documentation in the `docs/` folder.

## CI/CD & Monitoring

This repository uses GitHub Actions for automated testing, security scanning, and monitoring:

- ** Automated Tests:** Run on every PR/push
- ** Dependabot:** Weekly security scans
- ** Health Checks:** Weekly system monitoring
- ** Code Linting:** Automated style checks
- ** Stale Management:** Auto-closes inactive issues

See `.github/workflows/` for configuration and [docs/CI_CD_GUIDE.md](docs/CI_CD_GUIDE.md) for details.
