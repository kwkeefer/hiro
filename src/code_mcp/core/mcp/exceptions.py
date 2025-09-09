"""MCP-related exceptions."""

from typing import Any


class McpError(Exception):
    """Base exception for MCP-related errors."""

    pass


class ToolError(McpError):
    """Exception raised when tool execution fails."""

    def __init__(
        self, tool_name: str, message: str, details: dict[str, Any] | None = None
    ):
        self.tool_name = tool_name
        self.details = details or {}
        super().__init__(f"Tool '{tool_name}' failed: {message}")


class ResourceError(McpError):
    """Exception raised when resource access fails."""

    def __init__(self, uri: str, message: str, details: dict[str, Any] | None = None):
        self.uri = uri
        self.details = details or {}
        super().__init__(f"Resource '{uri}' failed: {message}")
