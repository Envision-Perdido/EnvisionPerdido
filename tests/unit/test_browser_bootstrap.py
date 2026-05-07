"""Unit tests for scripts/tooling/browser_bootstrap.py.

Covers:
- Cache key generation (_get_cache_key)
- Saving and loading cached artifacts (_save_cached_artifacts / _load_cached_artifacts)
- Cache expiration (TTL exceeded returns None)
- Invalid cache JSON returns None without raising
- Cache clearing: specific source+domain and full clear
- Synchronous wrapper (bootstrap_json_api) event-loop behaviour
- Async path: cache-hit returns cached data without launching browser
- Async path: PLAYWRIGHT_AVAILABLE=False raises RuntimeError
"""

import json
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from scripts.tooling.browser_bootstrap import (
    _get_cache_key,
    _load_cached_artifacts,
    _save_cached_artifacts,
    bootstrap_json_api,
    bootstrap_json_api_async,
    clear_bootstrap_cache,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SOURCE = "test_source"
_DOMAIN = "example.com"


# ---------------------------------------------------------------------------
# Cache key
# ---------------------------------------------------------------------------


class TestGetCacheKey:
    def test_returns_16_char_hex(self):
        key = _get_cache_key(_SOURCE, _DOMAIN)
        assert len(key) == 16
        assert all(c in "0123456789abcdef" for c in key)

    def test_same_inputs_give_same_key(self):
        assert _get_cache_key(_SOURCE, _DOMAIN) == _get_cache_key(_SOURCE, _DOMAIN)

    def test_different_source_gives_different_key(self):
        assert _get_cache_key("source_a", _DOMAIN) != _get_cache_key("source_b", _DOMAIN)

    def test_different_domain_gives_different_key(self):
        assert _get_cache_key(_SOURCE, "a.com") != _get_cache_key(_SOURCE, "b.com")


# ---------------------------------------------------------------------------
# Save / load cache
# ---------------------------------------------------------------------------


class TestCacheSaveLoad:
    def test_save_then_load_returns_same_data(self, tmp_path):
        artifacts = {"endpoint": "https://api.example.com/events", "method": "GET"}

        with patch("scripts.tooling.browser_bootstrap._get_cache_dir", return_value=tmp_path):
            _save_cached_artifacts(_SOURCE, _DOMAIN, artifacts)
            result = _load_cached_artifacts(_SOURCE, _DOMAIN)

        assert result is not None
        assert result["endpoint"] == "https://api.example.com/events"

    def test_load_returns_none_when_no_file(self, tmp_path):
        with patch("scripts.tooling.browser_bootstrap._get_cache_dir", return_value=tmp_path):
            result = _load_cached_artifacts(_SOURCE, _DOMAIN)
        assert result is None

    def test_save_adds_created_at_timestamp(self, tmp_path):
        artifacts = {"endpoint": "https://api.example.com/events"}

        with patch("scripts.tooling.browser_bootstrap._get_cache_dir", return_value=tmp_path):
            _save_cached_artifacts(_SOURCE, _DOMAIN, artifacts)
            result = _load_cached_artifacts(_SOURCE, _DOMAIN)

        assert "created_at" in result
        # Should parse without raising
        datetime.fromisoformat(result["created_at"])

    def test_expired_cache_returns_none(self, tmp_path):
        artifacts = {"endpoint": "https://api.example.com/events"}
        old_time = (datetime.now() - timedelta(hours=25)).isoformat()
        artifacts["created_at"] = old_time

        cache_key = _get_cache_key(_SOURCE, _DOMAIN)
        cache_file = tmp_path / f"{cache_key}.json"
        cache_file.write_text(json.dumps(artifacts))

        with patch("scripts.tooling.browser_bootstrap._get_cache_dir", return_value=tmp_path):
            result = _load_cached_artifacts(_SOURCE, _DOMAIN, ttl_hours=24)

        assert result is None

    def test_fresh_cache_within_ttl_returns_data(self, tmp_path):
        artifacts = {"endpoint": "https://api.example.com/events"}
        recent_time = (datetime.now() - timedelta(hours=1)).isoformat()
        artifacts["created_at"] = recent_time

        cache_key = _get_cache_key(_SOURCE, _DOMAIN)
        cache_file = tmp_path / f"{cache_key}.json"
        cache_file.write_text(json.dumps(artifacts))

        with patch("scripts.tooling.browser_bootstrap._get_cache_dir", return_value=tmp_path):
            result = _load_cached_artifacts(_SOURCE, _DOMAIN, ttl_hours=24)

        assert result is not None
        assert result["endpoint"] == "https://api.example.com/events"

    def test_invalid_json_cache_returns_none(self, tmp_path):
        cache_key = _get_cache_key(_SOURCE, _DOMAIN)
        cache_file = tmp_path / f"{cache_key}.json"
        cache_file.write_text("{this is not valid json")
        with patch("scripts.tooling.browser_bootstrap._get_cache_dir", return_value=tmp_path):
            result = _load_cached_artifacts(_SOURCE, _DOMAIN)

        assert result is None

    def test_cache_with_missing_created_at_returns_none(self, tmp_path):
        # An artifact without created_at should fail TTL check gracefully
        artifacts = {"endpoint": "https://api.example.com/events"}
        cache_key = _get_cache_key(_SOURCE, _DOMAIN)
        cache_file = tmp_path / f"{cache_key}.json"
        cache_file.write_text(json.dumps(artifacts))

        with patch("scripts.tooling.browser_bootstrap._get_cache_dir", return_value=tmp_path):
            result = _load_cached_artifacts(_SOURCE, _DOMAIN)

        assert result is None


# ---------------------------------------------------------------------------
# Cache clearing
# ---------------------------------------------------------------------------


class TestClearBootstrapCache:
    def test_clear_specific_source_domain(self, tmp_path):
        artifacts = {"endpoint": "https://api.example.com/events"}

        with patch("scripts.tooling.browser_bootstrap._get_cache_dir", return_value=tmp_path):
            _save_cached_artifacts(_SOURCE, _DOMAIN, artifacts)
            clear_bootstrap_cache(source_name=_SOURCE, domain=_DOMAIN)
            result = _load_cached_artifacts(_SOURCE, _DOMAIN)

        assert result is None

    def test_clear_all_removes_all_files(self, tmp_path):
        artifacts = {"endpoint": "https://api.example.com/events"}

        with patch("scripts.tooling.browser_bootstrap._get_cache_dir", return_value=tmp_path):
            _save_cached_artifacts("src1", "a.com", dict(artifacts))
            _save_cached_artifacts("src2", "b.com", dict(artifacts))

        # Clear all — pass no arguments
        with patch("scripts.tooling.browser_bootstrap._get_cache_dir", return_value=tmp_path):
            clear_bootstrap_cache()

        remaining = list(tmp_path.glob("*.json"))
        assert remaining == []

    def test_clear_nonexistent_source_does_not_raise(self, tmp_path):
        with patch("scripts.tooling.browser_bootstrap._get_cache_dir", return_value=tmp_path):
            clear_bootstrap_cache(source_name="nonexistent", domain="nowhere.com")


# ---------------------------------------------------------------------------
# Async bootstrap — cache-hit path
# ---------------------------------------------------------------------------


class TestBootstrapJsonApiAsync:
    @pytest.mark.asyncio
    async def test_returns_cached_artifacts_without_launching_browser(self, tmp_path):
        cached = {
            "endpoint": "https://api.example.com/events",
            "method": "GET",
            "headers": {},
            "cookies": [],
            "created_at": datetime.now().isoformat(),
        }

        with patch("scripts.tooling.browser_bootstrap._get_cache_dir", return_value=tmp_path):
            _save_cached_artifacts(_SOURCE, _DOMAIN, cached)

            with patch("scripts.tooling.browser_bootstrap.PLAYWRIGHT_AVAILABLE", True):
                with patch("scripts.tooling.browser_bootstrap.async_playwright") as mock_pw:
                    result = await bootstrap_json_api_async(
                        url=f"https://{_DOMAIN}/events",
                        source_name=_SOURCE,
                    )

                # Browser should NOT have been launched on cache-hit
                mock_pw.assert_not_called()

        assert result is not None
        assert result["endpoint"] == "https://api.example.com/events"

    @pytest.mark.asyncio
    async def test_raises_runtime_error_when_playwright_unavailable(self):
        with patch("scripts.tooling.browser_bootstrap.PLAYWRIGHT_AVAILABLE", False):
            with pytest.raises(RuntimeError, match="Playwright"):
                await bootstrap_json_api_async(
                    url=f"https://{_DOMAIN}/events",
                    source_name=_SOURCE,
                )


# ---------------------------------------------------------------------------
# Sync wrapper — event-loop behaviour
# ---------------------------------------------------------------------------


class TestBootstrapJsonApi:
    def test_sync_wrapper_returns_result_from_async(self, tmp_path):
        cached = {
            "endpoint": "https://api.example.com/events",
            "method": "GET",
            "headers": {},
            "cookies": [],
            "created_at": datetime.now().isoformat(),
        }

        with patch("scripts.tooling.browser_bootstrap._get_cache_dir", return_value=tmp_path):
            _save_cached_artifacts(_SOURCE, _DOMAIN, cached)

            with patch("scripts.tooling.browser_bootstrap.PLAYWRIGHT_AVAILABLE", True):
                result = bootstrap_json_api(
                    url=f"https://{_DOMAIN}/events",
                    source_name=_SOURCE,
                )

        assert result is not None
        assert result["endpoint"] == "https://api.example.com/events"

    def test_sync_wrapper_works_without_existing_event_loop(self, tmp_path):
        cached = {
            "endpoint": "https://api.example.com/events",
            "method": "GET",
            "created_at": datetime.now().isoformat(),
        }

        with patch("scripts.tooling.browser_bootstrap._get_cache_dir", return_value=tmp_path):
            _save_cached_artifacts(_SOURCE, _DOMAIN, cached)

            with patch("scripts.tooling.browser_bootstrap.PLAYWRIGHT_AVAILABLE", True):
                # Simulate no running event loop
                with patch(
                    "scripts.tooling.browser_bootstrap.asyncio.get_event_loop",
                    side_effect=RuntimeError("no event loop"),
                ):
                    result = bootstrap_json_api(
                        url=f"https://{_DOMAIN}/events",
                        source_name=_SOURCE,
                    )

        assert result is not None
