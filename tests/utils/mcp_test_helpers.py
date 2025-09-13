"""Reusable test helpers for FastMCP integration testing.

This module provides base classes and utilities for testing MCP providers
with actual FastMCP server instances.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastmcp import FastMCP
from mcp.types import (
    Resource,
)

from hiro.api.mcp.providers import BaseResourceProvider, BaseToolProvider
from hiro.api.mcp.server import FastMcpServerAdapter


class MockMcpClient:
    """Mock MCP client for testing server interactions."""

    def __init__(self):
        self.resources: list[Resource] = []
        self.resource_contents: dict[str, Any] = {}
        self.tool_results: dict[str, Any] = {}

    async def list_resources(self) -> list[Resource]:
        """List available resources."""
        return self.resources

    async def read_resource(self, uri: str) -> Any:
        """Read a specific resource."""
        if uri not in self.resource_contents:
            raise ValueError(f"Resource not found: {uri}")
        return self.resource_contents[uri]

    async def call_tool(self, name: str, arguments: dict) -> Any:
        """Call a tool with arguments."""
        if name not in self.tool_results:
            raise ValueError(f"Tool not found: {name}")
        return self.tool_results[name]


class BaseMcpProviderTest:
    """Base class for MCP provider integration tests.

    Provides common setup and helper methods for testing providers
    with actual FastMCP server instances.
    """

    @pytest.fixture
    async def mcp_server(self):
        """Create a FastMCP server instance for testing."""
        mcp = FastMCP("test-server")

        # Initialize with test capabilities
        @mcp.list_resources()
        async def list_resources_handler() -> list[Resource]:
            return []

        return mcp

    @pytest.fixture
    async def server_adapter(self):
        """Create a FastMcpServerAdapter for testing."""
        return FastMcpServerAdapter()

    @asynccontextmanager
    async def create_test_server(
        self,
        resource_provider: BaseResourceProvider | None = None,
        tool_provider: BaseToolProvider | None = None,
    ) -> AsyncIterator[tuple[FastMcpServerAdapter, FastMCP]]:
        """Create a test server with providers.

        Args:
            resource_provider: Optional resource provider to add
            tool_provider: Optional tool provider to add

        Yields:
            Tuple of (server_adapter, mcp_instance)
        """
        # Create server and MCP instance
        server = FastMcpServerAdapter()
        mcp = FastMCP("test-server")
        server._mcp = mcp

        # Add providers if provided
        if resource_provider:
            server.add_resource_provider(resource_provider)
        if tool_provider:
            server.add_tool_provider(tool_provider)

        # Start the server (mocked)
        server._setup_complete = True

        try:
            yield server, mcp
        finally:
            # Cleanup if needed
            pass

    async def get_resources_from_server(
        self, server: FastMcpServerAdapter
    ) -> list[dict[str, Any]]:
        """Get all resources from the server.

        Args:
            server: The server to query

        Returns:
            List of resource dictionaries
        """
        # Access the resource providers directly
        resources = []
        for provider in server._resource_providers:
            provider_resources = provider.get_resources()
            resources.extend(provider_resources)
        return resources

    async def read_resource_from_server(
        self, server: FastMcpServerAdapter, uri: str
    ) -> dict[str, Any]:
        """Read a specific resource from the server.

        Args:
            server: The server to query
            uri: Resource URI to read

        Returns:
            Resource contents
        """
        # Find the right provider and read the resource
        for provider in server._resource_providers:
            resources = provider.get_resources()
            if any(r["uri"] == uri for r in resources):
                return await provider.get_resource(uri)

        raise ValueError(f"Resource not found: {uri}")

    async def call_tool_on_server(
        self, server: FastMcpServerAdapter, tool_name: str, arguments: dict[str, Any]
    ) -> Any:
        """Call a tool on the server.

        Args:
            server: The server to use
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        # Find and execute the tool
        for _provider in server._tool_providers:
            # This would need to be implemented based on actual tool provider interface
            pass

        raise ValueError(f"Tool not found: {tool_name}")

    def assert_resource_valid(self, resource: dict[str, Any]):
        """Assert that a resource has valid MCP structure.

        Args:
            resource: Resource dictionary to validate
        """
        assert "uri" in resource, "Resource must have URI"
        assert "name" in resource, "Resource must have name"
        assert "mimeType" in resource, "Resource must have mimeType"

        # Optional but common fields
        if "description" in resource:
            assert isinstance(resource["description"], str)

    def assert_resource_contents_valid(self, contents: dict[str, Any]):
        """Assert that resource contents are valid.

        Args:
            contents: Resource contents to validate
        """
        # Basic validation - can be extended by subclasses
        assert contents is not None
        assert isinstance(contents, dict)


class AsyncContextManagerMock:
    """Mock for async context managers in tests."""

    def __init__(self, return_value=None):
        self.return_value = return_value
        self.entered = False
        self.exited = False

    async def __aenter__(self):
        self.entered = True
        return self.return_value

    async def __aexit__(self, *args):
        self.exited = True
        return False


def create_mock_mcp_server() -> MagicMock:
    """Create a mock MCP server for testing.

    Returns:
        Mock MCP server with common methods mocked
    """
    mock_server = MagicMock(spec=FastMCP)

    # Mock common MCP methods
    mock_server.list_resources = AsyncMock(return_value=[])
    mock_server.read_resource = AsyncMock()
    mock_server.list_tools = AsyncMock(return_value=[])
    mock_server.call_tool = AsyncMock()

    return mock_server


def create_test_resource(
    uri: str, name: str, mime_type: str = "application/json", description: str = ""
) -> dict[str, Any]:
    """Create a test resource dictionary.

    Args:
        uri: Resource URI
        name: Resource name
        mime_type: MIME type
        description: Optional description

    Returns:
        Resource dictionary
    """
    resource = {
        "uri": uri,
        "name": name,
        "mimeType": mime_type,
    }

    if description:
        resource["description"] = description

    return resource
