# Wren Haven Homestead Calendar Source Integration

This document describes the new Wren Haven Homestead calendar source and how to configure it.

## Overview

Wren Haven Homestead (https://www.wrenhavenhomestead.com/events) loads events via a JSON API that requires an Authorization header. To avoid constant Playwright overhead, the integration uses a **bootstrap + cache** strategy:

1. **On first run**: Playwright navigates the page, intercepts the JSON request, extracts the API endpoint and Authorization header, and caches these artifacts
2. **On subsequent runs**: The cached artifacts are reused for regular HTTP requests
3. **On cache expiry (24 hours)** or 401/403 errors: Automatic re-bootstrap

## Requirements

### New Python Packages

Add to `requirements.txt`:
```
playwright>=1.45.0
```

Then install Playwright's browser binaries:
```bash
playwright install chromium
```

On Windows (PowerShell):
```powershell
python -m playwright install chromium
```

## Configuration

### Environment Variables

No new environment variables required for basic operation. If Wren Haven requires API-specific auth, you can set:

```bash
# Optional: Override default behavior
WREN_HAVEN_FORCE_BOOTSTRAP=0  # Set to 1 to force re-bootstrap (ignore cache)
```

### Pipeline Configuration

To include Wren Haven in the automated pipeline, modify the `scrape_events()` call in `scripts/automated_pipeline.py`:

**Default (Perdido Chamber only - backward compatible):**
```python
scrape_events(year=2025, month=3)
```

**Include Wren Haven:**
```python
scrape_events(
    year=2025, 
    month=3,
    include_sources=['perdido_chamber', 'wren_haven']
)
```

**Only Wren Haven:**
```python
scrape_events(
    year=2025,
    month=3,
    include_sources=['wren_haven']
)
```

## How It Works

### Bootstrap Phase (First Run)

When `scrape_wren_haven()` is called:

1. **Check cache**: Look for cached auth artifacts in `data/cache/bootstrap/`
2. **If missing**: Launch Playwright in headless mode
3. **Navigate**: Go to https://www.wrenhavenhomestead.com/events
4. **Intercept**: Capture network requests (looking for JSON API calls)
5. **Click "Previous month"**: Trigger API request to discover endpoint
6. **Extract**: Get endpoint URL, Authorization header, and other auth details
7. **Cache**: Save artifacts with timestamp (TTL: 24 hours)

### Event Fetching Phase

1. **Load cached artifacts** or bootstrap if missing/expired
2. **Prepare headers**: Merge default headers with cached Authorization
3. **Make HTTP request** to the cached API endpoint
4. **Parse JSON response**: Extract event list
5. **Normalize**: Map Wren Haven fields to standard schema
6. **Return**: Pass to enrichment/classification pipeline

### Caching Details

**Cache location:** `data/cache/bootstrap/`
**Cache file:** Named by source + domain hash, contains:
- API endpoint URL
- HTTP method (GET/POST)
- Authorization header (token preserved)
- Cookies (if required)
- Request body template (for POST)
- Timestamp and TTL info

**Cache key format:** `{source_name}:{domain}` → SHA256 hash (first 16 chars)

**TTL:** 24 hours (configurable in code)

**Clearing cache:** 
```python
from scripts.browser_bootstrap import clear_bootstrap_cache

# Clear for one source
clear_bootstrap_cache('wren_haven_homestead', 'www.wrenhavenhomestead.com')

# Clear all cached artifacts
clear_bootstrap_cache()
```

## Event Field Mapping

Wren Haven API fields are mapped to the standard schema:

| Wren Haven Field | Mapped To | Fallback |
|---|---|---|
| `title` / `name` | `title` | - |
| `startDate` / `begin` | `start` | - |
| `endDate` / `finish` | `end` | - |
| `location` / `venue` | `location` | - |
| `link` / `url` | `url` | - |
| `summary` / `description` | `description` | - |
| `id` / `uid` | `uid` | - |
| `type` / `category` | `category` | - |

Once normalized, events flow through the standard enrichment pipeline:
- Venue normalization (via `venue_registry.py`)
- Paid/free detection (via `event_normalizer.py`)
- Image assignment (via keyword scoring)
- Classification (via SVM model)
- Filtering (long events, duplicates, etc.)

## Usage

### Manual Scraping

```python
from scripts.wren_haven_scraper import scrape_wren_haven

# Scrape all events (no date filter)
events = scrape_wren_haven()

# Scrape with date filter
events = scrape_wren_haven(
    start_date='2025-03-01',
    end_date='2025-04-30'
)

# Force re-bootstrap (ignore cache)
events = scrape_wren_haven(force_bootstrap=True)
```

### Integration with Automated Pipeline

The pipeline's `scrape_events()` function now accepts multiple sources:

```python
from scripts.automated_pipeline import scrape_events, assign_event_images, classify_events

# Scrape from multiple sources
all_events = scrape_events(include_sources=['perdido_chamber', 'wren_haven'])

# Convert to DataFrame for enrichment
df = pd.DataFrame(all_events)

# Standard enrichment pipeline (works on all sources)
df = assign_event_images(df)
df = classify_events(df)
```

## Troubleshooting

### "Playwright is required..."
**Error:** `ImportError: No module named 'playwright'`

**Fix:** Install Playwright and browser binaries:
```bash
pip install playwright
playwright install chromium
```

### "Could not discover API endpoint"
**Symptoms:** Bootstrap fails, says "Could not discover API endpoint"

**Causes:**
- Wren Haven website structure changed
- Playwright timeout too short
- Authorization header is not in standard format

**Fix:**
1. Check if Wren Haven website still uses the same "previous month" button selector
2. Increase timeout: `scrape_wren_haven(timeout_seconds=60)`
3. Force re-bootstrap: `scrape_wren_haven(force_bootstrap=True)`
4. Check browser logs manually by running with `headless=False`

### "401 Unauthorized" after some time
**Symptoms:** Events scrape fine initially, then start failing with 401

**Cause:** Authorization token in cache has expired

**Fix:** Clear the bootstrap cache to force re-bootstrap:
```python
from scripts.browser_bootstrap import clear_bootstrap_cache
clear_bootstrap_cache('wren_haven_homestead', 'www.wrenhavenhomestead.com')
```

Or let the code auto-refresh on 401 (code in `_fetch_events_from_api` detects 401 and retries).

### "Browser closed unexpectedly"
**Symptoms:** Playwright crashes during bootstrap

**Fix:**
1. Ensure Chromium is installed: `playwright install chromium`
2. Try with `headless=False` to see what's happening:
   ```python
   from scripts.browser_bootstrap import bootstrap_json_api
   bootstrap_json_api(
       url="https://www.wrenhavenhomestead.com/events",
       headless=False  # Open browser window
   )
   ```

## Testing

Run unit tests for the Wren Haven scraper:

```bash
python -m pytest tests/test_wren_haven_scraper.py -v
```

Tests use mocked network calls, so they don't require the site to be online. Key test cases:
- Event normalization (all field variants)
- Bootstrap cache (load/save/expiry)
- Error handling (network errors, malformed responses)
- Integration with pipeline (multiple sources)

## Code Structure

### Key Files

- **`scripts/wren_haven_scraper.py`**: Main scraper module
  - `scrape_wren_haven()`: Entry point
  - `normalize_event()`: Maps Wren Haven → standard schema
  - `_bootstrap_or_use_cached()`: Cache management
  - `_fetch_events_from_api()`: HTTP fetching with retry/backoff

- **`scripts/browser_bootstrap.py`**: Playwright helper utility
  - `bootstrap_json_api()`: Discover endpoint via Playwright
  - `_load_cached_artifacts()`: Cache load/TTL check
  - `_save_cached_artifacts()`: Cache save with metadata

- **`tests/test_wren_haven_scraper.py`**: Comprehensive test suite
  - Normalization tests
  - Caching tests
  - Error handling tests
  - Integration tests (mocked)

### Integration Points

Reuses existing code:
- **Event model**: Standard schema (title, start, end, location, url, description, uid, category)
- **Enrichment**: `scripts/event_normalizer.py` (paid/free detection, filtering)
- **Venue resolution**: `scripts/venue_registry.py` (location normalization)
- **Classification**: Existing SVM pipeline in `scripts/automated_pipeline.py`
- **HTTP patterns**: Retry/backoff, timeout, headers (consistent with existing code)

## Future Enhancements

- Support for recurring events (if API returns recurrence info)
- Automatic 401 refresh without full cache clear
- Support for POST-based event filtering (if API requires it)
- Webhook/push notification support (if Wren Haven offers it)
- Incremental sync (fetch only changes since last run)

## Questions?

Refer to the copilot-instructions.md for overall project context, or check the docstrings in `browser_bootstrap.py` and `wren_haven_scraper.py` for specific technical details.
