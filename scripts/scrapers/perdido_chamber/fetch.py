"""HTTP fetching layer for Perdido Chamber scraper.

Handles HTTP requests with retry logic and rate limiting.
"""

import re
import time
from typing import Callable
from urllib.parse import urljoin, urlparse

import requests
from requests.adapters import HTTPAdapter
from requests.auth import HTTPBasicAuth
from urllib3.util.retry import Retry

from .models import BASE, SOURCE_NAME

# Create session with exponential backoff
_session: requests.Session | None = None


def _get_session() -> requests.Session:
    """Get or create the global requests session with retry strategy."""
    global _session
    if _session is None:
        _session = requests.Session()

        retry_strategy = Retry(
            total=5,
            backoff_factor=0.5,
            status_forcelist=(429, 503),
            allowed_methods=["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        _session.mount("http://", adapter)
        _session.mount("https://", adapter)

        _session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472"
                    ".114 Safari/537.36"
                )
            }
        )

    return _session


def get_page_html(url: str, timeout: int = 30) -> str:
    """Fetch HTML page content with retry logic.

    Args:
        url: URL to fetch
        timeout: Request timeout in seconds

    Returns:
        HTML content as string

    Raises:
        requests.RequestException: If request fails
    """
    session = _get_session()
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    return response.text


def get_page_headers(url: str, timeout: int = 15) -> int:
    """Fetch HTTP HEAD to check status code (usually to verify existence).

    Args:
        url: URL to check
        timeout: Request timeout in seconds

    Returns:
        HTTP status code

    Raises:
        requests.RequestException: If request fails
    """
    session = _get_session()
    response = session.head(url, timeout=timeout, allow_redirects=True)
    return response.status_code


def fetch_ics_content(url: str, timeout: int = 30) -> bytes:
    """Fetch ICS file content.

    Args:
        url: URL to ICS file
        timeout: Request timeout in seconds

    Returns:
        ICS file content as bytes

    Raises:
        requests.RequestException: If request fails
    """
    session = _get_session()
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    return response.content
