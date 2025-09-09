"""Integration tests for MCP server and provider integration."""

from unittest.mock import MagicMock

import pytest

from code_mcp.api.mcp.server import FastMcpServerAdapter
from code_mcp.servers.http.config import HttpConfig
from code_mcp.servers.http.providers import HttpToolProvider


@pytest.mark.integration
class TestServerProviderIntegration:
    """Test that server properly integrates with providers using hybrid approach."""

    def test_server_accepts_http_tool_provider(self):
        """Server should accept HttpToolProvider and store it."""
        server = FastMcpServerAdapter()
        config = HttpConfig()
        provider = HttpToolProvider(config)

        # Should not raise any errors
        server.add_tool_provider(provider)

        # Provider should be stored
        assert provider in server._tool_providers

    def test_server_registers_http_tools_directly(self):
        """Server should register HTTP tools by accessing the provider's http_tool directly."""
        server = FastMcpServerAdapter()
        config = HttpConfig()
        provider = HttpToolProvider(config)

        # Mock the FastMCP instance to verify tool registration
        mock_mcp = MagicMock()
        server._mcp = mock_mcp

        server.add_tool_provider(provider)

        # Should have called mcp.tool() to register the HTTP tool directly
        assert mock_mcp.tool.called

        # Should have registered with the execute method directly
        call_args = mock_mcp.tool.call_args_list
        assert len(call_args) > 0

        # Verify the call was made with the execute method
        first_call = call_args[0]
        assert (
            first_call[0][0] == provider._http_tool.execute
        )  # First positional arg should be the execute method

        # Verify the tool was registered with correct name
        assert "name" in first_call[1]
        assert first_call[1]["name"] == "http_request"

    def test_server_handles_multiple_http_providers(self):
        """Server should handle multiple HTTP tool providers."""
        server = FastMcpServerAdapter()

        # Create two providers with different configurations
        config1 = HttpConfig()
        provider1 = HttpToolProvider(config1)

        config2 = HttpConfig()
        provider2 = HttpToolProvider(config2)

        # Mock to avoid actual registration
        mock_mcp = MagicMock()
        server._mcp = mock_mcp

        # Add both providers
        server.add_tool_provider(provider1)
        server.add_tool_provider(provider2)

        # Both should be stored
        assert len(server._tool_providers) == 2
        assert provider1 in server._tool_providers
        assert provider2 in server._tool_providers

        # Should have registered tools from both providers
        assert mock_mcp.tool.call_count == 2

    def test_server_hybrid_approach_architecture(self):
        """Test that server uses hybrid approach correctly."""
        server = FastMcpServerAdapter()
        config = HttpConfig()
        provider = HttpToolProvider(config)

        # Mock to capture registration details
        mock_mcp = MagicMock()
        server._mcp = mock_mcp

        server.add_tool_provider(provider)

        # Verify hybrid approach: direct registration, not protocol methods
        # The provider doesn't need get_tools() or call_tool() methods
        call_args = mock_mcp.tool.call_args_list[0]
        registered_function = call_args[0][0]

        # Should register the actual execute method, not a wrapper
        assert registered_function == provider._http_tool.execute

        # Provider can still be used for organization and testing
        assert provider.config == config
        assert provider.http_tool._config == config

    def test_non_http_provider_gracefully_ignored(self):
        """Server should gracefully handle providers without _http_tool."""
        server = FastMcpServerAdapter()

        # Create a provider without _http_tool
        class OtherToolProvider:
            def __init__(self):
                self.some_other_tool = "not_http"

        provider = OtherToolProvider()
        mock_mcp = MagicMock()
        server._mcp = mock_mcp

        # Should not raise errors, just not register anything
        server.add_tool_provider(provider)

        # No tools should be registered since this provider doesn't have _http_tool
        assert not mock_mcp.tool.called

        # Provider should still be stored (for future extensibility)
        assert provider in server._tool_providers
