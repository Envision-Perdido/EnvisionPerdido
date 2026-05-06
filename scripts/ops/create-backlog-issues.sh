#!/usr/bin/env bash
# =============================================================================
# create-backlog-issues.sh
#
# Creates all 22 backlog issues from the project research plan and adds them
# to the GitHub project board (org project #1).
#
# Prerequisites:
#   gh auth login          (must be authenticated with repo + project scopes)
#   gh extension install github/gh-projects   (for project-board assignment)
#
# Usage:
#   bash scripts/ops/create-backlog-issues.sh
#
# The script is idempotent: running it twice creates duplicate issues, so
# run it once on a fresh repo or check existing issues first.
# =============================================================================
set -euo pipefail

REPO="Envision-Perdido/EnvisionPerdido"

# ── 1. Ensure required labels exist ──────────────────────────────────────────

create_label() {
  local name="$1" color="$2" desc="$3"
  gh label create "$name" --color "$color" --description "$desc" --repo "$REPO" 2>/dev/null \
    || echo "  label '$name' already exists, skipping"
}

echo "==> Creating labels..."
create_label "scraping"    "0075ca" "Web scraping and data collection"
create_label "config"      "e4e669" "Configuration and environment setup"
create_label "ci"          "0e8a16" "Continuous integration / GitHub Actions"
create_label "quality"     "bfd4f2" "Code quality and style"
create_label "docker"      "1d76db" "Docker / containerisation"
create_label "deps"        "cfd3d7" "Dependency management"
create_label "pipeline"    "d93f0b" "Automation pipeline"
create_label "ml"          "5319e7" "Machine learning / model training"
create_label "data"        "c2e0c6" "Dataset preparation and labeling"
create_label "monitoring"  "f9d0c4" "Health checks and alerting"
create_label "testing"     "006b75" "Tests and test infrastructure"
create_label "automation"  "e99695" "Scheduling and workflow automation"
create_label "ux"          "fef2c0" "User-facing features and admin UI"
create_label "wordpress"   "21759b" "WordPress / EventON integration"
create_label "docs"        "0052cc" "Documentation"
create_label "security"    "ee0701" "Security vulnerabilities and fixes"

# ── 2. Helper: create issue and echo its URL ─────────────────────────────────

new_issue() {
  local title="$1" labels="$2" body="$3"
  echo ""
  echo "--> $title"
  gh issue create \
    --repo "$REPO" \
    --title "$title" \
    --label "$labels" \
    --body "$body"
}

# ── 3. P0 issues ─────────────────────────────────────────────────────────────
echo ""
echo "==> Creating P0 issues..."

new_issue \
  "[P0] Fix Wren Haven Wix HTML parser stub" \
  "bug,scraping" \
  "## Problem

\`scripts/scrapers/wren_haven/scraper.py\` line 32 contains a documented stub: \`parse_events_from_html()\` always returns \`[]\` because the Wix widget HTML selectors have not been reverse-engineered. The source is included in the production pipeline (\`include_sources=[\"perdido_chamber\", \"wren_haven\"]\`) but currently contributes **zero events**.

\`\`\`
# TODO: parse event cards from widget once live HTML structure is known.
return []
\`\`\`

## Steps to Reproduce

Run \`scrape_wren_haven()\` against the live site. Observe empty list returned.

## Acceptance Criteria

- [ ] Inspect rendered HTML from the Wren Haven Homestead events page (Playwright headless is available in \`scripts/scrapers/wren_haven/fetch.py\`)
- [ ] Identify CSS selectors for event cards in the Wix widget (\`data-hook=\"EVENTS_ROOT_NODE\"\` or equivalent)
- [ ] Implement \`parse_events_from_html()\` to return normalized event dicts
- [ ] All existing \`tests/unit/test_wren_haven_scraper.py\` tests pass
- [ ] Integration test against cached fixture HTML returns ≥ 1 event"

new_issue \
  "[P0] Add .env file loading support to env_loader.py" \
  "enhancement,config" \
  "## Problem

The README instructs remote server operators to create a root \`.env\` file (\`cp .env.example .env\`), and \`python-dotenv\` is listed in \`pyproject.toml\`. However, \`scripts/tooling/env_loader.py\` only parses \`.ps1\`/\`.sh\` files and **never calls \`load_dotenv()\`**. As a result, \`.env\`-based deployments silently receive no credentials.

## Acceptance Criteria

- [ ] \`env_loader.load_env()\` calls \`load_dotenv(dotenv_path=repo_root / \".env\")\` as a low-priority fallback (after platform-specific files, before giving up)
- [ ] Existing priority order (\`os.environ\` → \`.ps1/.sh\` → \`~/.secrets/\`) is preserved
- [ ] \`validate_env_config()\` works correctly after \`.env\` loading
- [ ] Unit test added covering the \`.env\` loading path"

new_issue \
  "[P0] Merge lxml security update — CVE-2026-41066 (PR #24)" \
  "dependencies,security" \
  "## Problem

Dependabot PR #24 bumps \`lxml\` from 6.0.3 → 6.1.0 to fix **CVE-2026-41066** (XXE injection via \`iterparse()\` and \`ETCompatXMLParser\`). This is a security fix that should be merged promptly.

## Acceptance Criteria

- [ ] PR #24 is reviewed and merged
- [ ] \`uv.lock\` updated
- [ ] CI passes on \`main\` after merge"

# ── 4. P1 issues ─────────────────────────────────────────────────────────────
echo ""
echo "==> Creating P1 issues..."

new_issue \
  "[P1] Expand CI lint workflow to cover all scripts" \
  "ci,quality" \
  "## Problem

\`.github/workflows/lint.yml\` has a hardcoded \`RUFF_TARGETS\` env var listing only 9 specific files. Any new script added to \`scripts/\` or \`tests/\` is silently excluded from linting in CI.

## Acceptance Criteria

- [ ] \`lint.yml\` runs \`ruff check scripts/ tests/\` (directory glob) instead of hardcoded file list
- [ ] All pre-existing violations in currently-unlinted files are resolved or suppressed with \`# noqa\` comments
- [ ] CI passes on \`main\` after the change"

new_issue \
  "[P1] Align Dockerfile to use uv sync instead of requirements.txt" \
  "docker,deps" \
  "## Problem

The \`Dockerfile\` installs dependencies via \`pip install -r requirements.txt\`, creating a divergence risk with \`pyproject.toml\`/\`uv.lock\` which is the authoritative dependency specification. When a dependency is updated in \`pyproject.toml\`, Docker builds continue using the old \`requirements.txt\` pin.

## Acceptance Criteria

- [ ] Dockerfile installs \`uv\`, then runs \`uv sync --no-dev\` from \`pyproject.toml\`/\`uv.lock\`
- [ ] \`docker build\` and \`docker compose up\` succeed
- [ ] \`requirements.txt\` kept for reference but clearly marked as secondary"

new_issue \
  "[P1] Implement persistent cross-run event deduplication" \
  "enhancement,pipeline" \
  "## Problem

The pipeline has intra-run deduplication (tested in \`tests/unit/test_deduplication.py\`) but no persistent store across runs. If the pipeline runs daily, recurring events will be re-uploaded to WordPress each day, potentially flooding the calendar.

## Acceptance Criteria

- [ ] A lightweight persistent store (SQLite or JSON at \`data/cache/uploaded_uids.json\`) tracks uploaded event UIDs with their upload timestamp
- [ ] \`upload_stage.upload_to_wordpress()\` skips events whose UID is already in the store
- [ ] Store is updated after each successful upload
- [ ] \`AUTO_DEDUP=false\` env var disables deduplication for testing/debugging
- [ ] Unit test for deduplication logic passes"

new_issue \
  "[P1] Implement iCal (.ics) export format" \
  "enhancement,pipeline" \
  "## Problem

\`scripts/pipeline/stages/export.py\` has a stubbed \`format=\"ical\"\` branch that logs a warning and returns \`None\`. iCal is a standard format useful for importing events into Google Calendar, Outlook, and other apps.

\`\`\`python
if format == \"ical\":
    logger.warning(\"iCal export is not yet implemented.\")
    return None
\`\`\`

## Acceptance Criteria

- [ ] \`export_for_calendar(df, format=\"ical\")\` produces a valid RFC 5545 \`.ics\` file
- [ ] Required fields: DTSTART, DTEND, SUMMARY, LOCATION, DESCRIPTION, URL, UID
- [ ] \`icalendar\` library added to \`pyproject.toml\` dependencies
- [ ] Unit test validates field presence and event count in the output file"

new_issue \
  "[P1] Connect multi-calendar generic scraper to pipeline" \
  "enhancement,scraping" \
  "## Problem

\`scripts/scrapers/multi_calendar/\` provides a generic CSS-selector-driven scraper that reads \`data/community_calendar_sources.json\`, but it is **never called from the pipeline**. Two of three sources in the config are disabled placeholder examples.

## Acceptance Criteria

- [ ] \`scrape_stage.scrape_events()\` supports additional sources configured in \`community_calendar_sources.json\`
- [ ] At least one real local calendar URL is enabled and producing events
- [ ] Pipeline integration test passes with mocked HTTP responses
- [ ] Graceful degradation if a configured source is unreachable"

new_issue \
  "[P1] Event sorting and filtering by category / location / paid status (Issue #25)" \
  "feature,wordpress" \
  "## Problem (from Issue #25)

As a user I should be able to sort events by category (e.g. music, trivia), filter by location and event type, and sort by free/paid status. Currently no frontend filtering UI exists on the EventON calendar.

## Acceptance Criteria

- [ ] WordPress EventON taxonomy configuration or query-parameter-based filter supports filtering by: category, location, paid/free status
- [ ] Filter UI visible to calendar visitors (widget or custom shortcode)
- [ ] Documentation updated
- [ ] Manual QA on live site passes

Closes #25"

# ── 5. P2 issues ─────────────────────────────────────────────────────────────
echo ""
echo "==> Creating P2 issues..."

new_issue \
  "[P2] Fix auto_label_and_train.py to use LinearSVC instead of SVC" \
  "bug,ml" \
  "## Problem

\`scripts/ml/auto_label_and_train.py\` uses \`sklearn.svm.SVC\` (RBF kernel) while the production pipeline uses \`LinearSVC\`. This means auto-labeled events may be classified with a different decision boundary, and confidence scores cannot be correctly computed via \`decision_function\`.

## Acceptance Criteria

- [ ] \`auto_label_and_train.py\` replaces \`SVC\` with \`LinearSVC\` to match production
- [ ] Confidence computed using \`decision_function\` + \`compute_confidence\` from \`training_support.py\`
- [ ] Unit test added verifying confidence scores are symmetric for equal-magnitude decision scores"

new_issue \
  "[P2] Retrain SVM model on expanded labeled dataset" \
  "ml,data" \
  "## Problem

The current model is trained on 424 labeled events. Labeled CSVs have grown since the last retrain and a fresh threshold sweep has not been run.

## Acceptance Criteria

- [ ] Labeled CSVs consolidated via \`scripts/ml/consolidate_training_data.py\`
- [ ] \`retrain_end_to_end.py\` run with full threshold sweep
- [ ] New model achieves ≥ 96% accuracy on held-out test set
- [ ] Model artifact updated in \`data/artifacts/\`
- [ ] Retrain log/report committed to repo"

new_issue \
  "[P2] Centralized rate limiting utility for scrapers" \
  "enhancement,scraping" \
  "## Problem

Rate limiting is handled ad-hoc in individual scrapers. \`tests/unit/test_rate_limiting.py\` exists but tests the implementation in a fragmented way.

## Acceptance Criteria

- [ ] \`scripts/tooling/rate_limiter.py\` provides a shared token-bucket or delay-based limiter
- [ ] Both \`perdido_chamber\` and \`wren_haven\` scrapers use this shared limiter
- [ ] \`test_rate_limiting.py\` tests pass against the shared implementation
- [ ] Limiter is configurable via env var (e.g. \`SCRAPER_RATE_LIMIT_RPS\`)"

new_issue \
  "[P2] Fix regenerate_descriptions package structure" \
  "bug,pipeline" \
  "## Problem

\`scripts/pipeline/regenerate_descriptions/\` is imported in \`automated_pipeline.py\` as a module, but the directory appears to only contain a log file (\`pipeline_2026-05-04.log\`), not a proper Python package. The import would fail silently (caught by a \`try/except ImportError\`) but OpenAI description enhancement is permanently unavailable.

## Acceptance Criteria

- [ ] \`scripts/pipeline/regenerate_descriptions/\` is a proper Python package with \`__init__.py\` and \`regenerate_descriptions.py\`
- [ ] Module-level docstring explains usage and all supported environment variables
- [ ] Import in \`automated_pipeline.py\` succeeds without errors
- [ ] Log files excluded from the package (moved to \`output/logs/\`)"

new_issue \
  "[P2] Document OPENAI_API_KEY and related secrets in GITHUB_SECRETS.md" \
  "docs" \
  "## Problem

\`automated_pipeline.py\` supports optional OpenAI description enhancement via \`OPENAI_API_KEY\`, \`OPENAI_MODEL\`, \`OPENAI_DRY_RUN\`, \`OPENAI_USE_BATCH\`, \`OPENAI_TOP_N\`, and \`OPENAI_MIN_CONFIDENCE\`. None of these are documented in \`docs/GITHUB_SECRETS.md\`.

## Acceptance Criteria

- [ ] \`docs/GITHUB_SECRETS.md\` has a new **Optional: OpenAI Enhancement** section documenting all 6 env vars
- [ ] Default values and valid options listed for each var
- [ ] Note that \`OPENAI_API_KEY\` is required to activate this feature and the pipeline skips it gracefully when absent"

new_issue \
  "[P2] Health check: add ML model artifact freshness validation" \
  "enhancement,monitoring" \
  "## Problem

\`scripts/pipeline/health_check.py\` verifies WordPress connectivity and event counts but does not check whether the ML model artifact is stale. An outdated model may silently produce degraded classifications.

## Acceptance Criteria

- [ ] Health check verifies \`data/artifacts/event_classifier_model.pkl\` exists and \`mtime\` is within \`HEALTH_MODEL_MAX_AGE_DAYS\` days (default: 90)
- [ ] Stale model triggers a **warning** in the health check report email (not a hard failure by default)
- [ ] New env var \`HEALTH_MODEL_MAX_AGE_DAYS\` documented in \`docs/GITHUB_SECRETS.md\`"

new_issue \
  "[P2] Expand smoke tests to cover all pipeline stages and scrapers" \
  "testing" \
  "## Problem

\`tests/smoke/test_imports.py\` only checks a subset of module imports. New stage files and scraper modules are not verified to import cleanly in CI.

## Acceptance Criteria

- [ ] \`tests/smoke/test_imports.py\` imports all \`scripts/pipeline/stages/*.py\` modules
- [ ] \`tests/smoke/test_imports.py\` imports all \`scripts/scrapers/**/scraper.py\` modules
- [ ] Smoke tests run in CI (\`test.yml\` already includes \`tests/smoke\`)
- [ ] All imports succeed without side-effects (no network calls, no file writes)"

new_issue \
  "[P2] End-to-end integration test using fixture data" \
  "testing" \
  "## Problem

\`tests/integration/test_pipeline_e2e.py\` exists but is minimal. There is no test that runs the full scrape → classify → export path against fixture data (no live network).

## Acceptance Criteria

- [ ] At least one test in \`tests/integration/test_pipeline_e2e.py\` runs the pipeline against fixture HTML/JSON responses (mocked network)
- [ ] Test asserts: correct event count, expected fields in output CSV, classification labels applied
- [ ] Test is marked \`@pytest.mark.integration\` (excluded from standard CI, run manually)"

# ── 6. P3 issues ─────────────────────────────────────────────────────────────
echo ""
echo "==> Creating P3 issues..."

new_issue \
  "[P3] Admin portal scaffolding (envision-admin-portal/)" \
  "feature,ux" \
  "## Problem

\`envision-admin-portal/\` exists in the repo root but is **empty**. A minimal admin portal would allow non-technical staff to view pipeline status and trigger re-runs without SSH access.

## Acceptance Criteria

- [ ] Minimal web UI (static HTML/JS or lightweight Flask/FastAPI) at \`envision-admin-portal/\`
- [ ] Displays: last pipeline run timestamp, events scraped/classified/uploaded counts, model version
- [ ] Provides a \"Run Pipeline\" button that triggers the pipeline (dry-run mode by default)
- [ ] \`envision-admin-portal/README.md\` documents how to run the portal locally and in Docker"

new_issue \
  "[P3] Scheduled pipeline automation via GitHub Actions" \
  "automation,ci" \
  "## Problem

The pipeline currently requires manual make.com configuration or Windows Task Scheduler for scheduling. A GitHub Actions scheduled workflow would improve visibility and remove the external dependency.

## Acceptance Criteria

- [ ] New \`.github/workflows/scheduled-pipeline.yml\` with \`schedule: cron: '0 8 * * *'\` trigger
- [ ] Uses SSH action (e.g. \`appleboy/ssh-action\`) with repo secrets for server SSH key
- [ ] Runs \`uv run python scripts/pipeline/automated_pipeline.py\` on deployment server
- [ ] Workflow is manually dispatchable (\`workflow_dispatch\`)
- [ ] Failure sends notification (email or GitHub notification)
- [ ] Documented in \`docs/CI_CD_GUIDE.md\`"

new_issue \
  "[P3] Model versioning and artifact registry" \
  "enhancement,ml" \
  "## Problem

All training runs overwrite \`data/artifacts/event_classifier_model.pkl\` with no version history. There is no way to roll back to a previous model if a retrain degrades accuracy.

## Acceptance Criteria

- [ ] Training produces a versioned artifact (e.g. \`event_classifier_model_v2_20260506.pkl\`)
- [ ] \`data/artifacts/model_registry.json\` tracks: version, accuracy, training date, dataset hash
- [ ] Pipeline selects the model registered as \`latest\` in the registry
- [ ] CLI flag \`--model-version\` on \`svm_train_from_file.py\` controls which version is registered as latest"

new_issue \
  "[P3] Active learning: identify and export near-boundary events for labeling" \
  "data,ml" \
  "## Problem

The labeled dataset (424 events) has not been systematically expanded. Events near the SVM decision boundary (\`|decision_score| < 0.5\`) are the most informative to label but are never surfaced for human review.

## Acceptance Criteria

- [ ] Script \`scripts/ml/export_for_labeling.py\` reads past pipeline output CSVs and exports events where \`|decision_score| < BOUNDARY_THRESHOLD\` (configurable, default 0.5)
- [ ] Output CSV includes all event fields plus \`decision_score\` and \`confidence\` for reviewer context
- [ ] After labeling, \`retrain_end_to_end.py\` can consume the labeled output
- [ ] Dataset grows by ≥ 50 new labeled events per active-learning cycle"

new_issue \
  "[P3] Docker Compose production profile" \
  "docker" \
  "## Problem

\`docker-compose.yml\` has two conflicting \`services:\` blocks (a formatting bug) and no separation between dev and production configurations. Running in production requires manual env var overrides.

## Acceptance Criteria

- [ ] \`docker-compose.yml\` fixed to a single valid YAML document (remove duplicate \`services:\` key)
- [ ] A \`production\` profile sets \`AUTO_UPLOAD=true\`, enables log rotation, and injects credentials from \`.env\`
- [ ] \`docker compose --profile production up\` starts the pipeline in production mode
- [ ] Dev profile (\`docker compose up\`) keeps \`AUTO_UPLOAD=false\` safe default"

# ── 7. Done ───────────────────────────────────────────────────────────────────
echo ""
echo "==> All issues created."
echo ""
echo "Next steps:"
echo "  1. Add issues to the project board:"
echo "     gh project item-add 1 --owner Envision-Perdido --url <issue-url>"
echo "  2. Or bulk-add via the GitHub Projects UI:"
echo "     https://github.com/orgs/Envision-Perdido/projects/1"
echo ""
