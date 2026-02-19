"""
Unit tests for Wren Haven Homestead scraper (HTML parsing approach).

All network calls and Playwright interactions are mocked.
"""

import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.wren_haven_scraper import (
    CACHE_DIR,
    WrenHavenScraperError,
    _load_cached_html,
    _parse_events_from_html,
    _save_cached_html,
    get_events,
    normalize_event,
    scrape_wren_haven,
)


class TestNormalizeEvent:
    """Test event normalization."""

    def test_normalize_event_with_all_fields(self):
        """Normalize event with all fields present."""
        raw = {
            "title": "Beach Cleanup",
            "start": "2026-02-15T09:00:00Z",
            "end": "2026-02-15T11:00:00Z",
            "location": "Pensacola Beach",
            "url": "https://example.com/event",
            "description": "Community cleanup",
            "id": "event123",
            "category": "Volunteer",
        }

        result = normalize_event(raw)

        assert result is not None
        assert result["title"] == "Beach Cleanup"
        assert result["location"] == "Pensacola Beach"
        assert result["url"] == "https://example.com/event"
        assert result["description"] == "Community cleanup"
        assert result["source"] == "wren_haven_homestead"

    def test_normalize_event_with_alternate_field_names(self):
        """Normalize event with alternative field names."""
        raw = {
            "name": "Concert",
            "startDate": "2026-03-20T18:00:00Z",
            "endDate": "2026-03-20T20:00:00Z",
            "venue": "The Wharf",
            "link": "https://example.com/concert",
            "summary": "Live music event",
        }

        result = normalize_event(raw)

        assert result is not None
        assert result["title"] == "Concert"
        assert result["location"] == "The Wharf"

    def test_normalize_event_minimal(self):
        """Normalize event with only required field."""
        raw = {"title": "Simple Event"}

        result = normalize_event(raw)

        assert result is not None
        assert result["title"] == "Simple Event"
        assert result["start"] is None
        assert result["location"] is None

    def test_normalize_event_no_title_filtered(self):
        """Event without title is filtered out."""
        raw = {"location": "Some Place", "start": "2026-02-15T09:00:00Z"}

        result = normalize_event(raw)

        assert result is None

    def test_normalize_event_whitespace_trimmed(self):
        """Whitespace is trimmed from title."""
        raw = {"title": "  Event Name  "}

        result = normalize_event(raw)

        assert result is not None
        assert result["title"] == "Event Name"


class TestCaching:
    """Test caching mechanism."""

    def test_cache_save_and_load(self):
        """HTML cache is saved and loaded."""
        test_html = "<html><body>Test</body></html>"

        _save_cached_html(test_html)
        loaded = _load_cached_html(force_refresh=False)

        assert loaded == test_html

        # Clean up
        cache_file = CACHE_DIR / "events.html"
        if cache_file.exists():
            cache_file.unlink()

    def test_cache_ttl_respected(self):
        """Cache is not used if older than TTL."""
        test_html = "<html>Old Cache</html>"

        _save_cached_html(test_html)
        cache_file = CACHE_DIR / "events.html"

        # Set old modification time
        import os
        import time

        old_time = time.time() - (25 * 3600)
        os.utime(cache_file, (old_time, old_time))

        loaded = _load_cached_html(force_refresh=False)

        assert loaded is None

        cache_file.unlink()

    def test_force_refresh_ignores_cache(self):
        """force_refresh=True bypasses cache."""
        test_html = "<html>Cached</html>"

        _save_cached_html(test_html)
        loaded = _load_cached_html(force_refresh=True)

        assert loaded is None

        cache_file = CACHE_DIR / "events.html"
        cache_file.unlink()


class TestHtmlParsing:
    """Test HTML parsing."""

    def test_parse_empty_html(self):
        """Parse empty HTML returns no events."""
        html = "<html></html>"

        result = _parse_events_from_html(html)

        assert result == []

    def test_parse_html_without_widget(self):
        """Parse HTML without events widget returns no events."""
        html = "<html><body><div>No events here</div></body></html>"

        result = _parse_events_from_html(html)

        assert result == []


class TestScrapeWrenHaven:
    """Test main scrape function."""

    @patch("scripts.wren_haven_scraper._fetch_events_html")
    def test_scrape_wren_haven_success(self, mock_fetch):
        """Successful scrape returns normalized events."""
        mock_fetch.return_value = "<html></html>"

        with patch("scripts.wren_haven_scraper._parse_events_from_html") as mock_parse:
            mock_parse.return_value = [
                {"title": "Event 1", "start": "2026-02-15T09:00:00Z", "location": "Place A"}
            ]

            result = scrape_wren_haven()

            assert len(result) == 1
            assert result[0]["title"] == "Event 1"

    @patch("scripts.wren_haven_scraper._fetch_events_html")
    def test_scrape_wren_haven_with_date_filters(self, mock_fetch):
        """Scrape respects date filters."""
        mock_fetch.return_value = "<html></html>"

        with patch("scripts.wren_haven_scraper._parse_events_from_html") as mock_parse:
            mock_parse.return_value = [
                {"title": "Before", "start": "2026-01-15T09:00:00Z"},
                {"title": "During", "start": "2026-02-15T09:00:00Z"},
                {"title": "After", "start": "2026-03-15T09:00:00Z"},
            ]

            start = datetime(2026, 2, 1)
            end = datetime(2026, 2, 28)

            result = scrape_wren_haven(start_date=start, end_date=end)

            assert len(result) == 1
            assert result[0]["title"] == "During"

    @patch("scripts.wren_haven_scraper._fetch_events_html")
    def test_scrape_wren_haven_empty_response(self, mock_fetch):
        """Handle empty response gracefully."""
        mock_fetch.return_value = "<html></html>"

        with patch("scripts.wren_haven_scraper._parse_events_from_html") as mock_parse:
            mock_parse.return_value = []

            result = scrape_wren_haven()

            assert result == []

    @patch("scripts.wren_haven_scraper._fetch_events_html")
    def test_scrape_wren_haven_fetch_error(self, mock_fetch):
        """Handle fetch error gracefully."""
        mock_fetch.side_effect = Exception("Network error")

        with pytest.raises(WrenHavenScraperError):
            scrape_wren_haven()

    @patch("scripts.wren_haven_scraper._fetch_events_html")
    def test_scrape_wren_haven_malformed_event(self, mock_fetch):
        """Skip malformed events."""
        mock_fetch.return_value = "<html></html>"

        with patch("scripts.wren_haven_scraper._parse_events_from_html") as mock_parse:
            mock_parse.return_value = [
                {"title": "Good Event", "start": "2026-02-15T09:00:00Z"},
                {"bad": "event"},
                {"title": "Another Good Event"},
            ]

            result = scrape_wren_haven()

            assert len(result) == 2
            assert result[0]["title"] == "Good Event"
            assert result[1]["title"] == "Another Good Event"


class TestGetEvents:
    """Test pipeline-compatible interface."""

    @patch("scripts.wren_haven_scraper.scrape_wren_haven")
    def test_get_events_default_month(self, mock_scrape):
        """get_events uses current month by default."""
        mock_scrape.return_value = [{"title": "Event", "start": datetime.now()}]

        result = get_events()

        assert len(result) == 1
        mock_scrape.assert_called_once()

    @patch("scripts.wren_haven_scraper.scrape_wren_haven")
    def test_get_events_specific_month(self, mock_scrape):
        """get_events filters by specified month."""
        mock_scrape.return_value = []

        result = get_events(year=2026, month=3)

        call_args = mock_scrape.call_args
        start_date = call_args.kwargs["start_date"]
        end_date = call_args.kwargs["end_date"]

        assert start_date.year == 2026
        assert start_date.month == 3
