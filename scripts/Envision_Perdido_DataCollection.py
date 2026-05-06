#!/usr/bin/env python3
"""Compatibility wrapper for moved scraper module."""

from __future__ import annotations

import re
import time
from urllib.parse import urljoin, urlparse

import requests

from scripts.scrapers import perdido_chamber_scraper as _impl
from scripts.scrapers.perdido_chamber_scraper import *  # noqa: F401,F403

BASE = _impl.BASE
MONTH_URL = _impl.MONTH_URL
SOURCE_NAME = _impl.SOURCE_NAME
sess = _impl.sess
BeautifulSoup = _impl.BeautifulSoup

create_session_with_retries = _impl.create_session_with_retries
find_ics_links = _impl.find_ics_links
get_event_url = _impl.get_event_url


def get_ics_url_from_event(event_url: str) -> str | None:
    """Compatibility wrapper that preserves old module-global patch points."""
    match = re.search(r"/events/details/([^/]+)", urlparse(event_url).path)
    if not match:
        print(f"Could not extract event slug from {event_url}")
        return None

    event_slug = match.group(1)

    new_format_url = urljoin(BASE, f"/events/addtocalendar/{event_slug}?format=ICal")
    try:
        time.sleep(0.1)
        resp = sess.head(new_format_url, timeout=15, allow_redirects=True)
        if resp.status_code == 200:
            return new_format_url
    except requests.RequestException:
        pass

    old_format_url = urljoin(BASE, f"/events/ical/{event_slug}.ics")
    try:
        time.sleep(0.1)
        resp = sess.head(old_format_url, timeout=15, allow_redirects=True)
        if resp.status_code == 200:
            return old_format_url
    except requests.RequestException:
        pass

    time.sleep(0.1)
    response = sess.get(event_url, timeout=30)
    response.raise_for_status()

    if BeautifulSoup is None:
        print("Cannot parse event page HTML due to BeautifulSoup installation.")
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    return find_ics_links(soup)


if __name__ == "__main__":
    import runpy

    runpy.run_module("scripts.scrapers.perdido_chamber_scraper", run_name="__main__")
