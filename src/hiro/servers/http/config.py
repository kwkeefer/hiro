"""HTTP server configuration."""

from dataclasses import dataclass


@dataclass
class HttpConfig:
    """Configuration for HTTP operations server."""

    proxy_url: str | None = None
    timeout: float = 30.0
    verify_ssl: bool = True
    tracing_headers: dict[str, str] | None = None

    # Database logging configuration
    logging_enabled: bool = True
    max_request_body_size: int = 1024 * 1024  # 1MB
    max_response_body_size: int = 1024 * 1024  # 1MB
    sensitive_headers: list[str] | None = None

    # Cookie session management
    cookie_sessions_enabled: bool = True
    cookie_sessions_config: str | None = (
        None  # Path to sessions YAML, None for XDG default
    )
    cookie_cache_ttl: int = 60  # Default cache TTL in seconds

    def __post_init__(self) -> None:
        """Initialize default tracing headers."""
        if self.tracing_headers is None:
            self.tracing_headers = {
                "User-Agent": "hiro-http-server/0.1.0",
                "X-MCP-Source": "hiro",
            }

        # Initialize empty sensitive headers - log everything by default
        if self.sensitive_headers is None:
            self.sensitive_headers = []
