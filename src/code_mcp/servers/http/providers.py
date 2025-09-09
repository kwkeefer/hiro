"""HTTP tool providers with configuration injection."""

from collections.abc import Sequence
from typing import Any

from code_mcp.utils.schema import generate_tool_schema

from .config import HttpConfig
from .tools import HttpRequestTool


class HttpToolProvider:
    """Tool provider for HTTP operations with injected configuration."""

    def __init__(self, config: HttpConfig):
        """Initialize with server configuration.

        Args:
            config: HTTP server configuration for proxy, headers, etc.
        """
        self._config = config
        self._http_tool = HttpRequestTool(config)

    def get_tools(self) -> Sequence[dict[str, Any]]:
        """Return HTTP tool definitions generated from function signatures.

        Schema is automatically generated from the execute method's type hints
        and docstring, ensuring documentation stays in sync with implementation.
        """
        return [generate_tool_schema(self._http_tool.execute, "http_request")]

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Execute HTTP tool with injected configuration.

        Args:
            name: Tool name to execute
            arguments: Tool arguments from LLM

        Returns:
            Tool execution result
        """
        if name == "http_request":
            return await self._http_tool.execute(**arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")

    @property
    def config(self) -> HttpConfig:
        """Access to current configuration."""
        return self._config
