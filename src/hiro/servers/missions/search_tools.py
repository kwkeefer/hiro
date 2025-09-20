"""Search tools for finding techniques and analyzing what worked."""

import logging
from collections import defaultdict
from typing import Annotated, Any
from uuid import UUID

from pydantic import Field
from sqlalchemy import text

from hiro.core.mcp.exceptions import ToolError
from hiro.core.vector.search import VectorSearch
from hiro.db.repositories import MissionActionRepository

logger = logging.getLogger(__name__)


class MissionSearchTool:
    """Search tools for finding relevant techniques and their effectiveness."""

    def __init__(
        self,
        action_repo: MissionActionRepository,
        vector_search: VectorSearch | None = None,
    ) -> None:
        """Initialize the search tool."""
        self._action_repo = action_repo
        self._vector_search = vector_search

    async def _get_session(self):
        """Get database session from repository if available."""
        if hasattr(self._action_repo, "_session_factory"):
            return self._action_repo._session_factory()
        raise ToolError("search", "No database session available for vector operations")

    async def find_similar_techniques(
        self,
        technique: Annotated[
            str, Field(description="Technique to search for similar ones")
        ],
        mission_id: Annotated[
            str | None, Field(description="Optional mission ID to limit search scope")
        ] = None,
        limit: Annotated[int, Field(description="Maximum results to return")] = 10,
        similarity_threshold: Annotated[
            float, Field(description="Minimum similarity score (0.0 to 1.0)")
        ] = 0.5,
    ) -> dict[str, Any]:
        """Find techniques similar to the provided one using vector similarity."""
        if not self._vector_search:
            raise ToolError(
                "find_similar_techniques",
                "Vector search not available (pgvector not configured)",
            )

        # Validate parameters
        if similarity_threshold < 0.0 or similarity_threshold > 1.0:
            raise ToolError(
                "find_similar_techniques",
                "Similarity threshold must be between 0.0 and 1.0",
            )

        mission_uuid = None
        if mission_id:
            try:
                mission_uuid = UUID(mission_id)
            except ValueError as e:
                raise ToolError(
                    "find_similar_techniques", f"Invalid mission UUID: {mission_id}"
                ) from e

        # Perform vector search
        async with await self._get_session() as session:
            results = await self._vector_search.find_similar_actions(
                query=technique,
                mission_id=mission_uuid,
                limit=limit * 2,  # Get extra to filter by threshold
                success_only=False,  # Include both successes and failures
                session=session,
            )

        # Filter by similarity threshold
        filtered = [
            r for r in results if r.get("similarity", 0) >= similarity_threshold
        ][:limit]

        # Group by technique to aggregate statistics
        technique_stats: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"success": 0, "failure": 0, "learnings": []}
        )

        for result in filtered:
            tech = result["technique"]
            if result["success"]:
                technique_stats[tech]["success"] += 1
            else:
                technique_stats[tech]["failure"] += 1
            if result.get("learning"):
                technique_stats[tech]["learnings"].append(result["learning"])

        # Format results
        techniques = []
        for tech, stats in technique_stats.items():
            total = stats["success"] + stats["failure"]
            success_rate = stats["success"] / total if total > 0 else 0
            techniques.append(
                {
                    "technique": tech,
                    "success_rate": round(success_rate, 2),
                    "total_uses": total,
                    "successes": stats["success"],
                    "failures": stats["failure"],
                    "sample_learnings": stats["learnings"][:2],  # First 2 learnings
                }
            )

        # Sort by success rate
        techniques.sort(
            key=lambda x: (x["success_rate"], x["total_uses"]), reverse=True
        )

        return {
            "query": technique,
            "similar_techniques": techniques,
            "total_found": len(techniques),
            "filters": {
                "mission_id": mission_id,
                "similarity_threshold": similarity_threshold,
            },
        }

    async def search_techniques(
        self,
        success_only: Annotated[
            bool, Field(description="Only return successful techniques")
        ] = False,
        mission_type: Annotated[
            str | None, Field(description="Filter by mission type")
        ] = None,
        min_success_rate: Annotated[
            float | None, Field(description="Minimum success rate (0.0 to 1.0)")
        ] = None,
        min_usage_count: Annotated[
            int, Field(description="Minimum times technique was used")
        ] = 1,
        limit: Annotated[int, Field(description="Maximum results")] = 20,
    ) -> dict[str, Any]:
        """Search for techniques based on their effectiveness and usage."""
        # Validate parameters
        if min_success_rate is not None and (
            min_success_rate < 0.0 or min_success_rate > 1.0
        ):
            raise ToolError(
                "search_techniques", "min_success_rate must be between 0.0 and 1.0"
            )

        async with await self._get_session() as session:
            # Build query
            sql = """
                SELECT
                    ta.technique,
                    ta.action_type,
                    COUNT(*) as usage_count,
                    SUM(CASE WHEN ta.success THEN 1 ELSE 0 END) as success_count,
                    AVG(CASE WHEN ta.success THEN 1.0 ELSE 0.0 END) as success_rate,
                    COUNT(DISTINCT ta.mission_id) as mission_count
                FROM mission_actions ta
            """

            # Join with missions if we need to filter by type
            if mission_type:
                sql += " JOIN missions m ON ta.mission_id = m.id"

            sql += " WHERE 1=1"

            params: dict[str, Any] = {"limit": limit, "min_usage": min_usage_count}

            if success_only:
                sql += " AND ta.success = true"

            if mission_type:
                sql += " AND m.mission_type = :mission_type"
                params["mission_type"] = mission_type

            sql += """
                GROUP BY ta.technique, ta.action_type
                HAVING COUNT(*) >= :min_usage
            """

            if min_success_rate is not None:
                sql += " AND AVG(CASE WHEN ta.success THEN 1.0 ELSE 0.0 END) >= :min_success_rate"
                params["min_success_rate"] = min_success_rate

            sql += " ORDER BY success_rate DESC, usage_count DESC LIMIT :limit"

            result = await session.execute(text(sql), params)
            rows = result.fetchall()

        # Format results
        techniques = []
        for row in rows:
            row_dict = dict(row._mapping)
            techniques.append(
                {
                    "technique": row_dict["technique"],
                    "action_type": row_dict["action_type"],
                    "success_rate": round(float(row_dict["success_rate"]), 2),
                    "usage_count": row_dict["usage_count"],
                    "success_count": row_dict["success_count"],
                    "mission_coverage": row_dict["mission_count"],
                }
            )

        return {
            "techniques": techniques,
            "total_found": len(techniques),
            "filters": {
                "success_only": success_only,
                "mission_type": mission_type,
                "min_success_rate": min_success_rate,
                "min_usage_count": min_usage_count,
            },
        }

    async def get_technique_stats(
        self,
        technique: Annotated[
            str, Field(description="Exact technique name to get stats for")
        ],
    ) -> dict[str, Any]:
        """Get detailed statistics for a specific technique."""
        async with await self._get_session() as session:
            # Get overall stats
            stats_sql = """
                SELECT
                    COUNT(*) as total_uses,
                    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successes,
                    COUNT(DISTINCT mission_id) as missions_used,
                    COUNT(DISTINCT action_type) as action_types,
                    MAX(created_at) as last_used
                FROM mission_actions
                WHERE technique = :technique
            """

            stats_result = await session.execute(
                text(stats_sql), {"technique": technique}
            )
            stats = stats_result.fetchone()

            if not stats or stats.total_uses == 0:
                return {
                    "technique": technique,
                    "found": False,
                    "message": f"No data found for technique: {technique}",
                }

            stats_dict = dict(stats._mapping)

            # Get context where it failed
            failure_sql = """
                SELECT
                    m.mission_type,
                    ta.learning,
                    COUNT(*) as failure_count
                FROM mission_actions ta
                JOIN missions m ON ta.mission_id = m.id
                WHERE ta.technique = :technique AND ta.success = false
                GROUP BY m.mission_type, ta.learning
                ORDER BY failure_count DESC
                LIMIT 5
            """

            failure_result = await session.execute(
                text(failure_sql), {"technique": technique}
            )
            failures = failure_result.fetchall()

            # Get context where it succeeded
            success_sql = """
                SELECT
                    m.mission_type,
                    ta.learning,
                    COUNT(*) as success_count
                FROM mission_actions ta
                JOIN missions m ON ta.mission_id = m.id
                WHERE ta.technique = :technique AND ta.success = true
                GROUP BY m.mission_type, ta.learning
                ORDER BY success_count DESC
                LIMIT 5
            """

            success_result = await session.execute(
                text(success_sql), {"technique": technique}
            )
            successes = success_result.fetchall()

        # Calculate derived stats
        total_uses = stats_dict["total_uses"]
        success_count = stats_dict["successes"]
        failure_count = total_uses - success_count
        success_rate = success_count / total_uses if total_uses > 0 else 0

        return {
            "technique": technique,
            "found": True,
            "stats": {
                "total_uses": total_uses,
                "success_count": success_count,
                "failure_count": failure_count,
                "success_rate": round(success_rate, 2),
                "missions_used_in": stats_dict["missions_used"],
                "action_types_used": stats_dict["action_types"],
                "last_used": stats_dict["last_used"].isoformat()
                if stats_dict["last_used"]
                else None,
            },
            "failure_contexts": [
                {
                    "mission_type": f.mission_type,
                    "learning": f.learning,
                    "count": f.failure_count,
                }
                for f in failures
            ],
            "success_contexts": [
                {
                    "mission_type": s.mission_type,
                    "learning": s.learning,
                    "count": s.success_count,
                }
                for s in successes
            ],
        }
