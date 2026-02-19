# Integration Tests

End-to-end and integration tests that validate feature workflows and system interactions.

## Test Files (8)

**Scrapers & Data Collection:**
- `test_wren_haven_scraper.py` — Wren Haven event scraper validation
- `test_perdido_scraper.py` — Perdido event scraper validation
- `test_scraper_error_isolation.py` — Scraper error handling and recovery
- `Envision_Perdido_DataCollection.py` — Full data collection pipeline

**API & External Integrations:**
- `test_google_sheets_source.py` — Google Sheets API integration
- `test_wordpress_uploader.py` — WordPress REST API integration

**Core Features:**
- `test_deduplication.py` — Event deduplication logic and validation
- `test_venue_registry.py` — Venue management and lookup

## Running Integration Tests

```bash
# Run all integration tests
pytest tests/integration/

# Run a specific test file
pytest tests/integration/test_wordpress_uploader.py

# Run a specific test
pytest tests/integration/test_wordpress_uploader.py::test_create_event

# Run with verbose output
pytest tests/integration/ -v

# Run with timeout (integration tests can be slower)
pytest tests/integration/ --timeout=60
```

## Characteristics

Integration tests typically:
- ✅ Test multiple components working together
- ✅ Validate API interactions (with mocks or test servers)
- ✅ Verify end-to-end workflows
- ✅ Use test fixtures and sample data
- ✅ May take longer to run (1-10 seconds each)
- ✅ Test error handling and edge cases

Integration tests often:
- Mock external APIs (don't call real production services)
- Use test databases or in-memory databases
- Validate data transformations across modules
- Test configuration and environment handling

## Mocking External Services

All integration tests mock external services to ensure reliability:

```python
import pytest
from unittest.mock import MagicMock, patch

@patch('scripts.wordpress_uploader.requests.post')
def test_wordpress_upload(mock_post):
    # Mock the WordPress API response
    mock_post.return_value.json.return_value = {'id': 123}
    
    # Test the upload logic
    result = upload_event({'title': 'Test Event'})
    assert result.id == 123
```

## Setup & Fixtures

Integration tests may use:
- Sample data files in `fixtures/`
- Test configuration from `conftest.py`
- Temporary files or databases
- Mocked API responses

## Adding New Integration Tests

When adding a new integration test:
1. Create a test file: `test_feature_name.py`
2. Follow naming: `test_<feature>_<scenario>`
3. Mock external dependencies (don't call real APIs)
4. Use fixtures from `conftest.py`
5. Test both success and error cases
6. Clean up any temporary resources

Example:
```python
import pytest
from unittest.mock import patch, MagicMock
from scripts.my_feature import process_events

@patch('scripts.my_feature.external_api.fetch')
def test_process_events_success(mock_fetch):
    mock_fetch.return_value = [{'id': 1, 'title': 'Event'}]
    
    result = process_events()
    assert len(result) == 1
    assert result[0].title == 'Event'

@patch('scripts.my_feature.external_api.fetch')
def test_process_events_error(mock_fetch):
    mock_fetch.side_effect = ConnectionError('API down')
    
    with pytest.raises(ConnectionError):
        process_events()
```

## Continuous Integration

Integration tests run in CI/CD with:
- Mocked external services
- Test data and fixtures
- Isolated test environment
- Timeout protection
- Detailed failure reporting

See `.github/workflows/` for CI configuration.

## Performance Considerations

Integration tests may run slower. Optimize with:
- Parallel test execution: `pytest -n auto`
- Only mock what's necessary
- Use smaller datasets
- Skip slow tests in local development: `pytest -m "not slow"`
