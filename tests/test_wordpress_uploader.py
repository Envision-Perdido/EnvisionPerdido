import json
import types
import calendar
from pathlib import Path
from datetime import datetime

import pandas as pd
import pytest

from scripts.wordpress_uploader import WordPressEventUploader


class DummyResponse:
    def __init__(self, status_code=200, data=None, text=''):
        self.status_code = status_code
        self._data = data or {}
        self.text = text

    def json(self):
        return self._data


class DummySession:
    def __init__(self):
        self.post_calls = []
        self.get_calls = []

    def post(self, url, auth=None, headers=None, data=None, json=None):
        self.post_calls.append({'url': url, 'json': json, 'headers': headers})
        # Simulate event creation endpoint
        if url.endswith('/media'):
            return DummyResponse(201, {'id': 42})
        if url.endswith('/ajde_events'):
            return DummyResponse(201, {'id': 999})
        # publishing
        if '/ajde_events/' in url:
            return DummyResponse(200, {})
        return DummyResponse(500, {}, text='not found')

    def get(self, url, timeout=30):
        self.get_calls.append(url)
        return DummyResponse(200, {'name': 'Test Location'})


def compute_expected_epoch(start_iso: str, tz_name: str = 'America/Chicago') -> int:
    # Mirror parse_event_metadata logic: treat naive as local tz, then remove tzinfo and take timestamp as if UTC
    dt = pd.to_datetime(start_iso)
    try:
        from zoneinfo import ZoneInfo
        local_tz = ZoneInfo(tz_name)
    except Exception:
        from dateutil.tz import gettz as ZoneInfo
        local_tz = ZoneInfo(tz_name)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=local_tz)

    local_naive = dt.replace(tzinfo=None)
    return int(calendar.timegm(local_naive.timetuple()))


def test_parse_event_metadata_naive_datetime():
    uploader = WordPressEventUploader('https://example.org', 'user', 'pass')

    event_row = {
        'start': '2025-09-15 10:00:00',
        'end': '2025-09-15 11:00:00',
        'location': 'Town Hall',
        'url': 'http://example.org/event1',
        'title': 'Community Meeting'
    }

    # Monkeypatch create_or_get_location to avoid network
    uploader.create_or_get_location = lambda name: 7

    meta = uploader.parse_event_metadata(event_row)

    assert 'evcal_srow' in meta
    assert 'evcal_erow' in meta
    assert meta['evcal_start_date'] == '2025-09-15'
    assert meta['evcal_start_time_ampm'] in ('am', 'pm')

    expected = compute_expected_epoch(event_row['start'])
    assert int(meta['evcal_srow']) == expected


def test_parse_event_metadata_aware_datetime():
    uploader = WordPressEventUploader('https://example.org', 'user', 'pass')
    # ISO with timezone
    event_row = {
        'start': '2025-11-01T09:00:00-05:00',
        'end': '2025-11-01T10:00:00-05:00',
        'location': 'Main St',
        'url': 'http://example.org/event2',
    }

    uploader.create_or_get_location = lambda name: None
    meta = uploader.parse_event_metadata(event_row)
    assert 'evcal_srow' in meta


def test_upload_image_and_create_event(monkeypatch, tmp_path):
    uploader = WordPressEventUploader('https://example.org', 'user', 'pass')

    dummy_sess = DummySession()
    uploader.session = dummy_sess

    # Simulate downloading an image from URL by monkeypatching requests.get
    class ImgResp:
        def __init__(self):
            self.content = b'JPEGDATA'
            self.status_code = 200

        def raise_for_status(self):
            return None

    import requests

    monkeypatch.setattr(requests, 'get', lambda url, timeout=30: ImgResp())

    # Test upload_image with URL
    media_id = uploader.upload_image('https://example.org/image.jpg', title='T')
    assert media_id == 42

    # Test create_event uses metadata and returns id
    event_row = {
        'title': 'Test Event',
        'description': 'desc',
        'start': '2025-09-20 08:00:00',
        'end': '2025-09-20 12:00:00',
        'location': 'Main St',
        'image_url': 'https://example.org/image.jpg'
    }

    # Monkeypatch upload_image to return media id without network
    uploader.upload_image = lambda src, title=None: 42

    created_id = uploader.create_event(event_row, image_column='image_url')
    assert created_id == 999
