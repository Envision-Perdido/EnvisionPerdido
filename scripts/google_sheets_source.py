"""
Google Sheets Event Source Integration

Fetches community event submissions from a Google Sheet and converts them
into the pipeline's internal event model for processing alongside scraped events.

This module:
- Authenticates via service account credentials (env var or base64-encoded JSON)
- Fetches rows from a configured sheet and range
- Normalizes headers and maps columns to internal event schema
- Handles date/time parsing with fallback strategies
- Provides robust error handling and logging
"""

import os
import json
import base64
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path

# Optional imports for Google Sheets API
try:
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    HAS_GOOGLE_API = True
except ImportError:
    HAS_GOOGLE_API = False

logger = logging.getLogger(__name__)


# Configuration via environment variables
def get_sheets_config() -> Dict[str, Optional[str]]:
    """Load Google Sheets configuration from environment variables.
    
    Returns:
        Dict with keys: spreadsheet_id, range, worksheet_name, credentials_path
    """
    return {
        'spreadsheet_id': os.getenv('SHEETS_SPREADSHEET_ID'),
        'range': os.getenv('SHEETS_RANGE', 'Form Responses 1!A:Z'),
        'worksheet_name': os.getenv('SHEETS_WORKSHEET_NAME', 'Form Responses 1'),
        'credentials_path': os.getenv('GOOGLE_APPLICATION_CREDENTIALS'),
        'credentials_b64': os.getenv('GOOGLE_SHEETS_SA_JSON_B64'),
    }


def load_service_account_credentials(
    credentials_path: Optional[str] = None,
    credentials_b64: Optional[str] = None
) -> Optional[dict]:
    """Load Google service account credentials from file or base64-encoded JSON.
    
    Args:
        credentials_path: Path to service account JSON file.
        credentials_b64: Base64-encoded service account JSON.
    
    Returns:
        Parsed credentials dict, or None if not found/invalid.
    
    Raises:
        ValueError: If both or neither credentials sources provided.
    """
    if credentials_path and credentials_b64:
        raise ValueError(
            "Provide only ONE of GOOGLE_APPLICATION_CREDENTIALS or "
            "GOOGLE_SHEETS_SA_JSON_B64, not both."
        )
    
    if credentials_path:
        if not Path(credentials_path).exists():
            raise FileNotFoundError(
                f"Service account credentials file not found: {credentials_path}"
            )
        with open(credentials_path, 'r') as f:
            return json.load(f)
    
    if credentials_b64:
        try:
            decoded = base64.b64decode(credentials_b64)
            return json.loads(decoded)
        except Exception as e:
            raise ValueError(f"Failed to decode GOOGLE_SHEETS_SA_JSON_B64: {e}")
    
    return None


def build_sheets_client(credentials: dict):
    """Build an authorized Google Sheets API client.
    
    Args:
        credentials: Service account credentials dict.
    
    Returns:
        Authorized Google Sheets v4 client.
    
    Raises:
        ImportError: If google-auth-httplib2 or google-api-python-client missing.
    """
    if not HAS_GOOGLE_API:
        raise ImportError(
            "Google API client libraries required. Install with: "
            "pip install google-auth google-auth-httplib2 google-api-python-client"
        )
    
    creds = service_account.Credentials.from_service_account_info(
        credentials,
        scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
    )
    return build('sheets', 'v4', credentials=creds)


def fetch_sheet_rows(
    spreadsheet_id: str,
    sheet_range: str,
    credentials: dict
) -> List[List[str]]:
    """Fetch all rows from a Google Sheet range.
    
    Args:
        spreadsheet_id: Google Sheets spreadsheet ID.
        sheet_range: Range in A1 notation (e.g., 'Form Responses 1!A:Z').
        credentials: Service account credentials dict.
    
    Returns:
        List of rows, where each row is a list of cell values (strings).
        First row is assumed to be headers.
    
    Raises:
        Exception: If API call fails.
    """
    service = build_sheets_client(credentials)
    
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=sheet_range,
            valueRenderOption='FORMATTED_VALUE',
            dateTimeRenderOption='FORMATTED_STRING'
        ).execute()
        
        rows = result.get('values', [])
        logger.info(f"Fetched {len(rows)} rows from Google Sheet (including header)")
        return rows
    
    except Exception as e:
        logger.error(f"Failed to fetch Google Sheet: {e}")
        raise


def normalize_header(header: str) -> str:
    """Normalize sheet header to internal column name.
    
    Args:
        header: Raw header text from sheet.
    
    Returns:
        Normalized header (lowercase, spaces→underscores, stripped).
    """
    return (
        header.strip()
        .lower()
        .replace(' ', '_')
        .replace('-', '_')
    )


def rows_to_dicts(rows: List[List[str]]) -> List[Dict[str, str]]:
    """Convert sheet rows to dictionaries using header row.
    
    Args:
        rows: List of rows from sheet; first row is headers.
    
    Returns:
        List of dicts with normalized column names.
    
    Raises:
        ValueError: If no rows provided.
    """
    if not rows or len(rows) == 0:
        raise ValueError("Sheet has no rows (no header)")
    
    if len(rows) == 1:
        logger.warning("Sheet has only header row, no data rows")
        return []
    
    headers = [normalize_header(h) for h in rows[0]]
    data_rows = rows[1:]
    
    dicts = []
    for row in data_rows:
        # Pad row with empty strings if it has fewer columns than header
        padded_row = row + [''] * (len(headers) - len(row))
        row_dict = {
            headers[i]: padded_row[i].strip() if i < len(padded_row) else ''
            for i in range(len(headers))
        }
        dicts.append(row_dict)
    
    return dicts


def parse_datetime_flexible(
    date_str: Optional[str],
    time_str: Optional[str] = None
) -> Optional[str]:
    """Parse date and optional time into ISO format string.
    
    Accepts multiple date formats and returns ISO format (YYYY-MM-DDTHH:MM:SS).
    
    Args:
        date_str: Date in various formats (MM/DD/YYYY, YYYY-MM-DD, etc.).
        time_str: Time in HH:MM or HH:MM AM/PM format (optional).
    
    Returns:
        ISO format string, or None if parsing fails.
    """
    if not date_str or not isinstance(date_str, str):
        return None
    
    date_str = date_str.strip()
    time_str = time_str.strip() if time_str else None
    
    # Combine date and time if both provided
    combined = f"{date_str} {time_str}".strip() if time_str else date_str
    
    # Try common date/time formats
    formats = [
        "%m/%d/%Y %I:%M %p",  # 12/31/2025 2:30 PM
        "%m/%d/%Y %H:%M",     # 12/31/2025 14:30
        "%m/%d/%Y",           # 12/31/2025
        "%Y-%m-%d %H:%M:%S",  # 2025-12-31 14:30:00
        "%Y-%m-%d %I:%M %p",  # 2025-12-31 2:30 PM
        "%Y-%m-%d %H:%M",     # 2025-12-31 14:30
        "%Y-%m-%d",           # 2025-12-31
        "%B %d, %Y %I:%M %p", # December 31, 2025 2:30 PM
        "%B %d, %Y",          # December 31, 2025
        "%b %d, %Y",          # Dec 31, 2025
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(combined, fmt)
            # Ensure time component is set if only date provided
            if not time_str and len(combined.split()) == 1:
                # For date-only strings, default to 00:00:00
                dt = dt.replace(hour=0, minute=0, second=0)
            return dt.isoformat()
        except ValueError:
            continue
    
    logger.warning(f"Could not parse date: '{date_str}' with time: '{time_str}'")
    return None


def map_sheet_row_to_event(
    row_dict: Dict[str, str],
    row_number: int = 0,
    column_mapping: Optional[Dict[str, str]] = None
) -> Optional[Dict[str, any]]:
    """Map a sheet row to internal event model.
    
    Args:
        row_dict: Row dict with normalized column names.
        row_number: Row number in sheet (for tracking).
        column_mapping: Custom mapping of sheet columns to event fields.
            Default mapping:
            - title: title/event_name/event
            - description: description/event_description
            - location: location/venue
            - start: start_date
            - end: end_date
            - start_time: start_time (optional)
            - end_time: end_time (optional)
            - url: url/registration_link/link
            - category: category/tags/type
            - organizer_name: organizer_name/organizer/contact_name
            - organizer_email: organizer_email/contact_email
    
    Returns:
        Event dict in pipeline format, or None if required fields missing.
    """
    if column_mapping is None:
        column_mapping = {
            'title': ['title', 'event_name', 'event'],
            'description': ['description', 'event_description', 'details'],
            'location': ['location', 'venue'],
            'start': ['start_date', 'date'],
            'start_time': ['start_time', 'time'],
            'end': ['end_date'],
            'end_time': ['end_time'],
            'url': ['url', 'registration_link', 'link'],
            'category': ['category', 'tags', 'type'],
            'organizer_name': ['organizer_name', 'organizer', 'contact_name'],
            'organizer_email': ['organizer_email', 'contact_email'],
        }
    
    def find_field(field_name: str) -> Optional[str]:
        """Find value in row_dict using mapping chain."""
        options = column_mapping.get(field_name, [field_name])
        for key in options:
            if key in row_dict and row_dict[key]:
                return row_dict[key] if row_dict[key] else None
        return None
    
    # Extract and normalize fields
    title = find_field('title')
    description = find_field('description')
    location = find_field('location')
    url = find_field('url')
    category = find_field('category')
    organizer_name = find_field('organizer_name')
    organizer_email = find_field('organizer_email')
    
    # Check required fields
    if not title:
        logger.warning(f"Row {row_number}: missing required field 'title'")
        return None
    
    # Parse dates
    start_date = find_field('start')
    start_time = find_field('start_time')
    start_iso = parse_datetime_flexible(start_date, start_time)
    
    if not start_iso:
        logger.warning(
            f"Row {row_number} ('{title}'): could not parse start date/time"
        )
        return None
    
    end_date = find_field('end')
    end_time = find_field('end_time')
    end_iso = parse_datetime_flexible(end_date, end_time) if end_date else None
    
    # Build event dict
    event = {
        'title': title,
        'description': description or '',
        'location': location or '',
        'start': start_iso,
        'end': end_iso or start_iso,  # Default end to start if not provided
        'url': url or '',
        'category': [category] if category else [],
        'source': 'google_sheets',
        'source_id': f"sheet_row_{row_number}",
    }
    
    # Add optional organizer info in description
    if organizer_name or organizer_email:
        organizer_info = []
        if organizer_name:
            organizer_info.append(f"Organizer: {organizer_name}")
        if organizer_email:
            organizer_info.append(f"Contact: {organizer_email}")
        if organizer_info:
            suffix = " | " + " | ".join(organizer_info)
            event['description'] = (event['description'] or '') + suffix
    
    return event


def get_events_from_sheets(
    column_mapping: Optional[Dict[str, str]] = None,
    dry_run: bool = False
) -> Tuple[List[Dict], List[str]]:
    """Main entry point: fetch events from Google Sheets.
    
    Args:
        column_mapping: Optional custom column mapping (see map_sheet_row_to_event).
        dry_run: If True, log config but don't call API.
    
    Returns:
        Tuple of (events_list, errors_list).
        - events_list: List of event dicts in pipeline format
        - errors_list: List of error messages encountered
    """
    config = get_sheets_config()
    errors = []
    
    # Validate configuration
    if not config['spreadsheet_id']:
        error = "SHEETS_SPREADSHEET_ID env var not set"
        logger.error(error)
        errors.append(error)
        return [], errors
    
    if not config['credentials_path'] and not config['credentials_b64']:
        error = (
            "Neither GOOGLE_APPLICATION_CREDENTIALS nor "
            "GOOGLE_SHEETS_SA_JSON_B64 env vars set"
        )
        logger.error(error)
        errors.append(error)
        return [], errors
    
    if dry_run:
        logger.info(f"DRY RUN: Would fetch from sheet {config['spreadsheet_id']}")
        logger.info(f"         Range: {config['range']}")
        return [], errors
    
    # Load credentials
    try:
        credentials = load_service_account_credentials(
            config['credentials_path'],
            config['credentials_b64']
        )
        if not credentials:
            error = "Could not load service account credentials"
            logger.error(error)
            errors.append(error)
            return [], errors
    except Exception as e:
        logger.error(f"Failed to load credentials: {e}")
        errors.append(str(e))
        return [], errors
    
    # Fetch rows from sheet
    try:
        rows = fetch_sheet_rows(
            config['spreadsheet_id'],
            config['range'],
            credentials
        )
    except Exception as e:
        error = f"Failed to fetch Google Sheet: {e}"
        logger.error(error)
        errors.append(error)
        return [], errors
    
    # Convert to dicts
    try:
        row_dicts = rows_to_dicts(rows)
    except Exception as e:
        error = f"Failed to parse sheet rows: {e}"
        logger.error(error)
        errors.append(error)
        return [], errors
    
    # Map to events
    events = []
    for i, row_dict in enumerate(row_dicts, start=2):  # start=2 (row 1 is header)
        try:
            event = map_sheet_row_to_event(row_dict, row_number=i, column_mapping=column_mapping)
            if event:
                events.append(event)
        except Exception as e:
            error = f"Error mapping row {i}: {e}"
            logger.warning(error)
            errors.append(error)
    
    logger.info(
        f"Google Sheets source: {len(events)} events mapped "
        f"({len(row_dicts) - len(events)} rows skipped/invalid)"
    )
    
    return events, errors
