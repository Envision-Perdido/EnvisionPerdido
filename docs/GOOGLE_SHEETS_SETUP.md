# Google Sheets Integration for Community Calendar

This document explains how to set up and use Google Sheets as an event submission source for the EnvisionPerdido Community Calendar pipeline.

## Overview

The Google Sheets integration allows community members to submit events via a Google Form (responses stored in a Google Sheet), which are automatically ingested into the pipeline alongside scraped events. The pipeline applies the same normalization, classification, validation, and deduplication to all submitted events before exporting to WordPress.

## Quick Setup

### 1. Create a Google Cloud Project and Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the **Google Sheets API**:
   - Go to APIs & Services → Library
   - Search for "Google Sheets API"
   - Click Enable
4. Create a service account:
   - Go to APIs & Services → Credentials
   - Click "Create Credentials" → Service Account
   - Fill in account details (name, description optional)
   - Click "Create and Continue"
   - Grant basic Editor role (or Viewer if read-only desired)
   - Click "Continue" and "Done"

### 2. Create and Download Service Account Key

1. In Credentials page, click on the service account you just created
2. Go to the "Keys" tab
3. Click "Add Key" → "Create new key"
4. Choose **JSON** format
5. Download the JSON file — **keep it secure and never commit to git**

### 3. Set Up Your Google Sheet

1. Create a new Google Sheet (or use existing)
2. **First row must be headers** with these column names:
   - `Title` or `Event Name` (required)
   - `Description` or `Event Description` (recommended)
   - `Location` or `Venue` (recommended)
   - `Start Date` (required) — format: MM/DD/YYYY or YYYY-MM-DD
   - `Start Time` (optional) — format: HH:MM or HH:MM AM/PM
   - `End Date` (optional) — defaults to start date if not provided
   - `End Time` (optional)
   - `URL` or `Registration Link` (optional)
   - `Category` or `Tags` (optional)
   - `Organizer Name` (optional)
   - `Organizer Email` (optional)

   **Note:** Column names are flexible; the integration uses pattern matching (e.g., "Title" or "Event Name" both work).

3. Share the sheet with your service account email:
   - Copy the service account email from the downloaded JSON (`client_email` field)
   - Click "Share" on your Google Sheet
   - Paste the email and give **Viewer** access
   - Click "Share"

### 4. Set Environment Variables

Store credentials outside your repository. Choose **one** of these methods:

#### Option A: Credentials File (Recommended for local development)

```bash
# macOS/Linux
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/service-account.json"
export SHEETS_SPREADSHEET_ID="your-spreadsheet-id-here"
export SHEETS_RANGE="Form Responses 1!A:Z"  # Adjust sheet name as needed

# Windows PowerShell
$env:GOOGLE_APPLICATION_CREDENTIALS="C:\path\to\service-account.json"
$env:SHEETS_SPREADSHEET_ID="your-spreadsheet-id"
$env:SHEETS_RANGE="Form Responses 1!A:Z"
```

#### Option B: Base64-Encoded JSON (Better for CI/CD)

```bash
# Encode your service account JSON
export GOOGLE_SHEETS_SA_JSON_B64=$(base64 -w0 < /path/to/service-account.json)
export SHEETS_SPREADSHEET_ID="your-spreadsheet-id"
export SHEETS_RANGE="Form Responses 1!A:Z"
```

To get your spreadsheet ID:
- Open the sheet in your browser
- The ID is in the URL: `https://docs.google.com/spreadsheets/d/<SPREADSHEET_ID>/edit`

### 5. Install Dependencies

```bash
pip install google-auth google-auth-httplib2 google-api-python-client
```

Or if using the existing `requirements.txt`, these may already be listed.

## Usage

### Enable Google Sheets in the Pipeline

Edit your pipeline invocation to include the `google_sheets` source:

```python
# In automated_pipeline.py or your custom script
from scripts.automated_pipeline import scrape_events

events, errors = scrape_events(
    include_sources=['perdido_chamber', 'wren_haven', 'google_sheets']
)
```

Or run the full pipeline with environment variable:

```bash
python scripts/automated_pipeline.py
# Pipeline will default to ['perdido_chamber']
# Add 'google_sheets' programmatically or modify the script
```

### Basic Usage Example

```python
from scripts import google_sheets_source

# Fetch events from configured sheet
events, errors = google_sheets_source.get_events_from_sheets()

if errors:
    print(f"Warnings/errors: {errors}")

for event in events:
    print(f"  - {event['title']} ({event['start']})")
```

### Custom Column Mapping

If your sheet uses different column names, provide a custom mapping:

```python
custom_mapping = {
    'title': ['event_title', 'event_name'],
    'location': ['venue_name', 'location'],
    'start': ['event_date'],
    'start_time': ['event_time'],
}

events, errors = google_sheets_source.get_events_from_sheets(
    column_mapping=custom_mapping
)
```

## Event Field Reference

### Required Fields (Pipeline will skip rows missing these)

| Field | Format | Notes |
|-------|--------|-------|
| **Title** | String (any length) | Event name/title |
| **Start Date** | MM/DD/YYYY or YYYY-MM-DD | Event start date (time defaults to 00:00) |

### Optional but Recommended

| Field | Format | Notes |
|-------|--------|-------|
| **Location** | String | Venue name or address |
| **Description** | String (multi-line OK) | Event details and description |
| **End Date** | MM/DD/YYYY or YYYY-MM-DD | Defaults to start date if not provided |

### Optional Fields

| Field | Format | Notes |
|-------|--------|-------|
| **Start Time** | HH:MM or HH:MM AM/PM | Defaults to 00:00 if not provided |
| **End Time** | HH:MM or HH:MM AM/PM | Defaults to start time if not provided |
| **URL** | Full URL | Registration, ticketing, or event link |
| **Category/Tags** | String or comma-separated | Event category or tags |
| **Organizer Name** | String | Person/organization submitting |
| **Organizer Email** | Email address | Contact email (appended to description) |

### Date/Time Parsing

The integration accepts multiple date formats:

- `12/31/2025` (MM/DD/YYYY)
- `2025-12-31` (YYYY-MM-DD)
- `December 31, 2025` (Long format)
- `Dec 31, 2025` (Short format)

Times can be:
- `14:30` (24-hour format)
- `2:30 PM` or `2:30 pm` (12-hour format with AM/PM)

All times are converted to ISO 8601 format (`YYYY-MM-DDTHH:MM:SS`) and follow the `SITE_TIMEZONE` env var (default: `America/Chicago`).

## How Events Flow Through the Pipeline

1. **Sheets Fetch**: `get_events_from_sheets()` reads rows and maps to internal event model
2. **Merge with Other Sources**: Combined with scraped Perdido Chamber and Wren Haven events
3. **Normalization**: Applied via `event_normalizer` (shared with all sources)
4. **Classification**: SVM classifier scores for "community event" likelihood
5. **Validation**: Required fields, date ranges, etc. checked
6. **Deduplication**: Duplicate detection (shared across all sources)
7. **Enrichment**: Image assignment, venue linking, tags
8. **Export**: CSV for review and upload to WordPress

Submitted events follow **the same pipeline** as scraped events — no special handling or bypass.

## Testing

Unit tests are located in `tests/test_google_sheets_source.py`:

```bash
# Run all Google Sheets tests
pytest tests/test_google_sheets_source.py

# Run specific test class
pytest tests/test_google_sheets_source.py::TestHeaderNormalization

# Run with coverage
pytest tests/test_google_sheets_source.py --cov=scripts.google_sheets_source
```

**Note:** Tests use mocked Google Sheets API calls — no live API access is required to run tests locally.

## Troubleshooting

### "SHEETS_SPREADSHEET_ID env var not set"

- Ensure you've set the `SHEETS_SPREADSHEET_ID` environment variable
- Check that the sheet ID is correctly extracted from the URL

### "Neither GOOGLE_APPLICATION_CREDENTIALS nor GOOGLE_SHEETS_SA_JSON_B64 env vars set"

- Choose one method (file path or base64) to provide credentials
- If using a file, ensure the path exists and is readable
- If using base64, ensure the encoding is valid

### "Failed to fetch Google Sheet: 403 Forbidden"

- The service account email isn't shared with the sheet
- Go to the sheet, click Share, and give the service account email **Viewer** access
- The service account email is the `client_email` field in the downloaded JSON

### "Could not parse date: '...' with time: '...'"

- Check that dates are in one of the supported formats
- Common issue: dates in locale-specific format not recognized
- Convert to MM/DD/YYYY or YYYY-MM-DD format and retry

### Rows are skipped silently

- Check the logs for warning messages (missing required fields, invalid dates)
- Ensure the first row contains headers
- Ensure rows have a title/event_name and start_date

## Environment Variables Summary

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `SHEETS_SPREADSHEET_ID` | Yes | Google Sheet ID | `1A2B3C4D...xyz` |
| `SHEETS_RANGE` | No | Sheet range in A1 notation | `Form Responses 1!A:Z` |
| `SHEETS_WORKSHEET_NAME` | No | Worksheet name | `Form Responses 1` |
| `GOOGLE_APPLICATION_CREDENTIALS` | One of these | Path to service account JSON file | `/path/to/creds.json` |
| `GOOGLE_SHEETS_SA_JSON_B64` | One of these | Base64-encoded service account JSON | `eyJh...` |
| `SITE_TIMEZONE` | No | Timezone for date conversion | `America/Chicago` (default) |

## Security Best Practices

1. **Never commit credentials to git.** Add to `.gitignore`:
   ```
   service-account.json
   secrets.json
   ```

2. **Use environment variables** instead of hardcoding paths or IDs in code.

3. **Limit service account permissions** — use **Viewer** role on the sheet, not Editor.

4. **Rotate credentials periodically.**

5. **For CI/CD**, use base64-encoded credentials in GitHub Secrets (not in `.env` files).

6. **Log minimal sensitive info** — the code avoids logging credentials or full API responses.

## Example Google Form Setup

To create a form that feeds into the sheet:

1. Create a new Google Form
2. Add form fields matching your column names:
   - Short answer → Event Name
   - Long answer → Description
   - Short answer → Location
   - Date field → Start Date
   - Time field → Start Time
   - etc.
3. Set form responses to go to your Google Sheet
4. Share the form link with community members

Forms automatically append new responses to the sheet in the correct order.

## Contributing

To extend the integration:

- **Custom column names**: Modify `column_mapping` in `map_sheet_row_to_event()`
- **New date formats**: Add patterns to `parse_datetime_flexible()`
- **Advanced filtering**: Modify `map_sheet_row_to_event()` to add validation logic
- **Tests**: Add to `tests/test_google_sheets_source.py`

All changes should maintain backward compatibility with existing pipeline behavior.
