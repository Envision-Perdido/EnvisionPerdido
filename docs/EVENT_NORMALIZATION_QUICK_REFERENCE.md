# Event Normalization Quick Reference

## Common Tasks

### Check if Event is Free/Paid
```python
from event_normalizer import detect_paid_or_free, PaidStatus

is_free, status, event_type = detect_paid_or_free(
    title="Concert Tonight",
    description="Free admission!",
    cost_text=""
)

if status == PaidStatus.FREE:
    print("Event is free!")
elif status == PaidStatus.PAID:
    print("Event requires payment")
else:
    print("Unknown cost")
```

### Infer Tags for an Event
```python
from tag_taxonomy import infer_tags

tags = infer_tags(
    title="Live Music on the Beach",
    description="Join us for an evening concert",
    location="Flora-Bama",
    max_tags=5
)
# Returns: ['live_music', 'beach', ...]
```

### Resolve Venue
```python
from venue_registry import resolve_venue

venue = resolve_venue("Flora Bama Lounge")
if venue:
    print(f"Matched: {venue.canonical_name} (ID: {venue.id})")
    print(f"Location: {venue.city}, {venue.state}")
else:
    print("No venue match found")
```

### Enrich Full Event
```python
from event_normalizer import enrich_event

event = {
    'title': 'Karaoke Night',
    'description': 'No cover charge! Sing your favorites.',
    'location': 'Perdido Key Sports Bar'
}

enriched = enrich_event(event)
# Returns event with: tags, is_free, venue_id, etc.
```

### Filter Events
```python
from event_normalizer import filter_events_dataframe
import pandas as pd

df = pd.DataFrame(events)
kept_df, filtered_df = filter_events_dataframe(df)

print(f"Kept: {len(kept_df)}, Filtered: {len(filtered_df)}")
```

## Available Tags

### Music & Entertainment
- `live_music` - Live bands, concerts, musicians
- `dj` - DJ events, dance parties
- `karaoke` - Karaoke nights
- `open_mic` - Open mic nights
- `comedy` - Stand-up comedy, comedy shows
- `theater` - Theater performances, plays

### Food & Drink
- `food_drink` - General food/drink events
- `happy_hour` - Happy hour specials
- `wine` - Wine tastings, wine events
- `beer` - Beer events, breweries
- `cocktails` - Cocktail events
- `brunch` - Brunch events
- `dinner` - Dinner events

### Family & Kids
- `family_friendly` - Family-friendly events
- `kids` - Kids/children's events

### Outdoors & Recreation
- `outdoors` - Outdoor events
- `beach` - Beach events
- `run_walk` - Runs, walks, marathons
- `fitness` - Fitness, yoga, workouts
- `sports_event` - Sports tournaments
- `fishing` - Fishing events
- `water_sports` - Kayaking, paddleboarding, etc.

### Arts & Culture
- `art` - Art shows, artists
- `craft` - Craft fairs, handmade goods
- `gallery` - Gallery openings
- `exhibition` - Exhibitions

### Community & Social
- `fundraiser` - Fundraising events
- `nonprofit` - Nonprofit events
- `charity` - Charity events
- `networking` - Networking events
- `market` - Markets, vendor events
- `festival` - Festivals
- `parade` - Parades

### Special Occasions
- `holiday` - Holiday events
- `seasonal` - Seasonal events

### Other
- `sports_watch` - Watch parties
- `trivia` - Trivia nights
- `educational` - Educational events
- `workshop` - Workshops

## Known Venues

| Venue ID | Canonical Name | City | State |
|----------|---------------|------|-------|
| flora-bama | Flora-Bama | Perdido Key | FL |
| perdido-key-sports-bar | Perdido Key Sports Bar | Perdido Key | FL |
| lillians | Lillian's Pizza | Lillian | AL |
| the-oyster-bar-perdido-key | The Oyster Bar | Perdido Key | FL |
| perdido-key-oyster-bar | Perdido Key Oyster Bar | Perdido Key | FL |
| big-lagoon-state-park | Big Lagoon State Park | Pensacola | FL |
| gulf-state-park | Gulf State Park | Gulf Shores | AL |
| perdido-beach-resort | Perdido Beach Resort | Orange Beach | AL |
| tacky-jacks | Tacky Jacks | Gulf Shores | AL |
| owa | OWA | Foley | AL |
| the-wharf | The Wharf | Orange Beach | AL |
| lulu-s | LuLu's | Gulf Shores | AL |
| the-hangout | The Hangout | Gulf Shores | AL |
| flora-bama-yacht-club | Flora-Bama Yacht Club | Orange Beach | AL |

## Event Data Model

### Input Fields (from scraper)
- `title` - Event title
- `description` - Event description
- `location` - Location text
- `category` - Event category
- `start` - Start datetime
- `end` - End datetime
- `url` - Source URL

### Enriched Fields (added)
- `is_free` - Boolean (True/False/None)
- `paid_status` - "FREE", "PAID", or "UNKNOWN"
- `event_type` - "free_event", "paid_event", or "event"
- `cost_text` - Extracted cost description
- `tags` - List of tag slugs
- `venue_id` - Matched venue ID (if found)
- `venue_name` - Canonical venue name
- `normalized_location` - Standardized location
- `should_filter` - Boolean filter flag
- `filter_reason` - Reason for filtering

## WordPress Meta Fields

When uploaded to WordPress, enriched data is stored in custom meta fields:

- `_venue_id` - Venue identifier
- `_event_cost` - Cost/price text for display
- `_event_type` - Event type slug
- `_paid_status` - "FREE" / "PAID" / "UNKNOWN"
- `_is_free` - "yes" or "no"
- `_event_tags` - Comma-separated tag slugs
- `_event_tags_display` - Comma-separated display names

## Running Tests

```powershell
# All tests
pytest tests/test_tag_taxonomy.py tests/test_venue_registry.py tests/test_event_normalizer.py

# Specific test file
pytest tests/test_tag_taxonomy.py -v

# Specific test
pytest tests/test_event_normalizer.py::TestPaidFreeDetection::test_explicit_free -v
```

## Troubleshooting

### Tags not detected?
- Check keyword patterns in `TAG_KEYWORDS` dictionary
- Verify text is lowercase for matching
- Tags are limited to top 5 by default (change `max_tags`)

### Venue not resolving?
- Check venue is in `KNOWN_VENUES` list
- Add aliases for variations
- Use `normalize_location_text()` to see normalized form

### Wrong paid/free status?
- Check both `PRICE_PATTERNS` and `FREE_PATTERNS`
- Free patterns have priority over price patterns
- "$0" is always treated as FREE

### Events being filtered incorrectly?
- Check `should_filter_brandon_styles_owa()` logic
- Verify location text and case sensitivity
- Review filter logs in pipeline output
