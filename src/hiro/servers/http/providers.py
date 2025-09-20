"""HTTP tool providers with configuration injection."""

from typing import TYPE_CHECKING, Any, Union

from hiro.db.repositories import HttpRequestRepository, TargetRepository

if TYPE_CHECKING:
    from hiro.db.lazy_repository import (
        LazyHttpRequestRepository,
        LazyTargetRepository,
    )

from .config import HttpConfig
from .cookie_sessions import CookieSessionProvider
from .tools import HttpRequestTool


class HttpToolProvider:
    """Tool provider for HTTP operations with injected configuration.

    IMPORTANT: This provider is part of the unified serve-http server.
    It provides HTTP request tools that are always available.

    When DATABASE_URL is configured, these tools work seamlessly with
    the AI logging tools from servers/ai_logging/ in the SAME server.

    Uses hybrid approach: provides organized structure and testable business logic,
    while allowing direct tool registration for FastMCP compatibility.
    """

    def __init__(
        self,
        config: HttpConfig,
        http_repo: Union[
            HttpRequestRepository, "LazyHttpRequestRepository", None
        ] = None,
        target_repo: Union[TargetRepository, "LazyTargetRepository", None] = None,
        mission_id: str | None = None,
        cookie_provider: CookieSessionProvider | None = None,
    ):
        """Initialize with server configuration and optional database repositories.

        Args:
            config: HTTP server configuration for proxy, headers, etc.
            http_repo: Repository for logging HTTP requests (optional)
            target_repo: Repository for managing targets (optional)
            mission_id: Current mission ID for linking requests (optional)
            cookie_provider: Provider for cookie sessions/profiles (optional)
        """
        self._config = config
        self._http_repo = http_repo
        self._target_repo = target_repo
        self._mission_id = mission_id
        self._cookie_provider = cookie_provider
        self._mission_provider: Any | None = (
            None  # Will be set via set_mission_provider
        )
        self._http_tool = HttpRequestTool(
            config=config,
            http_repo=http_repo,
            target_repo=target_repo,
            mission_id=mission_id,
            cookie_provider=cookie_provider,
        )

    @property
    def config(self) -> HttpConfig:
        """Access to current configuration."""
        return self._config

    @property
    def http_tool(self) -> HttpRequestTool:
        """Access to HTTP request tool for direct registration."""
        return self._http_tool

    def set_mission_provider(self, mission_provider: Any) -> None:
        """Set the mission provider for context awareness.

        This implements the dependency injection pattern from ADR-009.
        Called after both providers are created to link them.

        Args:
            mission_provider: MissionManagementProvider instance
        """
        self._mission_provider = mission_provider
        # Also update the HTTP tool's mission provider
        self._http_tool.set_mission_provider(mission_provider)
