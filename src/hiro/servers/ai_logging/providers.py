"""AI logging tool providers with database integration."""

from typing import TYPE_CHECKING, Union

from hiro.db.repositories import TargetContextRepository, TargetRepository

if TYPE_CHECKING:
    from hiro.db.lazy_repository import (
        LazyTargetContextRepository,
        LazyTargetRepository,
    )

from .tools import (
    CreateTargetTool,
    GetTargetContextTool,
    GetTargetSummaryTool,
    SearchTargetsTool,
    UpdateTargetContextTool,
    UpdateTargetStatusTool,
)


class AiLoggingToolProvider:
    """Tool provider for AI logging operations with database integration.

    IMPORTANT: This provider is part of the unified serve-http server.
    It provides target management tools when DATABASE_URL is configured.

    These tools work alongside HTTP tools from servers/http/ in the
    SAME server instance. This is NOT a separate server - all tools
    are registered with the single FastMCP server in cli.py.

    Integration with HTTP tools:
    - HTTP requests auto-create targets if they don't exist
    - HTTP requests auto-log to the database
    - These tools let you manage and query that data

    Uses hybrid approach: provides organized structure and testable business logic,
    while allowing direct tool registration for FastMCP compatibility.
    """

    def __init__(
        self,
        target_repo: Union[TargetRepository, "LazyTargetRepository", None] = None,
        context_repo: Union[
            TargetContextRepository, "LazyTargetContextRepository", None
        ] = None,
        mission_id: str | None = None,
    ):
        """Initialize with database repositories.

        Args:
            target_repo: Repository for managing targets (optional)
            context_repo: Repository for managing context versions (optional)
            mission_id: Current mission ID for linking operations (optional)
        """
        self._target_repo = target_repo
        self._context_repo = context_repo
        self._mission_id = mission_id

        # Initialize tools as properties for direct registration
        self._create_target_tool = CreateTargetTool(target_repo=target_repo)
        self._update_target_tool = UpdateTargetStatusTool(target_repo=target_repo)
        self._get_summary_tool = GetTargetSummaryTool(target_repo=target_repo)
        self._search_targets_tool = SearchTargetsTool(target_repo=target_repo)

        # Context management tools (simplified to 2 tools only)
        self._get_context_tool = GetTargetContextTool(
            context_repo=context_repo, target_repo=target_repo
        )
        self._update_context_tool = UpdateTargetContextTool(
            context_repo=context_repo, target_repo=target_repo
        )

    @property
    def create_target_tool(self) -> CreateTargetTool:
        """Access to create target tool for direct registration."""
        return self._create_target_tool

    @property
    def update_target_tool(self) -> UpdateTargetStatusTool:
        """Access to update target tool for direct registration."""
        return self._update_target_tool

    @property
    def get_summary_tool(self) -> GetTargetSummaryTool:
        """Access to get target summary tool for direct registration."""
        return self._get_summary_tool

    @property
    def search_targets_tool(self) -> SearchTargetsTool:
        """Access to search targets tool for direct registration."""
        return self._search_targets_tool

    @property
    def get_context_tool(self) -> GetTargetContextTool:
        """Access to get context tool for direct registration."""
        return self._get_context_tool

    @property
    def update_context_tool(self) -> UpdateTargetContextTool:
        """Access to update context tool for direct registration."""
        return self._update_context_tool
