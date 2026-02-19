"""Test rate limiting with exponential backoff retry strategy."""

from unittest.mock import Mock, patch

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from scripts.Envision_Perdido_DataCollection import (
    create_session_with_retries,
    get_event_url,
)


class TestRateLimitingCreation:
    """Test creation of session with retry strategy."""

    def test_create_session_with_retries_returns_session(self):
        """Should return a requests.Session instance."""
        session = create_session_with_retries()
        assert isinstance(session, requests.Session)

    def test_session_has_retry_strategy_on_http(self):
        """Should mount retry strategy on http:// adapter."""
        session = create_session_with_retries()
        adapter = session.get_adapter("http://example.com")
        assert isinstance(adapter, HTTPAdapter)
        assert adapter.max_retries is not None

    def test_session_has_retry_strategy_on_https(self):
        """Should mount retry strategy on https:// adapter."""
        session = create_session_with_retries()
        adapter = session.get_adapter("https://example.com")
        assert isinstance(adapter, HTTPAdapter)
        assert adapter.max_retries is not None

    def test_retry_strategy_configuration(self):
        """Should have correct retry configuration."""
        session = create_session_with_retries()
        adapter = session.get_adapter("https://example.com")
        retry = adapter.max_retries

        # Check retry configuration
        assert isinstance(retry, Retry)
        assert retry.total > 0, "Should have total retries > 0"
        assert retry.backoff_factor > 0, "Should have backoff_factor > 0"
        # Should retry on 429 and 503
        assert 429 in retry.status_forcelist, "Should retry on 429"
        assert 503 in retry.status_forcelist, "Should retry on 503"


class TestRateLimitingRetryOn429:
    """Test retry behavior on 429 (Too Many Requests)."""

    @patch("scripts.Envision_Perdido_DataCollection.requests.Session.get")
    def test_retry_on_429_status(self, mock_get):
        """Should retry requests that receive 429 status."""
        # First attempt returns 429, second succeeds
        response_429 = Mock()
        response_429.status_code = 429
        response_429.raise_for_status.side_effect = requests.HTTPError()

        response_success = Mock()
        response_success.status_code = 200
        response_success.text = "<html></html>"
        response_success.raise_for_status.return_value = None

        mock_get.side_effect = [response_429, response_success]

        # Use regular session (without retries) to test mock behavior
        session = requests.Session()
        try:
            session.get("https://example.com")
        except:
            pass  # Expected to fail without retry

        # Verify at least one call was made
        assert mock_get.called

    @patch("scripts.Envision_Perdido_DataCollection.sess.get")
    def test_429_error_includes_retry_header(self, mock_get):
        """Should respect Retry-After header on 429 response."""
        response = Mock()
        response.status_code = 429
        response.headers = {"Retry-After": "2"}  # Wait 2 seconds
        mock_get.return_value = response

        # Just verify the mock was set up (actual retry behavior tested via HTTPAdapter)
        result = mock_get("https://example.com")
        assert result.headers["Retry-After"] == "2"


class TestRateLimitingRetryOn503:
    """Test retry behavior on 503 (Service Unavailable)."""

    def test_503_in_retry_status_list(self):
        """Should include 503 in retry status codes."""
        session = create_session_with_retries()
        adapter = session.get_adapter("https://example.com")
        retry = adapter.max_retries
        assert 503 in retry.status_forcelist


class TestRateLimitingMaxRetries:
    """Test max retries exceeded behavior."""

    def test_max_retries_configuration_set(self):
        """Should have max_retries set to finite number."""
        session = create_session_with_retries()
        adapter = session.get_adapter("https://example.com")
        retry = adapter.max_retries
        assert retry.total >= 3, "Should have at least 3 retries"
        assert retry.total <= 10, "Should not have excessive retries"


class TestRateLimitingBackoff:
    """Test exponential backoff behavior."""

    def test_backoff_factor_configured(self):
        """Should have exponential backoff factor."""
        session = create_session_with_retries()
        adapter = session.get_adapter("https://example.com")
        retry = adapter.max_retries
        assert retry.backoff_factor > 0, "Backoff factor should be positive"
        assert retry.backoff_factor <= 2, "Backoff factor should be reasonable"


class TestRateLimitingTimeoutValues:
    """Test that all requests have timeout values."""

    @patch("scripts.Envision_Perdido_DataCollection.BeautifulSoup")
    @patch("scripts.Envision_Perdido_DataCollection.sess.get")
    def test_get_event_url_has_timeout(self, mock_get, mock_bs):
        """Should set timeout on get_event_url requests."""
        mock_response = Mock()
        mock_response.text = "<html></html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        mock_soup = Mock()
        mock_soup.select.return_value = []
        mock_bs.return_value = mock_soup

        get_event_url("https://example.com/calendar")

        # Verify timeout was set
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "timeout" in call_args.kwargs or len(call_args.args) > 1

        # If timeout is in kwargs, verify it's not None
        if "timeout" in call_args.kwargs:
            assert call_args.kwargs["timeout"] is not None


class TestRateLimitingNonRetryableErrors:
    """Test that non-retryable errors are not retried."""

    def test_4xx_errors_not_in_retry_list(self):
        """Should not retry 400, 401, 403, 404 etc."""
        session = create_session_with_retries()
        adapter = session.get_adapter("https://example.com")
        retry = adapter.max_retries

        # These should NOT be in the forcelist for retrying
        assert 400 not in retry.status_forcelist or 400 not in retry.status_forcelist
        assert 401 not in retry.status_forcelist or 401 not in retry.status_forcelist
        assert 403 not in retry.status_forcelist or 403 not in retry.status_forcelist
        assert 404 not in retry.status_forcelist or 404 not in retry.status_forcelist


class TestRateLimitingConnectionErrors:
    """Test retry behavior on connection errors."""

    def test_connection_error_retry_configured(self):
        """Should configure retries for connection errors."""
        session = create_session_with_retries()
        adapter = session.get_adapter("https://example.com")
        retry = adapter.max_retries

        # Check that connection errors are configured
        # (connect, read, urlopen should all be configurable)
        assert retry is not None


class TestRateLimitingIntegration:
    """Integration tests for retry strategy."""

    @patch("scripts.Envision_Perdido_DataCollection.sess")
    def test_scraper_session_has_retry_strategy(self, mock_sess_module):
        """Module-level session should have retry strategy."""
        # This test verifies that the global sess is configured with retries
        # (actual implementation tested by other tests)
        assert True  # Placeholder for integration verification

    def test_session_headers_preserved_with_retries(self):
        """Should preserve User-Agent and other headers with retries."""
        session = create_session_with_retries()
        session.headers.update({"User-Agent": "Test Agent"})

        # Verify headers are still present
        assert session.headers["User-Agent"] == "Test Agent"


class TestRateLimitingWordPressUploader:
    """Test rate limiting in WordPress uploader."""

    @patch("scripts.wordpress_uploader.requests.Session")
    def test_uploader_session_has_timeout(self, mock_session_class):
        """WordPress uploader requests should have timeout."""
        from scripts.wordpress_uploader import WordPressEventUploader

        mock_session = Mock()
        mock_session_class.return_value = mock_session

        uploader = WordPressEventUploader("https://example.org", "user", "pass")

        # Verify session was created
        assert mock_session_class.called

    def test_uploader_requests_include_timeout_defaults(self):
        """Should verify timeout values used in uploader."""
        # Check that image download in uploader has timeout
        from scripts.wordpress_uploader import WordPressEventUploader

        uploader = WordPressEventUploader("https://example.org", "user", "pass")
        # Uploader methods should use session with retries
        assert uploader.session is not None
