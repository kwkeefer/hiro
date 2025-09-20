"""Vector similarity search utilities using pgvector."""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .embeddings import EmbeddingGenerator

logger = logging.getLogger(__name__)


class VectorSearch:
    """PostgreSQL pgvector search utilities."""

    def __init__(
        self,
        embedding_generator: EmbeddingGenerator | None = None,
        similarity_threshold: float = 0.5,
    ):
        """Initialize vector search.

        Args:
            embedding_generator: EmbeddingGenerator instance.
            similarity_threshold: Default similarity threshold for searches.
        """
        self.embeddings = embedding_generator or EmbeddingGenerator()
        self.similarity_threshold = similarity_threshold

    async def encode_text(self, text: str) -> Any:
        """Encode text to embeddings (async wrapper for compatibility)."""
        return self.embeddings.encode_text(text)

    async def find_similar_actions(
        self,
        query: str,
        mission_id: UUID | None = None,
        limit: int = 10,
        success_only: bool = False,
        session: AsyncSession | None = None,
    ) -> list[dict[str, Any]]:
        """Find similar past actions using vector similarity.

        Args:
            session: Database session.
            query: Query text to search for.
            mission_id: Optional mission ID to filter by.
            limit: Maximum number of results.
            success_only: Only return successful actions.

        Returns:
            List of similar actions with similarity scores.
        """
        query_embedding = self.embeddings.encode_text(query)

        # Build the query with pgvector similarity
        # Note: For asyncpg, we need to use CAST
        sql = """
            SELECT
                ta.*,
                1 - (ta.action_embedding <=> CAST(:embedding AS vector)) as similarity
            FROM mission_actions ta
            WHERE ta.action_embedding IS NOT NULL
        """

        # Convert to string format for pgvector
        params: dict[str, str | float | int] = {
            "embedding": str(query_embedding.tolist())
        }

        if mission_id:
            sql += " AND ta.mission_id = :mission_id"
            params["mission_id"] = str(mission_id)

        if success_only:
            sql += " AND ta.success = true"

        # Note: <=> operator returns distance (0 = identical, 2 = opposite)
        # So we filter by distance < (1 - similarity_threshold)
        max_distance = 1.0 - self.similarity_threshold
        sql += """
            AND (ta.action_embedding <=> CAST(:embedding AS vector)) < :max_distance
            ORDER BY ta.action_embedding <=> CAST(:embedding AS vector)
            LIMIT :limit
        """
        params["max_distance"] = max_distance
        params["limit"] = limit

        if session is None:
            logger.warning("No database session provided for vector search")
            return []

        result = await session.execute(text(sql), params)
        rows = result.fetchall()

        # Convert rows to dictionaries
        actions = []
        for row in rows:
            action_dict = dict(row._mapping)
            actions.append(action_dict)

        return actions

    async def find_successful_patterns_by_technique(
        self,
        session: AsyncSession,
        technique: str,
        across_targets: bool = True,  # noqa: ARG002
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Find successful patterns similar to a technique.

        Args:
            session: Database session.
            technique: Technique to find patterns for.
            across_targets: Search across all targets or just current.
            limit: Maximum number of results.

        Returns:
            List of successful patterns with similarity scores.
        """
        technique_embedding = self.embeddings.encode_text(technique)

        sql = """
            SELECT
                ta.*,
                m.name as mission_name,
                m.mission_type,
                1 - (ta.action_embedding <=> CAST(:embedding AS vector)) as similarity
            FROM mission_actions ta
            JOIN missions m ON ta.mission_id = m.id
            WHERE ta.success = true
                AND ta.action_embedding IS NOT NULL
                AND (ta.action_embedding <=> CAST(:embedding AS vector)) < :max_distance
            ORDER BY ta.action_embedding <=> CAST(:embedding AS vector)
            LIMIT :limit
        """

        max_distance = 1.0 - self.similarity_threshold
        params: dict[str, str | float | int] = {
            "embedding": str(technique_embedding.tolist()),
            "max_distance": max_distance,
            "limit": limit,
        }

        result = await session.execute(text(sql), params)
        rows = result.fetchall()

        patterns = []
        for row in rows:
            pattern_dict = dict(row._mapping)
            patterns.append(pattern_dict)

        return patterns

    async def search_technique_library(
        self,
        session: AsyncSession,
        query: str,
        category: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search technique library using semantic search.

        Args:
            session: Database session.
            query: Query text to search for.
            category: Optional category filter.
            limit: Maximum number of results.

        Returns:
            List of matching techniques with similarity scores.
        """
        query_embedding = self.embeddings.encode_text(query)

        sql = """
            SELECT
                tl.*,
                1 - (tl.content_embedding <=> CAST(:embedding AS vector)) as similarity
            FROM technique_library tl
            WHERE tl.content_embedding IS NOT NULL
        """

        # Convert to string format for pgvector
        params: dict[str, str | float | int] = {
            "embedding": str(query_embedding.tolist())
        }

        if category:
            sql += " AND tl.category = :category"
            params["category"] = category

        max_distance = 1.0 - self.similarity_threshold
        sql += """
            AND (tl.content_embedding <=> CAST(:embedding AS vector)) < :max_distance
            ORDER BY tl.content_embedding <=> CAST(:embedding AS vector)
            LIMIT :limit
        """
        params["max_distance"] = max_distance
        params["limit"] = limit

        result = await session.execute(text(sql), params)
        rows = result.fetchall()

        techniques = []
        for row in rows:
            technique_dict = dict(row._mapping)
            techniques.append(technique_dict)

        return techniques

    async def find_successful_patterns(
        self,
        mission_type: str | None = None,
        target_id: UUID | None = None,
        limit: int = 10,
        session: AsyncSession | None = None,
    ) -> list[dict[str, Any]]:
        """Find successful patterns for a mission type.

        Args:
            mission_type: Optional mission type filter.
            target_id: Optional target ID filter.
            limit: Maximum number of results.
            session: Database session.

        Returns:
            List of successful patterns.
        """
        if not session:
            raise ValueError("Session is required for database operations")

        sql = """
            SELECT
                ta.*,
                m.name as mission_name,
                m.mission_type,
                m.goal as mission_goal
            FROM mission_actions ta
            JOIN missions m ON ta.mission_id = m.id
            WHERE ta.success = true
        """

        params: dict[str, str | int] = {"limit": limit}

        if mission_type:
            sql += " AND m.mission_type = :mission_type"
            params["mission_type"] = mission_type

        if target_id:
            sql += """
                AND EXISTS (
                    SELECT 1 FROM mission_targets mt
                    WHERE mt.mission_id = m.id AND mt.target_id = :target_id
                )
            """
            params["target_id"] = str(target_id)

        sql += """
            ORDER BY ta.created_at DESC
            LIMIT :limit
        """

        result = await session.execute(text(sql), params)
        rows = result.fetchall()

        patterns = []
        for row in rows:
            pattern_dict = dict(row._mapping)
            patterns.append(pattern_dict)

        return patterns

    async def add_action_embeddings(
        self,
        session: AsyncSession,
        action_id: UUID,
        technique: str,
        payload: str | None = None,
        result: str | None = None,
    ) -> None:
        """Generate and add embeddings for a mission action.

        Args:
            session: Database session.
            action_id: Action ID to update.
            technique: Technique description.
            payload: Optional payload.
            result: Optional result.
        """
        # Generate embeddings for action and result
        action_text = self.embeddings.combine_text_for_embedding(
            technique, payload, None
        )
        action_embedding = self.embeddings.encode_text(action_text)

        result_embedding = None
        if result:
            result_text = self.embeddings.combine_text_for_embedding(
                technique, None, result
            )
            result_embedding = self.embeddings.encode_text(result_text)

        # Update the action with embeddings
        update_sql = """
            UPDATE mission_actions
            SET action_embedding = CAST(:action_embedding AS vector)
        """
        params = {
            "action_embedding": str(action_embedding.tolist()),
            "action_id": str(action_id),
        }

        if result_embedding is not None:
            update_sql += ", result_embedding = CAST(:result_embedding AS vector)"
            params["result_embedding"] = str(result_embedding.tolist())

        update_sql += " WHERE id = :action_id"

        await session.execute(text(update_sql), params)
        await session.commit()

    async def add_technique_embedding(
        self,
        session: AsyncSession,
        technique_id: UUID,
        content: str,
    ) -> None:
        """Generate and add embedding for a technique library entry.

        Args:
            session: Database session.
            technique_id: Technique library entry ID.
            content: Content to embed.
        """
        embedding = self.embeddings.encode_text(content)

        update_sql = """
            UPDATE technique_library
            SET content_embedding = CAST(:embedding AS vector)
            WHERE id = :technique_id
        """

        await session.execute(
            text(update_sql),
            {"embedding": str(embedding.tolist()), "technique_id": str(technique_id)},
        )
        await session.commit()
