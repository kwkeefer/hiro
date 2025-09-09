"""HTTP operation tools for penetration testing."""

import json
from typing import Any, Literal

import httpx

from code_mcp.core.mcp.exceptions import ToolError

from .config import HttpConfig


class HttpRequestTool:
    """Tool for making raw HTTP requests with injected configuration."""

    def __init__(self, config: HttpConfig):
        """Initialize HTTP request tool with server configuration.

        Args:
            config: HTTP server configuration with proxy, headers, etc.
        """
        self._config = config

    async def execute(
        self,
        url: str,
        method: Literal[
            "GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"
        ] = "GET",
        headers: dict[str, str] | None = None,
        data: str | None = None,
        params: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None,
        follow_redirects: bool = True,
        auth: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Make HTTP request with full control over headers, data, and parameters.

        Proxy and tracing headers are automatically configured by the server.
        All requests are automatically routed through configured proxy and
        include tracing headers for audit purposes.

        Args:
            url: Target URL to request
            method: HTTP method to use
            headers: Custom headers as key-value pairs (merged with server tracing headers)
            data: Request body data (JSON string or raw data)
            params: URL parameters as key-value pairs
            cookies: Cookies as key-value pairs
            follow_redirects: Whether to follow HTTP redirects
            auth: Basic auth credentials with 'username' and 'password' keys

        Returns:
            Response data containing status_code, headers, text, json (if applicable),
            cookies, elapsed_ms, and request details for audit trail

        Raises:
            ToolError: If request fails due to timeout, connection, or other errors
        """
        try:
            # Prepare client configuration with injected settings
            client_config: dict[str, Any] = {
                "timeout": self._config.timeout,
                "verify": self._config.verify_ssl,
                "follow_redirects": follow_redirects,
            }

            # Inject proxy from server config if configured
            if self._config.proxy_url:
                client_config["proxy"] = self._config.proxy_url

            # Merge headers: injected tracing headers + user headers
            merged_headers: dict[str, str] = {}
            if self._config.tracing_headers:
                merged_headers.update(self._config.tracing_headers)
            if headers:
                merged_headers.update(headers)

            # Merge cookies: default cookies + user cookies (user overrides default)
            merged_cookies: dict[str, str] = {}
            if self._config.default_cookies:
                merged_cookies.update(self._config.default_cookies)
            if cookies:
                merged_cookies.update(cookies)

            # Prepare request configuration
            request_config: dict[str, Any] = {
                "method": method.upper(),
                "url": url,
                "headers": merged_headers,
                "params": params or {},
                "cookies": merged_cookies,
            }

            # Add authentication if provided
            if auth and "username" in auth and "password" in auth:
                request_config["auth"] = (auth["username"], auth["password"])

            # Add data if provided
            if data:
                # Try to parse as JSON first, fall back to raw string
                try:
                    request_config["json"] = json.loads(data)
                except json.JSONDecodeError:
                    request_config["content"] = data

            async with httpx.AsyncClient(**client_config) as client:
                response = await client.request(**request_config)

                # Parse response data
                response_data = {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "url": str(response.url),
                    "method": method.upper(),
                    "cookies": dict(response.cookies),
                    "elapsed_ms": response.elapsed.total_seconds() * 1000,
                    "encoding": response.encoding,
                }

                # Try to get response content as text
                try:
                    response_data["text"] = response.text
                except Exception:
                    response_data["text"] = "[Binary content - not displayable]"

                # Try to parse as JSON if possible
                try:
                    response_data["json"] = response.json()
                except Exception:
                    response_data["json"] = None

                # Add request details for audit trail (including injected config)
                response_data["request"] = {
                    "url": url,
                    "method": method.upper(),
                    "headers_sent": merged_headers,  # Show what was actually sent
                    "headers_user": headers or {},  # Show what user requested
                    "cookies": merged_cookies,  # Show cookies that were sent
                    "params": params or {},
                    "data": data,
                    "proxy_used": self._config.proxy_url,  # Show if proxy was used
                }

                return response_data

        except httpx.TimeoutException as e:
            raise ToolError(
                "http_request", f"Request timed out after {self._config.timeout}s"
            ) from e
        except httpx.ConnectError as e:
            raise ToolError("http_request", f"Connection failed: {e}") from e
        except Exception as e:
            raise ToolError("http_request", f"HTTP request failed: {e}") from e
