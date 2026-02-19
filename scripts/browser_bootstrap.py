"""
Minimal Playwright-based bootstrap helper for discovering JSON API endpoints and auth headers.

This module uses Playwright ONLY to:
1. Navigate to a calendar page
2. Intercept network requests to discover the JSON API endpoint
3. Extract Authorization headers, cookies, and request shape
4. Cache artifacts for reuse in regular HTTP-based fetching

Usage:
    bootstrap_artifacts = bootstrap_json_api(
        url="https://www.example.com/events",
        previous_month_selector="button[aria-label='Previous month']",
        source_name="example_source"
    )
    # Returns: {'endpoint': '...', 'headers': {...}, 'cookies': [...], ...}
    # Artifacts are automatically cached with TTL
"""

import asyncio
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

try:
    from playwright.async_api import async_playwright

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


def _get_cache_dir() -> Path:
    """Get or create cache directory for bootstrap artifacts."""
    cache_dir = Path(__file__).parent.parent / "data" / "cache" / "bootstrap"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _get_cache_key(source_name: str, domain: str) -> str:
    """Generate cache key from source name and domain."""
    key = f"{source_name}:{domain}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def _load_cached_artifacts(
    source_name: str, domain: str, ttl_hours: int = 24
) -> dict[str, Any] | None:
    """Load cached bootstrap artifacts if they exist and are not expired."""
    cache_dir = _get_cache_dir()
    cache_key = _get_cache_key(source_name, domain)
    cache_file = cache_dir / f"{cache_key}.json"

    if not cache_file.exists():
        return None

    try:
        with open(cache_file) as f:
            data = json.load(f)

        # Check TTL
        created_at = datetime.fromisoformat(data.get("created_at", ""))
        if datetime.now() - created_at > timedelta(hours=ttl_hours):
            return None  # Cache expired

        return data
    except Exception as e:
        print(f"Warning: Failed to load cached artifacts for {source_name}: {e}")
        return None


def _save_cached_artifacts(source_name: str, domain: str, artifacts: dict[str, Any]) -> None:
    """Save bootstrap artifacts to cache."""
    cache_dir = _get_cache_dir()
    cache_key = _get_cache_key(source_name, domain)
    cache_file = cache_dir / f"{cache_key}.json"

    artifacts["created_at"] = datetime.now().isoformat()

    try:
        with open(cache_file, "w") as f:
            json.dump(artifacts, f, indent=2)
    except Exception as e:
        print(f"Warning: Failed to save cached artifacts for {source_name}: {e}")


async def bootstrap_json_api_async(
    url: str,
    previous_month_selector: str = "button[aria-label='Previous month']",
    source_name: str = "source",
    capture_requests: int = 1,
    headless: bool = True,
    timeout_seconds: int = 30,
) -> dict[str, Any] | None:
    """
    Bootstrap JSON API endpoint discovery using Playwright.

    Args:
        url: Calendar page URL to navigate to
        previous_month_selector: CSS selector for "previous month" button
        source_name: Name of the source (for caching)
        capture_requests: Number of request captures to attempt
        headless: Run browser in headless mode
        timeout_seconds: Timeout for page operations

    Returns:
        Dictionary with keys:
            - endpoint: URL of the JSON endpoint
            - method: HTTP method (GET/POST)
            - headers: Authorization and other required headers
            - cookies: List of cookie dicts (name, value)
            - query_params: Example query parameters if present
            - body: Example request body if POST
            - discovered_at: ISO timestamp
    """

    if not PLAYWRIGHT_AVAILABLE:
        raise RuntimeError(
            "Playwright is required for bootstrap. Install with: pip install playwright"
        )

    from urllib.parse import urlparse

    domain = urlparse(url).netloc

    # Try loading from cache first
    cached = _load_cached_artifacts(source_name, domain)
    if cached:
        print(f"Loaded cached bootstrap artifacts for {source_name} from {domain}")
        return cached

    artifacts = {
        "endpoint": None,
        "method": "GET",
        "headers": {},
        "cookies": [],
        "query_params": {},
        "body": None,
        "requests_captured": 0,
        "discovered_at": datetime.now().isoformat(),
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context()
        page = await context.new_page()

        captured_requests = []

        async def handle_request(request):
            """Capture network requests."""
            if "json" in request.resource_type.lower() or "/api/" in request.url.lower():
                captured_requests.append(
                    {
                        "url": request.url,
                        "method": request.method,
                        "headers": dict(request.headers),
                        "post_data": request.post_data,
                    }
                )

        # Listen for requests
        page.on("request", handle_request)

        try:
            # Navigate to calendar page
            await page.goto(url, timeout=timeout_seconds * 1000, wait_until="networkidle")
            print(f"Navigated to {url}")

            # Wait briefly to see initial network activity
            await asyncio.sleep(2)

            # Click "previous month" button to trigger API request
            try:
                prev_button = page.locator(previous_month_selector).first
                if await prev_button.is_visible():
                    await prev_button.click()
                    print(f"Clicked '{previous_month_selector}'")
                    # Wait for network activity
                    await asyncio.sleep(2)
            except Exception as e:
                print(f"Could not click previous month button: {e}")

            # Extract cookies
            cookies = await context.cookies()
            artifacts["cookies"] = [
                {"name": c["name"], "value": c["value"], "domain": c["domain"]} for c in cookies
            ]

            # Process captured requests - prefer API/JSON requests
            if captured_requests:
                # Sort by recency and prefer POST/JSON
                captured_requests.sort(
                    key=lambda r: (
                        r["method"] != "POST",  # Prefer POST
                        "/api/" not in r["url"].lower(),  # Prefer /api/ URLs
                    )
                )

                for i, req in enumerate(captured_requests[:capture_requests]):
                    if artifacts["endpoint"] is None:
                        artifacts["endpoint"] = req["url"]
                        artifacts["method"] = req["method"]

                        # Extract Authorization header if present
                        if "authorization" in req["headers"]:
                            artifacts["headers"]["Authorization"] = req["headers"]["authorization"]

                        # Preserve other important headers
                        for header in ["content-type", "accept", "user-agent"]:
                            if header in req["headers"]:
                                artifacts["headers"][header] = req["headers"][header]

                        if req["post_data"]:
                            artifacts["body"] = req["post_data"]

                        artifacts["requests_captured"] = len(captured_requests)
                        print(f"Discovered endpoint: {req['method']} {req['url'][:80]}...")

        except Exception as e:
            print(f"Error during bootstrap: {e}")
        finally:
            await browser.close()

    # Cache artifacts
    if artifacts["endpoint"]:
        _save_cached_artifacts(source_name, domain, artifacts)

    return artifacts if artifacts["endpoint"] else None


def bootstrap_json_api(
    url: str,
    previous_month_selector: str = "button[aria-label='Previous month']",
    source_name: str = "source",
    **kwargs,
) -> dict[str, Any] | None:
    """
    Synchronous wrapper for bootstrap_json_api_async.

    Blocks until Playwright bootstrap completes.
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(
        bootstrap_json_api_async(
            url, previous_month_selector=previous_month_selector, source_name=source_name, **kwargs
        )
    )


def clear_bootstrap_cache(source_name: str | None = None, domain: str | None = None) -> None:
    """Clear bootstrap cache for a source (or all if not specified)."""
    cache_dir = _get_cache_dir()

    if source_name and domain:
        cache_key = _get_cache_key(source_name, domain)
        cache_file = cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            cache_file.unlink()
            print(f"Cleared cache for {source_name}:{domain}")
    else:
        # Clear all
        import shutil

        if cache_dir.exists():
            shutil.rmtree(cache_dir)
            cache_dir.mkdir(parents=True, exist_ok=True)
            print("Cleared all bootstrap cache")
