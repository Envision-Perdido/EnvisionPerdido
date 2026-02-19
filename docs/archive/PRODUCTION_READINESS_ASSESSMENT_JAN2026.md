# Production Readiness Assessment: EnvisionPerdido
**Date:** January 14, 2026 | **Scope:** Automated Community Event Calendar System

---

## 1. PRODUCTION READINESS SCORE: **62/100**

### Justification
✅ **Strengths:**
- Core pipeline logic is sound: scrape → classify → normalize → export → upload
- Good separation of concerns (scrapers, normalizers, uploaders in distinct modules)
- Comprehensive data quality functions (paid/free detection, filtering, venue resolution)
- Trained SVM model with 96.47% accuracy reduces manual review burden
- Defensive error handling in most places (try/except blocks)
- Email notification system provides observability for operators
- Safe defaults: dry-run mode, event creation as drafts, 60-day duration filter

❌ **Critical Gaps:**
- **No idempotency/deduplication:** Events with same UID will be uploaded repeatedly (silent data loss)
- **Missing structured logging:** Only print-based log() function; no machine-readable logs, no log rotation
- **No environment validation:** Missing upfront checks for required env vars; failures occur mid-pipeline
- **Silent scraper failures:** Errors in one source don't bubble up; pipeline continues with partial data
- **No data persistence/audit trail:** No immutable record of what was published; hard to debug or revert
- **Limited test coverage:** Fixtures exist but sparse test coverage of core paths (scraper, classifier chain)
- **Timezone handling risky:** Local naive datetime epoch hack works for EventON but fragile
- **No rate limiting/backoff:** Scraper can hammer upstream; no retry logic on 429/503

---

## 2. BLOCKING ISSUES (Must Fix Before Production)

### A. **Deduplication & Idempotency** ⚠️ CRITICAL
**Impact:** Events uploaded twice if pipeline runs twice on same data  
**Location:** `scripts/automated_pipeline.py`, `scripts/wordpress_uploader.py`

**Problem:**
- Events scraped by UID (from ICS), but no check if UID already exists in WordPress
- Running `automated_pipeline.py` → `wordpress_uploader.py` twice creates duplicate calendar entries
- No transactional safety; partial uploads can't be rolled back

**Must-Do:**
1. Add `get_event_by_uid()` method to `WordPressEventUploader`
2. Check if event (by UID) exists before `create_event()`
3. Store UID as custom post meta field (`_event_uid`)
4. Return "skipped (duplicate)" instead of creating new event
5. Log all duplicate detections as WARN level

**Estimated Effort:** 3–4 hours  
**Risk:** Medium (affects data integrity)

---

### B. **Environment Variable Validation at Startup** ⚠️ CRITICAL
**Impact:** Pipeline fails 90% through with unclear error  
**Location:** `scripts/automated_pipeline.py`, `scripts/env_loader.py`

**Problem:**
- `load_env()` silently succeeds even if files don't exist
- Email/WordPress credentials checked only when needed (lines 485+, 561+)
- If `WP_APP_PASSWORD` is empty, uploader fails after 5+ minutes of processing

**Must-Do:**
1. Create `validate_env_config()` function in `env_loader.py`
2. Check required vars at pipeline startup: 
   - `SMTP_SERVER`, `SMTP_PORT`, `SENDER_EMAIL`, `EMAIL_PASSWORD`, `RECIPIENT_EMAIL`
   - `WP_SITE_URL`, `WP_USERNAME`, `WP_APP_PASSWORD` (if `AUTO_UPLOAD=true`)
3. Fail fast with actionable error message if missing
4. Call `validate_env_config()` as first line in `main()`

**Estimated Effort:** 1–2 hours  
**Risk:** Low

---

### C. **Structured Logging with Audit Trail** ⚠️ CRITICAL
**Impact:** Can't debug failures; no proof of what was published; compliance risk  
**Location:** `scripts/` (all modules)

**Problem:**
- Only simple `log()` function that prints timestamps
- No log files written (only stdout)
- No way to correlate events with upload attempts
- Unattended cron job loses output if not redirected to syslog
- No metrics: how many scraped, classified, filtered, uploaded?

**Must-Do:**
1. Replace `log()` with Python `logging` module:
   ```python
   # scripts/logger.py
   import logging
   import sys
   from pathlib import Path
   
   LOG_DIR = Path(__file__).parent.parent / "output" / "logs"
   LOG_DIR.mkdir(parents=True, exist_ok=True)
   
   def get_logger(name: str):
       logger = logging.getLogger(name)
       logger.setLevel(logging.DEBUG)
       
       # File handler (rotating, 10 MB max, 5 files)
       from logging.handlers import RotatingFileHandler
       fh = RotatingFileHandler(
           LOG_DIR / f"{name}.log",
           maxBytes=10_000_000,
           backupCount=5
       )
       fh.setLevel(logging.DEBUG)
       
       # Console handler
       ch = logging.StreamHandler(sys.stdout)
       ch.setLevel(logging.INFO)
       
       # Formatter: JSON for structured logs
       import json
       class JSONFormatter(logging.Formatter):
           def format(self, record):
               log_obj = {
                   'timestamp': self.formatTime(record),
                   'level': record.levelname,
                   'logger': record.name,
                   'message': record.getMessage(),
                   'module': record.module,
                   'lineno': record.lineno,
               }
               if record.exc_info:
                   log_obj['exception'] = self.formatException(record.exc_info)
               return json.dumps(log_obj)
       
       formatter = JSONFormatter()
       fh.setFormatter(formatter)
       ch.setFormatter(logging.Formatter('[%(levelname)-8s] %(message)s'))
       
       logger.addHandler(fh)
       logger.addHandler(ch)
       return logger
   ```
2. Update all scripts to use: `logger = get_logger(__name__); logger.info("...")`
3. Add summary metrics at pipeline end:
   ```
   2025-01-14T18:45:22.123Z | scraped=847 | classified=124 | community=98 | filtered=3 | needs_review=12 | uploaded=85 | errors=0
   ```
4. Ensure logs rotate (don't fill disk)

**Estimated Effort:** 4–6 hours  
**Risk:** Medium (refactor; test thoroughly)

---

### D. **Scraper Error Isolation & Partial Failure Handling** ⚠️ CRITICAL
**Impact:** One broken scraper silently kills entire pipeline  
**Location:** `scripts/automated_pipeline.py` (lines 139–170)

**Problem:**
```python
if 'perdido_chamber' in include_sources:
    for m in range(month, min(month + 2, 13)):
        try:
            events = scrape_month(month_url)
            # ... append events
        except Exception as e:
            log(f"Error scraping {month_url}: {e}")
            # CONTINUES SILENTLY ❌
```
- If Wren Haven scraper fails, that error is logged but pipeline succeeds (partial data)
- No way to know at end whether data is incomplete
- Email notification doesn't mention scraper failures

**Must-Do:**
1. Collect errors in `scrape_events()`:
   ```python
   def scrape_events(...) -> tuple[list[dict], list[dict]]:  # (events, errors)
       all_events = []
       errors = []  # Collect, don't skip
       # ...
       return all_events, errors
   ```
2. In `main()`:
   ```python
   events, scrape_errors = scrape_events(...)
   if scrape_errors:
       logger.warning(f"Scraper errors: {len(scrape_errors)}")
       for error in scrape_errors:
           logger.warning(f"  - {error}")
   if not events:
       logger.critical("No events scraped. Aborting.")
       sys.exit(1)
   ```
3. Email notification must include scrape error summary
4. Set exit code to non-zero if scrape_errors (for cron/scheduler detection)

**Estimated Effort:** 2–3 hours  
**Risk:** Low

---

### E. **No Rate Limiting / Backoff on Scraper** ⚠️ HIGH
**Impact:** Scraper IP banned; upstream perceives DoS  
**Location:** `scripts/Envision_Perdido_DataCollection.py` (lines 175, 190, 315)

**Problem:**
- `time.sleep(1)` between ICS fetches, but no retry logic
- No exponential backoff on 429 (rate limit), 503 (service unavailable)
- Playwright in `wren_haven_scraper.py` has no headless browser connection pooling
- Can hammer Perdido Chamber website under heavy load

**Must-Do:**
1. Use `requests.adapters.HTTPAdapter` with retry strategy:
   ```python
   from requests.adapters import HTTPAdapter
   from urllib3.util.retry import Retry
   
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
2. Replace global `sess` with above
3. Add timeout to all requests (already mostly there; verify all)
4. Test against test fixtures, not live upstream

**Estimated Effort:** 1–2 hours  
**Risk:** Low

---

## 3. HIGH-PRIORITY TODOs (1–2 Weeks)

### 1. **Add Startup Health Check**
   - Verify model files exist before scraping
   - Test WordPress API connection early (not after 5 min of processing)
   - Verify output directories are writable
   - Dry-run email credentials check
   - **Effort:** 2–3 hours | **Risk:** Low

### 2. **Implement Event Deduplication by UID**
   - Add `_event_uid` meta field to WordPress events
   - Query before create: `get_posts(meta_query=[_event_uid = event.uid])`
   - Skip if exists; log as "duplicate"
   - Update test fixtures
   - **Effort:** 4–5 hours | **Risk:** Medium (WordPress API interaction)

### 3. **Migrate to Structured Logging**
   - Create `scripts/logger.py` with JSON logging
   - Replace all `log()` calls with `logger.info/warning/error/critical`
   - Ensure logs rotate
   - Add summary metrics to email notification
   - **Effort:** 4–6 hours | **Risk:** Medium

### 4. **Environment Validation at Startup**
   - Create `validate_env_config()` in `env_loader.py`
   - Call in `main()` before scraping
   - Fail fast with actionable error messages
   - **Effort:** 1–2 hours | **Risk:** Low

### 5. **Add Scraper Error Collection**
   - Return `(events, errors)` tuple from `scrape_events()`
   - Log errors at warning level; fail if critical
   - Include scrape error summary in email
   - Set exit code to non-zero on any scraper error
   - **Effort:** 2–3 hours | **Risk:** Low

### 6. **Add Rate Limiting with Exponential Backoff**
   - Use `urllib3.Retry` strategy in `Envision_Perdido_DataCollection.py`
   - Test against fixtures (no live scraping)
   - **Effort:** 1–2 hours | **Risk:** Low

### 7. **Expand Test Coverage**
   - Add fixtures for scraper test data (HTML, ICS)
   - Add tests for `classify_events()` happy path and error cases
   - Add integration test: raw data → CSV export
   - Add test for email notification generation
   - Target: 70%+ coverage of scripts (excluding Jupyter notebooks)
   - **Effort:** 5–8 hours | **Risk:** Low

### 8. **Add Data Persistence / Audit Log**
   - Save immutable copy of all events: `output/pipeline/events_raw_<timestamp>.json`
   - Save pre/post classification snapshots
   - Save uploaded event IDs with timestamps
   - Create script to audit what was uploaded: `scripts/audit_uploads.py`
   - **Effort:** 3–4 hours | **Risk:** Low

---

## 4. MEDIUM-PRIORITY TODOs (Polish & Robustness)

### 1. **Timezone Handling Formalization**
   - Document the "local epoch" workaround for EventON
   - Add test case: event in different timezone → verify epoch correct in WordPress
   - Consider using `pytz` or `dateutil` directly (already in requirements)
   - Verify all date conversions handle DST transitions
   - **Effort:** 3–4 hours | **Risk:** Medium (timezone is subtle)

### 2. **Venue Resolution Reliability**
   - Current venue matching is regex-based (in `event_normalizer.py`)
   - Add fallback to fuzzy matching (e.g., `fuzzywuzzy` or `difflib`)
   - Test against 50+ real venues in test fixtures
   - Document venue resolution rules (priority order)
   - **Effort:** 3–4 hours | **Risk:** Low

### 3. **Image Upload Resilience**
   - If image upload fails, don't fail event creation (current behavior; good)
   - But log with higher severity (currently Warning; should track failures)
   - Add retry logic: image upload is network-I/O; 1 retry is safe
   - **Effort:** 1–2 hours | **Risk:** Low

### 4. **Concurrent Upload Safety**
   - WordPress uploader uses `ThreadPoolExecutor` (line 17); verify it's thread-safe
   - Test with `max_workers=5` on 100+ events
   - Add test: upload same event twice concurrently → no duplicates (uses dedup from #3)
   - **Effort:** 2–3 hours | **Risk:** Medium

### 5. **Email Notification Robustness**
   - If email fails, don't fail pipeline (current behavior; good)
   - But log failure with CRITICAL level + include in next run summary
   - Add retry: Email is transactional; safe to retry once
   - Test SMTP timeout & auth failure scenarios
   - **Effort:** 2–3 hours | **Risk:** Low

### 6. **Configuration Documentation**
   - Add `docs/CONFIGURATION.md` with all env vars, defaults, examples
   - Add `docs/TROUBLESHOOTING.md` with common failures + fixes
   - Add `docs/MONITORING.md` with log patterns to watch for
   - **Effort:** 2–3 hours | **Risk:** None

### 7. **Add Health Check Endpoint**
   - Create `scripts/health_check.py` (already exists! verify it's comprehensive)
   - Should check: model files, WordPress connection, email credentials
   - Should be callable from cron to validate before running pipeline
   - **Effort:** 1–2 hours (already mostly done) | **Risk:** Low

### 8. **Paid/Free Detection Edge Cases**
   - Current detection is regex-based; document false positive rate
   - Add test cases for:
     - "Free parking" (shouldn't trigger free event)
     - "$5 discount" (should trigger paid)
     - "Free with registration; $15 fee optional" (context-dependent; log for review)
   - Consider ML-based approach if regex has >5% FP rate
   - **Effort:** 2–3 hours | **Risk:** Low

---

## 5. LOW-PRIORITY / NICE-TO-HAVE

### 1. **Dashboard / Metrics API**
   - Simple `/metrics` endpoint to expose pipeline stats (events scraped, classified, etc.)
   - Could be standalone Flask app or integrated into health check
   - Use for monitoring + alerting

### 2. **Incremental Scraping**
   - Currently scrapes all months every run; support incremental (last 2 weeks)
   - Saves bandwidth; reduces false duplicate risk
   - Requires persistent state (last_scraped_date)

### 3. **Bulk Event Deletion / Rollback**
   - Script to delete all events uploaded in a given run
   - Safe manual rollback if data quality issue discovered
   - Requires audit log (see High-Priority #8)

### 4. **Multi-Site Support**
   - Current code assumes single Perdido Chamber + single WordPress
   - Refactor to support multiple calendars / sources
   - Nice for other non-profits to reuse codebase

### 5. **Webhook Notifications**
   - Instead of email, support Slack/Teams/Discord for alerts
   - More timely notifications for unattended operation

### 6. **iCal Export**
   - Code has TODO (line 536): implement iCal export
   - Low priority; CSV is sufficient for WordPress upload

---

## 6. EXPLICIT "NOT NEEDED YET" Items

### ❌ Don't Do (Yet)

1. **Database Backend (PostgreSQL/MongoDB)**
   - Current CSV + JSON export is adequate for weekly/monthly runs
   - Add only if data volume > 1M events or query patterns become complex
   - **Premature optimization**

2. **Kubernetes / Containerization**
   - Single Windows Task Scheduler job is fine for current scale
   - Add only if multiple sites or continuous scraping needed
   - **Premature infrastructure**

3. **Real-Time Event Sync**
   - Current batch (weekly/monthly) model is good match for community calendar use case
   - Real-time adds complexity without clear benefit
   - **Over-engineering**

4. **OAuth2 for WordPress**
   - Application Passwords are secure enough for single trusted uploader
   - OAuth2 would add complexity; not needed for unattended operation
   - **Over-engineering**

5. **A/B Testing Classification Models**
   - Current SVM with 96.47% is solid
   - Only revisit if accuracy drops or false negative rate becomes painful
   - **Premature optimization**

6. **Distributed Scraping**
   - Current single-process scraper is I/O-bound, not CPU-bound
   - Parallelization adds complexity without clear benefit
   - **Premature optimization**

7. **ML Pipeline Retraining**
   - Manual retraining (via `svm_train_from_file.py`) is fine
   - Auto-retraining would require drift detection + human feedback loop
   - **Premature ML ops**

---

## 7. QUICK WINS (High Impact, Low Effort)

### 1. **Add `.gitignore` Entries** (15 min)
   ```
   output/logs/*.log*
   output/pipeline/*.csv
   output/pipeline/*.json
   data/cache/*
   data/artifacts/*.pkl
   .venv*
   *.pyc
   ```

### 2. **Add Pre-Pipeline Checks** (30 min)
   ```bash
   # scripts/pre_pipeline_check.ps1
   if (-not (Test-Path "data/artifacts/event_classifier_model.pkl")) {
       Write-Error "Model file missing!"
       exit 1
   }
   if ([string]::IsNullOrEmpty($env:WP_SITE_URL)) {
       Write-Error "WP_SITE_URL not set!"
       exit 1
   }
   # ... check other vars
   ```

### 3. **Improve README.md** (30 min)
   - Add "Troubleshooting" section
   - Add "How to Schedule with Task Scheduler" section
   - Add "Expected Runtime" section

### 4. **Add Timeout to All Requests** (30 min)
   - Verify all `requests.get/post` have `timeout=` parameter
   - Most do; catch any outliers

### 5. **Add Event Count Summary to Email** (30 min)
   - Pipeline already computes stats; email should highlight:
     - Total scraped / classified / community / uploaded
     - Confidence distribution (if low confidence rate high, alert)
     - Scraper error summary (if any)

### 6. **Test Against Fixtures, Not Live** (1 hour)
   - `tests/test_perdido_scraper.py` already uses DummySession; good
   - Ensure CI doesn't run live scrapes
   - Add fixture for Wren Haven HTML

### 7. **Document Event Filtering Rules** (30 min)
   - Add comments to `event_normalizer.py` filtering logic
   - Document "Brandon Styles @ OWA" filter
   - Document 60-day duration filter

### 8. **Add Env File Template** (15 min)
   ```bash
   # scripts/env.example.ps1
   $env:WP_SITE_URL = "https://your-site.org"
   $env:WP_USERNAME = "your_username"
   # ... etc with clear descriptions
   ```

---

## 8. ANALYSIS SUMMARY BY DIMENSION

### A) DATA INGESTION & SCRAPING
| Dimension | Status | Notes |
|-----------|--------|-------|
| Source coverage | ✅ Good | Perdido Chamber + Wren Haven |
| Robustness | ⚠️ Medium | No rate limiting; errors swallowed |
| Retry / backoff | ❌ Missing | No exponential backoff on 429/503 |
| Rate limiting | ❌ Missing | No throttling; can hammer upstream |
| Authorization | ✅ OK | HTTP auth for WP; standard headers for scrapers |
| Idempotency | ❌ Missing | Events will dupe on re-run |
| Deduplication | ❌ Missing | UID present but not checked in WP |

**Verdict:** Functional but fragile under load or partial failure. Add rate limiting + dedup immediately.

---

### B) DATA QUALITY
| Dimension | Status | Notes |
|-----------|--------|-------|
| Required fields | ✅ Good | title, start, location parsed; end optional |
| Date/time parsing | ⚠️ Medium | ICS parsing ok; timezone handling fragile |
| Paid vs free detection | ✅ Good | Regex-based; 95%+ accuracy in tests |
| Tag consistency | ✅ Good | Inference from keywords in description |
| Venue normalization | ✅ Good | Regex matching; fuzzy fallback exists |
| Duplicate prevention | ❌ Missing | UID present but not enforced |
| Near-duplicate handling | ⚠️ Medium | No fuzzy matching for similar titles |

**Verdict:** Good coverage. Dedup is critical missing piece.

---

### C) ERROR HANDLING & RESILIENCE
| Dimension | Status | Notes |
|-----------|--------|-------|
| Exception safety | ⚠️ Medium | Try/except blocks present; but silent failures |
| Partial failure isolation | ❌ Poor | One scraper fails → pipeline continues (partial data) |
| Safe retries | ❌ Missing | No retry logic; hard-coded sleep(1) |
| Infinite loop protection | ✅ OK | Fixed loop counts; no while True |
| Fallback behavior | ⚠️ Medium | ICS parsing fallback to HTML parse ok |
| Visibility of failures | ❌ Poor | Only logged to stdout; no audit trail |

**Verdict:** Needs structured error collection + exit code signaling.

---

### D) OBSERVABILITY
| Dimension | Status | Notes |
|-----------|--------|-------|
| Logging | ❌ Missing | Only stdout; no file logs |
| Structured logs | ❌ Missing | Plain text only; no JSON/metrics |
| Key metrics | ⚠️ Partial | Computed in-memory; not persisted |
| Audit trail | ❌ Missing | No record of what was uploaded |
| Alert-worthy conditions | ⚠️ Medium | Low-confidence events detected; scraper errors swallowed |
| Email notifications | ✅ Good | HTML emails with stats; CSV attached |

**Verdict:** Email is good; need file logs + audit trail.

---

### E) CONFIGURATION & SECRETS
| Dimension | Status | Notes |
|-----------|--------|-------|
| Env var usage | ✅ Good | All secrets in env vars |
| Secret handling | ✅ Good | App Passwords (not plain passwords); SMTP user/pass via env |
| Safe defaults | ✅ Good | AUTO_UPLOAD=false; events created as drafts |
| Dev/prod separation | ✅ Good | Env vars + WP_SITE_URL switch between sandbox/prod |
| Validation | ❌ Missing | No upfront checks; failures occur mid-pipeline |
| Documentation | ⚠️ Medium | Exists in README; could be more complete |

**Verdict:** Strong; add validation at startup.

---

### F) TESTING
| Dimension | Status | Notes |
|-----------|--------|-------|
| Parser tests | ✅ OK | test_event_normalizer.py covers paid/free detection |
| Normalizer tests | ✅ OK | Venue, tag, event type tests present |
| Scraper tests | ⚠️ Partial | test_perdido_scraper.py exists; needs Wren Haven fixtures |
| Integration tests | ❌ Missing | No end-to-end pipeline test |
| Edge cases | ⚠️ Medium | Some covered; timezone handling not tested |
| Fixtures | ✅ Good | Deterministic (no live network) |
| Coverage | ⚠️ Medium | Estimated 40–50%; need 70%+ |

**Verdict:** Good foundation; need more coverage + integration tests.

---

### G) PERFORMANCE & SCALE
| Dimension | Status | Notes |
|-----------|--------|-------|
| Daily/weekly runtime | ✅ Good | Scrape ~800 events in ~2–3 min; classify in <1 min |
| Headless browser use | ✅ OK | Playwright used only for Wren Haven; cached (24h TTL) |
| Recomputation avoidance | ✅ OK | Model cached in memory; image scoring vectorized |
| Concurrency safety | ⚠️ Medium | ThreadPoolExecutor used; verify thread-safety on image upload |
| Memory usage | ✅ OK | DataFrame operations efficient; no obvious leaks |
| Disk I/O | ⚠️ Medium | CSV write is blocking; fine for current scale |

**Verdict:** Good for current scale (weekly runs, ~1K events). Scale up only if needed.

---

### H) MAINTAINABILITY
| Dimension | Status | Notes |
|-----------|--------|-------|
| Code organization | ✅ Good | Modules for scraping, normalization, upload, email |
| Naming clarity | ✅ Good | Function/variable names are clear |
| Reusability | ✅ Good | WordPressEventUploader, event_normalizer can be reused |
| Extension points | ✅ OK | Easy to add new scraper (follow Wren Haven pattern) |
| Documentation | ⚠️ Medium | Docstrings present; README could be more detailed |
| Code style | ⚠️ Medium | Mostly follows Google Python Style Guide; some inconsistencies |
| Tech debt | ⚠️ Medium | Timezone hack, print-based logging, no audit trail |

**Verdict:** Clean code; good maintainability. Address tech debt before going live.

---

## 9. TRANSITION PLAN TO PRODUCTION

### Phase 1: Blocking Issues (Week 1–2)
1. ✅ Deduplication by UID (high-impact, catches biggest risk)
2. ✅ Environment validation (fast; prevents surprises)
3. ✅ Structured logging (enables observability)
4. ✅ Scraper error collection (prevents silent failures)
5. ✅ Rate limiting (reduces risk of being blocked)

### Phase 2: High-Priority Polish (Week 3–4)
6. ✅ Startup health checks (early failure detection)
7. ✅ Expand test coverage (confidence in changes)
8. ✅ Data persistence / audit log (compliance + debugging)

### Phase 3: Deploy to Production (Week 5)
9. ✅ Final manual testing against sandbox WordPress
10. ✅ Configure Windows Task Scheduler for weekly runs
11. ✅ Set up log rotation + email alerts
12. ✅ Go live on Monday with operator on standby

### Phase 4: Post-Launch Monitoring (Ongoing)
13. ✅ Monitor logs for first 3 runs
14. ✅ Verify dedup logic catches re-runs correctly
15. ✅ Track classification accuracy; retrain if needed
16. ✅ Collect user feedback on calendar quality

---

## 10. RISK ASSESSMENT

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Duplicate events published | HIGH | CRITICAL | ✅ Blocking issue #2: dedup by UID |
| Pipeline fails mid-run | MEDIUM | HIGH | ✅ Blocking issue #4: error collection |
| Missing env vars | MEDIUM | HIGH | ✅ Blocking issue #3: validation |
| Loss of audit trail | LOW | MEDIUM | ✅ High-priority #8: persist events |
| Timezone corruption | LOW | MEDIUM | ✅ Medium-priority #1: test DST |
| Rate limit / IP ban | MEDIUM | MEDIUM | ✅ Blocking issue #5: backoff |
| Email notification fails silently | LOW | LOW | ✅ Medium-priority #5: retry + log |

---

## 11. SIGN-OFF CHECKLIST

Before deploying to production, verify:

- [ ] Deduplication by UID implemented + tested
- [ ] Environment validation at startup + tested
- [ ] Structured logging in place + rotating correctly
- [ ] Scraper errors collected + reported in email
- [ ] Rate limiting + backoff implemented
- [ ] 70%+ test coverage (focus on core paths)
- [ ] Health check passes before pipeline runs
- [ ] Audit log persisted for all runs
- [ ] WordPress sandbox tests pass (create → publish → verify dates)
- [ ] Email notifications work (test with real credentials)
- [ ] Timezone handling verified (test EDT/CST transition)
- [ ] Documentation complete (README, setup, troubleshooting)
- [ ] Task Scheduler configured + dry-run succeeds
- [ ] Operator trained on monitoring + incident response
- [ ] Backup/rollback plan documented

---

**Report prepared by: GitHub Copilot**  
**Recommendations: Follow blocking issues in order; plan 2–3 weeks to production**
