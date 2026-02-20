# GitHub Secrets & Variables Setup

This guide covers every credential and configuration value that must be added to GitHub
**before making this repository public**.  Secrets are encrypted and never shown in logs;
variables are non-sensitive settings stored in plain text.

---

## How to Add Secrets / Variables

1. Go to your repository on GitHub.
2. Click **Settings** → **Secrets and variables** → **Actions**.
3. For each sensitive value: click **New repository secret**.
4. For each non-sensitive configuration value: click the **Variables** tab → **New repository variable**.

> **Org-level secrets / variables** (Settings → Secrets → Actions at the *organisation* level) work the same way and are automatically inherited by every repository in the organisation, so you only need to set them once if you manage multiple repos.

---

## Required Repository Secrets

These are used by the **Health Check** workflow (`.github/workflows/health-check.yml`).
The workflow will fail to authenticate with WordPress and the email provider if any of these
are missing.

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `WP_SITE_URL` | Full URL of your WordPress site | `https://envisionperdido.org` |
| `WP_USERNAME` | WordPress admin username | `admin` |
| `WP_APP_PASSWORD` | WordPress Application Password — generated in **Users → Profile → Application Passwords** (includes spaces) | `xxxx xxxx xxxx xxxx xxxx xxxx` |
| `SMTP_SERVER` | Outbound email (SMTP) hostname | `smtp.gmail.com` |
| `SMTP_PORT` | Outbound email (SMTP) port | `587` |
| `SENDER_EMAIL` | Email address that sends notifications | `youremail@gmail.com` |
| `EMAIL_PASSWORD` | App Password for the sender email account (for Gmail this is a 16-character app password, **not** your account password) | `abcd efgh ijkl mnop` |
| `RECIPIENT_EMAIL` | Email address that receives pipeline/health-check notifications | `youremail@gmail.com` |

### Generating a WordPress Application Password

1. Log in to your WordPress admin dashboard.
2. Go to **Users → Your Profile**.
3. Scroll to the **Application Passwords** section.
4. Enter a label (e.g. `GitHub Actions`) and click **Add New Application Password**.
5. Copy the generated password — it will only be shown once.
6. Add it to GitHub as the `WP_APP_PASSWORD` secret.

### Generating a Gmail App Password

1. Make sure **2-Step Verification** is enabled on your Google account.
2. Go to **Google Account → Security → App passwords**.
3. Select app: **Mail**, device: **Other** (type `GitHub Actions`).
4. Click **Generate** and copy the 16-character password.
5. Add it to GitHub as the `EMAIL_PASSWORD` secret.

> A regular Gmail account password will **not** work; you must use an App Password.

---

## Optional Repository Variables

These are non-sensitive configuration values.  They have built-in defaults so the workflows
run correctly without them, but you can override them by adding GitHub **Variables**
(not Secrets — they are visible in workflow logs).

| Variable Name | Default | Description |
|---------------|---------|-------------|
| `SITE_TIMEZONE` | `America/Chicago` | IANA timezone name used when computing EventON epoch timestamps (e.g. `America/New_York`, `America/Los_Angeles`) |
| `AUTO_UPLOAD` | `true` | Set to `false` to disable automatic WordPress uploads; the pipeline will export the CSV and send the review email but will not call the uploader |
| `HEALTH_MIN_UPCOMING` | `5` | Minimum number of upcoming events required for the health check to pass |
| `HEALTH_REQUIRE_PAGE` | `false` | Set to `true` to require the public calendar page to load successfully during health checks |
| `HEALTH_SEND_OK` | `false` | Set to `true` to send a success email even when the health check passes (useful for confirming the workflow ran) |

---

## Which Workflows Use Which Secrets

| Workflow file | Secrets / Variables used |
|---------------|--------------------------|
| `health-check.yml` | All 8 required secrets |
| `smoketest.yml` | `SITE_TIMEZONE` variable (optional; defaults to `America/Chicago`) |
| `test.yml` | None — tests are fully offline |
| `lint.yml` | None — linting is fully offline |
| `stale.yml` | None — uses the built-in `GITHUB_TOKEN` |

---

## Security Notes

- **Never commit credentials** to the repository.  The `scripts/windows/env.ps1` and
  `scripts/macos/env.sh` local config files are already listed in `.gitignore`.
- Use **repository secrets** (or org-level secrets) for all sensitive values.
- WordPress Application Passwords can be revoked at any time from the WordPress admin
  dashboard without changing your account password.
- Gmail App Passwords can be revoked from **Google Account → Security → App passwords**.
- Rotate secrets immediately if they are accidentally exposed.

---

## Verifying the Setup

After adding all secrets, trigger the Health Check workflow manually:

1. Go to the **Actions** tab.
2. Select **Health Check Monitoring**.
3. Click **Run workflow → Run workflow**.
4. Confirm the run completes with a ✅ green checkmark.

If it fails, expand the **Run health check** step to see which credential is incorrect.
See the [CI/CD Guide](CI_CD_GUIDE.md) for detailed troubleshooting steps.
