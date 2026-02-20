"""
Unit tests for event deduplication logic.

Tests that duplicate events (same UID) are not created twice.
"""

import unittest
from unittest.mock import Mock

import pandas as pd

from scripts.wordpress_uploader import WordPressEventUploader


class DummyResponse:
    def __init__(self, status_code=200, data=None):
        self.status_code = status_code
        self._data = data or {}

    def json(self):
        return self._data


class DummySession:
    """Mock session that simulates WordPress API."""

    def __init__(self):
        self.post_calls = []
        self.get_calls = []
        self.events_by_uid = {}  # Simulate WordPress storage

    def get(self, url, **kwargs):
        """Mock GET requests."""
        self.get_calls.append((url, kwargs))

        # Simulate /ajde_events query by UID
        if "/ajde_events" in url and "params" in kwargs:
            params = kwargs["params"]
            if params.get("meta_key") == "_event_uid":
                uid = params.get("meta_value")
                if uid in self.events_by_uid:
                    # Return existing event
                    return DummyResponse(200, [{"id": self.events_by_uid[uid]}])

        return DummyResponse(200, [])

    def post(self, url, **kwargs):
        """Mock POST requests."""
        self.post_calls.append((url, kwargs))

        # Simulate event creation
        if "/ajde_events" in url and "json" in kwargs:
            data = kwargs["json"]
            uid = data.get("meta", {}).get("_event_uid")
            if uid:
                event_id = 1000 + len(self.post_calls)
                self.events_by_uid[uid] = event_id
                return DummyResponse(201, {"id": event_id})

        # For other endpoints
        if "/media" in url:
            return DummyResponse(201, {"id": 42})

        return DummyResponse(200, {})


class TestDeduplication(unittest.TestCase):
    """Test deduplication by UID."""

    def setUp(self):
        """Set up test fixtures."""
        self.uploader = WordPressEventUploader("https://example.org", "user", "pass")
        self.uploader.session = DummySession()
        self.uploader.create_or_get_location = Mock(return_value=None)

    def test_get_event_by_uid_exists(self):
        """Test finding existing event by UID."""
        # Add an event to the mock
        self.uploader.session.events_by_uid["test-uid-123"] = 999

        result = self.uploader.get_event_by_uid("test-uid-123")
        self.assertEqual(result, 999)

    def test_get_event_by_uid_not_exists(self):
        """Test UID not found returns None."""
        result = self.uploader.get_event_by_uid("nonexistent-uid")
        self.assertIsNone(result)

    def test_get_event_by_uid_empty_string(self):
        """Test empty UID returns None."""
        result = self.uploader.get_event_by_uid("")
        self.assertIsNone(result)

    def test_create_event_new(self):
        """Test creating a new event (UID not found)."""
        event_row = pd.Series(
            {
                "title": "Test Event",
                "description": "A test event",
                "uid": "new-uid-456",
                "start": "2025-09-15 10:00:00",
                "end": "2025-09-15 11:00:00",
                "location": "Town Hall",
                "url": "http://example.org/event1",
            }
        )

        event_id = self.uploader.create_event(event_row)

        # Should create new event
        self.assertIsNotNone(event_id)
        self.assertGreater(event_id, 1000)

    def test_create_event_duplicate_skipped(self):
        """Test duplicate event is skipped."""
        # Add existing event to mock
        existing_uid = "duplicate-uid-789"
        self.uploader.session.events_by_uid[existing_uid] = 555

        event_row = pd.Series(
            {
                "title": "Test Event",
                "description": "A test event",
                "uid": existing_uid,
                "start": "2025-09-15 10:00:00",
                "end": "2025-09-15 11:00:00",
                "location": "Town Hall",
                "url": "http://example.org/event1",
            }
        )

        event_id = self.uploader.create_event(event_row)

        # Should NOT create; return None
        self.assertIsNone(event_id)

    def test_create_event_stores_uid_in_metadata(self):
        """Test that UID is stored in _event_uid metadata field."""
        event_row = pd.Series(
            {
                "title": "Test Event",
                "description": "A test event",
                "uid": "uid-with-metadata-001",
                "start": "2025-09-15 10:00:00",
                "end": "2025-09-15 11:00:00",
                "location": "Town Hall",
                "url": "http://example.org/event1",
            }
        )

        self.uploader.create_event(event_row)

        # Check that UID was stored
        self.assertIn("uid-with-metadata-001", self.uploader.session.events_by_uid)


class TestIdempotency(unittest.TestCase):
    """Test that pipeline is idempotent (safe to re-run)."""

    def setUp(self):
        """Set up test fixtures."""
        self.uploader = WordPressEventUploader("https://example.org", "user", "pass")
        self.uploader.session = DummySession()
        self.uploader.create_or_get_location = Mock(return_value=None)

    def test_upload_same_event_twice_no_duplicates(self):
        """Test uploading same event twice creates only one."""
        event_row = pd.Series(
            {
                "title": "Unique Event",
                "description": "Only once",
                "uid": "unique-event-123",
                "start": "2025-09-15 10:00:00",
                "end": "2025-09-15 11:00:00",
                "location": "Town Hall",
                "url": "http://example.org/event1",
            }
        )

        # First upload
        first_id = self.uploader.create_event(event_row)
        self.assertIsNotNone(first_id)

        # Second upload (same UID)
        second_id = self.uploader.create_event(event_row)
        self.assertIsNone(second_id)  # Should be skipped

        # Verify only one event was created
        self.assertEqual(
            len(self.uploader.session.events_by_uid),
            1,
            "Should have exactly one event in WordPress",
        )


if __name__ == "__main__":
    unittest.main()
