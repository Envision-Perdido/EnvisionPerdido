# Production Readiness TODO Checklist

**Status: DRAFT → PRODUCTION**  
**Current Score: 62/100** | **Target: 85+/100**

---

## 🔴 BLOCKING ISSUES (Must Complete Before Production Deployment)

### Issue 1: Deduplication & Idempotency
- [ ] Add `get_event_by_uid()` method to `WordPressEventUploader`
- [ ] Store event UID in custom post meta field `_event_uid`
- [ ] Check if UID exists before calling `create_event()`
- [ ] Return skip status (don't create) if UID exists
- [ ] Log skipped events at WARNING level
- [ ] Write unit test: upload same event twice → only one created
- [ ] Write integration test: upload CSV twice → second run skips all
- **Files to modify:**
  - `scripts/wordpress_uploader.py` (add `get_event_by_uid()` + dedup logic)
  - `scripts/automated_pipeline.py` (optional: log duplicate count)
  - `tests/test_wordpress_uploader.py` (add dedup tests)
- **Acceptance Criteria:**
  - Running pipeline twice with same data creates zero duplicates
  - Logs show "Skipped: duplicate" for each second upload
  - WordPress has `_event_uid` meta field on all events
- **Effort:** 3–4 hours | **Priority:** CRITICAL

---

### Issue 2: Environment Variable Validation at Startup
- [ ] Create `validate_env_config()` function in `env_loader.py`
- [ ] Check required vars: `SMTP_SERVER`, `SMTP_PORT`, `SENDER_EMAIL`, `EMAIL_PASSWORD`, `RECIPIENT_EMAIL`
- [ ] Check WP vars only if `AUTO_UPLOAD=true`: `WP_SITE_URL`, `WP_USERNAME`, `WP_APP_PASSWORD`
- [ ] Provide actionable error messages (what's missing, how to set)
- [ ] Call `validate_env_config()` as first statement in `main()`
- [ ] Test with missing vars → should fail fast with clear error
- [ ] Write test: missing `WP_APP_PASSWORD` → error message names it
- **Files to modify:**
  - `scripts/env_loader.py` (add `validate_env_config()`)
  - `scripts/automated_pipeline.py` (call `validate_env_config()` in `main()`)
  - `tests/` (add test for validation)
- **Acceptance Criteria:**
  - Pipeline fails in <1 second if env var missing
  - Error message is actionable (e.g., "Set WP_APP_PASSWORD in scripts/windows/env.ps1")
  - All required vars are validated
- **Effort:** 1–2 hours | **Priority:** CRITICAL

---

### Issue 3: Structured Logging with File Rotation
- [ ] Create `scripts/logger.py` with:
  - [ ] `get_logger(name)` function
  - [ ] File handler with `RotatingFileHandler` (10 MB max, 5 backups)
  - [ ] Console handler (INFO level)
  - [ ] JSON formatter for file logs (timestamps, level, message, module, lineno)
  - [ ] Plain text formatter for console (human readable)
- [ ] Replace all `log()` calls with `logger.info/warning/error/critical` in:
  - [ ] `automated_pipeline.py`
  - [ ] `wordpress_uploader.py`
  - [ ] `Envision_Perdido_DataCollection.py`
  - [ ] `wren_haven_scraper.py`
  - [ ] `event_normalizer.py`
- [ ] Add pipeline summary metrics at end of `main()`:
  ```
  logger.info(f"PIPELINE_SUMMARY scraped={N} classified={N} community={N} filtered={N} needs_review={N} uploaded={N} errors={N}")
  ```
- [ ] Test log rotation: generate >10 MB logs → verify rotation occurs
- [ ] Verify logs are in `output/logs/` directory
- **Files to create:**
  - `scripts/logger.py` (new)
- **Files to modify:**
  - `scripts/automated_pipeline.py` (replace log calls)
  - `scripts/wordpress_uploader.py` (replace log calls)
  - Others as above
- **Acceptance Criteria:**
  - Logs are JSON format in file; human-readable on console
  - Logs rotate correctly (don't fill disk)
  - Pipeline summary metrics appear in logs
  - Each log entry has timestamp, level, module, line number
- **Effort:** 4–6 hours | **Priority:** CRITICAL

---

### Issue 4: Scraper Error Isolation & Partial Failure Handling
- [ ] Modify `scrape_events()` to return `(events, errors)` tuple
- [ ] Collect errors instead of silently continuing (don't `continue` on exception)
- [ ] In `main()`:
  - [ ] Unpack `events, scrape_errors = scrape_events(...)`
  - [ ] Log each scrape error at WARNING level
  - [ ] If no events scraped, log CRITICAL and exit with code 1
  - [ ] Include scrape error count in email notification
- [ ] Add scrape error summary to email body (if any errors occurred)
- [ ] Test: break one scraper → pipeline continues with other scraper, logs errors, exits with error code
- **Files to modify:**
  - `scripts/automated_pipeline.py` (scrape_events signature + error handling)
  - `scripts/automated_pipeline.py` (main() error handling + email updates)
- **Acceptance Criteria:**
  - Scraper failure doesn't kill pipeline (other sources still processed)
  - All scraper errors logged with WARNING level
  - Email includes scrape error summary
  - Exit code is non-zero if any scraper errors occurred
  - Pipeline exits with CRITICAL if no events scraped
- **Effort:** 2–3 hours | **Priority:** CRITICAL

---

### Issue 5: Rate Limiting with Exponential Backoff
- [ ] Add `get_session_with_retries()` function in `Envision_Perdido_DataCollection.py`:
  ```python
  from urllib3.util.retry import Retry
  from requests.adapters import HTTPAdapter
  
  def get_session_with_retries():
      session = requests.Session()
      retry = Retry(
          total=3,
          backoff_factor=2,  # 2s, 4s, 8s
          status_forcelist=[429, 500, 502, 503, 504],
      )
      adapter = HTTPAdapter(max_retries=retry)
      session.mount('http://', adapter)
      session.mount('https://', adapter)
      return session
  ```
- [ ] Replace global `sess` with `get_session_with_retries()`
- [ ] Verify all requests have `timeout=30` parameter
- [ ] Test against fixtures (not live scraping)
- [ ] Verify backoff timing with mock (use `pytest-timeout` or manual timing)
- **Files to modify:**
  - `scripts/Envision_Perdido_DataCollection.py` (add function, replace sess)
  - `tests/test_perdido_scraper.py` (add test for retry logic)
- **Acceptance Criteria:**
  - 429 / 503 responses trigger backoff + retry
  - Backoff factor is 2 (exponential: 2s, 4s, 8s)
  - Total retries ≤ 3
  - All requests have timeout
- **Effort:** 1–2 hours | **Priority:** CRITICAL

---

## 🟠 HIGH-PRIORITY TODOs (1–2 Weeks)

### Todo 6: Startup Health Check
- [ ] Verify model files exist: `data/artifacts/event_classifier_model.pkl`, `event_vectorizer.pkl`
- [ ] Test WordPress API connection (call `/wp-json/users/me`)
- [ ] Test SMTP connection (verify SMTP server responds)
- [ ] Verify output directories are writable: `output/pipeline/`, `output/logs/`
- [ ] Log all checks at INFO level; fail fast if any critical check fails
- [ ] Create `check_startup()` function and call as first statement in `main()`
- **Files to create/modify:**
  - `scripts/automated_pipeline.py` (add `check_startup()` function + call in main())
  - `tests/test_automated_pipeline.py` (add test for startup checks)
- **Acceptance Criteria:**
  - Pipeline fails in <5 sec if model files missing
  - Pipeline fails in <10 sec if WordPress unreachable
  - Startup checks log success/failure to console + log file
  - Exit code is non-zero if any critical check fails
- **Effort:** 2–3 hours | **Priority:** HIGH

---

### Todo 7: Test Coverage Expansion
- [ ] Add test fixtures for scrapers:
  - [ ] HTML snapshot of Perdido Chamber month view (copy from live, commit)
  - [ ] 2–3 sample ICS files (copy from live, commit)
  - [ ] HTML snapshot of Wren Haven events page (Playwright screenshot)
- [ ] Add unit tests for `classify_events()` happy path:
  - [ ] Test that community events classified correctly
  - [ ] Test that confidence scores are in [0, 1]
  - [ ] Test that review flag set correctly (confidence < 0.75)
- [ ] Add integration test: raw data → classify → export CSV:
  - [ ] Load sample events
  - [ ] Classify
  - [ ] Verify output CSV has all required fields
- [ ] Add test for email notification generation (don't send; mock SMTP)
- [ ] Run `pytest --cov` and target 70%+ coverage on core scripts
- **Files to create/modify:**
  - `tests/fixtures/` (add HTML/ICS fixtures)
  - `tests/test_automated_pipeline.py` (add classify + email tests)
  - `tests/test_event_normalizer.py` (expand edge cases)
- **Acceptance Criteria:**
  - Coverage ≥ 70% for `scripts/` (excluding notebooks)
  - All fixtures are deterministic (no live network)
  - Integration test covers happy path
  - All tests pass with `pytest -v`
- **Effort:** 5–8 hours | **Priority:** HIGH

---

### Todo 8: Data Persistence & Audit Log
- [ ] Save immutable copy of events after each stage:
  - [ ] `output/pipeline/01_raw_<timestamp>.json` (scraped, no processing)
  - [ ] `output/pipeline/02_classified_<timestamp>.json` (post-classification)
  - [ ] `output/pipeline/03_exported_<timestamp>.csv` (final export for upload)
- [ ] Create `scripts/audit_uploads.py`:
  - [ ] Load CSV from `output/pipeline/`
  - [ ] Query WordPress for published events matching UIDs
  - [ ] Output report: uploaded vs published, any missing, any new in WP
  - [ ] Usage: `python scripts/audit_uploads.py`
- [ ] Ensure audit log includes:
  - [ ] Run timestamp
  - [ ] Number of events at each stage
  - [ ] Any errors or warnings
- **Files to create/modify:**
  - `scripts/audit_uploads.py` (new)
  - `scripts/automated_pipeline.py` (add calls to save JSON snapshots)
- **Acceptance Criteria:**
  - All event snapshots saved and timestamped
  - Audit script outputs human-readable report
  - Audit script can detect missing uploads
- **Effort:** 3–4 hours | **Priority:** HIGH

---

### Todo 9: Timezone Handling Formalization
- [ ] Document the "local epoch" workaround in code + docs:
  - [ ] Add comment in `wordpress_uploader.py` explaining why
  - [ ] Create `docs/TIMEZONE_HANDLING.md` with examples
- [ ] Add test case: create event at 2 PM Chicago time → verify epoch in WordPress
- [ ] Add test for DST transition (e.g., March 9 or Nov 2, 2025)
- [ ] Verify timezone handling in:
  - [ ] `Envision_Perdido_DataCollection.py` (_dt_to_iso)
  - [ ] `wordpress_uploader.py` (parse_event_metadata)
- **Files to create/modify:**
  - `docs/TIMEZONE_HANDLING.md` (new)
  - `tests/test_wordpress_uploader.py` (add DST test)
  - Comments in above scripts
- **Acceptance Criteria:**
  - Timezone handling is documented + tested
  - DST transitions handled correctly
  - Event times display correctly in WordPress calendar
- **Effort:** 3–4 hours | **Priority:** HIGH

---

## 🟡 MEDIUM-PRIORITY TODOs (Polish & Robustness)

### Todo 10: Venue Resolution Reliability
- [ ] Review current venue matching in `event_normalizer.py`
- [ ] If accuracy <90%, add fuzzy matching:
  ```python
  from difflib import SequenceMatcher
  # or: pip install fuzzywuzzy python-Levenshtein
  ```
- [ ] Test against 50+ real venues from past events
- [ ] Document venue resolution priority (exact match → fuzzy → create new)
- **Effort:** 3–4 hours | **Priority:** MEDIUM

---

### Todo 11: Image Upload Resilience
- [ ] Add retry logic for image upload (1 retry if timeout)
- [ ] Don't fail event creation if image upload fails (already ok)
- [ ] Log image upload failures at WARNING (currently done)
- [ ] Test: image upload timeout → event created, image skipped
- **Effort:** 1–2 hours | **Priority:** MEDIUM

---

### Todo 12: Concurrent Upload Safety
- [ ] Review `wordpress_uploader.py` ThreadPoolExecutor usage
- [ ] Verify dedup logic (Issue 1) works safely under concurrency
- [ ] Test with `max_workers=5` on 100+ events
- [ ] Add test: upload 100 events concurrently → all created, no duplicates
- **Effort:** 2–3 hours | **Priority:** MEDIUM

---

### Todo 13: Email Notification Robustness
- [ ] If email fails, log CRITICAL but don't fail pipeline (ok)
- [ ] Add retry logic: email is idempotent; 1 retry is safe
- [ ] Test SMTP timeout scenario (mock with fake server)
- [ ] Test auth failure scenario
- **Effort:** 2–3 hours | **Priority:** MEDIUM

---

### Todo 14: Configuration Documentation
- [ ] Create `docs/CONFIGURATION.md`:
  - [ ] All env variables listed with descriptions, defaults, examples
  - [ ] How to set on Windows/macOS/Linux
  - [ ] Safe test values vs production values
- [ ] Create `docs/TROUBLESHOOTING.md`:
  - [ ] Common errors + solutions
  - [ ] How to read logs
  - [ ] How to rollback if needed
- [ ] Create `docs/MONITORING.md`:
  - [ ] What metrics to watch
  - [ ] Log patterns that indicate problems
  - [ ] Alert thresholds
- **Effort:** 2–3 hours | **Priority:** MEDIUM

---

### Todo 15: Paid/Free Detection Edge Cases
- [ ] Review false positive/negative rate of regex patterns
- [ ] Add test cases:
  - [ ] "Free parking" → should NOT trigger free event
  - [ ] "$5 discount" → should trigger paid
  - [ ] "Free with registration; $15 optional" → log for manual review
- [ ] Document accuracy (e.g., "95% accuracy on real events")
- [ ] If FP rate >5%, consider ML-based approach
- **Effort:** 2–3 hours | **Priority:** MEDIUM

---

## 🟢 LOW-PRIORITY / NICE-TO-HAVE

### Todo 16: Dashboard / Metrics API
- [ ] Optional Flask endpoint: `GET /metrics` returns JSON with stats
- [ ] Metrics: scraped count, classified count, uploaded count, errors, runtime
- **Effort:** 3–4 hours | **Priority:** LOW

---

### Todo 17: Incremental Scraping
- [ ] Support `--incremental` flag to scrape only last 2 weeks
- [ ] Persist `last_scrape_timestamp` to `output/last_scrape.json`
- [ ] Reduces bandwidth + false duplicate risk
- **Effort:** 2–3 hours | **Priority:** LOW

---

### Todo 18: Bulk Event Deletion / Rollback
- [ ] Script to delete all events uploaded in a given run
- [ ] Usage: `python scripts/delete_events.py --run-id <timestamp>`
- [ ] Requires audit log (Todo 8)
- **Effort:** 2–3 hours | **Priority:** LOW

---

### Todo 19: Multi-Site Support
- [ ] Refactor to support multiple calendars / WordPress sites
- [ ] Config file: `config/sites.json` with site URLs + credentials
- **Effort:** 4–6 hours | **Priority:** LOW

---

### Todo 20: Webhook Notifications
- [ ] Support Slack / Teams / Discord instead of email
- [ ] Config: `--webhook-url https://hooks.slack.com/...`
- **Effort:** 2–3 hours | **Priority:** LOW

---

### Todo 21: iCal Export
- [ ] Implement TODO at line 536 of `automated_pipeline.py`
- [ ] Export events as `.ics` file
- **Effort:** 2–3 hours | **Priority:** LOW

---

## ⚡ QUICK WINS (High Impact, Low Effort)

### Quick Win 1: `.gitignore` Entries
- [ ] Add entries for logs, CSVs, model files, cache
- **Effort:** 15 min

---

### Quick Win 2: Pre-Pipeline Health Check Script
- [ ] Create `scripts/pre_pipeline_check.ps1` (Windows)
- [ ] Check model files, env vars, directory write permissions
- **Effort:** 30 min

---

### Quick Win 3: Improve README.md
- [ ] Add "Troubleshooting" section
- [ ] Add "Schedule with Task Scheduler" section
- [ ] Add "Expected Runtime" section
- **Effort:** 30 min

---

### Quick Win 4: Verify Timeouts
- [ ] Grep all `requests.get/post` calls; ensure `timeout=` parameter
- **Effort:** 30 min

---

### Quick Win 5: Event Count Summary in Email
- [ ] Email already computes stats; add:
  - [ ] Total scraped / classified / community / uploaded
  - [ ] Confidence distribution
  - [ ] Scraper error summary (if any)
- **Effort:** 30 min

---

### Quick Win 6: Env File Template
- [ ] Create `scripts/env.example.ps1`
- [ ] Clear descriptions for each variable
- **Effort:** 15 min

---

### Quick Win 7: Document Event Filtering Rules
- [ ] Add comments to `event_normalizer.py`
- [ ] Document "Brandon Styles @ OWA" rule
- [ ] Document 60-day duration filter
- **Effort:** 30 min

---

## 📋 SIGN-OFF CHECKLIST

Before deploying to production, verify:

- [ ] **Blocking Issues Complete:**
  - [ ] Issue 1: Deduplication by UID ✅
  - [ ] Issue 2: Environment validation ✅
  - [ ] Issue 3: Structured logging ✅
  - [ ] Issue 4: Scraper error isolation ✅
  - [ ] Issue 5: Rate limiting ✅

- [ ] **High-Priority TODOs Complete:**
  - [ ] Todo 6: Startup health check ✅
  - [ ] Todo 7: Test coverage ≥70% ✅
  - [ ] Todo 8: Data persistence + audit ✅
  - [ ] Todo 9: Timezone handling documented ✅

- [ ] **Testing & QA:**
  - [ ] All unit tests pass: `pytest -v`
  - [ ] Coverage ≥70%: `pytest --cov`
  - [ ] Sandbox WordPress tests pass
  - [ ] Dedup test passes: upload twice → no duplicates
  - [ ] Scraper error isolation test passes
  - [ ] Email notification test passes
  - [ ] Timezone test passes (EDT/CST)

- [ ] **Documentation:**
  - [ ] README updated
  - [ ] `docs/CONFIGURATION.md` created
  - [ ] `docs/TROUBLESHOOTING.md` created
  - [ ] `docs/TIMEZONE_HANDLING.md` created
  - [ ] `docs/MONITORING.md` created

- [ ] **Infrastructure:**
  - [ ] Windows Task Scheduler configured
  - [ ] Log rotation verified
  - [ ] Email alerts configured
  - [ ] Sandbox WordPress site ready
  - [ ] Backup / rollback plan documented

- [ ] **Operations:**
  - [ ] Operator trained on monitoring
  - [ ] Incident response plan documented
  - [ ] First run dry-run completed successfully
  - [ ] Logs reviewed + understood
  - [ ] Stakeholders notified + ready

- [ ] **Final Sign-Off:**
  - [ ] Tech lead approval
  - [ ] Security review (secrets handling, auth)
  - [ ] Operations team approval
  - [ ] Go/No-Go decision made

---

## 🎯 PRODUCTION DEPLOYMENT PLAN

### Week 1: Blocking Issues
- **Mon–Wed:** Dedup + env validation (Issues 1–2)
- **Wed–Fri:** Structured logging + error isolation (Issues 3–4)
- **Fri:** Rate limiting (Issue 5)

### Week 2: High-Priority
- **Mon–Tue:** Health checks + test coverage (Todos 6–7)
- **Wed:** Data persistence (Todo 8)
- **Thu–Fri:** Timezone + docs (Todos 9, 14)

### Week 3: Polish
- **Mon–Tue:** Medium-priority todos (Todos 10–15)
- **Wed–Fri:** Final testing + QA

### Week 4: Go Live
- **Mon:** Pre-production checklist
- **Tue–Wed:** Sandbox testing + dry runs
- **Thu:** Operator training
- **Fri:** **PRODUCTION DEPLOYMENT** (or defer to next week if issues found)

---

**Current Status:** DRAFT  
**Last Updated:** January 14, 2026  
**Owner:** [Your Name]  
**Review Cycle:** Weekly standup + final review before production
