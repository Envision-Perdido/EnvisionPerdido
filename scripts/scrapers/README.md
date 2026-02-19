# Data Collection & Scrapers

Web scrapers and data source integrations for event collection.

## Scripts (3)

- `Envision_Perdido_DataCollection.py` — Main Perdido Chamber scraper
  - Fetches events from Perdido Chamber calendar (BeautifulSoup HTML parsing)
  - Parses iCalendar (ICS) files for detailed event information
  - Handles timezone conversion and date parsing
  - Graceful fallback for missing optional dependencies
  - Session management with retry logic
  - Returns standardized event objects

- `wren_haven_scraper.py` — Wren Haven Homestead events scraper
  - Uses Playwright to render JavaScript-based Wix calendar
  - Navigates through months programmatically
  - Caches HTML responses (24-hour TTL) for performance
  - Parses events with venue and pricing information
  - Integrates with event normalization pipeline

- `google_sheets_source.py` — Google Sheets event submission sync
  - Authenticates via service account (env var or base64-encoded JSON)
  - Fetches rows from specified sheet and range
  - Normalizes headers and maps to internal event schema
  - Flexible datetime parsing with multiple format support
  - Robust error handling and logging
  - Returns standardized event objects

## Workflow

Typical scraping workflow:
```bash
# 1. Scrape Perdido Chamber events
python scrapers/Envision_Perdido_DataCollection.py

# 2. Scrape Wren Haven events (requires Playwright)
python scrapers/wren_haven_scraper.py

# 3. Fetch Google Sheets submissions
python scrapers/google_sheets_source.py

# 4. All combined in automated pipeline
python automated_pipeline.py
```

## Data Sources

### Perdido Chamber
- **URL:** https://business.perdidochamber.com/events
- **Method:** HTML parsing with BeautifulSoup
- **Format:** Mixed HTML and iCalendar
- **Frequency:** Manual runs or scheduled

### Wren Haven Homestead
- **URL:** https://www.wrenhavenhomestead.com/events
- **Method:** Playwright (JavaScript rendering) + BeautifulSoup
- **Format:** Wix calendar (requires JS)
- **Frequency:** Manual runs or scheduled
- **Note:** Requires Playwright browser and optional deps

### Google Sheets
- **Source:** Configured Google Sheet (form submissions)
- **Method:** Google Sheets API
- **Format:** Rows with normalized columns
- **Frequency:** Real-time (on-demand)
- **Auth:** Service account credentials

## Error Handling

Scrapers handle:
- Network timeouts with exponential backoff (5 retries default)
- Missing optional dependencies gracefully (falls back to JSON config)
- Malformed dates with multiple parsing strategies
- Rate limiting (429/503) with automatic retry
- JavaScript-heavy sites with Playwright fallback

## Performance & Caching

- **HTTP Retries:** Configurable retry strategy (default: 5 attempts)
- **Caching:** Wren Haven HTML cached for 24 hours
- **Session Reuse:** Connection pooling for performance
- **Timeouts:** Default 30-second timeout, configurable

## Integration

Scrapers output standardized event objects with:
- title, description, start_time, end_time
- location, venue_id, cost_text
- url, source, source_page
- Custom fields: paid_status, is_community, tags

This standardization allows:
- Unified normalization pipeline
- Consistent ML classification
- Deduplication across sources
- Unified WordPress upload

## Configuration

Environment variables:
- `GOOGLE_SHEETS_ID` — Spreadsheet ID for Google Sheets
- `GOOGLE_SHEETS_RANGE` — Sheet range (default: `Sheet1!A1:Z`)
- `GOOGLE_SERVICE_ACCOUNT` — Base64-encoded JSON or path
- `WRE_HAVEN_CACHE_HOURS` — Cache TTL (default: 24)
- `SITE_TIMEZONE` — Timezone for date parsing (default: America/Chicago)

## Dependencies

### Required
- `requests` — HTTP requests
- `pandas` — Data manipulation

### Optional
- `beautifulsoup4` — HTML parsing (Perdido Chamber, Wren Haven)
- `icalendar` — ICS parsing (Perdido Chamber)
- `playwright` — JavaScript rendering (Wren Haven)
- `google-auth` — Google auth (Google Sheets)
- `google-api-python-client` — Google Sheets API (Google Sheets)
- `zoneinfo` — Timezone handling (Python 3.9+, or `backports.zoneinfo`)

Scrapers gracefully handle missing optional dependencies.
