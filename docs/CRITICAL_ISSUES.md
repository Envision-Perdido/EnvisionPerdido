# CRITICAL PRODUCTION ISSUES - Quick Reference

**Read this first.** These 5 issues must be fixed before going live.

---

## 🔴 ISSUE 1: Duplicate Events (CRITICAL)

**Problem:** Running pipeline twice uploads events twice (silent data loss)

**Why it happens:**
```python
# Current code: scraped events have UID, but WordPress doesn't check for it
events = scrape_events()  # Events have 'uid' from ICS
for event in events:
    uploader.create_event(event)  # Creates EVERY time, doesn't check if exists
```

**Impact:** Community sees duplicate calendar entries; trust erodes

**Fix (3–4 hours):**
1. Add to `WordPressEventUploader.create_event()`:
   ```python
   # Check if event already exists (by UID)
   existing = self.get_event_by_uid(event_row['uid'])
   if existing:
       logger.warning(f"Skipped: event {event_row['uid']} already exists (ID {existing})")
       return None  # Don't create
   ```

2. Implement `get_event_by_uid()`:
   ```python
   def get_event_by_uid(self, uid: str) -> int | None:
       """Find event ID by UID meta field. Returns ID or None."""
       response = self.session.get(
           f"{self.api_base}/ajde_events",
           auth=self.auth,
           params={
               'meta_key': '_event_uid',
               'meta_value': uid,
               'per_page': 1,
           }
       )
       if response.status_code == 200 and response.json():
           return response.json()[0]['id']
       return None
   ```

3. Store UID in metadata:
   ```python
   metadata['_event_uid'] = event_row.get('uid')
   ```

**Test it:**
```python
def test_dedup():
    uploader.upload_events_from_csv('test.csv')  # Creates 10 events
    uploader.upload_events_from_csv('test.csv')  # Upload same CSV again
    # Should skip all 10, create 0 new events
```

---

## 🔴 ISSUE 2: Missing Environment Variables Crash Pipeline (CRITICAL)

**Problem:** If `WP_APP_PASSWORD` is missing, pipeline fails after 5+ minutes of processing

**Why it happens:**
```python
# Scripts import env vars at startup
WORDPRESS_CONFIG = {
    "app_password": os.getenv("WP_APP_PASSWORD", ""),  # Empty string if missing
}

def main():
    log("Starting scraping...")  # Takes 5 min
    log("Classifying...")        # Takes 1 min
    # ...
    created_ids, published = upload_to_wordpress(csv)  # FAILS HERE
    # "ERROR: WordPress connection failed"
    # Too late! All processing done, nothing to show for it
```

**Impact:** Operator has to wait 10 min to find out env var was wrong

**Fix (1–2 hours):**
1. Create `env_loader.py` function:
   ```python
   def validate_env_config():
       """Check all required env vars at startup. Fail fast if missing."""
       required = {
           'SMTP_SERVER': 'Email SMTP server',
           'SMTP_PORT': 'Email SMTP port',
           'SENDER_EMAIL': 'Email sender address',
           'EMAIL_PASSWORD': 'Email password',
           'RECIPIENT_EMAIL': 'Email recipient address',
       }
       
       auto_upload = os.getenv("AUTO_UPLOAD", "true").lower() in {"true", "1"}
       if auto_upload:
           required.update({
               'WP_SITE_URL': 'WordPress site URL',
               'WP_USERNAME': 'WordPress username',
               'WP_APP_PASSWORD': 'WordPress application password',
           })
       
       missing = []
       for key, description in required.items():
           if not os.getenv(key):
               missing.append(f"  - {key}: {description}")
       
       if missing:
           print("ERROR: Missing required environment variables:")
           print("\n".join(missing))
           print("\nSet these in scripts/windows/env.ps1 (or scripts/macos/env.sh)")
           sys.exit(1)
       
       print("✓ Environment validation passed")
   ```

2. Call at start of `main()`:
   ```python
   def main():
       validate_env_config()  # <-- ADD THIS FIRST
       
       log("Starting event scraping...")
       # ...
   ```

**Test it:**
```bash
# Unset a var, try to run
$env:WP_APP_PASSWORD = ""
python scripts/automated_pipeline.py
# Should fail in <1 second with clear error message
```

---

## 🔴 ISSUE 3: No Logging (CRITICAL)

**Problem:** Unattended cron job produces no logs; can't debug failures

**Why it happens:**
```python
def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")  # Only stdout; lost if not redirected
```

If Task Scheduler runs unattended, output is lost.

**Impact:** Silent failure; can't diagnose what went wrong

**Fix (4–6 hours):**
1. Create `scripts/logger.py`:
   ```python
   import logging
   import sys
   from pathlib import Path
   from logging.handlers import RotatingFileHandler
   import json
   
   LOG_DIR = Path(__file__).parent.parent / "output" / "logs"
   LOG_DIR.mkdir(parents=True, exist_ok=True)
   
   def get_logger(name: str):
       logger = logging.getLogger(name)
       logger.setLevel(logging.DEBUG)
       
       # File handler: rotate at 10 MB, keep 5 backups
       fh = RotatingFileHandler(
           LOG_DIR / f"{name}.log",
           maxBytes=10_000_000,
           backupCount=5
       )
       fh.setLevel(logging.DEBUG)
       
       # Console handler: INFO and above
       ch = logging.StreamHandler(sys.stdout)
       ch.setLevel(logging.INFO)
       
       # File format: JSON (machine-readable)
       class JSONFormatter(logging.Formatter):
           def format(self, record):
               log_obj = {
                   'timestamp': self.formatTime(record),
                   'level': record.levelname,
                   'message': record.getMessage(),
               }
               return json.dumps(log_obj)
       
       fh.setFormatter(JSONFormatter())
       ch.setFormatter(logging.Formatter('[%(levelname)-8s] %(message)s'))
       
       logger.addHandler(fh)
       logger.addHandler(ch)
       return logger
   ```

2. Replace `log()` calls throughout codebase:
   ```python
   # Old:
   log("Scraped 100 events")
   
   # New:
   logger = get_logger(__name__)
   logger.info("Scraped 100 events")
   ```

3. Add pipeline summary metrics:
   ```python
   logger.info(f"PIPELINE_SUMMARY scraped={847} classified={124} community={98} filtered=3 needs_review=12 uploaded=85 errors=0")
   ```

**Test it:**
```bash
python scripts/automated_pipeline.py
# Should see:
#   - Console output (human-readable)
#   - output/logs/automated_pipeline.log (JSON format)
# Run twice, verify first log is backed up to .1, .2, etc.
```

---

## 🔴 ISSUE 4: Scraper Errors Silently Kill Pipeline (CRITICAL)

**Problem:** If Wren Haven scraper fails, pipeline continues with partial data (undetected)

**Why it happens:**
```python
try:
    events = wren_haven_scraper.scrape_wren_haven()
except Exception as e:
    log(f"Error scraping Wren Haven: {e}")
    # CONTINUES - no indication of failure!
```

**Impact:** Email notification says "98 community events" but actually should be "124" (from 2 sources)

**Fix (2–3 hours):**
1. Return `(events, errors)` tuple:
   ```python
   def scrape_events(...) -> tuple[list[dict], list[str]]:
       all_events = []
       errors = []  # Collect errors instead of silently continuing
       
       # Perdido Chamber
       try:
           events = Envision_Perdido_DataCollection.scrape_month(month_url)
           all_events.extend(events)
       except Exception as e:
           errors.append(f"Perdido Chamber {month_url}: {e}")
       
       # Wren Haven
       try:
           events = wren_haven_scraper.scrape_wren_haven()
           all_events.extend(events)
       except Exception as e:
           errors.append(f"Wren Haven: {e}")
       
       return all_events, errors
   ```

2. In `main()`, handle errors:
   ```python
   events, scrape_errors = scrape_events(...)
   
   if scrape_errors:
       for error in scrape_errors:
           logger.warning(f"Scraper error: {error}")
   
   if not events:
       logger.critical("No events scraped. Aborting.")
       sys.exit(1)
   ```

3. Include errors in email:
   ```python
   if scrape_errors:
       email_body += f"\n⚠️  SCRAPER ERRORS: {len(scrape_errors)}\n"
       for error in scrape_errors:
           email_body += f"  - {error}\n"
   ```

**Test it:**
```python
# Break Wren Haven scraper (rename file, etc.)
python scripts/automated_pipeline.py
# Should:
#   1. Log warning for Wren Haven error
#   2. Continue with Perdido Chamber data
#   3. Include error in email
#   4. Exit with non-zero code
```

---

## 🔴 ISSUE 5: No Rate Limiting on Scraper (CRITICAL)

**Problem:** Scraper can hammer upstream; IP may get banned

**Why it happens:**
```python
# Only `time.sleep(1)` between requests; no backoff on 429/503
response = sess.get(ics_url, timeout=30)
response.raise_for_status()  # Throws on 429/503; no retry
```

**Impact:** Perdido Chamber blocks IP; scraper stops working

**Fix (1–2 hours):**
1. Add retry strategy to requests session:
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
   
   sess = get_session_with_retries()
   ```

2. Verify all requests have timeout:
   ```python
   response = sess.get(url, timeout=30)  # Already done in most places
   ```

**Test it:**
```python
# Mock a 429 response
def test_rate_limit_retry(monkeypatch):
    attempt_count = 0
    def mock_get(*args, **kwargs):
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
            response = Mock(status_code=429)
            response.raise_for_status = Mock(side_effect=requests.HTTPError())
            return response
        return Mock(status_code=200, text='<html>...</html>')
    
    monkeypatch.setattr('requests.Session.get', mock_get)
    result = get_event_url(month_url)
    assert attempt_count == 3  # Retried twice, succeeded on 3rd
```

---

## 📝 ACTION ITEMS

**This week:**
1. [ ] Fix Issue 1 (Dedup) — 3–4 hours
2. [ ] Fix Issue 2 (Env validation) — 1–2 hours
3. [ ] Fix Issue 3 (Logging) — 4–6 hours
4. [ ] Fix Issue 4 (Error isolation) — 2–3 hours
5. [ ] Fix Issue 5 (Rate limiting) — 1–2 hours

**Total time:** ~12–17 hours (~2–3 days of focused work)

**Result:** Production-ready pipeline with 75+/100 readiness score

---

## 🚀 DEPLOY CHECKLIST

Before going live:
- [ ] All 5 critical issues fixed
- [ ] Tests pass: `pytest -v`
- [ ] Sandbox WordPress test successful
- [ ] Logs verified (file + console)
- [ ] Dedup test passes (upload twice → no duplicates)
- [ ] Email notification test passes
- [ ] Environment validation works
- [ ] Operator trained on logs + monitoring
- [ ] Go/no-go decision made

---

**Reference Files:**
- Full assessment: `PRODUCTION_READINESS_ASSESSMENT.md`
- Full TODO list: `PRODUCTION_TODO_CHECKLIST.md`
- Copilot instructions: `.github/copilot-instructions.md`
