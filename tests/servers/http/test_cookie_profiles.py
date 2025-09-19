"""Tests for cookie profile integration in HTTP tools."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from hiro.servers.http.config import HttpConfig
from hiro.servers.http.cookie_sessions import CookieSessionProvider
from hiro.servers.http.tools import HttpRequestTool


@pytest.mark.asyncio
class TestCookieProfileIntegration:
    """Test cookie profile functionality in HttpRequestTool."""

    @pytest.fixture
    def mock_cookie_provider(self):
        """Create a mock cookie session provider."""
        provider = Mock(spec=CookieSessionProvider)
        return provider

    @pytest.fixture
    def http_config(self):
        """Create HTTP configuration for testing."""
        return HttpConfig(
            proxy_url="http://localhost:8080",
            timeout=30.0,
            verify_ssl=False,
            tracing_headers={"X-Test": "value"},
        )

    @pytest.fixture
    def http_tool_with_cookie_provider(self, http_config, mock_cookie_provider):
        """Create HTTP tool with cookie provider."""
        return HttpRequestTool(
            config=http_config,
            cookie_provider=mock_cookie_provider,
        )

    @pytest.mark.asyncio
    async def test_cookie_profile_loading(
        self, http_tool_with_cookie_provider, mock_cookie_provider
    ):
        """Test that cookie profiles are loaded and used correctly."""
        # Setup mock cookie provider response
        mock_cookie_provider.get_resource = AsyncMock(
            return_value={
                "cookies": {
                    "session_id": "abc123",
                    "auth_token": "secret_token",
                },
                "session_name": "test_profile",
                "description": "Test session",
                "last_updated": "2024-01-01T00:00:00Z",
                "from_cache": False,
            }
        )

        # Mock httpx to capture the request
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {"Content-Type": "application/json"}
            mock_response.cookies = {}
            mock_response.elapsed.total_seconds.return_value = 0.5
            mock_response.encoding = "utf-8"
            mock_response.text = '{"success": true}'
            mock_response.json.return_value = {"success": True}
            mock_response.url = "https://example.com/api"
            mock_response.content = b'{"success": true}'

            mock_instance = mock_client.return_value.__aenter__.return_value
            mock_instance.request = AsyncMock(return_value=mock_response)

            # Execute request with cookie profile
            result = await http_tool_with_cookie_provider.execute(
                url="https://example.com/api",
                cookie_profile="test_profile",
            )

            # Verify cookie provider was called
            mock_cookie_provider.get_resource.assert_called_once_with(
                "cookie-session://test_profile"
            )

            # Verify cookies were included in the request
            mock_instance.request.assert_called_once()
            call_kwargs = mock_instance.request.call_args.kwargs
            assert call_kwargs["cookies"] == {
                "session_id": "abc123",
                "auth_token": "secret_token",
            }

            # Verify response includes profile info
            assert result["request"]["cookie_profile"] == "test_profile"

    @pytest.mark.asyncio
    async def test_cookie_profile_merge_with_manual_cookies(
        self, http_tool_with_cookie_provider, mock_cookie_provider
    ):
        """Test that manual cookies override profile cookies with warning."""
        # Setup mock cookie provider response
        mock_cookie_provider.get_resource = AsyncMock(
            return_value={
                "cookies": {
                    "session_id": "profile_session",
                    "auth_token": "profile_token",
                    "theme": "dark",
                },
                "session_name": "test_profile",
            }
        )

        # Mock httpx
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {}
            mock_response.cookies = {}
            mock_response.elapsed.total_seconds.return_value = 0.5
            mock_response.encoding = "utf-8"
            mock_response.text = "OK"
            mock_response.json.side_effect = ValueError("Not JSON")
            mock_response.url = "https://example.com"
            mock_response.content = b"OK"

            mock_instance = mock_client.return_value.__aenter__.return_value
            mock_instance.request = AsyncMock(return_value=mock_response)

            # Execute with both profile and manual cookies
            with patch("hiro.servers.http.tools.logger") as mock_logger:
                await http_tool_with_cookie_provider.execute(
                    url="https://example.com",
                    cookie_profile="test_profile",
                    cookies='{"session_id": "manual_session", "new_cookie": "new_value"}',
                )

                # Verify warning was logged for overwritten cookies
                mock_logger.warning.assert_called_once()
                warning_msg = mock_logger.warning.call_args[0][0]
                assert "session_id" in warning_msg
                assert "test_profile" in warning_msg

            # Verify merged cookies (manual takes precedence)
            call_kwargs = mock_instance.request.call_args.kwargs
            assert call_kwargs["cookies"] == {
                "session_id": "manual_session",  # Manual override
                "auth_token": "profile_token",  # From profile
                "theme": "dark",  # From profile
                "new_cookie": "new_value",  # New from manual
            }

    @pytest.mark.asyncio
    async def test_cookie_profile_not_configured(self, http_config):
        """Test error when cookie profiles are used but not configured."""
        # Create tool without cookie provider
        tool = HttpRequestTool(config=http_config, cookie_provider=None)

        with pytest.raises(Exception) as exc_info:
            await tool.execute(
                url="https://example.com",
                cookie_profile="test_profile",
            )

        assert "Cookie profiles not configured" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_cookie_profile_not_found(
        self, http_tool_with_cookie_provider, mock_cookie_provider
    ):
        """Test error when specified cookie profile doesn't exist."""
        # Setup mock to raise error
        mock_cookie_provider.get_resource = AsyncMock(
            side_effect=Exception("Cookie session not found: nonexistent")
        )

        with pytest.raises(Exception) as exc_info:
            await http_tool_with_cookie_provider.execute(
                url="https://example.com",
                cookie_profile="nonexistent",
            )

        assert "nonexistent" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_cookie_profile_with_error(
        self, http_tool_with_cookie_provider, mock_cookie_provider
    ):
        """Test handling when cookie profile returns an error."""
        # Setup mock with error in response
        mock_cookie_provider.get_resource = AsyncMock(
            return_value={
                "cookies": {},
                "error": "Cookie file not found",
                "session_name": "test_profile",
            }
        )

        with pytest.raises(Exception) as exc_info:
            await http_tool_with_cookie_provider.execute(
                url="https://example.com",
                cookie_profile="test_profile",
            )

        assert "Cookie file not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_only_manual_cookies(self, http_tool_with_cookie_provider):
        """Test that manual cookies work without profiles."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {}
            mock_response.cookies = {}
            mock_response.elapsed.total_seconds.return_value = 0.5
            mock_response.encoding = "utf-8"
            mock_response.text = "OK"
            mock_response.json.side_effect = ValueError("Not JSON")
            mock_response.url = "https://example.com"
            mock_response.content = b"OK"

            mock_instance = mock_client.return_value.__aenter__.return_value
            mock_instance.request = AsyncMock(return_value=mock_response)

            # Execute with only manual cookies
            result = await http_tool_with_cookie_provider.execute(
                url="https://example.com",
                cookies='{"manual": "cookie"}',
            )

            # Verify only manual cookies are used
            call_kwargs = mock_instance.request.call_args.kwargs
            assert call_kwargs["cookies"] == {"manual": "cookie"}
            assert result["request"]["cookie_profile"] is None
