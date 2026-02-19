# Unit Tests

Fast, isolated tests for individual modules and functions.

## Test Files (4)

- `test_logger.py` — Logging functionality and output formatting
- `test_tag_taxonomy.py` — Tag system operations and validation
- `test_rate_limiting.py` — Request rate limiting mechanisms
- `test_event_normalizer.py` — Event data normalization and cleaning

## Running Unit Tests

```bash
# Run all unit tests
pytest tests/unit/

# Run a specific test file
pytest tests/unit/test_logger.py

# Run a specific test
pytest tests/unit/test_logger.py::test_log_format

# Run with verbose output
pytest tests/unit/ -v

# Run with coverage
pytest tests/unit/ --cov=scripts/logger
```

## Characteristics

Unit tests should:
- ✅ Test a single function or method in isolation
- ✅ Mock external dependencies (files, APIs, databases)
- ✅ Run quickly (typically < 100ms each)
- ✅ Be deterministic (same result every run)
- ✅ Have clear, descriptive test names

Unit tests should NOT:
- ❌ Make network requests
- ❌ Hit real databases or APIs
- ❌ Create files or perform I/O
- ❌ Test multiple modules together (use integration tests)
- ❌ Depend on external services or configuration

## Fixtures & Mocking

Use `conftest.py` for shared fixtures:
```python
# In conftest.py
@pytest.fixture
def mock_logger():
    return MagicMock(spec=Logger)

# In test file
def test_with_mock(mock_logger):
    assert mock_logger is not None
```

## Adding New Unit Tests

When adding a new test:
1. Create a test file: `test_module_name.py`
2. Follow existing naming conventions
3. Use descriptive test function names: `test_<feature>_<scenario>`
4. Mock external dependencies
5. Keep tests isolated and fast

Example:
```python
import pytest
from unittest.mock import MagicMock
from scripts.module_name import function_to_test

def test_function_normal_case():
    result = function_to_test("input")
    assert result == "expected_output"

def test_function_error_case():
    with pytest.raises(ValueError):
        function_to_test(None)
```

## Coverage Goals

Current test coverage targets:
- Core utilities: 90%+
- Data processing: 85%+
- Helper functions: 80%+

View coverage report:
```bash
pytest tests/unit/ --cov=scripts --cov-report=html
open htmlcov/index.html
```
