"""
Tests for Google Sheets Event Source Integration

Tests cover:
- Header normalization
- Row-to-dict conversion
- Date/time parsing with multiple formats
- Sheet row mapping to internal event model
- Integration with pipeline (mocked API calls)
- Error handling and edge cases
"""

import unittest
from unittest.mock import patch, MagicMock, Mock
from datetime import datetime
import json
import base64
import tempfile
import os
from pathlib import Path

from scripts import google_sheets_source


class TestHeaderNormalization(unittest.TestCase):
    """Test header normalization for sheet columns."""
    
    def test_normalize_basic(self):
        """Test basic header normalization."""
        assert google_sheets_source.normalize_header("Event Name") == "event_name"
        assert google_sheets_source.normalize_header("Start Date") == "start_date"
        assert google_sheets_source.normalize_header("Location") == "location"
    
    def test_normalize_whitespace(self):
        """Test normalization of extra whitespace."""
        assert google_sheets_source.normalize_header("  Event Title  ") == "event_title"
    
    def test_normalize_special_chars(self):
        """Test normalization of special characters."""
        assert google_sheets_source.normalize_header("Event-Name") == "event_name"
        assert google_sheets_source.normalize_header("Start - Date") == "start___date"
    
    def test_normalize_case(self):
        """Test case conversion."""
        assert google_sheets_source.normalize_header("EVENT NAME") == "event_name"
        assert google_sheets_source.normalize_header("EventName") == "eventname"


class TestRowsToDicts(unittest.TestCase):
    """Test conversion of sheet rows to dictionaries."""
    
    def test_basic_conversion(self):
        """Test basic row-to-dict conversion."""
        rows = [
            ["Event Name", "Location", "Start Date"],
            ["Meeting", "Library", "12/31/2025"]
        ]
        
        result = google_sheets_source.rows_to_dicts(rows)
        
        assert len(result) == 1
        assert result[0]['event_name'] == "Meeting"
        assert result[0]['location'] == "Library"
        assert result[0]['start_date'] == "12/31/2025"
    
    def test_multiple_rows(self):
        """Test conversion of multiple rows."""
        rows = [
            ["Title", "Location"],
            ["Event 1", "Venue 1"],
            ["Event 2", "Venue 2"],
            ["Event 3", "Venue 3"]
        ]
        
        result = google_sheets_source.rows_to_dicts(rows)
        assert len(result) == 3
    
    def test_padded_rows(self):
        """Test rows with fewer columns than header."""
        rows = [
            ["Title", "Location", "Date"],
            ["Event A", "Venue A"]  # Missing last column
        ]
        
        result = google_sheets_source.rows_to_dicts(rows)
        assert len(result) == 1
        assert result[0]['date'] == ""  # Should be empty string
    
    def test_whitespace_stripping(self):
        """Test whitespace stripping in values."""
        rows = [
            ["Title", "Location"],
            ["  Event  ", "  Venue  "]
        ]
        
        result = google_sheets_source.rows_to_dicts(rows)
        assert result[0]['title'] == "Event"
        assert result[0]['location'] == "Venue"
    
    def test_no_rows_error(self):
        """Test error when no rows provided."""
        with self.assertRaises(ValueError):
            google_sheets_source.rows_to_dicts([])
    
    def test_header_only_warning(self):
        """Test warning when only header row present."""
        rows = [["Title", "Location"]]
        result = google_sheets_source.rows_to_dicts(rows)
        assert len(result) == 0


class TestDateTimeParsing(unittest.TestCase):
    """Test flexible date/time parsing."""
    
    def test_parse_mdy_with_time_12h(self):
        """Test MM/DD/YYYY with 12-hour time."""
        result = google_sheets_source.parse_datetime_flexible(
            "12/31/2025", "2:30 PM"
        )
        assert result == "2025-12-31T14:30:00"
    
    def test_parse_mdy_with_time_24h(self):
        """Test MM/DD/YYYY with 24-hour time."""
        result = google_sheets_source.parse_datetime_flexible(
            "12/31/2025", "14:30"
        )
        assert result == "2025-12-31T14:30:00"
    
    def test_parse_mdy_date_only(self):
        """Test MM/DD/YYYY date only."""
        result = google_sheets_source.parse_datetime_flexible("12/31/2025")
        assert result == "2025-12-31T00:00:00"
    
    def test_parse_iso_format(self):
        """Test ISO format parsing."""
        result = google_sheets_source.parse_datetime_flexible("2025-12-31")
        assert result == "2025-12-31T00:00:00"
    
    def test_parse_long_format(self):
        """Test long date format."""
        result = google_sheets_source.parse_datetime_flexible("December 31, 2025")
        assert result == "2025-12-31T00:00:00"
    
    def test_parse_short_month_format(self):
        """Test short month format."""
        result = google_sheets_source.parse_datetime_flexible("Dec 31, 2025")
        assert result == "2025-12-31T00:00:00"
    
    def test_parse_combined_string(self):
        """Test parsing with combined date/time string."""
        result = google_sheets_source.parse_datetime_flexible("12/31/2025 2:30 PM")
        assert result == "2025-12-31T14:30:00"
    
    def test_parse_invalid_returns_none(self):
        """Test that invalid date returns None."""
        result = google_sheets_source.parse_datetime_flexible("invalid-date")
        assert result is None
    
    def test_parse_none_returns_none(self):
        """Test that None input returns None."""
        result = google_sheets_source.parse_datetime_flexible(None)
        assert result is None
    
    def test_parse_empty_string_returns_none(self):
        """Test that empty string returns None."""
        result = google_sheets_source.parse_datetime_flexible("")
        assert result is None


class TestSheetRowToEventMapping(unittest.TestCase):
    """Test mapping of sheet rows to internal event model."""
    
    def test_minimal_event(self):
        """Test mapping with minimal required fields."""
        row = {
            'title': 'Community Picnic',
            'start_date': '12/31/2025',
        }
        
        event = google_sheets_source.map_sheet_row_to_event(row, row_number=2)
        
        assert event is not None
        assert event['title'] == 'Community Picnic'
        assert event['start'] == '2025-12-31T00:00:00'
        assert event['source'] == 'google_sheets'
        assert event['source_id'] == 'sheet_row_2'
    
    def test_full_event(self):
        """Test mapping with all fields."""
        row = {
            'title': 'Concert',
            'description': 'Live music event',
            'location': 'Central Park',
            'start_date': '06/15/2025',
            'start_time': '7:00 PM',
            'end_date': '06/15/2025',
            'end_time': '10:00 PM',
            'url': 'https://example.com/concert',
            'category': 'Music',
            'organizer_name': 'John Doe',
            'organizer_email': 'john@example.com',
        }
        
        event = google_sheets_source.map_sheet_row_to_event(row, row_number=3)
        
        assert event is not None
        assert event['title'] == 'Concert'
        assert event['description'] == 'Live music event | Organizer: John Doe | Contact: john@example.com'
        assert event['location'] == 'Central Park'
        assert event['start'] == '2025-06-15T19:00:00'
        assert event['end'] == '2025-06-15T22:00:00'
        assert event['url'] == 'https://example.com/concert'
        assert event['category'] == ['Music']
    
    def test_missing_title_returns_none(self):
        """Test that missing title returns None."""
        row = {
            'description': 'Some event',
            'start_date': '12/31/2025',
        }
        
        event = google_sheets_source.map_sheet_row_to_event(row, row_number=2)
        assert event is None
    
    def test_invalid_date_returns_none(self):
        """Test that invalid start date returns None."""
        row = {
            'title': 'Event',
            'start_date': 'invalid',
        }
        
        event = google_sheets_source.map_sheet_row_to_event(row, row_number=2)
        assert event is None
    
    def test_default_end_to_start(self):
        """Test that missing end date defaults to start date."""
        row = {
            'title': 'Event',
            'start_date': '12/31/2025',
        }
        
        event = google_sheets_source.map_sheet_row_to_event(row, row_number=2)
        assert event['end'] == event['start']
    
    def test_custom_column_mapping(self):
        """Test custom column mapping."""
        row = {
            'event': 'Workshop',
            'info': 'Learn new skills',
            'venue': 'Community Center',
            'date': '12/31/2025',
        }
        
        mapping = {
            'title': ['event'],
            'description': ['info'],
            'location': ['venue'],
            'start': ['date'],
        }
        
        event = google_sheets_source.map_sheet_row_to_event(
            row, row_number=2, column_mapping=mapping
        )
        
        assert event is not None
        assert event['title'] == 'Workshop'
        assert event['description'] == 'Learn new skills'
        assert event['location'] == 'Community Center'
    
    def test_column_fallback_chain(self):
        """Test column mapping fallback chain."""
        row = {
            'event_name': 'Presentation',
            'start_date': '12/31/2025',
        }
        
        # Default mapping should try 'title' then 'event_name'
        event = google_sheets_source.map_sheet_row_to_event(row, row_number=2)
        
        assert event is not None
        assert event['title'] == 'Presentation'
    
    def test_organizer_info_appended_to_description(self):
        """Test that organizer info is appended to description."""
        row = {
            'title': 'Event',
            'description': 'Main description',
            'start_date': '12/31/2025',
            'organizer_name': 'Jane Smith',
        }
        
        event = google_sheets_source.map_sheet_row_to_event(row, row_number=2)
        
        assert 'Organizer: Jane Smith' in event['description']
        assert 'Main description' in event['description']


class TestGetSheetsConfig(unittest.TestCase):
    """Test configuration loading from environment variables."""
    
    @patch.dict(os.environ, {
        'SHEETS_SPREADSHEET_ID': 'test-id-123',
        'SHEETS_RANGE': 'Sheet1!A:Z',
        'GOOGLE_APPLICATION_CREDENTIALS': '/path/to/creds.json'
    })
    def test_load_config_from_env(self):
        """Test loading configuration from environment."""
        config = google_sheets_source.get_sheets_config()
        
        assert config['spreadsheet_id'] == 'test-id-123'
        assert config['range'] == 'Sheet1!A:Z'
        assert config['credentials_path'] == '/path/to/creds.json'
    
    @patch.dict(os.environ, {}, clear=True)
    def test_default_range(self):
        """Test default range value."""
        config = google_sheets_source.get_sheets_config()
        assert config['range'] == 'Form Responses 1!A:Z'


class TestLoadServiceAccountCredentials(unittest.TestCase):
    """Test service account credential loading."""
    
    def test_load_from_file(self):
        """Test loading credentials from file."""
        cred_data = {'type': 'service_account', 'project_id': 'test'}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(cred_data, f)
            temp_path = f.name
        
        try:
            result = google_sheets_source.load_service_account_credentials(
                credentials_path=temp_path
            )
            assert result['project_id'] == 'test'
        finally:
            os.unlink(temp_path)
    
    def test_load_from_base64(self):
        """Test loading credentials from base64-encoded JSON."""
        cred_data = {'type': 'service_account', 'project_id': 'test'}
        cred_json = json.dumps(cred_data)
        cred_b64 = base64.b64encode(cred_json.encode()).decode()
        
        result = google_sheets_source.load_service_account_credentials(
            credentials_b64=cred_b64
        )
        
        assert result['project_id'] == 'test'
    
    def test_file_not_found_error(self):
        """Test error when credentials file not found."""
        with self.assertRaises(FileNotFoundError):
            google_sheets_source.load_service_account_credentials(
                credentials_path='/nonexistent/path.json'
            )
    
    def test_both_credentials_error(self):
        """Test error when both credentials sources provided."""
        with self.assertRaises(ValueError):
            google_sheets_source.load_service_account_credentials(
                credentials_path='/path/to/creds.json',
                credentials_b64='base64data'
            )
    
    def test_invalid_base64_error(self):
        """Test error when base64 decoding fails."""
        with self.assertRaises(ValueError):
            google_sheets_source.load_service_account_credentials(
                credentials_b64='not-valid-base64!!!'
            )


class TestGetEventsFromSheets(unittest.TestCase):
    """Test main entry point for fetching events from Google Sheets."""
    
    @patch.dict(os.environ, {}, clear=True)
    def test_missing_spreadsheet_id(self):
        """Test error when SHEETS_SPREADSHEET_ID not set."""
        events, errors = google_sheets_source.get_events_from_sheets()
        
        assert events == []
        assert len(errors) > 0
        assert 'SHEETS_SPREADSHEET_ID' in errors[0]
    
    @patch.dict(os.environ, {'SHEETS_SPREADSHEET_ID': 'test-id'}, clear=True)
    def test_missing_credentials(self):
        """Test error when credentials not provided."""
        events, errors = google_sheets_source.get_events_from_sheets()
        
        assert events == []
        assert len(errors) > 0
        assert 'credential' in errors[0].lower()
    
    @patch.dict(os.environ, {
        'SHEETS_SPREADSHEET_ID': 'test-id',
        'GOOGLE_APPLICATION_CREDENTIALS': '/path/to/creds.json'
    })
    def test_dry_run(self):
        """Test dry run mode."""
        events, errors = google_sheets_source.get_events_from_sheets(dry_run=True)
        
        assert events == []
        assert errors == []
    
    @patch('scripts.google_sheets_source.fetch_sheet_rows')
    @patch('scripts.google_sheets_source.load_service_account_credentials')
    @patch.dict(os.environ, {
        'SHEETS_SPREADSHEET_ID': 'test-id',
        'GOOGLE_APPLICATION_CREDENTIALS': '/path/to/creds.json'
    })
    def test_successful_fetch(self, mock_load_creds, mock_fetch_rows):
        """Test successful event fetching."""
        # Mock credentials
        mock_load_creds.return_value = {'type': 'service_account'}
        
        # Mock sheet rows
        mock_fetch_rows.return_value = [
            ['Title', 'Location', 'Start Date'],
            ['Concert', 'Park', '12/31/2025'],
            ['Meeting', 'Library', '01/15/2026'],
        ]
        
        events, errors = google_sheets_source.get_events_from_sheets()
        
        assert len(events) == 2
        assert events[0]['title'] == 'Concert'
        assert events[1]['title'] == 'Meeting'
        assert len(errors) == 0
    
    @patch('scripts.google_sheets_source.fetch_sheet_rows')
    @patch('scripts.google_sheets_source.load_service_account_credentials')
    @patch.dict(os.environ, {
        'SHEETS_SPREADSHEET_ID': 'test-id',
        'GOOGLE_APPLICATION_CREDENTIALS': '/path/to/creds.json'
    })
    def test_partial_failure(self, mock_load_creds, mock_fetch_rows):
        """Test handling of rows with missing required fields."""
        mock_load_creds.return_value = {'type': 'service_account'}
        
        # Include one row with missing title
        mock_fetch_rows.return_value = [
            ['Title', 'Location', 'Start Date'],
            ['Valid Event', 'Park', '12/31/2025'],
            ['', 'Library', '01/15/2026'],  # Missing title
            ['Another Event', 'Hall', '02/01/2026'],
        ]
        
        events, errors = google_sheets_source.get_events_from_sheets()
        
        # Should have 2 valid events
        assert len(events) == 2
        assert events[0]['title'] == 'Valid Event'
        assert events[1]['title'] == 'Another Event'


class TestIntegrationWithPipeline(unittest.TestCase):
    """Test integration of Google Sheets source with pipeline."""
    
    @patch('scripts.google_sheets_source.get_events_from_sheets')
    def test_pipeline_receives_sheets_events(self, mock_get_events):
        """Test that pipeline can receive events from Google Sheets source."""
        # Mock Sheets response
        mock_get_events.return_value = [
            {
                'title': 'Community Workshop',
                'description': 'Learn new skills',
                'location': 'Community Center',
                'start': '2025-12-31T09:00:00',
                'end': '2025-12-31T11:00:00',
                'url': '',
                'category': [],
                'source': 'google_sheets',
                'source_id': 'sheet_row_2',
            }
        ], []
        
        # Simulate pipeline call
        events, errors = google_sheets_source.get_events_from_sheets()
        
        assert len(events) == 1
        assert events[0]['source'] == 'google_sheets'
        assert 'source_id' in events[0]
        assert len(errors) == 0


if __name__ == '__main__':
    unittest.main()
