---
name: calendar-env-setup
description: Set up local environment variables for the Envision Perdido calendar project when the user needs WordPress, email, and automation settings configured for local or Docker-driven runs.
---

# Calendar Env Setup

Use this skill when the task is to configure credentials and runtime environment variables for this repository.

## Supported Config Files

This repo's Python loader reads these locations:

- Windows: `scripts/windows/env.ps1`
- macOS/Linux: `scripts/macos/env.sh`
- Fallback secrets file:
  - Windows: `~/.secrets/envision_env.ps1`
  - macOS/Linux: `~/.secrets/envision_env.sh`

Do not assume a root `.env` file will be loaded. `.env` is gitignored, but the current `scripts/env_loader.py` does not parse it.

## Setup Workflow

1. Detect the platform.
2. Start from the existing template:
   - Windows: copy `scripts/windows/env.ps1.example` or `scripts/windows/env.ps1.template` to `scripts/windows/env.ps1`
   - macOS/Linux: copy `scripts/macos/env.sh.template` to `scripts/macos/env.sh`
3. Fill in the required values.
4. Prefer moving the finished secrets file to `~/.secrets/envision_env.ps1` or `~/.secrets/envision_env.sh` for safer machine-local storage.
5. Keep credentials out of git. The repo already ignores these files.

## Required Variables

Always configure:

- `SMTP_SERVER`
- `SMTP_PORT`
- `SENDER_EMAIL`
- `EMAIL_PASSWORD`
- `RECIPIENT_EMAIL`

Configure these as well when `AUTO_UPLOAD=true`:

- `WP_SITE_URL`
- `WP_USERNAME`
- `WP_APP_PASSWORD`

Common optional flags:

- `AUTO_UPLOAD`
- `SITE_TIMEZONE`
- `HEALTH_SEND_OK`

## Example Values

macOS/Linux format:

```bash
export WP_SITE_URL="https://your-site.org"
export WP_USERNAME="your_username"
export WP_APP_PASSWORD="xxxx xxxx xxxx xxxx xxxx xxxx"
export SMTP_SERVER="smtp.gmail.com"
export SMTP_PORT="587"
export SENDER_EMAIL="your-email@gmail.com"
export EMAIL_PASSWORD="your-app-password"
export RECIPIENT_EMAIL="notify@example.com"
export AUTO_UPLOAD="false"
export SITE_TIMEZONE="America/Chicago"
```

Windows PowerShell format:

```powershell
$env:WP_SITE_URL = "https://your-site.org"
$env:WP_USERNAME = "your_username"
$env:WP_APP_PASSWORD = "xxxx xxxx xxxx xxxx xxxx xxxx"
$env:SMTP_SERVER = "smtp.gmail.com"
$env:SMTP_PORT = "587"
$env:SENDER_EMAIL = "your-email@gmail.com"
$env:EMAIL_PASSWORD = "your-app-password"
$env:RECIPIENT_EMAIL = "notify@example.com"
$env:AUTO_UPLOAD = "false"
$env:SITE_TIMEZONE = "America/Chicago"
```

## Verification

After setup, run one of the documented commands that imports `scripts/env_loader.py`, for example:

```bash
docker compose run --rm app python scripts/health_check.py
```

or, for a local venv workflow:

```bash
python scripts/health_check.py
```

If variables are missing, the project prints a fail-fast validation message naming the missing keys.

## Notes

- Storing secrets in a gitignored file can be safe for local development, but it is only safe if the file remains untracked and machine-local.
- If the user specifically wants first-class `.env` support, that requires a code change to teach `scripts/env_loader.py` to parse `.env`.
