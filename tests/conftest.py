"""Pytest configuration and fixtures for all tests."""

import pytest
from scripts.logger import reset_logger


@pytest.fixture(autouse=True)
def cleanup_logger():
    """Cleanup logger after each test to avoid file handle leaks on Windows."""
    yield
    # Cleanup after test
    reset_logger()
