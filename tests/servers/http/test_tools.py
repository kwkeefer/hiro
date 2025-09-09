"""Integration tests for HttpRequestTool cookie functionality."""

import json
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from code_mcp.servers.http.config import HttpConfig
from code_mcp.servers.http.tools import HttpRequestTool


class TestHttpRequestToolCookies:
    """Test HttpRequestTool cookie merging functionality."""

    @pytest.mark.integration
    async def test_request_with_no_cookies(self):
        """Test request with no default or user cookies."""
        # Arrange
        config = HttpConfig()
        tool = HttpRequestTool(config)

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {}
            mock_response.url = "https://example.com"
            mock_response.cookies = {}
            mock_response.elapsed = timedelta(seconds=0.5)
            mock_response.encoding = "utf-8"
            mock_response.text = "success"
            mock_response.json.side_effect = Exception("No JSON")

            mock_client.return_value.__aenter__.return_value.request = AsyncMock(
                return_value=mock_response
            )

            # Act
            result = await tool.execute(url="https://example.com")

            # Assert
            assert result["request"]["cookies"] == {}

    @pytest.mark.integration
    async def test_request_with_default_cookies_only(self, tmp_path):
        """Test request with only default cookies from file."""
        # Arrange
        default_cookies = {"session_id": "default123", "tracking": "track456"}
        cookie_file = tmp_path / "cookies.json"
        cookie_file.write_text(json.dumps(default_cookies))

        config = HttpConfig(default_cookies_file=str(cookie_file))
        tool = HttpRequestTool(config)

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {}
            mock_response.url = "https://example.com"
            mock_response.cookies = {}
            mock_response.elapsed = timedelta(seconds=0.5)
            mock_response.encoding = "utf-8"
            mock_response.text = "success"
            mock_response.json.side_effect = Exception("No JSON")

            mock_client.return_value.__aenter__.return_value.request = AsyncMock(
                return_value=mock_response
            )

            # Act
            result = await tool.execute(url="https://example.com")

            # Assert
            assert result["request"]["cookies"] == default_cookies

    @pytest.mark.integration
    async def test_request_with_user_cookies_only(self):
        """Test request with only user-provided cookies."""
        # Arrange
        config = HttpConfig()
        tool = HttpRequestTool(config)
        user_cookies = {"user_session": "user123", "preference": "dark"}

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {}
            mock_response.url = "https://example.com"
            mock_response.cookies = {}
            mock_response.elapsed = timedelta(seconds=0.5)
            mock_response.encoding = "utf-8"
            mock_response.text = "success"
            mock_response.json.side_effect = Exception("No JSON")

            mock_client.return_value.__aenter__.return_value.request = AsyncMock(
                return_value=mock_response
            )

            # Act
            result = await tool.execute(url="https://example.com", cookies=user_cookies)

            # Assert
            assert result["request"]["cookies"] == user_cookies

    @pytest.mark.integration
    async def test_cookie_merging_user_overrides_default(self, tmp_path):
        """Test that user cookies override default cookies for same keys."""
        # Arrange
        default_cookies = {
            "session_id": "default123",
            "tracking": "track456",
            "lang": "en",
        }
        cookie_file = tmp_path / "cookies.json"
        cookie_file.write_text(json.dumps(default_cookies))

        config = HttpConfig(default_cookies_file=str(cookie_file))
        tool = HttpRequestTool(config)

        user_cookies = {
            "session_id": "user789",
            "preference": "dark",
        }  # Override session_id

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {}
            mock_response.url = "https://example.com"
            mock_response.cookies = {}
            mock_response.elapsed = timedelta(seconds=0.5)
            mock_response.encoding = "utf-8"
            mock_response.text = "success"
            mock_response.json.side_effect = Exception("No JSON")

            mock_client.return_value.__aenter__.return_value.request = AsyncMock(
                return_value=mock_response
            )

            # Act
            result = await tool.execute(url="https://example.com", cookies=user_cookies)

            # Assert
            expected_cookies = {
                "session_id": "user789",  # User override
                "tracking": "track456",  # Default preserved
                "lang": "en",  # Default preserved
                "preference": "dark",  # User addition
            }
            assert result["request"]["cookies"] == expected_cookies

    @pytest.mark.integration
    async def test_cookies_sent_to_httpx_client(self, tmp_path):
        """Test that merged cookies are actually sent to httpx client."""
        # Arrange
        default_cookies = {"default_key": "default_val"}
        cookie_file = tmp_path / "cookies.json"
        cookie_file.write_text(json.dumps(default_cookies))

        config = HttpConfig(default_cookies_file=str(cookie_file))
        tool = HttpRequestTool(config)

        user_cookies = {"user_key": "user_val"}
        expected_merged = {"default_key": "default_val", "user_key": "user_val"}

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {}
            mock_response.url = "https://example.com"
            mock_response.cookies = {}
            mock_response.elapsed = timedelta(seconds=0.5)
            mock_response.encoding = "utf-8"
            mock_response.text = "success"
            mock_response.json.side_effect = Exception("No JSON")

            mock_request = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.request = mock_request

            # Act
            await tool.execute(url="https://example.com", cookies=user_cookies)

            # Assert
            mock_request.assert_called_once()
            call_kwargs = mock_request.call_args[1]
            assert call_kwargs["cookies"] == expected_merged

    @pytest.mark.integration
    async def test_audit_trail_shows_merged_cookies_only(self, tmp_path):
        """Test that audit trail only shows final merged cookies, not sources."""
        # Arrange
        default_cookies = {"default": "value"}
        cookie_file = tmp_path / "cookies.json"
        cookie_file.write_text(json.dumps(default_cookies))

        config = HttpConfig(default_cookies_file=str(cookie_file))
        tool = HttpRequestTool(config)

        user_cookies = {"user": "value"}

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {}
            mock_response.url = "https://example.com"
            mock_response.cookies = {}
            mock_response.elapsed = timedelta(seconds=0.5)
            mock_response.encoding = "utf-8"
            mock_response.text = "success"
            mock_response.json.side_effect = Exception("No JSON")

            mock_client.return_value.__aenter__.return_value.request = AsyncMock(
                return_value=mock_response
            )

            # Act
            result = await tool.execute(url="https://example.com", cookies=user_cookies)

            # Assert - Only merged cookies shown, no separate default/user breakdown
            request_info = result["request"]
            assert "cookies" in request_info
            assert "cookies_default" not in request_info
            assert "cookies_user" not in request_info
            assert request_info["cookies"] == {"default": "value", "user": "value"}
