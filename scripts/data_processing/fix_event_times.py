"""
Fix EventON event times on WordPress by reconstructing local datetime
from stored date/time meta fields and updating evcal_srow/evcal_erow
with UTC epoch seconds.

Assumptions:
- Site local timezone is America/Chicago (override via SITE_TIMEZONE env var)
- EventON meta fields present: evcal_start_date, evcal_start_time_hour,
  evcal_start_time_min, evcal_start_time_ampm, and corresponding end fields.

Usage:
  python scripts/fix_event_times.py

Requires env vars: WP_SITE_URL, WP_USERNAME, WP_APP_PASSWORD
"""

import os
from datetime import datetime
from zoneinfo import ZoneInfo
import requests
from requests.auth import HTTPBasicAuth

SITE_TZ = os.getenv("SITE_TIMEZONE", "America/Chicago")
LOCAL_TZ = ZoneInfo(SITE_TZ)
UTC = ZoneInfo("UTC")

SITE = os.getenv("WP_SITE_URL", "https://sandbox.envisionperdido.org").rstrip("/")
AUTH = HTTPBasicAuth(os.getenv("WP_USERNAME", ""), os.getenv("WP_APP_PASSWORD", ""))
API = f"{SITE}/wp-json/wp/v2"


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def _compose_dt(date_str: str, hour_str: str, min_str: str, ampm: str) -> datetime | None:
    try:
        hour = int(hour_str)
        minute = int(min_str)
        if ampm.lower() == "pm" and hour != 12:
            hour += 12
        if ampm.lower() == "am" and hour == 12:
            hour = 0
        dt_naive = datetime.strptime(date_str, "%Y-%m-%d").replace(hour=hour, minute=minute)
        return dt_naive.replace(tzinfo=LOCAL_TZ)
    except Exception:
        return None


def fetch_events(page: int = 1, per_page: int = 100):
    r = requests.get(
        f"{API}/ajde_events",
        params={"per_page": per_page, "page": page, "status": "any", "orderby": "id", "order": "desc"},
        auth=AUTH,
        timeout=30,
    )
    if r.status_code == 200:
        return r.json()
    raise RuntimeError(f"Events API returned {r.status_code}: {r.text[:200]}")


def fix_event(event: dict) -> bool:
    meta = event.get("meta", {})
    s_date = meta.get("evcal_start_date")
    s_hour = meta.get("evcal_start_time_hour")
    s_min = meta.get("evcal_start_time_min")
    s_ampm = meta.get("evcal_start_time_ampm")

    e_date = meta.get("evcal_end_date")
    e_hour = meta.get("evcal_end_time_hour")
    e_min = meta.get("evcal_end_time_min")
    e_ampm = meta.get("evcal_end_time_ampm")

    changed = False

    # Reconstruct start
    start_local = _compose_dt(s_date, s_hour, s_min, s_ampm) if s_date and s_hour and s_min and s_ampm else None
    if start_local:
        start_utc = start_local.astimezone(UTC)
        new_srow = str(int(start_utc.timestamp()))
        if meta.get("evcal_srow") != new_srow:
            meta["evcal_srow"] = new_srow
            changed = True

    # Reconstruct end
    end_local = _compose_dt(e_date, e_hour, e_min, e_ampm) if e_date and e_hour and e_min and e_ampm else None
    if end_local:
        end_utc = end_local.astimezone(UTC)
        new_erow = str(int(end_utc.timestamp()))
        if meta.get("evcal_erow") != new_erow:
            meta["evcal_erow"] = new_erow
            changed = True

    if not changed:
        return False

    # Update event meta
    r = requests.post(
        f"{API}/ajde_events/{event['id']}",
        auth=AUTH,
        json={"meta": meta},
        timeout=30,
    )
    if r.status_code == 200:
        return True
    else:
        log(f"Failed to update event {event['id']}: {r.status_code} {r.text[:200]}")
        return False


def main():
    log("Starting WordPress event time fix...")
    if not (os.getenv("WP_USERNAME") and os.getenv("WP_APP_PASSWORD")):
        log("WordPress credentials missing in environment.")
        return

    fixed = 0
    page = 1
    while True:
        try:
            events = fetch_events(page=page)
        except Exception as e:
            log(f"Error fetching events: {e}")
            break

        if not events:
            break

        for ev in events:
            if fix_event(ev):
                fixed += 1
        page += 1

    log(f"Done. Fixed timestamps on {fixed} events.")


if __name__ == "__main__":
    main()
