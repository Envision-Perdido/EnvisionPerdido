# Google Sheets Integration Summary

## Status: ✅ Complete & Production Ready

### Changes Made

#### 1. **New Source Implementation** (`scripts/google_sheets_source.py`)
- Fetches events from a configured Google Sheet
- Implements automatic column mapping to match normalized event headers
- **Normalized column mapping:**
  - `title` → event title
  - `date` → event date (multiple formats: `mm/dd/yyyy`, `mmddyyyy`, `yyyy-mm-dd`)
  - `time` → event time (formats: `h:m a`, `HH:mm`)
  - `location` → event location
  - `description` → event description
  - `latitude` → location latitude
  - `longitude` → location longitude

#### 2. **Enhancements**
- **Retry logic** for JWT token refresh errors (up to 3 attempts with exponential backoff)
- **Graceful fallback** when Google Sheet credentials are missing
- **Structured error handling** with metric tracking
- **Safe defaults** with disabled-by-default activation

#### 3. **Pipeline Integration**
- Modified `scripts/automated_pipeline.py` to support Google Sheets as an optional event source
- **Default behavior:** Google Sheets is disabled (requires `INCLUDE_GOOGLE_SHEETS=true` environment variable)
- Integrated with existing visibility tracking and event classification

### Environment Variables

To enable Google Sheets integration:

```bash
# Set in your environment before running the pipeline
export INCLUDE_GOOGLE_SHEETS=true

# Then run
python scripts/automated_pipeline.py
```

**Required environment variables for Google Sheets:**
- `GOOGLE_SHEETS_CREDENTIALS` — Path to service account JSON credentials file
- `GOOGLE_SHEET_ID` — Google Sheet ID containing events

### How to Use

1. **Create a service account** in Google Cloud Console
2. **Create a Sheet** with the following columns:
   - `title` (required)
   - `date` (required, formats: `mm/dd/yyyy`, `mmddyyyy`, `yyyy-mm-dd`)
   - `time` (optional, formats: `h:m a`, `HH:mm`)
   - `location` (optional)
   - `description` (optional)
   - `latitude` (optional)
   - `longitude` (optional)

3. **Set environment variables:**
   ```bash
   export GOOGLE_SHEETS_CREDENTIALS="/path/to/service_account.json"
   export GOOGLE_SHEET_ID="your_sheet_id_here"
   export INCLUDE_GOOGLE_SHEETS=true
   ```

4. **Run the pipeline:**
   ```bash
   python scripts/automated_pipeline.py
   ```

### Default Behavior

- **Google Sheets is disabled by default** — the pipeline uses only Perdido Chamber and Wren Haven sources
- **No breaking changes** — existing workflows remain unaffected
- **Opt-in integration** — explicitly enable with environment variable

### Error Handling

The implementation includes robust error handling:
- JWT token refresh with exponential backoff (up to 3 retries)
- Missing credentials → graceful skip with warning
- Invalid date formats → logged and excluded from results
- Network errors → retried with backoff, then skipped

### Testing

Test the integration by:
1. Setting credentials and `INCLUDE_GOOGLE_SHEETS=true`
2. Running: `python scripts/automated_pipeline.py`
3. Check `output/logs/` for integration logs
4. Verify events in `output/pipeline/` CSV file

### Limitations

- Requires active Google Cloud service account with Sheets API enabled
- JWT token must be valid in credentials file
- Sheet must be shared with service account email
- Timezone handling follows `SITE_TIMEZONE` environment variable (default: `America/Chicago`)

### Future Improvements

- [ ] Webhook support for real-time Sheet updates
- [ ] Column mapping configuration file
- [ ] Built-in Sheet validation before processing
- [ ] Batch date/time format detection
- [ ] Sheet change tracking for incremental updates

---

**Last Updated:** 2025  
**Integration Status:** Production Ready  
**Deployment Checklist:** ✅ Complete
