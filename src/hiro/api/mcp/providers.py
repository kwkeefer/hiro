"""Base implementations for MCP providers."""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any


class BaseToolProvider(ABC):
    """Base implementation for tool providers."""

    @abstractmethod
    def get_tools(self) -> Sequence[dict[str, Any]]:
        """Return list of tool definitions.

        Returns:
            Sequence of tool definitions compatible with MCP spec.
        """
        pass

    @abstractmethod
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
        pass


class BaseResourceProvider(ABC):
    """Base implementation for resource providers."""

    @abstractmethod
    def get_resources(self) -> Sequence[dict[str, Any]]:
        """Return list of resource definitions.

        Returns:
            Sequence of resource definitions compatible with MCP spec.
        """
        pass

    @abstractmethod
    async def get_resource(self, uri: str) -> dict[str, Any]:
        """Retrieve a resource by URI.

        Args:
            uri: Resource URI to retrieve

        Returns:
            Resource data

        Raises:
            ResourceError: If resource cannot be retrieved
        """
        pass
