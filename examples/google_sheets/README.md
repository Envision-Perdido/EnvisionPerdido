# Google Sheets Integration Examples

Reference implementations for working with Google Sheets in Envision Perdido.

## Files

- `google_sheets_format_example.py` — Shows the expected data format for Google Sheets upload
- `google_sheets_integration_example.py` — Complete working example of Google Sheets integration

## Use Cases

### Data Format Example

Learn the required structure for exporting event data to Google Sheets:
```bash
python google_sheets_format_example.py
```

This example shows:
- Column structure for event data
- Required fields and formats
- Handling of optional fields
- Datetime and timezone representation

### Integration Example

See a full end-to-end example of:
```bash
python google_sheets_integration_example.py
```

This example demonstrates:
- Authentication setup
- Reading from a Google Sheet
- Writing event data
- Error handling and retries
- Batch operations

## Configuration

Both examples require:
- Google Sheets API credentials
- Proper environment variables (set in `.env`)
- A Google Sheet with the correct structure

See main project documentation for Google Sheets setup: [docs/GOOGLE_SHEETS_SETUP.md](../../docs/GOOGLE_SHEETS_SETUP.md)

## Common Patterns

These examples show the recommended patterns for:
- Error handling in API calls
- Rate limiting considerations
- Data validation before upload
- Logging and debugging output
- Working with multiple sheets

Use these as templates when extending Google Sheets integration.
