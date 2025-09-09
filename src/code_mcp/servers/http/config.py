"""HTTP server configuration."""

from dataclasses import dataclass


@dataclass
class HttpConfig:
    """Configuration for HTTP operations server."""

    proxy_url: str | None = None
    timeout: float = 30.0
    verify_ssl: bool = True
    tracing_headers: dict[str, str] | None = None

    def __post_init__(self) -> None:
        """Initialize default tracing headers."""
        if self.tracing_headers is None:
            self.tracing_headers = {
                "User-Agent": "code-mcp-http-server/0.1.0",
                "X-MCP-Source": "code-mcp",
            }
