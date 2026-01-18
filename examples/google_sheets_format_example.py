"""
Example of Google Sheets event submission format.

This file demonstrates how community members should structure their
Google Form responses (or direct sheet entries) for the Community Calendar.

Key points:
- First row: headers (column names)
- Column names are flexible but must include title and start_date
- All dates should be in MM/DD/YYYY or YYYY-MM-DD format
- Times are optional (default to 00:00 if not provided)
"""

# Example 1: Minimal valid submission (only required fields)
minimal_event = {
    "title": "Community Potluck",
    "start_date": "06/15/2025",
}

# Example 2: Full event with all fields
full_event = {
    "title": "Annual Summer Festival",
    "description": "Join us for a day of music, food, and community!",
    "location": "Central Park Amphitheater",
    "start_date": "07/20/2025",
    "start_time": "10:00 AM",
    "end_date": "07/20/2025",
    "end_time": "6:00 PM",
    "url": "https://example.com/festival",
    "category": "Community Festival",
    "organizer_name": "Jane Smith",
    "organizer_email": "jane@example.com",
}

# Example 3: Event with alternative column names (all are valid)
alternative_names = {
    "event_name": "Yoga in the Park",  # Alternative to 'title'
    "event_description": "Free yoga class",  # Alternative to 'description'
    "venue": "Riverside Park",  # Alternative to 'location'
    "date": "06/22/2025",  # Alternative to 'start_date'
    "event_time": "7:00 PM",  # Alternative to 'start_time'
}

# Example 4: Google Sheet structure (as displayed in spreadsheet)
# Header row (required):
# | Title | Location | Start Date | Start Time | End Date | End Time | Description | URL | Category |
#
# Data rows:
# | Community Picnic | Park | 06/15/2025 | 12:00 PM | 06/15/2025 | 4:00 PM | Family gathering | https://... | Social |
# | Book Club | Library | 06/18/2025 | 6:00 PM | 06/18/2025 | 7:30 PM | Monthly meeting | | Culture |
# | Fitness Class | Community Center | 06/20/2025 | | | | Drop-in fitness | | Health |

# Example 5: How the module maps to internal pipeline format
mapped_event = {
    # Core fields (always present)
    "title": "Community Workshop",
    "description": "Learn new skills",
    "location": "Community Center",
    "start": "2025-06-20T14:00:00",  # Converted to ISO format
    "end": "2025-06-20T16:00:00",
    
    # Optional fields
    "url": "https://example.com/workshop",
    "category": ["Education"],
    
    # Source tracking (added automatically)
    "source": "google_sheets",
    "source_id": "sheet_row_42",
}

# Example 6: Column mapping (if you use different names)
example_column_mapping = {
    # Internal field name: [list of accepted column names in sheet]
    'title': ['title', 'event_name', 'event', 'event_title'],
    'description': ['description', 'event_description', 'details', 'info'],
    'location': ['location', 'venue', 'venue_name', 'address'],
    'start': ['start_date', 'date', 'event_date'],
    'start_time': ['start_time', 'time', 'event_time'],
    'end': ['end_date', 'end', 'finish_date'],
    'end_time': ['end_time', 'end_time'],
    'url': ['url', 'registration_link', 'link', 'website'],
    'category': ['category', 'tags', 'type', 'event_type'],
    'organizer_name': ['organizer_name', 'organizer', 'contact_name', 'submitted_by'],
    'organizer_email': ['organizer_email', 'contact_email', 'email'],
}

if __name__ == '__main__':
    print("Google Sheets Format Examples")
    print("=" * 60)
    print("\nMinimal event (required fields only):")
    print(minimal_event)
    print("\nFull event (with all optional fields):")
    print(full_event)
    print("\nAlternative column names (all valid):")
    print(alternative_names)
