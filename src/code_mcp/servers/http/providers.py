"""HTTP tool providers with configuration injection."""

from .config import HttpConfig
from .tools import HttpRequestTool


class HttpToolProvider:
    """Tool provider for HTTP operations with injected configuration.

    Uses hybrid approach: provides organized structure and testable business logic,
    while allowing direct tool registration for FastMCP compatibility.
    """

    def __init__(self, config: HttpConfig):
        """Initialize with server configuration.

        Args:
            config: HTTP server configuration for proxy, headers, etc.
        """
        self._config = config
        self._http_tool = HttpRequestTool(config)

    @property
    def config(self) -> HttpConfig:
        """Access to current configuration."""
        return self._config

    @property
    def http_tool(self) -> HttpRequestTool:
        """Access to HTTP request tool for direct registration."""
        return self._http_tool
