# Event Normalization & Enrichment Implementation Summary

## Overview
This document summarizes the end-to-end enhancements implemented for the automated community calendar ingestion system. All features include parsing, normalization, persistence, and comprehensive test coverage.

## Implemented Features

### 1. PAID/FREE Event Detection (`event_type`)
**Module:** `scripts/event_normalizer.py`

**Functionality:**
- Automatically determines if an event is FREE, PAID, or UNKNOWN based on content analysis
- Parses price/cost indicators from title, description, and cost fields
- Handles edge cases: $0, "no cover", "complimentary", "free with RSVP", etc.
- Robust currency parsing with phone number exclusion
- Stores results in: `is_free`, `paid_status`, `event_type`, `cost_text` fields

**Test Coverage:** 14 unit tests covering free indicators, price detection, edge cases, and HTML handling

### 2. Event Filtering (Brandon Styles @ OWA)
**Module:** `scripts/event_normalizer.py`

**Functionality:**
- Filters out "Brandon Styles" events at OWA in Foley, AL
- Keeps Brandon Styles events on the Florida side
- Case-insensitive matching with structured logging
- Sets `should_filter` and `filter_reason` fields

**Test Coverage:** 6 unit tests covering various location combinations and case sensitivity

### 3. Event Tagging System
**Module:** `scripts/tag_taxonomy.py`

**Taxonomy:** 40+ controlled tags organized by category:
- Music: `live_music`, `dj`, `karaoke`, `open_mic`, `comedy`, `theater`
- Food/Drink: `food_drink`, `happy_hour`, `wine`, `beer`, `cocktails`, `brunch`
- Family: `family_friendly`, `kids`
- Outdoors: `beach`, `outdoors`, `run_walk`, `fitness`, `sports_event`, `fishing`
- Arts: `art`, `craft`, `gallery`, `exhibition`
- Community: `fundraiser`, `nonprofit`, `market`, `festival`, `parade`
- Special: `holiday`, `seasonal`, `trivia`, `educational`

**Functionality:**
- Deterministic keyword-based tag inference using regex patterns
- Scores tags by keyword frequency, returns top 5 (configurable)
- Consistent tag format: lowercase with underscores
- Tag validation against controlled taxonomy

**Test Coverage:** 30 unit tests including inference, validation, and 10 representative real-world events

### 4. Venue Resolution & Linking
**Module:** `scripts/venue_registry.py`

**Known Venues Registry:** 15 pre-programmed venues with aliases
- Flora-Bama (with aliases: "Flora Bama", "Flora-Bama Lounge")
- Perdido Key Sports Bar (aliases: "PK Sports Bar", "PKSB")
- Lillian's Pizza, OWA, The Wharf, LuLu's, The Hangout, etc.

**Functionality:**
- Normalizes location text (lowercase, punctuation removal, whitespace collapse)
- Matches against canonical names and aliases
- Sets `venue_id`, `venue_name`, `normalized_location` when matched
- Handles partial matches in longer location strings
- Supports runtime venue additions

**Test Coverage:** 28 unit tests covering normalization, matching, aliases, and real-world variations

## Integration Points

### Automated Pipeline (`scripts/automated_pipeline.py`)
```python
# New enrichment step in classify_events()
events_df = enrich_events_dataframe(events_df)  # Add tags, paid/free, venue data
kept_df, filtered_df = filter_events_dataframe(events_df)  # Apply filters
```

### WordPress Uploader (`scripts/wordpress_uploader.py`)
Enhanced `parse_event_metadata()` to include:
- Normalized location (`normalized_location` → canonical venue name)
- Venue ID (`venue_id` → custom meta field `_venue_id`)
- Cost information (`cost_text` → `_event_cost`)
- Event type (`event_type`, `paid_status`, `is_free` → meta fields)
- Tags (stored in `_event_tags` and `_event_tags_display` meta fields)

## Data Model Extensions

### Event Fields Added:
- `is_free` (boolean)
- `paid_status` (FREE | PAID | UNKNOWN)
- `event_type` (free_event | paid_event | event)
- `cost_text` (extracted cost description)
- `tags` (list of tag slugs)
- `venue_id` (matched venue ID)
- `venue_name` (canonical venue name)
- `normalized_location` (standardized location text)
- `should_filter` (boolean)
- `filter_reason` (string)

### WordPress Meta Fields:
- `_venue_id`: Venue identifier
- `_event_cost`: Cost/price text
- `_event_type`: Event type slug
- `_paid_status`: Paid status
- `_is_free`: "yes" or "no"
- `_event_tags`: Comma-separated tag slugs
- `_event_tags_display`: Comma-separated display names

## Test Results

**Total Tests:** 85
**Pass Rate:** 100%

**Breakdown:**
- Tag Taxonomy: 30 tests ✓
- Venue Registry: 28 tests ✓
- Event Normalizer: 27 tests ✓

**Coverage Areas:**
- Paid/free detection edge cases (14 tests)
- Brandon Styles filtering (6 tests)
- Tag inference for various event types (17 tests)
- Venue resolution with aliases (13 tests)
- Location normalization (7 tests)
- Full event enrichment (5 tests)
- Real-world representative events (10 tests)

## Usage

### Running Tests:
```powershell
# Activate virtual environment
& .venvEnvisionPerdido\Scripts\Activate.ps1

# Run all new tests
python -m pytest tests/test_tag_taxonomy.py tests/test_venue_registry.py tests/test_event_normalizer.py -v
```

### Pipeline Execution:
```powershell
# Set environment variables
$env:AUTO_UPLOAD = "false"  # Safe default
$env:SITE_TIMEZONE = "America/Chicago"

# Run pipeline with enrichment
python scripts/automated_pipeline.py
```

### Adding New Venues:
Edit `scripts/venue_registry.py` and add to `KNOWN_VENUES` list:
```python
Venue(
    id="new-venue-id",
    canonical_name="Venue Name",
    aliases=["Alias 1", "Alias 2"],
    city="City",
    state="FL",
)
```

### Adding New Tags:
1. Add tag constant to `TagTaxonomy` class in `scripts/tag_taxonomy.py`
2. Add keyword patterns to `TAG_KEYWORDS` dictionary
3. Use lowercase with underscores format

## File Summary

### New Files Created:
1. **`scripts/tag_taxonomy.py`** (380 lines)
   - Tag taxonomy constants (40+ tags)
   - Keyword patterns for inference
   - `infer_tags()` function
   - Tag validation utilities

2. **`scripts/venue_registry.py`** (228 lines)
   - Venue dataclass with normalization
   - Known venues registry (15 venues)
   - `resolve_venue()` function
   - Location text normalization

3. **`scripts/event_normalizer.py`** (335 lines)
   - `detect_paid_or_free()` - cost detection
   - `should_filter_brandon_styles_owa()` - filtering logic
   - `enrich_event()` - full enrichment pipeline
   - `filter_events_dataframe()` - DataFrame filtering

4. **`tests/test_tag_taxonomy.py`** (287 lines)
   - 30 unit tests for tag inference and taxonomy

5. **`tests/test_venue_registry.py`** (277 lines)
   - 28 unit tests for venue resolution and normalization

6. **`tests/test_event_normalizer.py`** (289 lines)
   - 27 unit tests for paid/free detection, filtering, and enrichment

### Modified Files:
1. **`scripts/automated_pipeline.py`**
   - Added import for `event_normalizer`
   - Integrated enrichment in `classify_events()`
   - Added filtering step with logging

2. **`scripts/wordpress_uploader.py`**
   - Enhanced `parse_event_metadata()` for new fields
   - Added `_set_event_tags()` helper
   - Tag handling in `create_event()`

## Key Design Decisions

1. **Deterministic Tagging:** Tags are inferred using keyword matching rather than ML to ensure consistency and debuggability

2. **Controlled Taxonomy:** Fixed set of tags prevents vocabulary explosion and ensures WordPress compatibility

3. **Venue Registry:** Pre-programmed venues with aliases for offline operation and deterministic matching

4. **Import Strategy:** Modules use absolute imports for compatibility with pipeline and test execution

5. **Priority Ordering:** Free indicators have higher priority than price patterns to handle "$0" correctly

6. **Meta Field Storage:** Tags and event data stored as WordPress custom meta fields for EventON compatibility

## Future Enhancements

1. **Venue Database:** Consider moving venue registry to SQLite database for easier management
2. **Tag Taxonomy UI:** Admin interface for managing tags and keywords
3. **ML-Based Tagging:** Optional ML model for tag suggestion (with human review)
4. **Location Geocoding:** Add lat/lng coordinates for venues
5. **Duplicate Detection:** Enhanced duplicate event detection using venue normalization
6. **Analytics:** Track tag distribution and venue popularity

## Logging & Debugging

All filtering operations are logged with structured messages:
```
FILTERED: Brandon Styles Live at OWA Parks, Foley, AL - Reason: FILTER_BRANDON_STYLES_OWA_AL
```

Enrichment statistics are logged:
```
Enrichment complete. Added tags, event types, and venue data.
Filtered out 2 events: [details]
```

## Dependencies

No new external dependencies added. Uses existing packages:
- `pandas` - DataFrame operations
- `re` - Regex matching
- Standard library: `dataclasses`, `typing`, `enum`

---

**Implementation Date:** January 2026
**Author:** GitHub Copilot (Claude Sonnet 4.5)
**Test Pass Rate:** 100% (85/85 tests passing)
