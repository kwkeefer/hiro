"""HTTP operation tools for penetration testing."""

import json
import logging
from typing import Any, Literal
from urllib.parse import urlparse

import httpx

from code_mcp.core.mcp.exceptions import ToolError
from code_mcp.db.repositories import HttpRequestRepository, TargetRepository
from code_mcp.db.schemas import HttpRequestCreate

from .config import HttpConfig

logger = logging.getLogger(__name__)


class HttpRequestTool:
    """Tool for making raw HTTP requests with injected configuration."""

    def __init__(
        self,
        config: HttpConfig,
        http_repo: HttpRequestRepository
        | Any
        | None = None,  # Any for LazyHttpRequestRepository
        target_repo: TargetRepository
        | Any
        | None = None,  # Any for LazyTargetRepository
        session_id: str | None = None,
    ):
        """Initialize HTTP request tool with server configuration.

        Args:
            config: HTTP server configuration with proxy, headers, etc.
            http_repo: Repository for logging HTTP requests (optional)
            target_repo: Repository for managing targets (optional)
            session_id: Current AI session ID for linking requests (optional)
        """
        self._config = config
        self._http_repo = http_repo
        self._target_repo = target_repo
        self._session_id = session_id

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
        # Initialize tracking variables
        request_record = None
        target_record = None
        error_message = None

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
            request_body_for_logging = None
            if data:
                # Try to parse as JSON first, fall back to raw string
                try:
                    request_config["json"] = json.loads(data)
                    request_body_for_logging = data
                except json.JSONDecodeError:
                    request_config["content"] = data
                    request_body_for_logging = data

            # Create target and log pre-request if database logging is enabled
            if self._config.logging_enabled and self._http_repo and self._target_repo:
                try:
                    # Auto-create/get target from URL
                    target_record = await self._target_repo.get_or_create_from_url(url)

                    # Log request (pre-response)
                    parsed_url = urlparse(url)
                    request_record = await self._log_request_start(
                        method=method.upper(),
                        url=url,
                        host=parsed_url.hostname or parsed_url.netloc,
                        path=parsed_url.path or "/",
                        query_params=dict(params) if params else None,
                        headers=merged_headers,
                        cookies=merged_cookies,
                        request_body=request_body_for_logging,
                    )

                    # Link request to target
                    if request_record and target_record:
                        await self._http_repo.link_to_target(
                            request_record.id, target_record.id
                        )

                except Exception as e:
                    logger.warning(f"Failed to log request start: {e}", exc_info=True)

            async with httpx.AsyncClient(**client_config) as client:
                response = await client.request(**request_config)

                # Calculate elapsed time
                elapsed_ms = response.elapsed.total_seconds() * 1000

                # Parse response data
                response_data = {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "url": str(response.url),
                    "method": method.upper(),
                    "cookies": dict(response.cookies),
                    "elapsed_ms": elapsed_ms,
                    "encoding": response.encoding,
                }

                # Try to get response content as text
                response_body_text = None
                try:
                    response_body_text = response.text
                    response_data["text"] = response_body_text
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

                # Log response data if database logging is enabled
                if self._config.logging_enabled and self._http_repo and request_record:
                    try:
                        await self._log_request_complete(
                            request_record.id,
                            status_code=response.status_code,
                            response_headers=dict(response.headers),
                            response_body=response_body_text,
                            response_size=len(response.content)
                            if response.content
                            else None,
                            elapsed_ms=elapsed_ms,
                        )
                    except Exception as e:
                        logger.warning(f"Failed to log response: {e}", exc_info=True)

                return response_data

        except httpx.TimeoutException as e:
            error_message = f"Request timed out after {self._config.timeout}s"
            await self._log_request_error(request_record, error_message)
            raise ToolError("http_request", error_message) from e
        except httpx.ConnectError as e:
            error_message = f"Connection failed: {e}"
            await self._log_request_error(request_record, error_message)
            raise ToolError("http_request", error_message) from e
        except Exception as e:
            error_message = f"HTTP request failed: {e}"
            await self._log_request_error(request_record, error_message)
            raise ToolError("http_request", error_message) from e

    async def _log_request_start(
        self,
        method: str,
        url: str,
        host: str,
        path: str,
        query_params: dict | None = None,
        headers: dict | None = None,
        cookies: dict | None = None,
        request_body: str | None = None,
    ) -> Any | None:
        """Log the start of an HTTP request."""
        if not self._http_repo:
            return None

        try:
            # Truncate large request bodies
            truncated_body = request_body
            if request_body and len(request_body) > self._config.max_request_body_size:
                truncated_body = (
                    request_body[: self._config.max_request_body_size]
                    + "... [TRUNCATED]"
                )

            # Filter sensitive headers (though we're logging everything by default)
            filtered_headers = self._filter_sensitive_data(headers or {})

            from uuid import UUID

            # Convert session_id to UUID if provided
            session_uuid = UUID(self._session_id) if self._session_id else None

            request_data = HttpRequestCreate(
                session_id=session_uuid,
                method=method,
                url=url,
                host=host,
                path=path,
                query_params=query_params,
                headers=filtered_headers,
                cookies=cookies,
                request_body=truncated_body,
            )

            return await self._http_repo.create(request_data)

        except Exception as e:
            logger.error(f"Failed to create request record: {e}", exc_info=True)
            return None

    async def _log_request_complete(
        self,
        request_id: Any,
        status_code: int,
        response_headers: dict,
        response_body: str | None,
        response_size: int | None,
        elapsed_ms: float,
    ) -> None:
        """Log the completion of an HTTP request."""
        if not self._http_repo:
            return

        try:
            # Truncate large response bodies
            truncated_body = response_body
            if (
                response_body
                and len(response_body) > self._config.max_response_body_size
            ):
                truncated_body = (
                    response_body[: self._config.max_response_body_size]
                    + "... [TRUNCATED]"
                )

            # Filter sensitive headers
            filtered_response_headers = self._filter_sensitive_data(response_headers)

            from code_mcp.db.schemas import HttpRequestUpdate

            update_data = HttpRequestUpdate(
                status_code=status_code,
                response_headers=filtered_response_headers,
                response_body=truncated_body,
                response_size=response_size,
                elapsed_ms=elapsed_ms,
            )

            logger.debug(f"Updating request {request_id} with response data")
            await self._http_repo.update(request_id, update_data)
            logger.debug(f"Request {request_id} updated successfully")

        except Exception as e:
            logger.error(f"Failed to update request record: {e}", exc_info=True)

    async def _log_request_error(
        self, request_record: Any | None, error_message: str
    ) -> None:
        """Log an error for an HTTP request."""
        if not self._http_repo or not request_record:
            return

        try:
            from code_mcp.db.schemas import HttpRequestUpdate

            update_data = HttpRequestUpdate(error_message=error_message)
            await self._http_repo.update(request_record.id, update_data)
        except Exception as e:
            logger.error(f"Failed to log request error: {e}", exc_info=True)

    def _filter_sensitive_data(self, data: dict) -> dict:
        """Filter sensitive headers/data based on configuration."""
        if not self._config.sensitive_headers:
            # Log everything by default
            return data

        # Filter out sensitive headers if configured
        filtered = {}
        for key, value in data.items():
            if key.lower() in [h.lower() for h in self._config.sensitive_headers]:
                filtered[key] = "[FILTERED]"
            else:
                filtered[key] = value
        return filtered
