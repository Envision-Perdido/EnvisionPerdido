"""Cache layer for Wren Haven HTML fetching.

Stores rendered event page HTML to avoid redundant Playwright runs during
the 24-hour TTL window.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

CACHE_TTL_HOURS = 24
CACHE_DIR = Path(__file__).parent.parent.parent.parent / "data" / "cache" / "wren_haven"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def load_cached_html(force_refresh: bool = False) -> str | None:
    """Return cached HTML if it exists and is within TTL, else *None*."""
    cache_file = CACHE_DIR / "events.html"

    if not force_refresh and cache_file.exists():
        file_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
        age_hours = (datetime.now() - file_time).total_seconds() / 3600

        if age_hours < CACHE_TTL_HOURS:
            try:
                html = cache_file.read_text(encoding="utf-8")
                print(
                    f"[Wren Haven] Using cached HTML ({age_hours:.1f}h old) - skipping Playwright"
                )
                return html
            except OSError:
                pass
        else:
            print(
                f"[Wren Haven] Cache expired ({age_hours:.1f}h > {CACHE_TTL_HOURS}h TTL)"
                " - fetching fresh"
            )

    return None


def save_cached_html(html: str) -> None:
    """Persist *html* to the cache file (silent on error)."""
    try:
        (CACHE_DIR / "events.html").write_text(html, encoding="utf-8")
    except OSError:
        pass
