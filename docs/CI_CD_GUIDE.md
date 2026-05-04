# CI/CD & Monitoring Guide

This guide explains all the GitHub Actions agents configured for the EnvisionPerdido automated calendar system.

## Table of Contents
- [Overview](#overview)
- [Agent 1: Dependabot (Security Scanning)](#agent-1-dependabot-security-scanning)
- [Agent 2: Automated Testing](#agent-2-automated-testing)
- [Agent 3: Health Check Monitoring](#agent-3-health-check-monitoring)
- [Agent 4: Code Linting (Ruff)](#agent-4-code-linting-ruff)
- [Agent 5: Stale Issue/PR Manager](#agent-5-stale-issuepr-manager)
- [GitHub Secrets Setup](#github-secrets-setup)
- [Troubleshooting](#troubleshooting)

---

## Overview

The EnvisionPerdido repository uses 5 priority GitHub agents to automate testing, security, monitoring, code quality, and housekeeping:

| Priority | Agent | Trigger | Purpose |
|----------|-------|---------|---------|
| 1 | Dependabot | Weekly | Security vulnerability scanning |
| 2 | Automated Tests | Push/PR | Run pytest test suite |
| 3 | Health Check | Weekly (Mon 8am UTC) | System health monitoring |
| 4 | Code Linting | Push/PR | Code style and quality checks |
| 5 | Stale Manager | Daily | Close inactive issues/PRs |

All workflows are located in `.github/workflows/` and can be viewed in the **Actions** tab of the GitHub repository.

---

## Agent 1: Dependabot (Security Scanning)

**File:** `.github/dependabot.yml`

### What it does
- Monitors `requirements.txt` for security vulnerabilities in Python packages
- Automatically creates pull requests when updates are available
- Groups minor and patch updates together to reduce PR noise

### When it runs
- Weekly (configured schedule)
- Automatically on new vulnerabilities

### Configuration
```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
```

### How to interpret results
1. Dependabot creates PRs with titles like: "Bump package-name from X.Y.Z to X.Y.Z+1"
2. Review the PR description for:
   - **Security vulnerabilities:** Critical to merge immediately
   - **Compatibility:** Check if breaking changes exist
   - **Release notes:** Read changelog for major updates

3. Check the **Security** tab → **Dependabot alerts** for vulnerability details

### Actions to take
- **Security updates:** Merge immediately after CI passes
- **Minor/Patch updates:** Review and merge when convenient
- **Major updates:** Test thoroughly before merging

---

## Agent 2: Automated Testing

**File:** `.github/workflows/test.yml`

### What it does
- Runs the full pytest test suite on every push and pull request
- Installs Playwright browsers for browser_bootstrap tests
- Reports test results and failures

### When it runs
- On every push to `main` branch
- On every pull request targeting `main`

### Test coverage
The test suite includes:
- `test_deduplication.py` - Event deduplication logic
- `test_event_normalizer.py` - Event normalization
- `test_logger.py` - Logging functionality
- `test_rate_limiting.py` - Rate limiting
- `test_scraper_error_isolation.py` - Error handling
- `test_tag_taxonomy.py` - Tag management
- `test_venue_registry.py` - Venue tracking
- `test_wordpress_uploader.py` - WordPress integration
- `test_wren_haven_scraper.py` - Wren Haven scraper

### How to interpret results
1. **✅ Green checkmark:** All tests passed
2. **❌ Red X:** One or more tests failed
3. Click on the failed job to see detailed output

### Viewing test output
```bash
# Click on the workflow run
# Click on "Run Tests" job
# Expand "Run pytest" step
# Review traceback and error messages
```

### Common test failures
- **Import errors:** Missing dependencies (check requirements.txt)
- **Playwright errors:** Browser not installed (workflow installs chromium)
- **Assertion errors:** Code changes broke existing functionality

### Actions to take
- **Never merge a PR with failing tests** (unless unrelated pre-existing failures)
- Fix test failures before requesting review
- Add new tests when adding new features

---

## Agent 3: Health Check Monitoring

**File:** `.github/workflows/health-check.yml`

### What it does
- Runs `scripts/pipeline/health_check.py` to verify system health
- Tests WordPress connectivity and authentication
- Validates email/SMTP configuration
- Sends alerts on failures

### When it runs
- **Scheduled:** Every Monday at 8:00 AM UTC
- **Manual:** Via workflow_dispatch button in Actions tab

### Configuration
This workflow requires **GitHub Secrets** to be configured (see [GitHub Secrets Setup](#github-secrets-setup)).

### How to interpret results
1. **✅ Success:** All systems operational
2. **❌ Failure:** One or more checks failed

Health check verifies:
- WordPress site reachability
- WordPress authentication (REST API)
- SMTP server connectivity
- Email sending capability

### Manual trigger
To manually run the health check:
1. Go to **Actions** tab
2. Select "Health Check Monitoring" workflow
3. Click **Run workflow** button
4. Select branch (usually `main`)
5. Click green **Run workflow** button

### Viewing health check output
```bash
# Navigate to workflow run
# Click "System Health Check" job
# Expand "Run health check" step
# Review output from health_check.py
```

### Common health check failures

#### WordPress connection failed
- **Cause:** Invalid `WP_SITE_URL` or site is down
- **Fix:** Verify URL is correct and site is accessible

#### WordPress authentication failed
- **Cause:** Invalid credentials or expired app password
- **Fix:** Regenerate WordPress app password and update secret

#### SMTP connection failed
- **Cause:** Invalid SMTP settings or blocked port
- **Fix:** Verify SMTP_SERVER, SMTP_PORT, and firewall rules

#### Email send failed
- **Cause:** Invalid email credentials or 2FA not configured
- **Fix:** For Gmail, generate an App Password (not account password)

### Actions to take
- **Weekly:** Review health check results
- **On failure:** Investigate immediately (system may be down)
- **After failure:** Run manual health check after fixing issues

---

## Agent 4: Code Linting (Ruff)

**File:** `.github/workflows/lint.yml`

### What it does
- Runs Ruff linter to check Python code style and quality
- Checks for PEP 8 violations, unused imports, undefined variables
- Validates code formatting with Ruff formatter

### When it runs
- On every push to `main` branch
- On every pull request targeting `main`

### Configuration
Ruff configuration is in `.ruff.toml`:
```toml
line-length = 100
target-version = "py313"
exclude = [".venv*", "data", "output", "notebooks"]
```

### How to interpret results
1. **✅ All checks passed:** Code meets style guidelines
2. **❌ Linting errors:** Code has style violations or errors
3. Click on workflow run to see detailed violations

### Viewing linting output
Ruff provides inline annotations on the PR:
- Violations appear as comments on specific lines
- Error messages explain the issue
- Error codes (e.g., `E501`, `F401`) link to documentation

### Common linting errors

#### E501: Line too long
```python
# Before (line too long)
result = some_really_long_function_name(param1, param2, param3, param4, param5, param6, param7, param8)

# After (fixed)
result = some_really_long_function_name(
    param1, param2, param3, param4,
    param5, param6, param7, param8
)
```

#### F401: Unused import
```python
# Before (unused import)
import requests
import json  # Never used

# After (fixed)
import requests
```

#### F821: Undefined name
```python
# Before (typo in variable name)
user_name = "Alice"
print(username)  # NameError

# After (fixed)
user_name = "Alice"
print(user_name)
```

### Running Ruff locally
```bash
# Install Ruff
pip install ruff

# Check for issues
ruff check .

# Auto-fix issues
ruff check . --fix

# Check formatting
ruff format --check .

# Auto-format
ruff format .
```

### Actions to take
- Fix linting errors before requesting PR review
- Use `ruff check . --fix` to auto-fix simple issues
- Configure your editor to run Ruff on save

---

## Agent 5: Stale Issue/PR Manager

**File:** `.github/workflows/stale.yml`

### What it does
- Automatically marks issues/PRs as stale after 60 days of inactivity
- Automatically closes stale issues/PRs after 30 additional days (90 days total)
- Posts friendly comments before marking stale and closing
- Exempts issues with labels: `pinned`, `security`, `critical`

### When it runs
- **Scheduled:** Daily at midnight UTC
- **Manual:** Via workflow_dispatch button

### Configuration
```yaml
days-before-stale: 60
days-before-close: 30  # After being marked stale
exempt-issue-labels: 'pinned,security,critical'
```

### How to interpret results
The bot posts comments on issues/PRs:

**After 60 days of inactivity:**
> "This issue has been inactive for 60 days and will be closed in 30 days if no activity occurs."

**After 90 days total:**
> "This issue was closed due to inactivity."

### Preventing stale closure
To keep an issue/PR open:
1. **Add activity:** Post a comment or commit
2. **Add exempt label:** Apply `pinned`, `security`, or `critical` label
3. **Re-open:** If auto-closed, just re-open the issue

### Common scenarios

#### Important issue marked as stale
- Add `pinned` label to prevent future stale marking
- Post a comment explaining why it's still relevant

#### PR waiting on external dependency
- Add `pinned` label
- Comment with status update on the dependency

#### Security issue marked as stale
- Should already be exempt with `security` label
- If not, add the label immediately

### Actions to take
- **Weekly:** Review stale issues and determine if they're still relevant
- **When marked stale:** Respond within 30 days or it will close
- **Use labels wisely:** Apply `pinned`/`critical` to important issues

---

## GitHub Secrets Setup

The **Health Check Monitoring** agent requires GitHub Secrets to be configured.

For the complete list of required secrets, optional variables, step-by-step credential
generation instructions, and security notes, see the dedicated guide:

**→ [docs/GITHUB_SECRETS.md](GITHUB_SECRETS.md)**

### Quick reference

| Secret Name | Description |
|------------|-------------|
| `WP_SITE_URL` | WordPress site URL |
| `WP_USERNAME` | WordPress username |
| `WP_APP_PASSWORD` | WordPress Application Password |
| `SMTP_SERVER` | Email server hostname |
| `SMTP_PORT` | Email server port |
| `SENDER_EMAIL` | Email address for sending |
| `EMAIL_PASSWORD` | Email App Password |
| `RECIPIENT_EMAIL` | Email address for alerts |

### Verifying secrets

After adding secrets:
1. Go to **Actions** tab
2. Select "Health Check Monitoring" workflow
3. Click **Run workflow** → **Run workflow**
4. Check if the run succeeds

If it fails:
- Review workflow logs for specific error messages
- Double-check each secret value for typos
- Ensure WordPress app password has proper permissions
- Verify SMTP settings are correct for your provider

---

## Troubleshooting

### Workflow not triggering

**Problem:** Workflow doesn't run on push/PR

**Solutions:**
1. Check workflow file exists in `.github/workflows/`
2. Verify YAML syntax is valid (use online YAML validator)
3. Ensure workflow is enabled in **Actions** tab
4. Check branch triggers match your branch name

### Workflow stuck in "Queued"

**Problem:** Workflow queued but never starts

**Solutions:**
1. Check GitHub Actions status page
2. Verify organization/account has Actions enabled
3. Check if concurrent workflow limits are reached

### Test failures on CI but passes locally

**Problem:** Tests pass on your machine but fail in CI

**Possible causes:**
1. **Missing dependencies:** Update `requirements.txt`
2. **Environment differences:** Python version mismatch
3. **Timezone differences:** CI uses UTC
4. **Missing environment variables:** Add to workflow or secrets

**Solutions:**
```bash
# Match CI Python version locally
pyenv install 3.13
pyenv local 3.13

# Install exact dependencies
pip install -r requirements.txt

# Run tests the same way CI does
pytest tests/ -v --tb=short
```

### Dependabot PRs failing tests

**Problem:** Dependabot updates break tests

**Solutions:**
1. Review Dependabot PR carefully for breaking changes
2. Update code to accommodate new package version
3. Pin problematic package version in `requirements.txt`:
   ```
   # Before
   requests

   # After (pin version)
   requests==2.31.0
   ```

### Health check fails with authentication error

**Problem:** Health check workflow fails with 401/403 errors

**Solutions:**
1. Verify WordPress app password is current (regenerate if old)
2. Check WordPress REST API is enabled
3. Verify user has appropriate permissions
4. Test credentials locally:
   ```bash
   python scripts/pipeline/health_check.py
   ```

### Linting fails with too many errors

**Problem:** Ruff reports hundreds of violations

**Solutions:**
1. Run `ruff check . --fix` to auto-fix simple issues
2. Run `ruff format .` to auto-format code
3. Commit fixes in a separate "linting fixes" commit
4. For large projects, consider gradual adoption:
   ```toml
   # .ruff.toml
   ignore = [
       "E501",  # line too long (temporarily)
   ]
   ```

### Secrets not working in workflow

**Problem:** Workflow can't access secrets

**Solutions:**
1. Verify secrets are set at repository level (not organization)
2. Check secret names match exactly (case-sensitive)
3. Ensure workflow has correct permissions
4. Test with `workflow_dispatch` manual trigger

---

## Best Practices

### For developers

1. **Run tests locally before pushing**
   ```bash
   pytest tests/ -v
   ```

2. **Run linting before committing**
   ```bash
   ruff check . --fix
   ruff format .
   ```

3. **Monitor CI status after pushing**
   - Check green checkmarks on commits
   - Fix failures immediately

4. **Keep dependencies updated**
   - Review Dependabot PRs promptly
   - Test updates in development branch first

### For maintainers

1. **Review health check results weekly**
   - Every Monday after 8am UTC
   - Investigate failures immediately

2. **Manage stale issues monthly**
   - Review issues marked as stale
   - Close or update as appropriate
   - Apply `pinned` to long-term issues

3. **Monitor Dependabot alerts**
   - Check Security tab regularly
   - Prioritize security updates

4. **Update secrets when credentials change**
   - WordPress app passwords expire
   - Email passwords change
   - Update GitHub secrets immediately

---

## Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Dependabot Documentation](https://docs.github.com/en/code-security/dependabot)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [pytest Documentation](https://docs.pytest.org/)

---

## Support

For issues with CI/CD or monitoring agents:
1. Check this guide for troubleshooting steps
2. Review workflow logs in Actions tab
3. Open an issue with the `ci-cd` label
4. Include relevant logs and error messages
