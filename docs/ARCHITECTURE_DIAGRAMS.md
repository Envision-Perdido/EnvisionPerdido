# Wren Haven Integration - Architecture Diagram

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                     AUTOMATED PIPELINE                              │
│                  (automated_pipeline.py)                            │
│                                                                     │
│  scrape_events(include_sources=['perdido_chamber', 'wren_haven'])   │
└────────────────┬──────────────────────────────────┬─────────────────┘
                 │                                  │
         ┌───────▼────────┐              ┌──────────▼──────────┐
         │ PERDIDO CHAMBER │              │   WREN HAVEN        │
         │  Data Collection│              │   Scraper           │
         └───────┬────────┘              └──────────┬──────────┘
                 │                                  │
         [ICS Scraper]                    [JSON API Scraper]
         Chamber Website                          │
         Parse .ics files                    ┌────▼────────┐
         Extract: title, start,              │  Bootstrap  │
                 end, location,              │  (1st run)  │
                 url, description            │             │
                                             │ Playwright: │
                 │                           │ - Navigate  │
                 │                           │ - Click btn │
                 │                           │ - Intercept │
                 │                           │ - Extract   │
                 │                           │   auth      │
                 │                           └────┬────────┘
                 │                                │
                 │              ┌─────────────────▼──────────┐
                 │              │   Cache Management          │
                 │              │   (browser_bootstrap.py)    │
                 │              │                             │
                 │              │ Save: data/cache/bootstrap/ │
                 │              │ TTL: 24 hours               │
                 │              └─────────────────┬──────────┘
                 │                                │
                 │              ┌─────────────────▼──────────┐
                 │              │   HTTP Fetch                │
                 │              │   (Cached auth)             │
                 │              │                             │
                 │              │ GET/POST to endpoint        │
                 │              │ + Authorization header      │
                 │              │ + Cookies (if present)      │
                 │              │ Parse JSON response         │
                 │              └─────────────────┬──────────┘
                 │                                │
         ┌───────▼────────────────────────────────▼────────┐
         │          NORMALIZATION                          │
         │    (Both sources → standard schema)             │
         │                                                  │
         │  Wren Haven:                                    │
         │  - title/name → title                           │
         │  - startDate/begin → start                      │
         │  - endDate/finish → end                         │
         │  - location/venue → location                    │
         │  - link/url → url                               │
         │  - description/summary → description            │
         │  - id/uid → uid                                 │
         │  - type/category → category                     │
         │                                                  │
         │  Chamber: (already standard format)             │
         │  - title, start, end, location, etc.            │
         │                                                  │
         └────────────────┬─────────────────────────────────┘
                          │
         ┌────────────────▼─────────────────┐
         │   DATAFRAME                      │
         │   (Combined Events)              │
         │                                  │
         │   title   | start  | end | ...  │
         │   ────────────────────────────  │
         │   Event 1 | ...    | ... | ...  │ ← Perdido Chamber
         │   Event 2 | ...    | ... | ...  │ ← Wren Haven
         │   Event 3 | ...    | ... | ...  │ ← Perdido Chamber
         │   ...                           │
         └────────────────┬─────────────────┘
                          │
         ┌────────────────▼──────────────────────────────┐
         │  ENRICHMENT PIPELINE                         │
         │  (existing code, works on all sources)       │
         │                                              │
         │  1. event_normalizer.py                      │
         │     └─ Paid/free detection                   │
         │     └─ Cost extraction                       │
         │     └─ Event type classification             │
         │     └─ Long event filtering (>60 days)       │
         │                                              │
         │  2. venue_registry.py                        │
         │     └─ Location normalization                │
         │     └─ Match to canonical venue names        │
         │                                              │
         │  3. Image assignment                         │
         │     └─ Keyword-based matching                │
         │     └─ Assign event_images                   │
         │                                              │
         │  4. Feature building                         │
         │     └─ TF-IDF text features                  │
         │     └─ Prepare for classification            │
         │                                              │
         │  5. SVM Classification                       │
         │     └─ Load trained model                    │
         │     └─ Predict: community or non-community   │
         │     └─ Get confidence scores                 │
         │                                              │
         │  6. Filtering                                │
         │     └─ Keep: confidence >= 0.75 OR manual    │
         │     └─ Flag: 0.5-0.75 for review             │
         │     └─ Drop: < 0.5 confidence                │
         └────────────────┬──────────────────────────────┘
                          │
         ┌────────────────▼──────────────────────────────┐
         │  COMMUNITY EVENTS DATAFRAME                  │
         │                                              │
         │  All enriched & classified events             │
         │  Ready for calendar upload                   │
         └────────────────┬──────────────────────────────┘
                          │
         ┌────────────────▼──────────────────────────────┐
         │  EXPORT & NOTIFICATION                       │
         │                                              │
         │  1. Export to CSV                            │
         │     └─ output/pipeline/calendar_upload_*.csv │
         │                                              │
         │  2. Email notification                       │
         │     └─ Summary stats                         │
         │     └─ List of events                        │
         │     └─ Confidence scores                     │
         │                                              │
         │  3. WordPress upload (optional)              │
         │     └─ Create draft events                   │
         │     └─ Upload images                         │
         │     └─ Set metadata (dates, location, etc.)  │
         │     └─ (Manual publish step)                 │
         └──────────────────────────────────────────────┘
```

---

## Bootstrap Sequence (First Run Only)

```
scrape_wren_haven()
    │
    ├─ Check cache
    │  └─ data/cache/bootstrap/{hash}.json exists?
    │     ├─ YES, < 24h old → Use cached artifacts (DONE, 1ms)
    │     └─ NO or EXPIRED → Continue to bootstrap
    │
    └─ Launch Playwright
       │
       ├─ Browser.launch(headless=True)
       │
       ├─ Page.goto('https://www.wrenhavenhomestead.com/events')
       │
       ├─ Setup request interception
       │  └─ Listen for all network requests
       │
       ├─ Click "Previous month" button
       │  └─ button[aria-label='Previous month'].click()
       │
       ├─ Intercept JSON request
       │  │
       │  └─ Filter for requests with 'json' or '/api/' in URL
       │
       ├─ Extract from intercepted request:
       │  ├─ endpoint = request.url
       │  ├─ method = request.method (GET/POST)
       │  ├─ headers = {
       │  │    'Authorization': 'Bearer token_xxx',
       │  │    'Content-Type': 'application/json',
       │  │    'User-Agent': '...',
       │  │    ... other headers
       │  │  }
       │  ├─ cookies = page.context.cookies()
       │  └─ body = request.post_data (if POST)
       │
       ├─ Save to cache
       │  └─ data/cache/bootstrap/{hash}.json
       │     {
       │       "endpoint": "https://api.wrenhavenhomestead.com/events",
       │       "method": "GET",
       │       "headers": {...},
       │       "cookies": [...],
       │       "created_at": "2025-01-14T12:00:00",
       │       "requests_captured": 1
       │     }
       │
       └─ Close browser
          └─ Return artifacts
```

---

## HTTP Fetch Sequence (Every Run)

```
_fetch_events_from_api(artifacts)
    │
    ├─ endpoint = artifacts['endpoint']
    │  └─ "https://api.wrenhavenhomestead.com/events"
    │
    ├─ headers = merge(DEFAULT_HEADERS, artifacts['headers'])
    │  └─ {
    │      'User-Agent': '...',
    │      'Authorization': 'Bearer token_xxx',  ← from cache
    │      'Content-Type': 'application/json'     ← from cache
    │    }
    │
    ├─ cookies = artifacts['cookies']
    │  └─ [
    │      {'name': 'session_id', 'value': 'abc123', 'domain': '...'},
    │      ...
    │    ]
    │
    ├─ Retry loop (max 3 attempts with exponential backoff)
    │  │
    │  ├─ Attempt 1 (timeout: 30s)
    │  │  │
    │  │  ├─ requests.get(
    │  │  │   endpoint,
    │  │  │   headers=headers,
    │  │  │   cookies={...},
    │  │  │   params={'start': '2025-03-01', 'end': '2025-03-31'}
    │  │  │  )
    │  │  │
    │  │  ├─ 200 OK?
    │  │  │  ├─ YES → Parse JSON, extract event list, return
    │  │  │  └─ NO → Raise, retry
    │  │  │
    │  │  ├─ 401 Unauthorized?
    │  │  │  └─ Retry (hope for transient issue)
    │  │  │
    │  │  └─ Connection timeout?
    │  │     └─ Wait 1s, retry
    │  │
    │  ├─ Attempt 2 (wait 2s first)
    │  │  └─ (same as attempt 1)
    │  │
    │  └─ Attempt 3 (wait 4s first)
    │     └─ (same as attempt 1)
    │
    └─ Return list of event dicts
       [
         {"id": "001", "title": "Event 1", "start": "...", ...},
         {"id": "002", "title": "Event 2", "start": "...", ...},
         ...
       ]
```

---

## Cache File Structure

**Location**: `data/cache/bootstrap/`  
**Filename**: `{SHA256(source_name:domain)[:16]}.json`  
**Example**: `wren_haven_homestead:www.wrenhavenhomestead.com` → `a1b2c3d4e5f6g7h8.json`

```json
{
  "endpoint": "https://api.wrenhavenhomestead.com/v1/events",
  "method": "GET",
  "headers": {
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)..."
  },
  "cookies": [
    {
      "name": "session_id",
      "value": "abc123def456ghi789",
      "domain": ".wrenhavenhomestead.com"
    },
    {
      "name": "auth_token",
      "value": "xyz789abc456def123",
      "domain": ".wrenhavenhomestead.com"
    }
  ],
  "query_params": {
    "start": "2025-03-01",
    "end": "2025-03-31"
  },
  "body": null,
  "requests_captured": 2,
  "discovered_at": "2025-01-14T12:00:00.000000",
  "created_at": "2025-01-14T12:00:00.000000"
}
```

---

## Event Normalization Mapping

```
Raw Wren Haven Event (from JSON API):
┌──────────────────────────────────────┐
│ {                                    │
│   "id": "wh-001",                    │
│   "title": "Spring Garden Workshop", │
│   "startDate": "2025-03-15T10:00:00",│
│   "endDate": "2025-03-15T12:00:00",  │
│   "location": "Wren Haven Farm, AL", │
│   "link": "https://wrenhaven.../",  │
│   "summary": "Learn about...",       │
│   "type": "Workshop"                 │
│ }                                    │
└──────────────────────────────────────┘
         │
         │ normalize_event()
         │
         ▼
Normalized Event (standard schema):
┌──────────────────────────────────────┐
│ {                                    │
│   "title": "Spring Garden Workshop", │
│   "start": "2025-03-15T10:00:00",   │
│   "end": "2025-03-15T12:00:00",     │
│   "location": "Wren Haven Farm, AL", │
│   "url": "https://wrenhaven.../",   │
│   "description": "Learn about...",   │
│   "uid": "wh-001",                  │
│   "category": "Workshop",            │
│   "_raw_source": "wren_haven_..."    │
│ }                                    │
└──────────────────────────────────────┘
         │
         │ (flows into DataFrame)
         │
         ▼
     [Enrichment Pipeline]
         │
    (All existing code:
     paid/free, venue norm,
     images, classification)
```

---

## Integration Points with Existing Code

```
wren_haven_scraper.py
    ├─ Uses: requests.Session (same as Envision_Perdido_DataCollection.py)
    │
    ├─ Feeds into: event_normalizer.py
    │   ├─ detect_paid_or_free()
    │   ├─ extract_cost_text()
    │   ├─ filter_events_dataframe()
    │   └─ enrich_events_dataframe()
    │
    ├─ Feeds into: venue_registry.py
    │   ├─ normalize_location_text()
    │   └─ match_venue()
    │
    ├─ Feeds into: automated_pipeline.py
    │   ├─ classify_events()
    │   ├─ assign_event_images()
    │   ├─ export_for_calendar()
    │   └─ send_email_notification()
    │
    └─ Tests use patterns from: test_perdido_scraper.py
        ├─ DummySession mock
        ├─ DummyResponse mock
        ├─ Pytest fixtures
        └─ Deterministic test data
```

---

## Timing Breakdown

### First Run (with Playwright bootstrap)

```
scrape_events(include_sources=['pedido_chamber', 'wren_haven'])
    │
    ├─ Perdido Chamber scrap:        2s (2 months × 1s each)
    ├─ Wren Haven bootstrap:         8s (Playwright, click, intercept)
    ├─ Wren Haven fetch:             2s (HTTP request + parse)
    ├─ Combine & normalize:          0.5s (250 events)
    ├─ Enrich (paid/free, etc):      2s (normalize locations, etc.)
    ├─ Assign images:                1s (keyword matching)
    ├─ Build features (TF-IDF):      1s (250 events)
    ├─ SVM classification:           0.5s (predict class)
    ├─ Filter & export CSV:          0.5s
    └─ Send email:                   1s (SMTP)
    ─────────────────────────────────
    TOTAL:                          ~18-20 seconds
```

### Subsequent Runs (with cached auth)

```
scrape_events(include_sources=['perdido_chamber', 'wren_haven'])
    │
    ├─ Perdido Chamber scrap:        2s (2 months × 1s each)
    ├─ Wren Haven cache load:        0.001s (JSON read)
    ├─ Wren Haven fetch:             2s (HTTP request + parse)
    ├─ Combine & normalize:          0.5s
    ├─ Enrich (paid/free, etc):      2s
    ├─ Assign images:                1s
    ├─ Build features (TF-IDF):      1s
    ├─ SVM classification:           0.5s
    ├─ Filter & export CSV:          0.5s
    └─ Send email:                   1s
    ─────────────────────────────────
    TOTAL:                          ~10-12 seconds
```

---

## Error Handling Flow

```
scrape_wren_haven()
    │
    ├─ Try: bootstrap_or_use_cached()
    │  │
    │  ├─ Success → proceed
    │  │
    │  └─ Exception
    │     ├─ WrenHavenScraperError → log error, return []
    │     ├─ ImportError (Playwright missing) → log warning, return []
    │     └─ Unexpected exception → log error, return []
    │
    ├─ Try: _fetch_events_from_api()
    │  │
    │  ├─ Success (200 OK) → parse JSON, proceed
    │  │
    │  ├─ HTTP errors (401, 403, 500)
    │  │  └─ Retry up to 3x with exponential backoff
    │  │
    │  ├─ Connection error (timeout, DNS)
    │  │  └─ Retry up to 3x with exponential backoff
    │  │
    │  └─ JSON parse error
    │     └─ Log error, raise WrenHavenScraperError
    │
    ├─ Try: normalize_event() for each raw event
    │  │
    │  ├─ Success → add to normalized list
    │  │
    │  └─ Exception (key missing, etc.)
    │     └─ Log warning, skip event, continue
    │
    └─ Return normalized events or empty list
```

---

## Key Design Decisions Visualized

### Decision 1: Bootstrap Only Once

```
Timeline:
Day 1: 10s (Playwright bootstrap) → 2s (fetch) = 12s total
Day 2: 0s (cache hit)             → 2s (fetch) = 2s total
Day 3: 0s (cache hit)             → 2s (fetch) = 2s total
...
Day 25: 10s (cache expired, re-bootstrap) → 2s (fetch) = 12s total
```

### Decision 2: Reuse Entire Pipeline

```
                 ┌─ normalize
Wren Haven ──────┤─ enrich
                 ├─ classify ← ALL EXISTING CODE
                 └─ export

                 ┌─ normalize
Perdido ────────┤─ enrich
                 ├─ classify
                 └─ export
```

No duplication. Both sources share pipeline.

### Decision 3: Optional Playwright Dependency

```
If Playwright installed:
    ✓ Wren Haven source works
    ✓ Bootstrap + auth discovery automatic

If Playwright NOT installed:
    ✓ Perdido Chamber source still works
    ✗ Wren Haven source fails gracefully with helpful error
    ✓ Pipeline continues with available sources
```

---

End of architecture documentation.
