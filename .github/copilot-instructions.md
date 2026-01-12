## Quick orientation for AI coding agents

Be concise — this repo automates scraping, classifying, reviewing and uploading community events to a WordPress EventON calendar.
Focus on the following surfaces to be immediately productive: code entry points, config patterns, data flows, and safety guardrails used by humans.

### Key entry points (what to run / inspect)
- `scripts/automated_pipeline.py` — full pipeline: scrape → classify → export → email → (optional) upload
- `scripts/wordpress_uploader.py` — interactive uploader (dry-run → create drafts → publish)
- `Envision_Perdido_DataCollection.py` — scraper and ics parsing (used by the pipeline)
- `data/artifacts/` — model artifacts: `event_classifier_model.pkl`, `event_vectorizer.pkl`

### Configuration & environment variables (explicit, important)
- WordPress: `WP_SITE_URL`, `WP_USERNAME`, `WP_APP_PASSWORD` (App passwords, used via HTTP Basic auth)
- Email: `SENDER_EMAIL`, `EMAIL_PASSWORD` (Gmail App Passwords), `RECIPIENT_EMAIL`, `SMTP_SERVER`, `SMTP_PORT`
- Behavior flags: `AUTO_UPLOAD` (default true when unset), `SITE_TIMEZONE` (default `America/Chicago`)

macOS (zsh) quick env var snippet (copy/paste into your `~/.zshrc` or run in shell to set for session):

```zsh
# WordPress
export WP_SITE_URL="https://sandbox.example.org"
export WP_USERNAME="your_wp_username"
export WP_APP_PASSWORD="xxxx xxxx xxxx xxxx xxxx xxxx"

# Email / SMTP
export SMTP_SERVER="smtp.gmail.com"
export SMTP_PORT="587"
export SENDER_EMAIL="your_email@gmail.com"
export EMAIL_PASSWORD="your_16_char_app_password"
export RECIPIENT_EMAIL="your_email@gmail.com"

# Behavior
export AUTO_UPLOAD="false"        # safe default when testing
export SITE_TIMEZONE="America/Chicago"
```

Examples: the pipeline checks for model files at `data/artifacts/*` and will exit early if missing. The uploader conducts a DRY RUN by default and creates events as `status: draft` (safe-by-default).

### Important project-specific conventions
- Confidence threshold: events with `confidence < 0.75` are flagged as `needs_review` (see `automated_pipeline.classify_events`).
- Long-event filter: community events with duration > 60 days are filtered out before export.
- Calendar export files are written to `output/pipeline/` and named `calendar_upload_<timestamp>.csv` (uploader picks the most recent file).
- EventON specifics: uploader writes EventON metadata keys (e.g. `evcal_srow`, `evcal_erow`) and uses the custom post type `ajde_events`. The code stores a "local epoch" (treat local naive datetime as UTC) — avoid changing the epoch logic without confirming EventON expectations.

### Timezones & robustness
- Code tries to use `zoneinfo.ZoneInfo` and falls back to backports/dateutil if missing. `SITE_TIMEZONE` controls local timezone used when producing EventON epochs.
- `Envision_Perdido_DataCollection` prefers ICS parsing (requires `icalendar`) but falls back gracefully when optional deps are missing. When writing fixes or changes, preserve these defensive dynamic imports.

### Tests and quick checks
- Unit tests live under `tests/` (example: `tests/test_perdido_scraper.py`). They stub `requests.Session` so you can run `pytest` locally for scraper logic without touching the network.
- Run tests: create/activate a venv, install `requirements.txt`, then `pytest` or `python -m pytest`.

### Developer workflows & tips
- Local dev: use `scripts/run_with_venv.sh <script>` on macOS/Linux or create a venv named in README (`.venvEnvisionPerdido`) on Windows.
- To reproduce full run: set env vars, then `python scripts/automated_pipeline.py`. Check `output/pipeline/` for artifacts and `output/logs/` for logs.
- For WordPress integration changes, test against a sandbox WP site and use the uploader's dry-run first — it prints action summaries and requires interactive confirmation before making changes.

### Files to inspect for context when making changes
- `scripts/automated_pipeline.py` — classification thresholds, email formatting, export paths
- `Envision_Perdido_DataCollection.py` — scraping, ICS discovery fallback, parsing helpers (`_dt_to_iso`)
- `scripts/wordpress_uploader.py` — metadata mapping (`parse_event_metadata`), image upload flow, REST endpoints
- `docs/QUICKSTART.md` and `docs/PROJECT_STRUCTURE.md` — human-run workflows and assumptions (Windows-focused examples)

### Safe WordPress testing checklist
Follow this checklist whenever you modify upload logic or run the uploader against a site.
1. Create a sandbox WordPress site (do not use production).
2. Install EventON and the `plugins/eventon-rest-api-meta.php` helper plugin if not present.
3. Create a test WordPress user and generate an Application Password for that user.
4. Set the macOS zsh env vars (see snippet above) and keep `AUTO_UPLOAD=false` while testing.
5. Run the pipeline to produce `output/pipeline/calendar_upload_<timestamp>.csv` (no auto-upload):

```zsh
python scripts/automated_pipeline.py
```

6. Open `output/pipeline/` and verify the generated CSV contents (titles, dates, `evcal_srow` values).
7. Run the uploader in dry-run mode (it runs dry-run first by default):

```zsh
python scripts/wordpress_uploader.py
```

8. Confirm the dry-run output lists events correctly. Only proceed if rows, times, and locations look right.
9. If you decide to upload, allow the uploader to create events as DRAFTS first. Inspect drafts in WP admin.
10. Publish one or two events manually in WP admin to verify appearance, timezones, and metadata are correct before publishing the rest.
11. If anything is wrong (dates, timezone offsets, or missing metadata), stop and fix `parse_event_metadata` or `_dt_to_iso` code; do not mass-publish.


### Safety & non-goals
- The pipeline auto-uploads by default (controlled by `AUTO_UPLOAD`); do not enable auto-upload in CI or in an LLM-driven change without explicit human approval and a sandbox site.
- Avoid changing EventON epoch/metadata logic without manual verification: mistaken epochs publish events on wrong dates.

Please review this draft and tell me if you'd like: more examples (env var snippets), a small checklist for safe WordPress testing, or inline pointers to the model training scripts (`scripts/svm_train_from_file.py`, `scripts/auto_label_and_train.py`).
