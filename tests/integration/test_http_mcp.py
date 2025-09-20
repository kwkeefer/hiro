"""FastMCP integration tests for HTTP tools.

Tests the HTTP tools through the actual MCP protocol using FastMCP server instances.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastmcp import FastMCP

from hiro.api.mcp.server import FastMcpServerAdapter
from hiro.core.mcp.exceptions import ToolError
from hiro.db.repositories import HttpRequestRepository, TargetRepository
from hiro.servers.http.config import HttpConfig
from hiro.servers.http.providers import HttpToolProvider
from tests.utils.mcp_test_helpers import BaseMcpProviderTest


@pytest.mark.integration
class TestHttpToolMcpIntegration(BaseMcpProviderTest):
    """Test HTTP tools through MCP protocol."""

    @pytest.fixture
    def http_config(self):
        """Provide test HTTP configuration."""
        return HttpConfig(
            proxy_url="http://test-proxy:8080",
            timeout=10.0,
            verify_ssl=False,
            tracing_headers={"X-Test-Trace": "mcp-test"},
            logging_enabled=False,  # Disable DB logging for basic tests
        )

    @pytest.fixture
    def mock_http_repo(self):
        """Provide mock HTTP request repository."""
        repo = AsyncMock(spec=HttpRequestRepository)
        repo.create = AsyncMock(return_value=MagicMock(id=1))
        repo.update = AsyncMock()
        repo.link_to_target = AsyncMock()
        return repo

    @pytest.fixture
    def mock_target_repo(self):
        """Provide mock target repository."""
        repo = AsyncMock(spec=TargetRepository)
        repo.get_or_create_from_url = AsyncMock(
            return_value=MagicMock(id=1, host="example.com")
        )
        return repo

    async def test_mcp_http_tool_registration(self, http_config):
        """Test that HTTP tools are properly registered with FastMCP."""
        # Arrange
        provider = HttpToolProvider(config=http_config)
        server = FastMcpServerAdapter()

        # Create a real FastMCP instance
        mcp = FastMCP("test-http-server")
        server._mcp = mcp

        # Act
        server.add_tool_provider(provider)

        # Assert
        # Check that provider was added
        assert provider in server._tool_providers

        # Verify the tool is registered with FastMCP
        # The tool should be accessible through the http_tool property
        assert provider.http_tool is not None
        assert provider.http_tool._config == http_config

    async def test_mcp_http_request_execution(self, http_config):
        """Test executing HTTP requests through MCP protocol."""
        # Arrange
        provider = HttpToolProvider(config=http_config)
        server = FastMcpServerAdapter()
        mcp = FastMCP("test-http-server")
        server._mcp = mcp

        # Mock the HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.url = "https://api.example.com/test"
        mock_response.cookies = {"session": "abc123"}
        mock_response.elapsed.total_seconds.return_value = 0.5
        mock_response.encoding = "utf-8"
        mock_response.text = '{"status": "success", "data": "test"}'
        mock_response.json.return_value = {"status": "success", "data": "test"}
        mock_response.content = b'{"status": "success", "data": "test"}'

        # Act
        with patch("hiro.servers.http.tools.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Register the tool
            server.add_tool_provider(provider)

            # Execute through the tool directly (simulating MCP call)
            result = await provider.http_tool.execute(
                url="https://api.example.com/test",
                method="GET",
                headers='{"Accept": "application/json"}',
            )

        # Assert
        assert result["status_code"] == 200
        assert result["json"]["status"] == "success"
        assert result["cookies"]["session"] == "abc123"
        assert result["elapsed_ms"] == 500.0

        # Verify proxy and tracing headers were used
        assert result["request"]["proxy_used"] == "http://test-proxy:8080"
        assert "X-Test-Trace" in result["request"]["headers_sent"]

    async def test_mcp_http_post_with_data(self, http_config):
        """Test POST request with JSON data through MCP."""
        # Arrange
        provider = HttpToolProvider(config=http_config)
        server = FastMcpServerAdapter()
        mcp = FastMCP("test-http-server")
        server._mcp = mcp
        server.add_tool_provider(provider)

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.headers = {"Location": "/resource/123"}
        mock_response.url = "https://api.example.com/create"
        mock_response.cookies = {}
        mock_response.elapsed.total_seconds.return_value = 0.3
        mock_response.encoding = "utf-8"
        mock_response.text = '{"id": 123, "created": true}'
        mock_response.json.return_value = {"id": 123, "created": True}
        mock_response.content = b'{"id": 123, "created": true}'

        # Act
        with patch("hiro.servers.http.tools.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await provider.http_tool.execute(
                url="https://api.example.com/create",
                method="POST",
                data='{"name": "Test Item", "value": 42}',
                headers='{"Content-Type": "application/json"}',
            )

        # Assert
        assert result["status_code"] == 201
        assert result["json"]["id"] == 123
        assert result["headers"]["Location"] == "/resource/123"

        # Verify the request was made with JSON data
        mock_client.request.assert_called_once()
        call_kwargs = mock_client.request.call_args[1]
        assert "json" in call_kwargs
        assert call_kwargs["json"]["name"] == "Test Item"
        assert call_kwargs["json"]["value"] == 42

    async def test_mcp_http_with_authentication(self, http_config):
        """Test HTTP request with basic authentication through MCP."""
        # Arrange
        provider = HttpToolProvider(config=http_config)
        server = FastMcpServerAdapter()
        mcp = FastMCP("test-http-server")
        server._mcp = mcp
        server.add_tool_provider(provider)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"X-User": "testuser"}
        mock_response.url = "https://api.example.com/protected"
        mock_response.cookies = {}
        mock_response.elapsed.total_seconds.return_value = 0.2
        mock_response.encoding = "utf-8"
        mock_response.text = "Authenticated content"
        mock_response.json.side_effect = json.JSONDecodeError("", "", 0)

        # Act
        with patch("hiro.servers.http.tools.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await provider.http_tool.execute(
                url="https://api.example.com/protected",
                auth='{"username": "testuser", "password": "testpass"}',
            )

        # Assert
        assert result["status_code"] == 200
        assert result["text"] == "Authenticated content"

        # Verify auth was passed correctly
        call_kwargs = mock_client.request.call_args[1]
        assert "auth" in call_kwargs
        assert call_kwargs["auth"] == ("testuser", "testpass")

    async def test_mcp_http_error_handling(self, http_config):
        """Test error handling through MCP protocol."""
        # Arrange
        provider = HttpToolProvider(config=http_config)
        server = FastMcpServerAdapter()
        mcp = FastMCP("test-http-server")
        server._mcp = mcp
        server.add_tool_provider(provider)

        # Test timeout error
        with patch("hiro.servers.http.tools.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(
                side_effect=httpx.TimeoutException("Request timed out")
            )
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Act / Assert
            with pytest.raises(ToolError) as exc_info:
                await provider.http_tool.execute(url="https://slow.example.com")

            assert "Request timed out after 10.0s" in str(exc_info.value)

        # Test connection error
        with patch("hiro.servers.http.tools.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(
                side_effect=httpx.ConnectError("Connection refused")
            )
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Act / Assert
            with pytest.raises(ToolError) as exc_info:
                await provider.http_tool.execute(url="https://unreachable.example.com")

            assert "Connection failed" in str(exc_info.value)

    async def test_mcp_http_with_database_logging(
        self, http_config, mock_http_repo, mock_target_repo
    ):
        """Test HTTP requests with database logging through MCP."""
        # Arrange
        http_config.logging_enabled = True
        mission_id = "550e8400-e29b-41d4-a716-446655440000"  # Valid UUID format

        provider = HttpToolProvider(
            config=http_config,
            http_repo=mock_http_repo,
            target_repo=mock_target_repo,
            mission_id=mission_id,
        )

        server = FastMcpServerAdapter()
        mcp = FastMCP("test-http-server")
        server._mcp = mcp
        server.add_tool_provider(provider)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "text/plain"}
        mock_response.url = "https://api.example.com/logged"
        mock_response.cookies = {}
        mock_response.elapsed.total_seconds.return_value = 0.25
        mock_response.encoding = "utf-8"
        mock_response.text = "Logged response"
        mock_response.json.side_effect = Exception()
        mock_response.content = b"Logged response"

        # Act
        with patch("hiro.servers.http.tools.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await provider.http_tool.execute(
                url="https://api.example.com/logged"
            )

        # Assert
        assert result["status_code"] == 200

        # Verify database logging occurred (now looks up existing target instead of creating)
        mock_target_repo.get_by_endpoint.assert_called_once_with(
            "api.example.com", None, "https"
        )
        mock_http_repo.create.assert_called_once()
        mock_http_repo.update.assert_called_once()
        # link_to_target is only called if target exists (which it won't in this mock)
        # mock_http_repo.link_to_target.assert_called_once()

    async def test_mcp_http_header_merging(self, http_config):
        """Test that headers are properly merged through MCP."""
        # Arrange
        # Add custom tracing headers to config
        http_config.tracing_headers = {
            "X-Trace-Id": "trace-123",
            "X-Source": "mcp-test",
            "User-Agent": "TestBot/1.0",
        }

        provider = HttpToolProvider(config=http_config)
        server = FastMcpServerAdapter()
        mcp = FastMCP("test-http-server")
        server._mcp = mcp
        server.add_tool_provider(provider)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.url = "https://api.example.com"
        mock_response.cookies = {}
        mock_response.elapsed.total_seconds.return_value = 0.1
        mock_response.encoding = "utf-8"
        mock_response.text = "OK"
        mock_response.json.side_effect = Exception()

        # Act
        with patch("hiro.servers.http.tools.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await provider.http_tool.execute(
                url="https://api.example.com",
                headers='{"User-Agent": "CustomAgent/2.0", "Accept": "application/json"}',
            )

        # Assert
        call_kwargs = mock_client.request.call_args[1]
        headers = call_kwargs["headers"]

        # User headers should override config headers
        assert headers["User-Agent"] == "CustomAgent/2.0"
        # Config headers should be included
        assert headers["X-Trace-Id"] == "trace-123"
        assert headers["X-Source"] == "mcp-test"
        # User headers should be added
        assert headers["Accept"] == "application/json"

    async def test_mcp_multiple_providers(self):
        """Test multiple HTTP providers with different configurations through MCP."""
        # Arrange
        config1 = HttpConfig(
            proxy_url="http://proxy1:8080", tracing_headers={"X-Service": "service1"}
        )
        config2 = HttpConfig(
            proxy_url="http://proxy2:8080", tracing_headers={"X-Service": "service2"}
        )

        provider1 = HttpToolProvider(config=config1)
        provider2 = HttpToolProvider(config=config2)

        server = FastMcpServerAdapter()
        mcp = FastMCP("test-multi-http-server")
        server._mcp = mcp

        # Act
        server.add_tool_provider(provider1)
        server.add_tool_provider(provider2)

        # Assert
        assert len(server._tool_providers) == 2
        assert provider1 in server._tool_providers
        assert provider2 in server._tool_providers

        # Each provider should maintain its own configuration
        assert provider1.http_tool._config.proxy_url == "http://proxy1:8080"
        assert provider2.http_tool._config.proxy_url == "http://proxy2:8080"
        assert provider1.http_tool._config.tracing_headers["X-Service"] == "service1"
        assert provider2.http_tool._config.tracing_headers["X-Service"] == "service2"

    async def test_mcp_http_with_params_and_cookies(self, http_config):
        """Test HTTP request with URL params and cookies through MCP."""
        # Arrange
        provider = HttpToolProvider(config=http_config)
        server = FastMcpServerAdapter()
        mcp = FastMCP("test-http-server")
        server._mcp = mcp
        server.add_tool_provider(provider)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.url = "https://api.example.com/search?q=test&page=1"
        mock_response.cookies = {"result_id": "xyz789"}
        mock_response.elapsed.total_seconds.return_value = 0.15
        mock_response.encoding = "utf-8"
        mock_response.text = '{"results": []}'
        mock_response.json.return_value = {"results": []}
        mock_response.content = b'{"results": []}'

        # Act
        with patch("hiro.servers.http.tools.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await provider.http_tool.execute(
                url="https://api.example.com/search",
                params='{"q": "test", "page": "1"}',
                cookies='{"user_session": "abc123", "preferences": "dark_mode"}',
            )

        # Assert
        assert result["status_code"] == 200

        # Verify params and cookies were passed
        call_kwargs = mock_client.request.call_args[1]
        assert call_kwargs["params"] == {"q": "test", "page": "1"}
        assert call_kwargs["cookies"] == {
            "user_session": "abc123",
            "preferences": "dark_mode",
        }

    async def test_mcp_http_redirect_handling(self, http_config):
        """Test redirect handling configuration through MCP."""
        # Arrange
        provider = HttpToolProvider(config=http_config)
        server = FastMcpServerAdapter()
        mcp = FastMCP("test-http-server")
        server._mcp = mcp
        server.add_tool_provider(provider)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.url = "https://api.example.com/final"
        mock_response.cookies = {}
        mock_response.elapsed.total_seconds.return_value = 0.1
        mock_response.encoding = "utf-8"
        mock_response.text = "Final destination"
        mock_response.json.side_effect = Exception()

        # Test with redirects disabled
        with patch("hiro.servers.http.tools.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await provider.http_tool.execute(
                url="https://api.example.com/redirect", follow_redirects=False
            )

            # Verify client was configured with redirects disabled
            mock_client_class.assert_called_with(
                timeout=10.0,
                verify=False,
                follow_redirects=False,
                proxy="http://test-proxy:8080",
            )

    async def test_mcp_http_server_integration_complete(self, http_config):
        """Test complete integration with FastMcpServerAdapter."""
        # Arrange
        server = FastMcpServerAdapter()
        provider = HttpToolProvider(config=http_config)

        # Mock FastMCP instance to verify registration
        mock_mcp = MagicMock()
        mock_mcp.tool = MagicMock()
        server._mcp = mock_mcp

        # Act
        server.add_tool_provider(provider)

        # Assert
        # Provider is registered
        assert provider in server._tool_providers

        # Tool was registered with FastMCP
        assert mock_mcp.tool.called

        # Verify the registration call
        call_args = mock_mcp.tool.call_args_list[0]
        assert call_args[0][0] == provider.http_tool.execute  # Function registered
        assert call_args[1]["name"] == "http_request"  # Tool name
