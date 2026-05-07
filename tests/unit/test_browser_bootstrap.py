"""Unit tests for bootstrap cache helpers."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from scripts.tooling import browser_bootstrap


def test_get_cache_key_is_stable() -> None:
    first = browser_bootstrap._get_cache_key("source-a", "example.com")
    second = browser_bootstrap._get_cache_key("source-a", "example.com")
    different = browser_bootstrap._get_cache_key("source-b", "example.com")

    assert first == second
    assert len(first) == 16
    assert first != different


def test_save_and_load_cached_artifacts_round_trip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(browser_bootstrap, "_get_cache_dir", lambda: tmp_path)
    artifacts = {"endpoint": "https://example.com/api/events", "headers": {"accept": "json"}}

    browser_bootstrap._save_cached_artifacts("source-a", "example.com", artifacts)
    loaded = browser_bootstrap._load_cached_artifacts("source-a", "example.com")

    assert loaded is not None
    assert loaded["endpoint"] == artifacts["endpoint"]
    assert loaded["headers"] == artifacts["headers"]
    assert "created_at" in loaded


def test_load_cached_artifacts_returns_none_for_expired_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(browser_bootstrap, "_get_cache_dir", lambda: tmp_path)
    cache_key = browser_bootstrap._get_cache_key("source-a", "example.com")
    cache_file = tmp_path / f"{cache_key}.json"
    cache_file.write_text(
        json.dumps(
            {
                "endpoint": "https://example.com/api/events",
                "created_at": (datetime.now(UTC) - timedelta(hours=30)).isoformat(),
            }
        )
    )

    assert browser_bootstrap._load_cached_artifacts("source-a", "example.com") is None


def test_load_cached_artifacts_handles_invalid_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(browser_bootstrap, "_get_cache_dir", lambda: tmp_path)
    cache_key = browser_bootstrap._get_cache_key("source-a", "example.com")
    (tmp_path / f"{cache_key}.json").write_text("{not valid json")

    loaded = browser_bootstrap._load_cached_artifacts("source-a", "example.com")

    assert loaded is None
    assert "Failed to load cached artifacts" in capsys.readouterr().out


def test_bootstrap_json_api_uses_async_helper(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    async def fake_bootstrap(url: str, previous_month_selector: str, source_name: str, **kwargs):
        captured["url"] = url
        captured["previous_month_selector"] = previous_month_selector
        captured["source_name"] = source_name
        captured["kwargs"] = kwargs
        return {"endpoint": "https://example.com/api/events"}

    monkeypatch.setattr(browser_bootstrap, "bootstrap_json_api_async", fake_bootstrap)

    result = browser_bootstrap.bootstrap_json_api(
        "https://example.com/events",
        previous_month_selector=".prev",
        source_name="source-a",
        capture_requests=2,
    )

    assert result == {"endpoint": "https://example.com/api/events"}
    assert captured == {
        "url": "https://example.com/events",
        "previous_month_selector": ".prev",
        "source_name": "source-a",
        "kwargs": {"capture_requests": 2},
    }


def test_bootstrap_json_api_creates_event_loop_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created_loop = asyncio.new_event_loop()

    async def fake_bootstrap(url: str, previous_month_selector: str, source_name: str, **kwargs):
        return {
            "url": url,
            "previous_month_selector": previous_month_selector,
            "source_name": source_name,
            "kwargs": kwargs,
        }

    monkeypatch.setattr(browser_bootstrap, "bootstrap_json_api_async", fake_bootstrap)
    monkeypatch.setattr(browser_bootstrap.asyncio, "get_event_loop", lambda: (_ for _ in ()).throw(RuntimeError))
    monkeypatch.setattr(browser_bootstrap.asyncio, "new_event_loop", lambda: created_loop)

    try:
        result = browser_bootstrap.bootstrap_json_api("https://example.com/events", source_name="source-b")
    finally:
        created_loop.close()

    assert result["source_name"] == "source-b"


def test_clear_bootstrap_cache_removes_single_cache_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(browser_bootstrap, "_get_cache_dir", lambda: tmp_path)
    browser_bootstrap._save_cached_artifacts(
        "source-a", "example.com", {"endpoint": "https://example.com/api/events"}
    )
    browser_bootstrap._save_cached_artifacts(
        "source-b", "example.com", {"endpoint": "https://example.com/api/other"}
    )

    browser_bootstrap.clear_bootstrap_cache("source-a", "example.com")

    remaining_files = sorted(p.name for p in tmp_path.glob("*.json"))
    expected_remaining = [
        f"{browser_bootstrap._get_cache_key('source-b', 'example.com')}.json"
    ]
    assert remaining_files == expected_remaining


def test_clear_bootstrap_cache_removes_all_cache_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(browser_bootstrap, "_get_cache_dir", lambda: tmp_path)
    browser_bootstrap._save_cached_artifacts(
        "source-a", "example.com", {"endpoint": "https://example.com/api/events"}
    )

    browser_bootstrap.clear_bootstrap_cache()

    assert list(tmp_path.glob("*.json")) == []


def test_bootstrap_json_api_async_returns_cached_artifacts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cached = {"endpoint": "https://example.com/api/events", "created_at": datetime.now(UTC).isoformat()}

    def fail_if_called():
        raise AssertionError("Playwright should not be invoked when cache is valid")

    monkeypatch.setattr(browser_bootstrap, "PLAYWRIGHT_AVAILABLE", True)
    monkeypatch.setattr(browser_bootstrap, "_load_cached_artifacts", lambda *args, **kwargs: cached)
    monkeypatch.setattr(browser_bootstrap, "async_playwright", fail_if_called)

    result = asyncio.run(
        browser_bootstrap.bootstrap_json_api_async(
            "https://example.com/events",
            source_name="source-a",
        )
    )

    assert result == cached


def test_bootstrap_json_api_async_discovers_endpoint_and_caches_artifacts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_saved: dict[str, object] = {}

    class FakeRequest:
        resource_type = "fetch"
        url = "https://example.com/api/events"
        method = "POST"
        headers = {
            "authorization": "Bearer token",
            "content-type": "application/json",
            "accept": "application/json",
            "user-agent": "pytest",
        }
        post_data = '{"month":"2026-05"}'

    class FakeButton:
        async def is_visible(self) -> bool:
            return True

        async def click(self) -> None:
            return None

    class FakeLocator:
        first = FakeButton()

    class FakePage:
        def __init__(self) -> None:
            self._handler = None

        def on(self, event: str, handler) -> None:
            assert event == "request"
            self._handler = handler

        async def goto(self, url: str, timeout: int, wait_until: str) -> None:
            assert url == "https://example.com/events"
            assert timeout == 30000
            assert wait_until == "networkidle"
            await self._handler(FakeRequest())

        def locator(self, selector: str) -> FakeLocator:
            assert selector == ".prev"
            return FakeLocator()

    class FakeContext:
        def __init__(self) -> None:
            self.page = FakePage()

        async def new_page(self) -> FakePage:
            return self.page

        async def cookies(self) -> list[dict[str, str]]:
            return [{"name": "session", "value": "abc", "domain": "example.com"}]

    class FakeBrowser:
        def __init__(self) -> None:
            self.context = FakeContext()

        async def new_context(self) -> FakeContext:
            return self.context

        async def close(self) -> None:
            return None

    class FakeChromium:
        async def launch(self, headless: bool) -> FakeBrowser:
            assert headless is True
            return FakeBrowser()

    class FakePlaywrightContextManager:
        async def __aenter__(self):
            return type("Playwright", (), {"chromium": FakeChromium()})()

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

    async def fake_sleep(_: int) -> None:
        return None

    monkeypatch.setattr(browser_bootstrap, "PLAYWRIGHT_AVAILABLE", True)
    monkeypatch.setattr(browser_bootstrap, "_load_cached_artifacts", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        browser_bootstrap,
        "_save_cached_artifacts",
        lambda source_name, domain, artifacts: captured_saved.update(
            {
                "source_name": source_name,
                "domain": domain,
                "artifacts": artifacts,
            }
        ),
    )
    monkeypatch.setattr(browser_bootstrap, "async_playwright", lambda: FakePlaywrightContextManager())
    monkeypatch.setattr(browser_bootstrap.asyncio, "sleep", fake_sleep)

    result = asyncio.run(
        browser_bootstrap.bootstrap_json_api_async(
            "https://example.com/events",
            previous_month_selector=".prev",
            source_name="source-a",
        )
    )

    assert result is not None
    assert result["endpoint"] == "https://example.com/api/events"
    assert result["method"] == "POST"
    assert result["headers"]["Authorization"] == "Bearer token"
    assert result["headers"]["content-type"] == "application/json"
    assert result["headers"]["accept"] == "application/json"
    assert result["headers"]["user-agent"] == "pytest"
    assert result["cookies"] == [{"name": "session", "value": "abc", "domain": "example.com"}]
    assert result["body"] == '{"month":"2026-05"}'
    assert result["requests_captured"] == 1
    assert captured_saved["source_name"] == "source-a"
    assert captured_saved["domain"] == "example.com"
    assert captured_saved["artifacts"]["endpoint"] == "https://example.com/api/events"
