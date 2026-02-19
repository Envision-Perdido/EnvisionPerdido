# Test Suite

Comprehensive test coverage for the Envision Perdido project.

## Structure

### Root Level (Fixtures & Configuration)

- `conftest.py` — Pytest configuration and shared fixtures
- `fixtures/` — Test data, mock responses, and fixture files

### unit/

Unit tests for individual modules (4 tests):
- `test_logger.py` — Logging utility validation
- `test_tag_taxonomy.py` — Tag taxonomy operations
- `test_rate_limiting.py` — Rate limiting functionality
- `test_event_normalizer.py` — Event data normalization

These tests validate individual components in isolation without external dependencies.

### integration/

Integration and end-to-end tests (8 tests):
- `test_deduplication.py` — Event deduplication logic
- `test_google_sheets_source.py` — Google Sheets integration
- `test_venue_registry.py` — Venue management and registry
- `test_wordpress_uploader.py` — WordPress REST API integration
- `test_wren_haven_scraper.py` — Wren Haven event scraper
- `test_scraper_error_isolation.py` — Error handling in scrapers
- `test_perdido_scraper.py` — Perdido event scraper
- `Envision_Perdido_DataCollection.py` — Full data collection pipeline

These tests validate feature workflows with external systems, databases, or APIs.

## Running Tests

**Run all tests:**
```bash
pytest
```

**Run only unit tests:**
```bash
pytest tests/unit/
```

**Run only integration tests:**
```bash
pytest tests/integration/
```

**Run a specific test file:**
```bash
pytest tests/unit/test_logger.py
```

**Run with verbose output:**
```bash
pytest -v
```

**Run with coverage report:**
```bash
pytest --cov=scripts --cov-report=html
```

## Fixtures & Test Data

Shared test utilities and fixtures are in:
- `conftest.py` — Pytest hooks, session-level fixtures, command-line options
- `fixtures/` — Mock data, sample responses, test datasets

## CI/CD Integration

Tests are automatically run on:
- Pull requests (enabled in `.github/workflows/`)
- Commits to main/dev branches
- Manual workflow dispatch

See `.github/workflows/smoketest.yml` for CI configuration.

## Notes on Test Categories

**Unit tests** are fast, isolated, and can run without:
- Network access
- External APIs or databases
- File I/O (use mocks instead)

**Integration tests** verify:
- Multi-module interactions
- External system integration (with mocks)
- End-to-end workflows
- Large dataset handling

Keep unit tests fast by mocking external dependencies. Use integration tests to verify that components work together correctly.
