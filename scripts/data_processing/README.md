# Data Processing & Normalization

Event data cleaning, normalization, and enrichment scripts.

## Scripts (6)

- `event_normalizer.py` — Normalize and enrich event data
  - Detects paid vs free events using regex patterns
  - Infers event types and categories
  - Normalizes location and venue information
  - Filters out non-community events (e.g., business-only)
  - Adds tags and metadata

- `events_to_labelset.py` — Convert events to labeled training set
  - Loads events from CSV or other format
  - Normalizes column names and data types
  - Generates weak labels based on keyword patterns
  - Produces labelset for manual annotation

- `clean_chamber_urls.py` — Remove unsafe Chamber URLs from events
  - Fetches all events from WordPress REST API
  - Removes 'evcal_lmlink' meta field with Chamber URLs
  - Prevents external redirect vulnerability
  - Reports cleaned event count

- `fix_event_times.py` — Fix and standardize event times
  - Reconstructs local datetime from stored meta fields
  - Recalculates epoch seconds (evcal_srow/evcal_erow)
  - Respects site timezone (default: America/Chicago)
  - Updates all events via WordPress REST API

- `fill_recurring_labels.py` — Propagate labels in recurring event series
  - Identifies recurring events by series_id
  - Propagates manual labels to all events in series
  - Fills missing labels using most common in series
  - Handles URL, title, and location normalization

- `merge_and_propagate_labels.py` — Merge manual and predicted labels
  - Combines manual labels with SVM predictions
  - Manual labels take priority over predictions
  - Propagates labels within event series
  - Produces final labeled dataset

## Workflow

Typical data processing workflow:
```bash
# 1. Normalize raw event data
python data_processing/event_normalizer.py input.csv output.csv

# 2. Create training set
python data_processing/events_to_labelset.py raw_events.csv

# 3. After manual labeling, fill recurring events
python data_processing/fill_recurring_labels.py

# 4. Fix event times on WordPress
python data_processing/fix_event_times.py

# 5. Clean unsafe URLs
python data_processing/clean_chamber_urls.py
```

## Data Transformations

### Paid/Free Detection
Uses regex patterns to identify:
- Prices: `$19.99`, `ticket`, `admission`
- Free indicators: `free`, `no cover charge`, `complimentary`
- Phone numbers (false positive exclusion)

### Event Filtering
Removes:
- Business-only events (board meetings, ribbon cuttings)
- Sponsor events (leads groups, chamber networking)
- Events at specific venues (Brandon Styles @ OWA)

### Tag Inference
Uses keyword matching on title/description to infer:
- Festival, parade, market, community, workshop
- Volunteer, fundraiser, music, food, art, sports
- Family-friendly indicators

### Location Normalization
- Removes extra whitespace and case normalization
- Matches against known venue registry
- Resolves aliases and common variations

## Integration with Pipeline

These scripts are used by:
- `automated_pipeline.py` — Normalizes scraped events before classification
- ML scripts — Feed normalized data to SVM classifier
- WordPress uploader — Clean and format before upload

## Error Handling

Scripts handle:
- Missing/malformed data with sensible defaults
- Network errors with retry logic
- Timezone issues with fallback to UTC
- API rate limiting and HTTP 429/503 errors

## Configuration

Environment variables:
- `SITE_TIMEZONE` — WordPress timezone (default: `America/Chicago`)
- `WP_SITE_URL`, `WP_USERNAME`, `WP_APP_PASSWORD` — WordPress credentials
- `CONFIDENCE_THRESHOLD` — Minimum label confidence to keep (default: 0.75)
