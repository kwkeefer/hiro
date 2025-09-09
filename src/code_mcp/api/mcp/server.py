"""FastMCP server adapter implementation."""

from collections.abc import Awaitable, Callable
from typing import Any

from fastmcp import FastMCP

from code_mcp.core.mcp.exceptions import ResourceError, ToolError
from code_mcp.core.mcp.protocols import ResourceProvider, ToolProvider


class FastMcpServerAdapter:
    """Adapter that makes FastMCP work with our protocols."""

    def __init__(self, name: str = "code-mcp-server"):
        """Initialize the FastMCP server adapter.

        Args:
            name: Server name for MCP identification
        """
        self._mcp = FastMCP(name)
        self._tool_providers: list[ToolProvider] = []
        self._resource_providers: list[ResourceProvider] = []

    def add_tool_provider(self, provider: ToolProvider) -> None:
        """Add a tool provider to the server.

        Args:
            provider: Object implementing ToolProvider protocol
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

    def _register_tools(self, provider: ToolProvider) -> None:
        """Register tools from a provider with FastMCP."""
        tools = provider.get_tools()

        for tool_def in tools:
            tool_name = tool_def["name"]

            def make_tool_wrapper(
                name: str, prov: ToolProvider
            ) -> Callable[..., Awaitable[Any]]:
                async def tool_wrapper(arguments: dict[str, Any] | None = None) -> Any:
                    """Wrapper function for tool execution."""
                    if arguments is None:
                        arguments = {}
                    try:
                        return await prov.call_tool(name, arguments)
                    except Exception as e:
                        raise ToolError(name, str(e)) from e

                return tool_wrapper

            # Register with FastMCP
            self._mcp.tool(
                make_tool_wrapper(tool_name, provider),
                name=tool_name,
                description=tool_def.get("description", ""),
            )

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

    def start(self, transport: str = "stdio", **_kwargs: Any) -> None:
        """Start the MCP server.

        Args:
            transport: Transport type (stdio, sse, etc.)
            **_kwargs: Additional server configuration (currently unused)
        """
        if transport == "stdio":
            self._mcp.run(transport="stdio")
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
