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

### Local Development (Windows)

```powershell
# Install uv once (if needed):
# powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Create/sync local environment from lockfile
cd path\to\EnvisionPerdido
uv sync

# Run the pipeline
uv run python scripts\automated_pipeline.py

# Upload events to WordPress
uv run python scripts\wordpress_uploader.py

# Health check
uv run python scripts\health_check.py
```

### Remote Deployment (Linux/macOS via make.com)

For remote server deployment with make.com orchestration:

```bash
# 1. Clone repository on remote server
git clone https://github.com/Envision-Perdido/EnvisionPerdido.git
cd EnvisionPerdido

# 2. Set up environment
cp .env.example .env
nano .env  # Add your WordPress & email credentials

# 3. Verify setup (optional but recommended)
make verify

# 4. Test in dry-run mode (safe, no uploads)
make dry-run

# 5. Enable full automation (make.com will call this)
make run-pipeline
```

**make.com Configuration Example:**

```
[Trigger: Schedule (daily 8am) OR Webhook]
    ↓
[SSH Module: Execute command]
    Host: your-server.example.com
    Command: cd /home/ubuntu/EnvisionPerdido && make dry-run
    ↓
[Conditional: Check exit code = 0]
    ↓
[SSH Module: Execute command]
    Command: cd /home/ubuntu/EnvisionPerdido && make run-pipeline
    ↓
[Email: Send completion notification]
```

For complete setup instructions, see [Deployment on make.com](#deployment-on-make.com) below.

## Documentation

All detailed documentation is in the `docs/` folder. See **[docs/INDEX.md](docs/INDEX.md)** for a complete navigation guide.

**Quick Links:**
- **[Quick Start Guide](docs/QUICKSTART.md)** - Get started in 5 minutes
- **[Project Structure](docs/PROJECT_STRUCTURE.md)** - Folder organization and file locations
- **[WordPress Integration](docs/WORDPRESS_INTEGRATION_GUIDE.md)** - Calendar upload workflow
- **[GitHub Secrets Setup](docs/GITHUB_SECRETS.md)** - Required secrets and variables before going public
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

- Python 3.13+
- uv (recommended package/environment manager)
- WordPress site with EventON plugin
- Gmail account for email notifications (or SMTP server)
- Windows Task Scheduler (for automation)

Dependencies are managed in `pyproject.toml` and pinned in `uv.lock`.

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

## Running Tests Locally

Install dependencies and run the unit test suite from the project root:

```bash
uv sync
uv run python -m pytest tests/unit -v --tb=short
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
uv run python -m pytest tests/unit -v --tb=short -m "not slow and not network and not integration"
```

## Deployment on make.com

This project supports automated deployment and orchestration via **make.com** using SSH commands on a remote server.

### Prerequisites

Your supervisor/deployment server needs:

- **Linux or macOS** with SSH access
- **Git** installed
- **Python 3.11+** installed
- An SSH key pair (for make.com to authenticate)
- `.env` file with WordPress & email credentials (filled from `.env.example`)
- Model artifacts at `data/artifacts/event_classifier_model.pkl` and `event_vectorizer.pkl`

### First-Time Server Setup

SSH into your deployment server and run:

```bash
# Clone repository
git clone https://github.com/Envision-Perdido/EnvisionPerdido.git
cd EnvisionPerdido

# Set up from template
cp .env.example .env

# Edit with your WordPress & email credentials
nano .env

# Install dependencies (creates .venv and syncs from pyproject.toml + uv.lock)
make setup

# Verify everything is configured correctly
make verify
```

Once `make verify` passes, the server is ready for make.com integration.

### make.com Webhook/Scenario Configuration

In **make.com**, create a scenario with the following modules:

1. **Trigger**: 
   - "Schedule" (e.g., daily at 8am)
   - OR "Webhooks" (if triggered by external event)

2. **Dry-run Test** (SSH module):
   - **Host**: `your-server.example.com`
   - **Port**: `22` (or your SSH port)
   - **Username**: `ubuntu` (or your user)
   - **Private Key**: [upload your SSH key]
   - **Command**: 
     ```bash
     cd /home/ubuntu/EnvisionPerdido && make dry-run
     ```

3. **Conditional Check**:
   - If **exit code** from step 2 is `0`, proceed to step 4
   - Otherwise, send error notification

4. **Full Pipeline** (SSH module):
   - Same host/credentials as step 2
   - **Command**:
     ```bash
     cd /home/ubuntu/EnvisionPerdido && make run-pipeline
     ```

5. **Notification** (Email module):
   - Send completion summary to supervisors
   - Include exit status and logs

### Available make Targets

From the remote server (or via make.com SSH):

```bash
make help           # Show all available targets
make setup          # Create .venv and sync dependencies with uv
make verify         # Check setup (env, artifacts, packages)
make test           # Run pytest suite
make lint           # Run ruff linter
make dry-run        # Safe test run (AUTO_UPLOAD=false, no uploads)
make run-pipeline   # Full pipeline with WordPress uploads
make run-uploader   # Interactive uploader (manual review)
```

### Monitoring & Logs

After each run, check:

- **CSV exports**: `output/pipeline/calendar_upload_*.csv` (latest file)
- **Logs**: `output/logs/automated_pipeline_*.log` (latest file)

Logs include:
- Scraping results (count, sources)
- Classification results (count, confidence)
- WordPress upload status
- Email delivery confirmation

make.com will capture stdout/stderr from SSH commands. Configure email notifications in make.com to alert on failures.

### Troubleshooting

**SSH connection fails:**
- Check SSH key is uploaded to make.com
- Verify public key is in `~/.ssh/authorized_keys` on server
- Ensure firewall allows SSH (port 22 or custom)

**Pipeline exits with error:**
- SSH into server: `cd EnvisionPerdido && tail -50 output/logs/*.log`
- Run `make verify` to check setup
- Ensure `.env` is filled with valid credentials

**No events scraped/classified:**
- Check data sources are accessible: `curl https://perdidochamber.org`
- Verify model artifacts exist: `ls -la data/artifacts/`
- Review full log: `cat output/logs/automated_pipeline_*.log | grep -i error`

For debugging during development, use `make dry-run` to test without uploading to WordPress.

