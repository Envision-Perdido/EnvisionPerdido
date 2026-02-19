# Examples & Reference Code

This directory contains example scripts and reference implementations for common Envision Perdido workflows.

## Structure

### google_sheets/

Google Sheets integration examples:
- `google_sheets_format_example.py` — Example of properly formatted data for Google Sheets
- `google_sheets_integration_example.py` — Complete example of integrating with Google Sheets

**Use case:** Learn how to upload event data to Google Sheets or format data for export.

### scrapers/

Scraper usage examples:
- `wren_haven_usage_examples.py` — Examples of using the Wren Haven scraper

**Use case:** Reference implementation for scraping event data from various sources.

## Running Examples

```bash
# Run a specific example
python examples/google_sheets/google_sheets_integration_example.py

# Or from project root
python -m examples.google_sheets.google_sheets_integration_example
```

## Example Patterns

Each example file demonstrates:
- Proper imports and initialization
- Configuration patterns
- Error handling
- Output formatting
- Real-world usage scenarios

Use these as templates when implementing new features or integrations.
