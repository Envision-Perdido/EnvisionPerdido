# Google Sheets Integration - Quick Start

The EnvisionPerdido Community Calendar now supports **Google Sheets** as an event submission source!

## What This Means

Community members can submit events via a Google Sheet (or Google Form with responses stored in a sheet), and those events are automatically ingested into the same pipeline as scraped events. The pipeline applies identical normalization, classification, validation, deduplication, and enrichment to all sources.

## Setup (5 minutes)

1. **Read the setup guide:** [`docs/GOOGLE_SHEETS_SETUP.md`](docs/GOOGLE_SHEETS_SETUP.md)
   - Create a Google Cloud service account
   - Create a Google Sheet with event columns
   - Set environment variables

2. **Validate your setup:**
   ```bash
   python scripts/validate_google_sheets_integration.py
   ```

3. **Test (optional):**
   ```bash
   python examples/google_sheets_integration_example.py
   ```

## Enable in Pipeline

To include Google Sheets events in your pipeline run:

```python
from scripts.automated_pipeline import scrape_events

events, errors = scrape_events(
    include_sources=['perdido_chamber', 'google_sheets']
)
```

Or modify `automated_pipeline.py` to add `'google_sheets'` to the default sources.

## How It Works

```
Google Sheet
    ↓
Fetch & Map
    ↓
Internal Event Model
    ↓ [Same pipeline as scraped events]
    ├─ Normalization
    ├─ Classification
    ├─ Validation
    ├─ Deduplication
    ├─ Enrichment
    └─ Export (CSV)
    ↓
WordPress Upload
```

## Key Features

- ✅ **Flexible column names** — `Title`, `Event Name`, `event_title` all work
- ✅ **Multiple date formats** — `12/31/2025`, `2025-12-31`, `December 31, 2025`
- ✅ **Optional time fields** — Defaults to 00:00 if not provided
- ✅ **Organizer tracking** — Appends name/email to event description
- ✅ **Custom mapping** — Override column names with your own
- ✅ **Graceful error handling** — Logs warnings, skips invalid rows
- ✅ **Secure credentials** — Service account, environment variables, no secrets in code

## Files Added

| File | Purpose |
|------|---------|
| `scripts/google_sheets_source.py` | Core Sheets integration module |
| `tests/test_google_sheets_source.py` | 41 comprehensive tests (100% pass) |
| `docs/GOOGLE_SHEETS_SETUP.md` | Complete setup and configuration guide |
| `docs/GOOGLE_SHEETS_IMPLEMENTATION_SUMMARY.md` | Technical implementation details |
| `examples/google_sheets_format_example.py` | Example data formats |
| `examples/google_sheets_integration_example.py` | 5 runnable integration examples |
| `scripts/validate_google_sheets_integration.py` | Validation/verification script |

## Minimal Changes to Existing Code

- Only **18 lines added** to `scripts/automated_pipeline.py`
- **0 breaking changes** to existing functionality
- All existing sources (Perdido Chamber, Wren Haven) work unchanged
- Optional feature — can be ignored if not needed

## Backward Compatible

Default behavior is unchanged. To use Google Sheets, you must explicitly:
1. Set environment variables
2. Add `'google_sheets'` to `include_sources` parameter
3. Or modify pipeline code to include it by default

## Documentation

- 🔧 **Setup:** [`docs/GOOGLE_SHEETS_SETUP.md`](docs/GOOGLE_SHEETS_SETUP.md)
- 📋 **Implementation:** [`docs/GOOGLE_SHEETS_IMPLEMENTATION_SUMMARY.md`](docs/GOOGLE_SHEETS_IMPLEMENTATION_SUMMARY.md)
- 💡 **Examples:** [`examples/google_sheets_integration_example.py`](examples/google_sheets_integration_example.py)
- 🧪 **Tests:** `pytest tests/test_google_sheets_source.py`

## Support

If you encounter issues:

1. Run validation script: `python scripts/validate_google_sheets_integration.py`
2. Check environment variables are set: `echo $SHEETS_SPREADSHEET_ID`
3. Review troubleshooting section in [`docs/GOOGLE_SHEETS_SETUP.md`](docs/GOOGLE_SHEETS_SETUP.md)
4. Check logs for detailed error messages

## Next Steps

1. Read [`docs/GOOGLE_SHEETS_SETUP.md`](docs/GOOGLE_SHEETS_SETUP.md)
2. Create your Google Sheet with event columns
3. Set environment variables
4. Run `python scripts/validate_google_sheets_integration.py`
5. Run pipeline with `include_sources=['google_sheets']`

---

**Status:** ✅ Production-ready. Thoroughly tested and documented.
