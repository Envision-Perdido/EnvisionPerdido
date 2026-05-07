"""Fetch layer for Wren Haven events.

Two strategies are supported:
1. **Playwright** — renders the Wix calendar JavaScript and returns raw HTML
   (preferred; requires ``playwright`` to be installed).
2. **REST API** — direct HTTP call to a discovered JSON endpoint
   (used as fallback when bootstrap artifacts are available).

Both paths run through :func:`fetch_events_html`, which also manages the
24-hour HTML cache via :mod:`scripts.scrapers.wren_haven.cache`.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import requests

from scripts.scrapers.wren_haven.cache import load_cached_html, save_cached_html

try:
    from playwright.async_api import async_playwright
except ImportError:
    async_playwright = None

SOURCE_URL = "https://www.wrenhavenhomestead.com/events"


# ---------------------------------------------------------------------------
# Playwright path
# ---------------------------------------------------------------------------


async def _fetch_with_playwright() -> str:
    """Render the Wix events page with Playwright and return combined HTML."""
    if async_playwright is None:
        raise RuntimeError(
            "Playwright not installed. Install with: pip install playwright"
        )

    all_html: list[str] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            await page.goto(SOURCE_URL, wait_until="networkidle", timeout=30000)
            await page.wait_for_selector("[data-hook='EVENTS_ROOT_NODE']", timeout=5000)
            all_html.append(await page.content())

            # Navigate forward 3 months to collect upcoming events.
            for _ in range(3):
                try:
                    next_button = page.locator("button[aria-label='Next month']")
                    await next_button.click()
                    await page.wait_for_timeout(1000)
                    all_html.append(await page.content())
                except Exception:
                    break
        finally:
            await browser.close()

    return "\n".join(all_html)


def fetch_events_html(force_refresh: bool = False) -> str:
    """Return event HTML, using the 24 h cache when possible."""
    cached = load_cached_html(force_refresh=force_refresh)
    if cached:
        return cached

    try:
        html = asyncio.run(_fetch_with_playwright())
        save_cached_html(html)
        return html
    except Exception as exc:
        raise RuntimeError(f"Failed to fetch Wren Haven events page: {exc}") from exc


# ---------------------------------------------------------------------------
# REST API path (used when bootstrap artifacts are present)
# ---------------------------------------------------------------------------


def _prepare_headers(artifacts: dict[str, Any]) -> dict[str, str]:
    headers: dict[str, str] = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    if artifacts.get("headers"):
        headers.update(artifacts["headers"])
    return headers


def fetch_events_from_api(
    start_date: str | None = None,
    end_date: str | None = None,
    bootstrap_artifacts: dict[str, Any] | None = None,
    max_retries: int = 3,
) -> list[dict[str, Any]]:
    """Call the Wren Haven JSON API and return raw event dicts.

    Args:
        start_date: ISO date string filter (``YYYY-MM-DD``), optional.
        end_date: ISO date string filter (``YYYY-MM-DD``), optional.
        bootstrap_artifacts: Cached endpoint / auth info from browser bootstrap.
        max_retries: Number of retry attempts with exponential back-off.

    Returns:
        List of raw event dicts; empty list if none found.

    Raises:
        RuntimeError: After all retries are exhausted.
    """
    if bootstrap_artifacts is None:
        bootstrap_artifacts = {
            "endpoint": SOURCE_URL,
            "method": "GET",
            "headers": {},
            "cookies": [],
        }

    endpoint = bootstrap_artifacts.get("endpoint", SOURCE_URL)
    method = bootstrap_artifacts.get("method", "GET")
    headers = _prepare_headers(bootstrap_artifacts)
    cookies = bootstrap_artifacts.get("cookies", [])
    body = bootstrap_artifacts.get("body")

    if not endpoint:
        raise RuntimeError("No endpoint available")

    params: dict[str, str] = {}
    request_body: Any = None

    if start_date:
        params["start"] = start_date
    if end_date:
        params["end"] = end_date

    if method.upper() == "POST" and body:
        try:
            request_body = json.loads(body) if isinstance(body, str) else body
            if start_date:
                request_body["start"] = start_date
            if end_date:
                request_body["end"] = end_date
        except (json.JSONDecodeError, TypeError):
            request_body = body

    session = requests.Session()
    last_error: Exception | None = None

    for attempt in range(max_retries):
        try:
            if attempt > 0:
                time.sleep(0.5 * attempt)

            kwargs: dict[str, Any] = {"headers": headers, "timeout": 30}
            if cookies:
                kwargs["cookies"] = {c["name"]: c["value"] for c in cookies}

            if method.upper() == "POST":
                if request_body:
                    kwargs["json"] = request_body
                response = session.post(endpoint, **kwargs)
            else:
                if params:
                    kwargs["params"] = params
                response = session.get(endpoint, **kwargs)

            response.raise_for_status()
            data = response.json()

            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                for key in ("events", "items", "results", "data"):
                    if key in data and isinstance(data[key], list):
                        return data[key]
                return [data]
            return []

        except requests.exceptions.RequestException as exc:
            last_error = exc
            if attempt < max_retries - 1:
                wait = 2**attempt
                print(f"Attempt {attempt + 1} failed: {exc}. Retrying in {wait}s...")
                time.sleep(wait)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"API response was not valid JSON: {exc}") from exc
        except Exception as exc:
            raise RuntimeError(f"Error fetching events: {exc}") from exc

    raise RuntimeError(
        f"Failed to fetch events after {max_retries} retries: {last_error}"
    )
