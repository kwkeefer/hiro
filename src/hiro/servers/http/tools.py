"""HTTP operation tools for penetration testing."""

import json
import logging
from typing import Annotated, Any, ClassVar, Literal
from urllib.parse import ParseResult, urlparse

import httpx
from pydantic import BaseModel, Field, field_validator

from hiro.core.mcp.exceptions import ToolError
from hiro.db.repositories import HttpRequestRepository, TargetRepository
from hiro.db.schemas import HttpRequestCreate

from .config import HttpConfig
from .cookie_sessions import CookieSessionProvider

logger = logging.getLogger(__name__)


class HttpRequestParams(BaseModel):
    """Parameters for HTTP request with built-in data transformations."""

    # Define field descriptions as class variables for reuse
    URL_DESC: ClassVar[str] = "Target URL to request"
    METHOD_DESC: ClassVar[str] = "HTTP method to use"
    HEADERS_DESC: ClassVar[str] = (
        'Custom headers as JSON object, e.g. {"User-Agent": "MyBot", "Accept": "application/json"}'
    )
    DATA_DESC: ClassVar[str] = "Request body data (JSON string or raw data)"
    PARAMS_DESC: ClassVar[str] = (
        'URL parameters as JSON object, e.g. {"page": "1", "limit": "10"}'
    )
    COOKIES_DESC: ClassVar[str] = (
        'Cookies as JSON object, e.g. {"session": "abc123", "theme": "dark"}'
    )
    COOKIE_PROFILE_DESC: ClassVar[str] = (
        "Name of a cookie profile/session to load cookies from (e.g. 'admin_session'). "
        "Profile cookies are merged with manually provided cookies, with manual cookies taking precedence."
    )
    FOLLOW_REDIRECTS_DESC: ClassVar[str] = "Whether to follow HTTP redirects"
    AUTH_DESC: ClassVar[str] = (
        'Basic auth as JSON object with username and password, e.g. {"username": "user", "password": "pass"}'
    )

    url: str = Field(description=URL_DESC)
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"] = Field(
        "GET", description=METHOD_DESC
    )
    headers: dict[str, str] | None = Field(None, description=HEADERS_DESC)
    data: str | None = Field(None, description=DATA_DESC)
    params: dict[str, str] | None = Field(None, description=PARAMS_DESC)
    cookies: dict[str, str] | None = Field(None, description=COOKIES_DESC)
    cookie_profile: str | None = Field(None, description=COOKIE_PROFILE_DESC)
    follow_redirects: bool = Field(True, description=FOLLOW_REDIRECTS_DESC)
    auth: dict[str, str] | None = Field(None, description=AUTH_DESC)

    @field_validator("headers", "params", "cookies", "auth", mode="before")
    @classmethod
    def parse_json_strings(cls, v: Any) -> dict[str, str] | None:
        """Convert JSON strings to dictionaries if needed."""
        if v is None:
            return None
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if not isinstance(parsed, dict):
                    raise ValueError("Must be a JSON object")
                # Convert all values to strings
                return {str(k): str(val) for k, val in parsed.items()}
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON: {e}") from e
        if isinstance(v, dict):
            # Ensure all keys and values are strings
            return {str(k): str(val) for k, val in v.items()}
        return v  # type: ignore[no-any-return]

    @property
    def method_upper(self) -> str:
        """Get method in uppercase."""
        return self.method.upper()

    @property
    def params_dict(self) -> dict[str, str]:
        """Get params as dict, never None."""
        return self.params or {}

    @property
    def parsed_url(self) -> ParseResult:
        """Get parsed URL components."""
        return urlparse(self.url)

    @property
    def host(self) -> str:
        """Get hostname from URL."""
        parsed = self.parsed_url
        return parsed.hostname or parsed.netloc

    @property
    def path(self) -> str:
        """Get path from URL."""
        return self.parsed_url.path or "/"

    @property
    def auth_tuple(self) -> tuple[str, str] | None:
        """Get auth as tuple for httpx if valid."""
        if self.auth and "username" in self.auth and "password" in self.auth:
            return (self.auth["username"], self.auth["password"])
        return None

    def get_json_data(self) -> Any | None:
        """Parse data as JSON if possible, return None if not valid JSON."""
        if not self.data:
            return None
        try:
            return json.loads(self.data)
        except json.JSONDecodeError:
            return None

    @property
    def is_json_data(self) -> bool:
        """Check if data is valid JSON."""
        return self.get_json_data() is not None

    def merge_headers(self, base_headers: dict[str, str] | None) -> dict[str, str]:
        """Merge request headers with base headers (request headers override)."""
        merged = {}
        if base_headers:
            merged.update(base_headers)
        if self.headers:
            merged.update(self.headers)
        return merged


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
        cookie_provider: CookieSessionProvider | None = None,
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
        self._cookie_provider = cookie_provider

    async def execute(
        self,
        url: Annotated[str, Field(description=HttpRequestParams.URL_DESC)],
        method: Annotated[
            Literal["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
            Field(description=HttpRequestParams.METHOD_DESC),
        ] = "GET",
        headers: Annotated[
            str | None, Field(description=HttpRequestParams.HEADERS_DESC)
        ] = None,
        data: Annotated[
            str | None, Field(description=HttpRequestParams.DATA_DESC)
        ] = None,
        params: Annotated[
            str | None, Field(description=HttpRequestParams.PARAMS_DESC)
        ] = None,
        cookies: Annotated[
            str | None, Field(description=HttpRequestParams.COOKIES_DESC)
        ] = None,
        cookie_profile: Annotated[
            str | None, Field(description=HttpRequestParams.COOKIE_PROFILE_DESC)
        ] = None,
        follow_redirects: Annotated[
            bool, Field(description=HttpRequestParams.FOLLOW_REDIRECTS_DESC)
        ] = True,
        auth: Annotated[
            str | None, Field(description=HttpRequestParams.AUTH_DESC)
        ] = None,
    ) -> dict[str, Any]:
        """Make HTTP request with full control over headers, data, and parameters.

        Proxy and tracing headers are automatically configured by the server.
        All requests are automatically routed through configured proxy and
        include tracing headers for audit purposes.

        Args:
            url: Target URL to request
            method: HTTP method to use
            headers: Custom headers as JSON string, e.g. '{"User-Agent": "MyBot", "Accept": "application/json"}'
            data: Request body data (JSON string or raw data)
            params: URL parameters as JSON string, e.g. '{"page": "1", "limit": "10"}'
            cookies: Cookies as JSON string, e.g. '{"session": "abc123", "theme": "dark"}'
            cookie_profile: Name of a cookie profile to load cookies from (e.g. 'admin_session')
            follow_redirects: Whether to follow HTTP redirects
            auth: Basic auth as JSON string, e.g. '{"username": "user", "password": "pass"}'

        Returns:
            Response data containing status_code, headers, text, json (if applicable),
            cookies, elapsed_ms, and request details for audit trail

        Raises:
            ToolError: If request fails due to timeout, connection, or other errors
        """
        # Create and validate parameters using Pydantic model
        try:
            request = HttpRequestParams(
                url=url,
                method=method,
                headers=headers,  # type: ignore[arg-type]  # Validator converts JSON string to dict
                data=data,
                params=params,  # type: ignore[arg-type]  # Validator converts JSON string to dict
                cookies=cookies,  # type: ignore[arg-type]  # Validator converts JSON string to dict
                cookie_profile=cookie_profile,
                follow_redirects=follow_redirects,
                auth=auth,  # type: ignore[arg-type]  # Validator converts JSON string to dict
            )
        except Exception as e:
            raise ToolError("http_request", f"Invalid parameters: {str(e)}") from e

        # Load cookies from profile if specified
        merged_cookies = {}
        if request.cookie_profile:
            if not self._cookie_provider:
                raise ToolError(
                    "http_request",
                    "Cookie profiles not configured. Please configure cookie sessions to use profiles.",
                )

            try:
                # Get cookies from the profile
                profile_data = await self._cookie_provider.get_resource(
                    f"cookie-session://{request.cookie_profile}"
                )

                # Check for errors in the profile response
                if "error" in profile_data:
                    raise ToolError(
                        "http_request",
                        f"Failed to load cookie profile '{request.cookie_profile}': {profile_data['error']}",
                    )

                # Extract cookies from profile
                profile_cookies = profile_data.get("cookies", {})
                merged_cookies.update(profile_cookies)

            except ToolError:
                raise  # Re-raise ToolErrors as-is
            except Exception as e:
                raise ToolError(
                    "http_request",
                    f"Failed to load cookie profile '{request.cookie_profile}': {str(e)}",
                ) from e

        # Merge with manually provided cookies
        if request.cookies:
            # Check for overlapping cookies and warn
            if merged_cookies:
                overlapping = set(merged_cookies.keys()) & set(request.cookies.keys())
                if overlapping:
                    logger.warning(
                        f"Cookie profile '{request.cookie_profile}' cookies overwritten for keys: {overlapping}"
                    )

            merged_cookies.update(request.cookies)

        # Update request object with merged cookies
        request.cookies = merged_cookies if merged_cookies else None

        # Initialize tracking variables
        request_record = None
        target_record = None
        error_message = None

        try:
            # Prepare client configuration with injected settings
            client_config: dict[str, Any] = {
                "timeout": self._config.timeout,
                "verify": self._config.verify_ssl,
                "follow_redirects": request.follow_redirects,
            }

            # Inject proxy from server config if configured
            if self._config.proxy_url:
                client_config["proxy"] = self._config.proxy_url

            # Merge headers: injected tracing headers + user headers
            merged_headers = request.merge_headers(self._config.tracing_headers)

            # Prepare request configuration
            request_config: dict[str, Any] = {
                "method": request.method_upper,
                "url": request.url,
                "headers": merged_headers,
                "params": request.params_dict,
                "cookies": merged_cookies,
            }

            # Add authentication if provided
            if request.auth_tuple:
                request_config["auth"] = request.auth_tuple

            # Add data if provided
            request_body_for_logging = None
            if request.data:
                json_data = request.get_json_data()
                if json_data is not None:
                    request_config["json"] = json_data
                else:
                    request_config["content"] = request.data
                request_body_for_logging = request.data

            # Create target and log pre-request if database logging is enabled
            if self._config.logging_enabled and self._http_repo and self._target_repo:
                try:
                    # Auto-create/get target from URL
                    target_record = await self._target_repo.get_or_create_from_url(
                        request.url
                    )

                    # Log request (pre-response)
                    request_record = await self._log_request_start(
                        method=request.method_upper,
                        url=request.url,
                        host=request.host,
                        path=request.path,
                        query_params=request.params_dict if request.params else None,
                        headers=merged_headers,
                        cookies=request.cookies or {},
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
                    "method": request.method_upper,
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
                    "url": request.url,
                    "method": request.method_upper,
                    "headers_sent": merged_headers,  # Show what was actually sent
                    "headers_user": request.headers or {},  # Show what user requested
                    "cookies": merged_cookies,  # Show cookies that were sent
                    "cookie_profile": request.cookie_profile,  # Show profile used if any
                    "params": request.params or {},
                    "data": request.data,
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

            from hiro.db.schemas import HttpRequestUpdate

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
            from hiro.db.schemas import HttpRequestUpdate

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
