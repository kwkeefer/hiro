"""FastMCP server adapter implementation."""

from collections.abc import Awaitable, Callable
from typing import Any, Protocol

from fastmcp import FastMCP

from hiro.core.mcp.exceptions import ResourceError
from hiro.core.mcp.protocols import ResourceProvider


class ToolProviderLike(Protocol):
    """Protocol for objects that can provide tools via hybrid approach."""

    # No required methods - providers can provide tools in various ways


class HttpToolProviderLike(Protocol):
    """Protocol for HTTP tool providers in hybrid approach."""

    _http_tool: Any


class AiLoggingToolProviderLike(Protocol):
    """Protocol for AI logging tool providers in hybrid approach."""

    _create_target_tool: Any
    _update_target_tool: Any
    _get_summary_tool: Any
    _search_targets_tool: Any


class FastMcpServerAdapter:
    """Adapter that makes FastMCP work with our protocols."""

    def __init__(self, name: str = "hiro-server"):
        """Initialize the FastMCP server adapter.

        Args:
            name: Server name for MCP identification
        """
        self._mcp = FastMCP(name)
        self._tool_providers: list[ToolProviderLike] = []
        self._resource_providers: list[ResourceProvider] = []

    def add_tool_provider(self, provider: ToolProviderLike) -> None:
        """Add a tool provider to the server.

        Args:
            provider: Object that can provide tools (hybrid approach)
        """
        self._tool_providers.append(provider)
        self._register_tools(provider)

    def add_resource_provider(self, provider: ResourceProvider) -> None:
        """Add a resource provider to the server.

        Args:
            provider: Object implementing ResourceProvider protocol
        """
        self._resource_providers.append(provider)
        self._register_resources(provider)

    def _register_tools(self, provider: ToolProviderLike) -> None:
        """Register tools from a provider with FastMCP.

        Uses hybrid approach: protocols for organization, direct registration for simplicity.
        """
        # Register HTTP tools directly for better FastMCP compatibility
        if hasattr(provider, "_http_tool"):
            self._mcp.tool(
                provider._http_tool.execute,
                name="http_request",
                description="Make HTTP request with full control over headers, data, and parameters.",
            )

        # Register AI logging tools for target management
        if hasattr(provider, "_create_target_tool"):
            self._mcp.tool(
                provider._create_target_tool.execute,
                name="create_target",
                description="Register a new target for testing with host, port, protocol, and metadata.",
            )

        if hasattr(provider, "_update_target_tool"):
            self._mcp.tool(
                provider._update_target_tool.execute,
                name="update_target_status",
                description="Update target status, risk level, and metadata.",
            )

        if hasattr(provider, "_get_summary_tool"):
            self._mcp.tool(
                provider._get_summary_tool.execute,
                name="get_target_summary",
                description="Get comprehensive target summary with statistics on notes, attempts, and requests.",
            )

        if hasattr(provider, "_search_targets_tool"):
            self._mcp.tool(
                provider._search_targets_tool.execute,
                name="search_targets",
                description="Search and filter targets by host, status, risk level, or protocol.",
            )

        # Register context management tools (simplified to 2 tools)
        if hasattr(provider, "_get_context_tool"):
            self._mcp.tool(
                provider._get_context_tool.execute,
                name="get_target_context",
                description="Get current or specific context version for a target.",
            )

        if hasattr(provider, "_update_context_tool"):
            self._mcp.tool(
                provider._update_context_tool.execute,
                name="update_target_context",
                description="Create or update target context (creates new immutable version).",
            )

        # For future tool types, we can add similar direct registrations here
        # This avoids the complexity of generic wrappers while keeping provider organization

    def _register_resources(self, provider: ResourceProvider) -> None:
        """Register resources from a provider with FastMCP."""
        resources = provider.get_resources()

        for resource_def in resources:
            resource_uri = resource_def["uri"]

            def make_resource_wrapper(
                uri: str, prov: ResourceProvider
            ) -> Callable[[], Awaitable[dict[str, Any]]]:
                async def resource_wrapper() -> dict[str, Any]:
                    """Wrapper function for resource access."""
                    try:
                        return await prov.get_resource(uri)
                    except Exception as e:
                        raise ResourceError(uri, str(e)) from e

                return resource_wrapper

            # Register with FastMCP
            self._mcp.resource(
                resource_uri,
                name=resource_def.get("name", ""),
                description=resource_def.get("description", ""),
                mime_type=resource_def.get("mimeType", "text/plain"),
            )(make_resource_wrapper(resource_uri, provider))

    def start(self, transport: str = "http", **kwargs: Any) -> None:
        """Start the MCP server.

        Args:
            transport: Transport type (http, stdio, sse)
            **kwargs: Additional server configuration (host, port, path for HTTP)
        """
        if transport == "stdio":
            self._mcp.run(transport="stdio")
        elif transport == "http":
            # HTTP streaming transport (recommended)
            host = kwargs.get("host", "127.0.0.1")
            port = kwargs.get("port", 8000)
            path = kwargs.get("path", "/mcp")
            print(f"Starting HTTP MCP server at http://{host}:{port}{path}")
            self._mcp.run(transport="http", host=host, port=port, path=path)
        elif transport == "sse":
            # SSE transport (deprecated but supported)
            host = kwargs.get("host", "127.0.0.1")
            port = kwargs.get("port", 8000)
            print(f"Starting SSE MCP server at http://{host}:{port}")
            self._mcp.run(transport="sse", host=host, port=port)
        else:
            raise ValueError(f"Unsupported transport: {transport}")

    async def stop(self) -> None:
        """Stop the MCP server."""
        # FastMCP handles cleanup automatically
        pass

    @property
    def mcp(self) -> FastMCP:
        """Access to underlying FastMCP instance."""
        return self._mcp
