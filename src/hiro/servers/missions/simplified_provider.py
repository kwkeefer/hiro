"""Simplified mission management provider following ADR-017 principles."""

import logging
from typing import Any

from fastmcp import Context

from hiro.core.mcp.protocols import ToolProvider
from hiro.core.vector.search import VectorSearch
from hiro.db.repositories import (
    HttpRequestRepository,
    MissionActionRepository,
    MissionRepository,
)

from .core_tools import MissionCoreTool
from .library_tools import KnowledgeLibraryTool
from .search_tools import MissionSearchTool

logger = logging.getLogger(__name__)


class SimplifiedMissionProvider(ToolProvider):
    """Simplified mission management provider with clear tool separation.

    Following ADR-017:
    - Core tools: Mission operations during testing
    - Search tools: Finding what worked/didn't work
    - Library tools: Curated knowledge management
    """

    def __init__(
        self,
        mission_repo: MissionRepository,
        action_repo: MissionActionRepository,
        request_repo: HttpRequestRepository,
        vector_search: VectorSearch | None = None,
    ) -> None:
        """Initialize the simplified provider."""
        self._mission_repo = mission_repo
        self._action_repo = action_repo
        self._request_repo = request_repo
        self._vector_search = vector_search

        # Initialize tool categories
        self._core_tool = MissionCoreTool(
            mission_repo=mission_repo,
            action_repo=action_repo,
            vector_search=vector_search,
        )

        self._search_tool = MissionSearchTool(
            action_repo=action_repo,
            vector_search=vector_search,
        )

        # Library tool requires vector search
        self._library_tool: KnowledgeLibraryTool | None
        if vector_search:
            # Get session factory from action repo if available
            session_factory = None
            if hasattr(action_repo, "_session_factory"):
                session_factory = action_repo._session_factory

            self._library_tool = KnowledgeLibraryTool(
                vector_search=vector_search,
                session_factory=session_factory,
            )
        else:
            self._library_tool = None

        # Track current mission context at provider level (ADR-016)
        self._current_mission_id = None
        self._current_cookie_profile = None

    def register_tools(self, server: Any) -> None:
        """Register all simplified mission tools with the MCP server."""

        # ===== CORE OPERATIONS (During Testing) =====
        server.tool(
            self._core_tool.create_mission,
            name="create_mission",
            description="Create a new security testing mission",
        )

        server.tool(
            self._core_tool.set_mission_context,
            name="set_mission_context",
            description="Set the current mission context for HTTP requests",
        )

        server.tool(
            self._core_tool.get_mission_context,
            name="get_mission_context",
            description="Get mission context with basic stats (current or specific mission)",
        )

        server.tool(
            self._core_tool.record_action,
            name="record_action",
            description="Record a test action and link recent HTTP requests",
        )

        # ===== SEARCH TOOLS (Finding What Worked) =====
        if self._vector_search:
            server.tool(
                self._search_tool.find_similar_techniques,
                name="find_similar_techniques",
                description="Find techniques similar to a given one using vector similarity",
            )

        server.tool(
            self._search_tool.search_techniques,
            name="search_techniques",
            description="Search techniques by success rate, type, and usage",
        )

        server.tool(
            self._search_tool.get_technique_stats,
            name="get_technique_stats",
            description="Get detailed statistics for a specific technique",
        )

        # ===== LIBRARY TOOLS (Curated Knowledge) =====
        if self._library_tool:
            server.tool(
                self._library_tool.add_to_library,
                name="add_to_library",
                description="Add a valuable technique to the curated knowledge library",
            )

            server.tool(
                self._library_tool.search_library,
                name="search_library",
                description="Search the curated knowledge library for proven techniques",
            )

            server.tool(
                self._library_tool.get_library_stats,
                name="get_library_stats",
                description="Get statistics about the knowledge library",
            )

        logger.info(
            f"Registered {10 if self._library_tool else 7} mission tools "
            f"(vector search {'enabled' if self._vector_search else 'disabled'})"
        )

    # ===== Provider-level context management (ADR-016) =====

    def get_current_mission_id(self) -> str | None:
        """Get the current mission ID for HTTP tool integration."""
        # First check if core tool has a mission set
        if (
            hasattr(self._core_tool, "_current_mission_id")
            and self._core_tool._current_mission_id
        ):
            return str(self._core_tool._current_mission_id)
        return self._current_mission_id

    def get_current_cookie_profile(self) -> str | None:
        """Get the current cookie profile for HTTP tool integration."""
        return self._current_cookie_profile

    async def set_mission_context_wrapper(
        self,
        ctx: Context,  # noqa: ARG002
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Wrapper for set_mission_context that also updates provider state."""
        result = await self._core_tool.set_mission_context(**kwargs)

        # Update provider-level state for HTTP tool integration
        self._current_mission_id = kwargs.get("mission_id")
        self._current_cookie_profile = kwargs.get("cookie_profile")

        return result
