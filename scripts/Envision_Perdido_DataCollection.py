"""Data collection and parsing for Perdido Chamber events.

This module provides scrapers and parsers for event data from:
- Perdido Chamber website (using BeautifulSoup HTML parsing)
- ICS (iCalendar) files for event details
- Optional timezone support via zoneinfo, backports.zoneinfo, or dateutil

The module gracefully handles missing optional dependencies:
- BeautifulSoup4 (bs4) for HTML parsing
- iCalendar for ICS parsing
- zoneinfo/backports.zoneinfo/dateutil for timezone handling
"""

import time
import re
import csv
import json
from urllib.parse import urlparse, urljoin
from datetime import datetime
try:
    from zoneinfo import ZoneInfo
except ImportError:
    # Try dynamic imports to avoid static analyzer errors for optional
    # packages
    try:
        import importlib
        _bz = importlib.import_module("backports.zoneinfo")
        ZoneInfo = getattr(_bz, "ZoneInfo")
    except (ImportError, AttributeError):
        try:
            import importlib
            _dt = importlib.import_module("dateutil.tz")
            # dateutil.tz.gettz returns a tzinfo-like object when called
            # with a name
            ZoneInfo = getattr(_dt, "gettz")
        except (ImportError, AttributeError):
            ZoneInfo = None
            print("Warning: no ZoneInfo implementation available; install "
                  "Python 3.9+, backports.zoneinfo, or python-dateutil to "
                  "enable timezone support.")

import importlib
import requests
from typing import Optional, TYPE_CHECKING, List, Dict

# Allow static type checkers to see BeautifulSoup without importing it at
# runtime
if TYPE_CHECKING:
    from bs4 import BeautifulSoup

# Attempt a dynamic import to avoid static analyzer errors when the package
# is not installed
try:
    _bs = importlib.import_module("bs4")
    BeautifulSoup = getattr(_bs, "BeautifulSoup")
except (ImportError, AttributeError):
    BeautifulSoup = None
    print("Warning: 'bs4' (BeautifulSoup) package not found. Install with "
          "'pip install beautifulsoup4' to enable HTML parsing.")

try:
    _ical = importlib.import_module("icalendar")
    Calendar = getattr(_ical, "Calendar")
except (ImportError, AttributeError):
    Calendar = None
    print("Warning: 'icalendar' package not found. Install with "
          "'pip install icalendar' to enable ICS parsing.")
import os


BASE = "https://business.perdidochamber.com"

# Month view of calendar
MONTH_URL = "https://business.perdidochamber.com/events/calendar/2025-09-01"

sess = requests.Session()
sess.headers.update({
    # Mimic a browser to prevent the scraper from being blocked
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472"
                   ".114 Safari/537.36")
})

## SiteMap URL: https://business.perdidochamber.com/SiteMap.xml
## List of all URL's we can scrape according to their robots.txt
## https://business.perdidochamber.com/robots.txt


def get_event_url(month_url: str) -> list[str]:
    """Get event detail URLs from a chamber calendar month view.
    
    Args:
        month_url: URL to the chamber calendar month view.
    
    Returns:
        List of unique event detail URLs.
    
    Raises:
        RuntimeError: If BeautifulSoup is not available.
        requests.RequestException: If HTTP request fails.
    """
    # Send the HTTP request to the calendar page
    response = sess.get(month_url, timeout=30)
    response.raise_for_status()

    # Parse the HTML content of the page
    if BeautifulSoup is None:
        raise RuntimeError(
            "BeautifulSoup is required to parse HTML; install "
            "beautifulsoup4"
        )
    soup = BeautifulSoup(response.text, 'html.parser')

    # Collect the event detail links
    event_links = []
    for anchor in soup.select('a[href*="/events/details"]'):
        href = anchor.get('href')
        if href:
            event_links.append(urljoin(BASE, href))

    # Delete redundant copies while preserving order
    seen, unique_links = set(), []
    for link in event_links:
        if link not in seen:
            seen.add(link)
            unique_links.append(link)
    return unique_links

def find_ics_links(soup) -> str | None:
    """Find iCalendar download link on an event detail page.
    
    Args:
        soup: BeautifulSoup parsed HTML object.
    
    Returns:
        URL to ICS file, or None if not found.
    """
    anchor = soup.find(
        'a',
        string=re.compile(
            r'Add to Calendar\s*-\s*iCal',
            re.IGNORECASE
        )
    )
    if anchor and anchor.get('href'):
        return urljoin(BASE, anchor['href'])
    
    generic = soup.select_one('a[href$=".ics"]')
    if generic and generic.get('href'):
        return urljoin(BASE, generic['href'])
    
    return None

def get_ics_url_from_event(event_url: str) -> str | None:
    """Fetches the ICS URL from the event page.
    
       GrowthZone event detail pages include an "Add to Calendar -> iCal" link 
       that points to an ICS file. If that link cannot be found, this function
       falls back to constructing the .ics URL from the event detil slug.

       Args:
           event_url (str): The URL of the event detail page.

       Returns:
           str | None: The URL of the ICS file, or None if it cannot be found.
    """
    try:
        time.sleep(1)  # be polite and avoid overwhelming the server
        response = sess.get(event_url, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching event page {event_url}: {e}")
        return None

    if BeautifulSoup is None:
        print("Cannot parse event page HTML because BeautifulSoup is not installed.")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Look for the "Add to Calendar -> iCal" link
    ics_link = find_ics_links(soup)
    if ics_link:
        return ics_link
    
    # Fallback: Construct the ICS URL from the event detail slug
    match = re.search(r'/events/details/([^/]+)', urlparse(event_url).path)
    if match:
        event_slug = match.group(1)
        return urljoin(BASE, f"/events/ical/{event_slug}.ics")
    else:
        return None

#ics fetching and parsing 
def fetch_calendar(ics_url: str) -> Optional[object]:
    # If the icalendar package is not available, skip ICS fetching.
    if Calendar is None:
        print("Cannot fetch ICS files because the 'icalendar' package is not installed.")
        return None

    # download and parse the ics file into an icalendar object
    try:
        time.sleep(1)  # be polite and avoid overwhelming the server
        response = sess.get(ics_url, timeout=30)
        response.raise_for_status()
        # use Calendar.from_ical when available
        if Calendar is not None and hasattr(Calendar, 'from_ical'):
            return Calendar.from_ical(response.content)
        # fallback to module-level _ical if available
        if '_ical' in globals() and hasattr(_ical, 'Calendar'):
            return _ical.Calendar.from_ical(response.content)
    except requests.RequestException as e:
        print(f"Error fetching ICS file {ics_url}: {e}")
    except Exception as e:
        print(f"Error parsing ICS file from {ics_url}: {e}")

    return None

def _dt_to_iso(v):
    #handle date or datetime with or without timezone, convert to America/Chicago, return ISO format string

    if not v:
        return None
    
    #icalendar stores time as vDDDTypes; .dt can be date or datetime
    dt = getattr(v, 'dt', v)
    
    try:
        #if it's a datetime with timezone info, convert to America/Chicago
        if hasattr(dt, 'tzinfo') and dt.tzinfo is not None:
            local_tz = ZoneInfo(os.getenv("SITE_TIMEZONE", "America/Chicago"))
            dt = dt.astimezone(local_tz)
            # Return naive local time (remove timezone for consistency with downstream code)
            return dt.replace(tzinfo=None).isoformat()
        #if its a date or naive datetime, return as-is
        if hasattr(dt, 'isoformat'):
            return dt.isoformat()
        
        #fallback: convert to string
        return str(dt)
    except Exception:
        return str(dt)

def _text_or_none(val):
    return str(val) if val is not None else None

def parse_calendar_to_events(cal, source_ics: str, source_page: Optional[str] = None) -> List[Dict]:
    # extract VEVENTS into a list of normalized dicts
    events = []
    if cal is None:
        return events
    
    for component in cal.walk():
        # Some icalendar implementations require checking .name
        if getattr(component, 'name', '').upper() != 'VEVENT':
            continue
        summary = _text_or_none(component.get('SUMMARY'))
        description = _text_or_none(component.get('DESCRIPTION'))
        location = _text_or_none(component.get('LOCATION'))
        url = _text_or_none(component.get('URL'))
        uid = _text_or_none(component.get('UID'))
        category = _text_or_none(component.get('CATEGORIES'))
        if category is not None:
            #categories can be a vText or list-like; normalize
            try:
                category = list(category.cats)
            except Exception:
                category = [_text_or_none(category)]

        event = {
            "title": summary,
            "description": description,
            "location": location,
            "start": _dt_to_iso(component.get('DTSTART')),
            "end": _dt_to_iso(component.get('DTEND')),
            "url": url,
            "uid": uid,
            "category": category,
            "last_modified": _dt_to_iso(component.get('LAST-MODIFIED')),
            "created": _dt_to_iso(component.get('CREATED')),

            #provencence
            "source_ics": source_ics,
            "source_page": source_page
        }

        events.append(event)
        
    return events

def scrape_month(month_url: str, pause_seconds: float = 0.4) -> list[dict]:
    # Scrape all events from a month view URL
    all_events: list[dict] = []
    errors: list[str] = []

    try:
        event_pages = get_event_url(month_url)
    except Exception as e:
        print(f"Error fetching event URLs from {month_url}: {e}")
        return all_events   
    print(f"Found {len(event_pages)} event pages in month view.")

    seen_ics: set[str] = set()
    for i, page_url in enumerate(event_pages, 1):
        try:
            ics = get_ics_url_from_event(page_url)
            if not ics:
                errors.append(f"No ICS link found on event page {page_url}")
                continue    

            if ics in seen_ics:
                continue
            seen_ics.add(ics)

            cal = fetch_calendar(ics)
            events = parse_calendar_to_events(cal, source_ics=ics, source_page=page_url)
            all_events.extend(events)
        except Exception as e:
            errors.append(f"Error processing event page {page_url}: {e}")
        finally:
            time.sleep(pause_seconds)  # be polite and avoid overwhelming the server

    print(f"Scraped {len(all_events)} events with {len(errors)} errors.")
    if errors:
        for msg in errors[:5]:
            print(f"  - {msg}")
        if len(errors) > 5:
            print(f"  ... and {len(errors) - 5} more errors.")
    return all_events

#save to JSON/csv
def save_events_json(events: list[dict], path: str = "perdido_events.json"):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)

def save_events_csv(events: list[dict], path: str = "perdido_events.csv"):   
    if not events:
        print("No events to save.")
        return

    cols = [
        "title", "start", "end", "location", "url",
        "description", "uid", "category",
    ]         

    #flatten categories
    def rowify(e):
        r = {k: e.get(k) for k in cols}
        if isinstance(r.get("category"), list):
            r["category"] = ";".join(filter(None, map(str, r["category"])))
        return r
    
    with open(path, "w", newline = "", encoding = "utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        for event in events:
            writer.writerow(rowify(event))

if __name__ == "__main__":
    print("[runner] starting scrape for all months in 2025...", flush=True)

    OUT_DIR = "C:\\Users\\scott\\UWF-Code\\EnvisionPerdido"
    os.makedirs(OUT_DIR, exist_ok=True)

    all_events = []
    for month in range(1, 13):
        month_str = f"2025-{month:02d}-01"
        month_url = f"https://business.perdidochamber.com/events/calendar/{month_str}"
        print(f"[runner] scraping {month_url}", flush=True)
        try:
            events = scrape_month(month_url)
            print(f"[runner] scraped {len(events)} events from {month_url}", flush=True)
            all_events.extend(events)
        except Exception as e:
            print(f"[runner] error scraping {month_url}: {e}", flush=True)

    print(f"[runner] total events scraped: {len(all_events)}", flush=True)

    json_path = os.path.join(OUT_DIR, "perdido_events_2025.json")
    csv_path  = os.path.join(OUT_DIR, "perdido_events_2025.csv")

    save_events_json(all_events, json_path)
    save_events_csv(all_events, csv_path)

    print(f"[runner] wrote:\n  - {json_path}\n  - {csv_path}", flush=True)
    print("[done]", flush=True)



