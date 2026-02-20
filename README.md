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
└── tests/          # Test files (unit/, integration/, smoke/)
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

## Running Tests Locally

Install dependencies and run the unit test suite from the project root:

```bash
pip install -r requirements.txt pytest
python -m pytest tests/unit -v --tb=short
```

Tests are organized under `tests/`:

| Directory | Purpose | Runs in CI? |
|---|---|---|
| `tests/unit/` | Fast, isolated unit tests — no network or external deps | ✅ Yes |
| `tests/integration/` | Integration tests requiring external services | ❌ Manual only |
| `tests/smoke/` | Lightweight smoke tests for module imports and config | ❌ Manual only |

Use pytest markers to skip slow or network-dependent tests:

```bash
# Run only tests that are not slow/network/integration
python -m pytest tests/unit -v --tb=short -m "not slow and not network and not integration"
```

