"""
Tests for Wren Haven Homestead scraper.

Uses fixtures and mocking to avoid live network requests.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

# Import the scraper module
sys.path.insert(0, str(Path(__file__).resolve().parent))

from scripts.wren_haven_scraper import (
    normalize_event,
    scrape_wren_haven,
    _prepare_request_headers,
    WrenHavenScraperError
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def sample_wren_haven_api_response():
    """Sample JSON response from Wren Haven API."""
    return [
        {
            "id": "wh-001",
            "title": "Spring Garden Workshop",
            "startDate": "2025-03-15T10:00:00",
            "endDate": "2025-03-15T12:00:00",
            "location": "Wren Haven Farm, Alabama",
            "link": "https://www.wrenhavenhomestead.com/events/spring-garden",
            "summary": "Learn about spring gardening techniques",
            "type": "Workshop"
        },
        {
            "id": "wh-002",
            "title": "Homesteading Basics Class",
            "startDate": "2025-04-05T14:00:00",
            "endDate": "2025-04-05T16:00:00",
            "location": "Wren Haven Facility",
            "link": "https://www.wrenhavenhomestead.com/events/homesteading-basics",
            "description": "Everything you need to know to get started with homesteading",
            "type": "Class"
        }
    ]


@pytest.fixture
def bootstrap_artifacts():
    """Sample bootstrap artifacts from Playwright discovery."""
    return {
        'endpoint': 'https://api.wrenhavenhomestead.com/v1/events',
        'method': 'GET',
        'headers': {
            'Authorization': 'Bearer test_token_12345',
            'Content-Type': 'application/json'
        },
        'cookies': [
            {'name': 'session_id', 'value': 'abc123def456', 'domain': '.wrenhavenhomestead.com'}
        ],
        'query_params': {},
        'discovered_at': '2025-01-14T12:00:00'
    }


# ============================================================================
# NORMALIZATION TESTS
# ============================================================================

def test_normalize_event_with_all_fields():
    """Test normalizing an event with all expected fields."""
    raw = {
        "id": "wh-001",
        "title": "Spring Garden Workshop",
        "startDate": "2025-03-15T10:00:00",
        "endDate": "2025-03-15T12:00:00",
        "location": "Wren Haven Farm",
        "link": "https://example.com/event",
        "summary": "A fun workshop",
        "type": "Workshop"
    }
    
    event = normalize_event(raw)
    
    assert event['title'] == "Spring Garden Workshop"
    assert event['start'] == "2025-03-15T10:00:00"
    assert event['end'] == "2025-03-15T12:00:00"
    assert event['location'] == "Wren Haven Farm"
    assert event['url'] == "https://example.com/event"
    assert event['description'] == "A fun workshop"
    assert event['category'] == "Workshop"
    assert event['uid'] == "wh-001"
    assert event['_raw_source'] == 'wren_haven_homestead'


def test_normalize_event_with_alternate_field_names():
    """Test normalizing when API uses alternate field names."""
    raw = {
        "id": "event-123",
        "name": "Homesteading Basics",
        "begin": "2025-04-05T14:00:00",
        "finish": "2025-04-05T16:00:00",
        "venue": "Wren Haven Facility",
        "description": "Learn homesteading"
    }
    
    event = normalize_event(raw)
    
    assert event['title'] == "Homesteading Basics"
    assert event['start'] == "2025-04-05T14:00:00"
    assert event['end'] == "2025-04-05T16:00:00"
    assert event['location'] == "Wren Haven Facility"


def test_normalize_event_minimal():
    """Test normalizing an event with only required fields."""
    raw = {
        "id": "min-001",
        "title": "Minimal Event"
    }
    
    event = normalize_event(raw)
    
    assert event['title'] == "Minimal Event"
    assert event['uid'] == "min-001"
    assert event['start'] is None
    assert event['location'] is None


def test_normalize_event_no_title_filtered():
    """Scraper should skip events without titles."""
    raw = {
        "id": "no-title",
        "start": "2025-05-01",
    }
    
    # This would be filtered by scrape_wren_haven, but normalize itself doesn't
    event = normalize_event(raw)
    assert event['title'] == ''


# ============================================================================
# REQUEST HEADER TESTS
# ============================================================================

def test_prepare_request_headers_merges_auth(bootstrap_artifacts):
    """Test that prepared headers include auth from bootstrap artifacts."""
    headers = _prepare_request_headers(bootstrap_artifacts)
    
    assert 'Authorization' in headers
    assert headers['Authorization'] == 'Bearer test_token_12345'
    assert 'Content-Type' in headers
    assert headers['Content-Type'] == 'application/json'


def test_prepare_request_headers_keeps_user_agent(bootstrap_artifacts):
    """Test that User-Agent is preserved."""
    headers = _prepare_request_headers(bootstrap_artifacts)
    
    assert 'User-Agent' in headers
    assert 'Mozilla' in headers['User-Agent']


def test_prepare_request_headers_empty_artifacts():
    """Test with minimal/empty bootstrap artifacts."""
    artifacts = {'headers': {}}
    headers = _prepare_request_headers(artifacts)
    
    assert 'User-Agent' in headers  # Default should be present
    assert headers is not None


# ============================================================================
# SCRAPER INTEGRATION TESTS (MOCKED)
# ============================================================================

@patch('scripts.wren_haven_scraper._fetch_events_from_api')
@patch('scripts.wren_haven_scraper._bootstrap_or_use_cached')
def test_scrape_wren_haven_success(mock_bootstrap, mock_fetch, sample_wren_haven_api_response, bootstrap_artifacts):
    """Test successful scraping with mocked network calls."""
    mock_bootstrap.return_value = bootstrap_artifacts
    mock_fetch.return_value = sample_wren_haven_api_response
    
    events = scrape_wren_haven()
    
    assert len(events) == 2
    assert events[0]['title'] == "Spring Garden Workshop"
    assert events[1]['title'] == "Homesteading Basics Class"
    assert all(e['_raw_source'] == 'wren_haven_homestead' for e in events)


@patch('scripts.wren_haven_scraper._fetch_events_from_api')
@patch('scripts.wren_haven_scraper._bootstrap_or_use_cached')
def test_scrape_wren_haven_with_date_filters(mock_bootstrap, mock_fetch, sample_wren_haven_api_response, bootstrap_artifacts):
    """Test scraping with date filters."""
    mock_bootstrap.return_value = bootstrap_artifacts
    mock_fetch.return_value = sample_wren_haven_api_response
    
    events = scrape_wren_haven(
        start_date='2025-03-01',
        end_date='2025-04-30'
    )
    
    mock_fetch.assert_called_once()
    call_args = mock_fetch.call_args
    assert call_args.kwargs['start_date'] == '2025-03-01'
    assert call_args.kwargs['end_date'] == '2025-04-30'
    assert len(events) == 2


@patch('scripts.wren_haven_scraper._fetch_events_from_api')
@patch('scripts.wren_haven_scraper._bootstrap_or_use_cached')
def test_scrape_wren_haven_empty_response(mock_bootstrap, mock_fetch, bootstrap_artifacts):
    """Test scraping when API returns no events."""
    mock_bootstrap.return_value = bootstrap_artifacts
    mock_fetch.return_value = []
    
    events = scrape_wren_haven()
    
    assert len(events) == 0


@patch('scripts.wren_haven_scraper._fetch_events_from_api')
@patch('scripts.wren_haven_scraper._bootstrap_or_use_cached')
def test_scrape_wren_haven_bootstrap_error(mock_bootstrap, mock_fetch):
    """Test graceful handling of bootstrap failure."""
    mock_bootstrap.side_effect = WrenHavenScraperError("Bootstrap failed")
    
    events = scrape_wren_haven()
    
    # Should return empty list, not raise
    assert events == []


@patch('scripts.wren_haven_scraper._fetch_events_from_api')
@patch('scripts.wren_haven_scraper._bootstrap_or_use_cached')
def test_scrape_wren_haven_malformed_event(mock_bootstrap, mock_fetch, bootstrap_artifacts):
    """Test handling of malformed events in API response."""
    mock_bootstrap.return_value = bootstrap_artifacts
    
    # Mix of good and bad events
    mixed_response = [
        {"id": "good-1", "title": "Good Event"},
        {"id": "bad-1"},  # Missing title - should be filtered
        {"id": "good-2", "title": "Another Event"}
    ]
    mock_fetch.return_value = mixed_response
    
    events = scrape_wren_haven()
    
    # Should only get events with titles
    assert len(events) == 2
    assert all(e['title'] for e in events)


# ============================================================================
# CACHING TESTS
# ============================================================================

@patch('scripts.wren_haven_scraper._load_cached_artifacts')
@patch('scripts.wren_haven_scraper.bootstrap_json_api')
@patch('scripts.wren_haven_scraper._fetch_events_from_api')
def test_scrape_uses_cache_on_first_call(mock_fetch, mock_bootstrap_fn, mock_load_cache, sample_wren_haven_api_response):
    """Test that second call reuses cached artifacts."""
    mock_artifacts = {'endpoint': 'https://api.example.com/events', 'method': 'GET', 'headers': {}}
    mock_load_cache.return_value = mock_artifacts
    mock_fetch.return_value = sample_wren_haven_api_response
    
    # First call should use cache
    scrape_wren_haven()
    
    # Playwright bootstrap function should not be called
    mock_bootstrap_fn.assert_not_called()
    mock_load_cache.assert_called_once()


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

@patch('scripts.wren_haven_scraper._fetch_events_from_api')
@patch('scripts.wren_haven_scraper._bootstrap_or_use_cached')
def test_scrape_wren_haven_network_error(mock_bootstrap, mock_fetch):
    """Test handling of network errors during fetch."""
    mock_bootstrap.return_value = {'endpoint': 'https://api.example.com/events', 'method': 'GET', 'headers': {}}
    mock_fetch.side_effect = WrenHavenScraperError("Connection timeout")
    
    events = scrape_wren_haven()
    
    assert events == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
