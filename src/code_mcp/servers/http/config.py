"""HTTP server configuration."""

import json
import logging
from dataclasses import dataclass
from pathlib import Path


@dataclass
class HttpConfig:
    """Configuration for HTTP operations server."""

    proxy_url: str | None = None
    timeout: float = 30.0
    verify_ssl: bool = True
    tracing_headers: dict[str, str] | None = None
    default_cookies_file: str | None = None
    default_cookies: dict[str, str] | None = None

    def __post_init__(self) -> None:
        """Initialize default tracing headers and load cookies from file."""
        if self.tracing_headers is None:
            self.tracing_headers = {
                "User-Agent": "code-mcp-http-server/0.1.0",
                "X-MCP-Source": "code-mcp",
            }

        # Load default cookies from file if specified
        if self.default_cookies_file is not None:
            self._load_cookies_from_file()
        elif self.default_cookies is None:
            self.default_cookies = {}

    def _load_cookies_from_file(self) -> None:
        """Load cookies from JSON file."""
        if not self.default_cookies_file:
            return

        try:
            cookie_path = Path(self.default_cookies_file)
            if not cookie_path.exists():
                logging.warning(f"Cookie file not found: {self.default_cookies_file}")
                self.default_cookies = {}
                return

            with cookie_path.open("r") as f:
                cookies_data = json.load(f)

            if not isinstance(cookies_data, dict):
                logging.error(
                    f"Cookie file must contain a JSON object: {self.default_cookies_file}"
                )
                self.default_cookies = {}
                return

            # Ensure all values are strings
            self.default_cookies = {str(k): str(v) for k, v in cookies_data.items()}
            logging.info(
                f"Loaded {len(self.default_cookies)} default cookies from {self.default_cookies_file}"
            )

        except json.JSONDecodeError as e:
            logging.error(
                f"Invalid JSON in cookie file {self.default_cookies_file}: {e}"
            )
            self.default_cookies = {}
        except Exception as e:
            logging.error(f"Error loading cookie file {self.default_cookies_file}: {e}")
            self.default_cookies = {}
