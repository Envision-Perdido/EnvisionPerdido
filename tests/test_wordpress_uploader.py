import calendar
import hashlib
import json

import pandas as pd

from scripts.wordpress_uploader import WordPressEventUploader


class DummyResponse:
    def __init__(self, status_code=200, data=None, text=""):
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
        self.post_calls.append({"url": url, "json": json, "headers": headers})
        # Simulate event creation endpoint
        if url.endswith("/media"):
            return DummyResponse(201, {"id": 42})
        if url.endswith("/ajde_events"):
            return DummyResponse(201, {"id": 999})
        # publishing or media update
        if "/ajde_events/" in url or "/media/" in url:
            return DummyResponse(200, {})
        return DummyResponse(500, {}, text="not found")

    def get(self, url, timeout=30, auth=None, params=None):
        self.get_calls.append(url)
        # For UID queries, return empty (no duplicates found)
        if params and params.get("meta_key") == "_event_uid":
            return DummyResponse(200, [])
        # For media search queries, return empty (no existing media by default)
        if url.endswith("/media") and params and "search" in params:
            return DummyResponse(200, [])
        return DummyResponse(200, {"name": "Test Location"})


def compute_expected_epoch(start_iso: str, tz_name: str = "America/Chicago") -> int:
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
    uploader = WordPressEventUploader("https://example.org", "user", "pass")

    event_row = {
        "start": "2025-09-15 10:00:00",
        "end": "2025-09-15 11:00:00",
        "location": "Town Hall",
        "url": "http://example.org/event1",
        "title": "Community Meeting",
    }

    # Monkeypatch create_or_get_location to avoid network
    uploader.create_or_get_location = lambda name: 7

    meta = uploader.parse_event_metadata(event_row)

    assert "evcal_srow" in meta
    assert "evcal_erow" in meta
    assert meta["evcal_start_date"] == "2025-09-15"
    assert meta["evcal_start_time_ampm"] in ("am", "pm")

    expected = compute_expected_epoch(event_row["start"])
    assert int(meta["evcal_srow"]) == expected


def test_parse_event_metadata_aware_datetime():
    uploader = WordPressEventUploader("https://example.org", "user", "pass")
    # ISO with timezone
    event_row = {
        "start": "2025-11-01T09:00:00-05:00",
        "end": "2025-11-01T10:00:00-05:00",
        "location": "Main St",
        "url": "http://example.org/event2",
    }

    uploader.create_or_get_location = lambda name: None
    meta = uploader.parse_event_metadata(event_row)
    assert "evcal_srow" in meta


def test_upload_image_and_create_event(monkeypatch, tmp_path):
    uploader = WordPressEventUploader("https://example.org", "user", "pass")

    dummy_sess = DummySession()
    uploader.session = dummy_sess

    # Simulate downloading an image from URL by monkeypatching requests.get
    class ImgResp:
        def __init__(self):
            self.content = b"JPEGDATA"
            self.status_code = 200

        def raise_for_status(self):
            return None

    import requests

    monkeypatch.setattr(requests, "get", lambda url, timeout=30: ImgResp())

    # Test upload_image with URL
    media_id = uploader.upload_image("https://example.org/image.jpg", title="T")
    assert media_id == 42

    # Test create_event uses metadata and returns id
    event_row = pd.Series(
        {
            "title": "Test Event",
            "description": "desc",
            "start": "2025-09-20 08:00:00",
            "end": "2025-09-20 12:00:00",
            "location": "Main St",
            "image_url": "https://example.org/image.jpg",
            "uid": "test-event-123",  # Add UID so it's not skipped as duplicate
            "url": "http://example.org/event",  # URL field needed for metadata
        }
    )

    # Monkeypatch upload_image and create_or_get_location to avoid network calls
    uploader.upload_image = lambda src, title=None: 42
    uploader.create_or_get_location = lambda name: 7  # Return mock location ID

    created_id = uploader.create_event(event_row, image_column="image_url")
    assert created_id == 999


# ---------------------------------------------------------------------------
# Image deduplication tests
# ---------------------------------------------------------------------------

IMAGE_BYTES = b"FAKEJPEGDATA"
IMAGE_HASH = hashlib.sha256(IMAGE_BYTES).hexdigest()


def test_get_image_hash():
    """_get_image_hash returns the correct SHA-256 hex digest."""
    uploader = WordPressEventUploader("https://example.org", "user", "pass")
    assert uploader._get_image_hash(IMAGE_BYTES) == IMAGE_HASH


def test_hash_cache_roundtrip(tmp_path):
    """_save_hash_cache / _load_hash_cache round-trip correctly."""
    uploader = WordPressEventUploader("https://example.org", "user", "pass")
    uploader._hash_cache_path = tmp_path / "media_hash_cache.json"

    # Initially empty
    assert uploader._load_hash_cache() == {}

    # Save and reload
    cache = {IMAGE_HASH: 55}
    uploader._save_hash_cache(cache)
    loaded = uploader._load_hash_cache()
    assert loaded == {IMAGE_HASH: 55}


def test_find_existing_media_by_hash_uses_local_cache(tmp_path):
    """find_existing_media_by_hash returns cached media ID without calling the API."""
    uploader = WordPressEventUploader("https://example.org", "user", "pass")
    uploader._hash_cache_path = tmp_path / "media_hash_cache.json"
    uploader.session = DummySession()

    # Pre-populate cache
    cache = {IMAGE_HASH: 77}
    uploader._save_hash_cache(cache)

    result = uploader.find_existing_media_by_hash(IMAGE_HASH)
    assert result == 77

    # No WP API call should have been made
    assert uploader.session.get_calls == []


def test_find_existing_media_by_hash_queries_wp_and_caches(tmp_path):
    """find_existing_media_by_hash searches WP API on cache miss and updates cache."""
    uploader = WordPressEventUploader("https://example.org", "user", "pass")
    uploader._hash_cache_path = tmp_path / "media_hash_cache.json"

    # WP returns one matching media attachment
    class HashSearchSession(DummySession):
        def get(self, url, timeout=30, auth=None, params=None):
            self.get_calls.append(url)
            if url.endswith("/media") and params and "search" in params:
                return DummyResponse(200, [{"id": 99, "source_url": "https://example.org/img.jpg"}])
            return DummyResponse(200, [])

    uploader.session = HashSearchSession()

    result = uploader.find_existing_media_by_hash(IMAGE_HASH)
    assert result == 99

    # Cache should be populated now
    assert uploader._load_hash_cache()[IMAGE_HASH] == 99


def test_find_existing_media_by_filename(tmp_path):
    """find_existing_media_by_filename matches by filename in source_url."""
    uploader = WordPressEventUploader("https://example.org", "user", "pass")
    uploader._hash_cache_path = tmp_path / "media_hash_cache.json"

    class FilenameSearchSession(DummySession):
        def get(self, url, timeout=30, auth=None, params=None):
            self.get_calls.append(url)
            if url.endswith("/media") and params and "search" in params:
                return DummyResponse(
                    200, [{"id": 88, "source_url": "https://example.org/event_banner.jpg", "slug": "event_banner"}]
                )
            return DummyResponse(200, [])

    uploader.session = FilenameSearchSession()

    result = uploader.find_existing_media_by_filename("event_banner.jpg")
    assert result == 88


def test_upload_image_reuses_hash_match(monkeypatch, tmp_path):
    """upload_image returns existing media ID when a hash match is found (no upload)."""
    uploader = WordPressEventUploader("https://example.org", "user", "pass")
    uploader._hash_cache_path = tmp_path / "media_hash_cache.json"

    class ImgResp:
        content = IMAGE_BYTES
        status_code = 200

        def raise_for_status(self):
            return None

    import requests

    monkeypatch.setattr(requests, "get", lambda url, timeout=30: ImgResp())

    # Pre-populate local cache so no WP API call is needed
    uploader._save_hash_cache({IMAGE_HASH: 55})
    dummy_sess = DummySession()
    uploader.session = dummy_sess

    media_id = uploader.upload_image("https://example.org/image.jpg")
    assert media_id == 55

    # Must NOT have POSTed to /media (no upload)
    upload_calls = [c for c in dummy_sess.post_calls if c["url"].endswith("/media")]
    assert upload_calls == []


def test_upload_image_reuses_filename_match(monkeypatch, tmp_path):
    """upload_image returns existing media ID on filename match and updates cache."""
    uploader = WordPressEventUploader("https://example.org", "user", "pass")
    uploader._hash_cache_path = tmp_path / "media_hash_cache.json"

    class ImgResp:
        content = IMAGE_BYTES
        status_code = 200

        def raise_for_status(self):
            return None

    import requests

    monkeypatch.setattr(requests, "get", lambda url, timeout=30: ImgResp())

    class FilenameSession(DummySession):
        def get(self, url, timeout=30, auth=None, params=None):
            self.get_calls.append(url)
            if url.endswith("/media") and params and "search" in params:
                search = params.get("search", "")
                # Hash search: return empty; filename search: return match
                if "ep_hash" in search:
                    return DummyResponse(200, [])
                return DummyResponse(
                    200, [{"id": 66, "source_url": "https://example.org/image.jpg", "slug": "image"}]
                )
            return DummyResponse(200, [])

    uploader.session = FilenameSession()

    media_id = uploader.upload_image("https://example.org/image.jpg")
    assert media_id == 66

    # Cache should be updated with the hash → id mapping
    assert uploader._load_hash_cache()[IMAGE_HASH] == 66

    # Must NOT have POSTed to /media (no upload)
    upload_calls = [c for c in uploader.session.post_calls if c["url"].endswith("/media")]
    assert upload_calls == []


def test_upload_image_uploads_and_stores_hash(monkeypatch, tmp_path):
    """upload_image uploads fresh image and stores hash token in description + cache."""
    uploader = WordPressEventUploader("https://example.org", "user", "pass")
    uploader._hash_cache_path = tmp_path / "media_hash_cache.json"

    class ImgResp:
        content = IMAGE_BYTES
        status_code = 200

        def raise_for_status(self):
            return None

    import requests

    monkeypatch.setattr(requests, "get", lambda url, timeout=30: ImgResp())

    dummy_sess = DummySession()
    uploader.session = dummy_sess

    media_id = uploader.upload_image("https://example.org/image.jpg", title="My Image")
    assert media_id == 42

    # Cache should be populated
    assert uploader._load_hash_cache()[IMAGE_HASH] == 42

    # A PATCH/POST to /media/42 should have been made to store the hash token
    update_calls = [c for c in dummy_sess.post_calls if "/media/42" in c["url"]]
    assert update_calls, "Expected a POST to /media/42 to store the hash token"
    description = update_calls[0]["json"].get("description", "")
    assert f"ep_hash=SHA256:{IMAGE_HASH}" in description
