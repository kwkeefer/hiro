"""MCP protocols for type-safe composition."""

from collections.abc import Sequence
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ToolProvider(Protocol):
    """Protocol for objects that can provide MCP tools."""

    def get_tools(self) -> Sequence[dict[str, Any]]:
        """Return list of tool definitions.

        Returns:
            Sequence of tool definitions compatible with MCP spec.
        """
        ...

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Execute a tool with given arguments.

        Args:
            name: Tool name to execute
            arguments: Tool arguments

        Returns:
            Tool execution result

        Raises:
            ToolError: If tool execution fails
        """
        ...


@runtime_checkable
class ResourceProvider(Protocol):
    """Protocol for objects that can provide MCP resources."""

    def get_resources(self) -> Sequence[dict[str, Any]]:
        """Return list of resource definitions.

        Returns:
            Sequence of resource definitions compatible with MCP spec.
        """
        ...

    async def get_resource(self, uri: str) -> dict[str, Any]:
        """Retrieve a resource by URI.

        Args:
            uri: Resource URI to retrieve

        Returns:
            Resource data

        Raises:
            ResourceError: If resource cannot be retrieved
        """
        ...


class McpServer(Protocol):
    """Protocol for MCP server implementations."""

    def add_tool_provider(self, provider: ToolProvider) -> None:
        """Add a tool provider to the server.

        Args:
            provider: Object implementing ToolProvider protocol
        """
        ...

    def add_resource_provider(self, provider: ResourceProvider) -> None:
        """Add a resource provider to the server.

        Args:
            provider: Object implementing ResourceProvider protocol
        """
        ...

    async def start(self, **kwargs: Any) -> None:
        """Start the MCP server.

        Args:
            **kwargs: Server-specific configuration
        """
        ...

    async def stop(self) -> None:
        """Stop the MCP server."""
        ...
