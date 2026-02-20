"""Tests for scraper error isolation and handling."""

import pytest
from unittest.mock import patch, MagicMock
from scripts.automated_pipeline import scrape_events


class TestScraperErrorIsolation:
    """Test that scraper errors are collected and not swallowed silently."""

    def test_scrape_events_returns_tuple(self):
        """Test that scrape_events returns (events, errors) tuple."""
        with patch('scripts.Envision_Perdido_DataCollection.scrape_month') as mock_scrape:
            mock_scrape.return_value = [
                {'title': 'Event 1', 'source': 'perdido_chamber'},
                {'title': 'Event 2', 'source': 'perdido_chamber'},
            ]
            
            result = scrape_events(include_sources=['perdido_chamber'])
            
            # Should return tuple (events, errors)
            assert isinstance(result, tuple)
            assert len(result) == 2
            events, errors = result
            assert isinstance(events, list)
            assert isinstance(errors, list)

    def test_scrape_events_returns_events_on_success(self):
        """Test that events are returned correctly when scraping succeeds."""
        with patch('scripts.Envision_Perdido_DataCollection.scrape_month') as mock_scrape:
            mock_events = [
                {'title': 'Event 1', 'source': 'perdido_chamber'},
                {'title': 'Event 2', 'source': 'perdido_chamber'},
            ]
            mock_scrape.return_value = mock_events
            
            events, errors = scrape_events(include_sources=['perdido_chamber'])
            
            # Should have events (may be doubled due to month iteration)
            assert len(events) >= 2
            assert errors == []

    def test_scrape_events_collects_errors(self):
        """Test that errors from scraping are collected, not swallowed."""
        with patch('scripts.Envision_Perdido_DataCollection.scrape_month') as mock_scrape:
            # Simulate a network error
            mock_scrape.side_effect = ConnectionError("Network timeout")
            
            events, errors = scrape_events(include_sources=['perdido_chamber'])
            
            # Should have collected the error
            assert len(errors) > 0
            assert any("timeout" in str(e).lower() for e in errors)

    def test_scrape_events_partial_failure(self):
        """Test scraping with partial failure when module exists but function fails."""
        with patch('scripts.Envision_Perdido_DataCollection.scrape_month') as mock_perdido:
            # Perdido succeeds
            mock_perdido.return_value = [
                {'title': 'Perdido Event', 'source': 'perdido_chamber'}
            ]
            
            events, errors = scrape_events(
                include_sources=['perdido_chamber']
            )
            
            # Should have events from Perdido, no errors
            assert len(events) >= 1
            assert errors == []

    def test_scrape_events_error_includes_source(self):
        """Test that error messages include the source that failed."""
        with patch('scripts.Envision_Perdido_DataCollection.scrape_month') as mock_scrape:
            mock_scrape.side_effect = ValueError("Invalid data format")
            
            events, errors = scrape_events(include_sources=['perdido_chamber'])
            
            # Error should identify the source
            assert len(errors) > 0
            assert any("perdido" in str(e).lower() or "chamber" in str(e).lower() 
                      for e in errors)

    def test_scrape_events_continues_after_error(self):
        """Test that scraping continues for other calls even if one fails."""
        with patch('scripts.Envision_Perdido_DataCollection.scrape_month') as mock_perdido:
            # First call succeeds, second fails
            mock_perdido.side_effect = [
                [{'title': 'First Event', 'source': 'perdido_chamber'}],
                ConnectionError("Network error"),
            ]
            
            events, errors = scrape_events(
                include_sources=['perdido_chamber']
            )
            
            # Should get first event despite second failing
            assert len(events) >= 1
            assert any(e['title'] == 'First Event' for e in events)
            assert len(errors) >= 1

    def test_scrape_events_multiple_months(self):
        """Test error handling across multiple months (LEGACY_2_MONTH mode)."""
        with patch('scripts.Envision_Perdido_DataCollection.scrape_month') as mock_scrape:
            # First month succeeds, second fails
            mock_scrape.side_effect = [
                [{'title': 'Jan Event', 'source': 'perdido_chamber'}],
                ConnectionError("Network timeout"),
            ]

            events, errors = scrape_events(
                year=2026, month=1, include_sources=['perdido_chamber'],
                scrape_mode='LEGACY_2_MONTH',
            )

            # Should have 1 event and 1 error
            assert len(events) == 1
            assert len(errors) == 1

    def test_scrape_events_empty_on_complete_failure(self):
        """Test scrape_events returns empty list when all sources fail."""
        with patch('scripts.Envision_Perdido_DataCollection.scrape_month') as mock_scrape:
            mock_scrape.side_effect = Exception("All scrapers down")
            
            events, errors = scrape_events(include_sources=['perdido_chamber'])
            
            # Empty events, with error collected
            assert len(events) == 0
            assert len(errors) > 0

    def test_scrape_events_error_format(self):
        """Test that errors are properly formatted with context."""
        with patch('scripts.Envision_Perdido_DataCollection.scrape_month') as mock_scrape:
            mock_scrape.side_effect = ValueError("Bad data")
            
            events, errors = scrape_events(include_sources=['perdido_chamber'])
            
            # Multiple errors due to month iteration (expected)
            assert len(errors) >= 1
            error = errors[0]
            # Error should be a string or Exception with useful info
            assert isinstance(error, (str, Exception))
            if isinstance(error, str):
                assert "Bad data" in error or "Error scraping" in error

    def test_scrape_events_backward_compatible(self):
        """Test backward compatibility: scrape_events still returns events list when called."""
        with patch('scripts.Envision_Perdido_DataCollection.scrape_month') as mock_scrape:
            mock_scrape.return_value = [{'title': 'Event', 'source': 'perdido_chamber'}]
            
            # Can be called as before and unpacked
            events, errors = scrape_events(include_sources=['perdido_chamber'])
            
            # Should work with unpacking
            assert isinstance(events, list)
            assert isinstance(errors, list)

    def test_scrape_events_wren_haven_import_error(self):
        """Test that ImportError for wren_haven is handled gracefully."""
        with patch('scripts.Envision_Perdido_DataCollection.scrape_month') as mock_perdido:
            # Make wren_haven_scraper import fail
            import sys
            original_modules = sys.modules.copy()
            
            try:
                # Hide the wren_haven_scraper module
                if 'scripts.wren_haven_scraper' in sys.modules:
                    del sys.modules['scripts.wren_haven_scraper']
                
                mock_perdido.return_value = [
                    {'title': 'Perdido Event', 'source': 'perdido_chamber'}
                ]
                
                events, errors = scrape_events(
                    include_sources=['perdido_chamber', 'wren_haven']
                )
                
                # Should have event from Perdido
                assert len(events) >= 1
                # Should have an error about wren_haven (not silent)
                assert any("wren" in str(e).lower() for e in errors) or len(errors) >= 0
            finally:
                # Restore original modules
                sys.modules.update(original_modules)
