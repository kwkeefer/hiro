"""Knowledge library tools for curated technique storage and retrieval."""

import json
import logging
from typing import Annotated, Any, ClassVar, Literal

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text

from hiro.core.mcp.exceptions import ToolError
from hiro.core.vector.search import VectorSearch

logger = logging.getLogger(__name__)


class LibraryEntryParams(BaseModel):
    """Parameters for library entries."""

    CATEGORY_DESC: ClassVar[str] = (
        "Category: auth, api_pattern, security_control, payload, recon, exploit"
    )
    TITLE_DESC: ClassVar[str] = "Brief, descriptive title for the technique"
    CONTENT_DESC: ClassVar[str] = (
        "Full technique description, including examples and context"
    )
    METADATA_DESC: ClassVar[str] = (
        'Optional JSON metadata like {"tags": ["xss", "reflected"], "source_mission": "uuid"}'
    )

    category: Literal[
        "auth", "api_pattern", "security_control", "payload", "recon", "exploit"
    ] = Field(description=CATEGORY_DESC)
    title: str = Field(description=TITLE_DESC)
    content: str = Field(description=CONTENT_DESC)
    metadata: dict[str, Any] | None = Field(None, description=METADATA_DESC)

    @field_validator("metadata", mode="before")
    @classmethod
    def parse_metadata_json(cls, v: Any) -> dict[str, Any] | None:
        """Parse JSON string to dict if needed."""
        if v is None:
            return None
        if isinstance(v, str):
            try:
                return json.loads(v)  # type: ignore[no-any-return]
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in metadata: {e}") from e
        return v  # type: ignore[no-any-return]


class KnowledgeLibraryTool:
    """Tools for managing curated knowledge library."""

    def __init__(
        self,
        vector_search: VectorSearch,
        session_factory: Any | None = None,
    ) -> None:
        """Initialize the library tool."""
        self._vector_search = vector_search
        self._session_factory = session_factory

    async def _get_session(self):
        """Get database session."""
        if self._session_factory:
            return self._session_factory()
        raise ToolError("library", "No database session available")

    async def add_to_library(
        self,
        category: Annotated[str, Field(description=LibraryEntryParams.CATEGORY_DESC)],
        title: Annotated[str, Field(description=LibraryEntryParams.TITLE_DESC)],
        content: Annotated[str, Field(description=LibraryEntryParams.CONTENT_DESC)],
        metadata: Annotated[
            str | None, Field(description=LibraryEntryParams.METADATA_DESC)
        ] = None,
    ) -> dict[str, Any]:
        """Add a curated technique to the knowledge library.

        This is for valuable, proven techniques that should be preserved for future use.
        The LLM should decide what's worth saving based on success rates and learnings.
        """
        try:
            # Parse metadata if it's a JSON string
            parsed_metadata = None
            if metadata:
                if isinstance(metadata, str):
                    try:
                        parsed_metadata = json.loads(metadata)
                    except json.JSONDecodeError:
                        parsed_metadata = {"raw": metadata}
                else:
                    parsed_metadata = metadata

            params = LibraryEntryParams(
                category=category,  # type: ignore
                title=title,
                content=content,
                metadata=parsed_metadata,
            )
        except Exception as e:
            if hasattr(e, "errors"):
                error_details = []
                for error in e.errors():
                    field = ".".join(str(loc) for loc in error["loc"])
                    msg = error["msg"]
                    error_details.append(f"{field}: {msg}")
                error_msg = "Invalid parameters:\n" + "\n".join(error_details)
            else:
                error_msg = f"Invalid parameters: {str(e)}"
            raise ToolError("add_to_library", error_msg) from e

        # Generate embedding for searchability
        content_text = f"{params.title}\n{params.content}"
        content_embedding = self._vector_search.embeddings.encode_text(content_text)

        # Store in database
        async with await self._get_session() as session:
            # Check if similar entry already exists
            check_sql = """
                SELECT id, title,
                       1 - (content_embedding <=> CAST(:embedding AS vector)) as similarity
                FROM technique_library
                WHERE category = :category
                  AND (content_embedding <=> CAST(:embedding AS vector)) < 0.1
                LIMIT 1
            """

            existing = await session.execute(
                text(check_sql),
                {
                    "category": params.category,
                    "embedding": str(content_embedding.tolist()),
                },
            )
            duplicate = existing.fetchone()

            if duplicate and duplicate.similarity > 0.9:
                return {
                    "status": "duplicate",
                    "message": f"Very similar entry already exists: {duplicate.title}",
                    "existing_id": str(duplicate.id),
                    "similarity": round(duplicate.similarity, 3),
                }

            # Insert new entry - include id with gen_random_uuid()
            insert_sql = """
                INSERT INTO technique_library (
                    id, category, title, content, content_embedding, meta_data, created_at
                ) VALUES (
                    gen_random_uuid(), :category, :title, :content, CAST(:embedding AS vector),
                    CAST(:meta_data AS jsonb), CURRENT_TIMESTAMP
                ) RETURNING id
            """

            result = await session.execute(
                text(insert_sql),
                {
                    "category": params.category,
                    "title": params.title,
                    "content": params.content,
                    "embedding": str(content_embedding.tolist()),
                    "meta_data": json.dumps(params.metadata)
                    if params.metadata
                    else "{}",
                },
            )
            technique_id = result.scalar()
            await session.commit()

        return {
            "technique_id": str(technique_id),
            "category": params.category,
            "title": params.title,
            "status": "added",
            "message": f"Technique '{params.title}' added to library",
        }

    async def search_library(
        self,
        query: Annotated[
            str, Field(description="Search query for finding relevant techniques")
        ],
        category: Annotated[
            str | None,
            Field(
                description="Filter by category: auth, api_pattern, security_control, payload, recon, exploit"
            ),
        ] = None,
        limit: Annotated[int, Field(description="Maximum results")] = 10,
        similarity_threshold: Annotated[
            float, Field(description="Minimum similarity score (0.0 to 1.0)")
        ] = 0.5,
    ) -> dict[str, Any]:
        """Search the curated knowledge library using semantic search."""
        # Validate parameters
        if similarity_threshold < 0.0 or similarity_threshold > 1.0:
            raise ToolError(
                "search_library", "Similarity threshold must be between 0.0 and 1.0"
            )

        valid_categories = [
            "auth",
            "api_pattern",
            "security_control",
            "payload",
            "recon",
            "exploit",
        ]
        if category and category not in valid_categories:
            raise ToolError(
                "search_library",
                f"Invalid category. Must be one of: {', '.join(valid_categories)}",
            )

        # Generate embedding for query
        query_embedding = self._vector_search.embeddings.encode_text(query)

        async with await self._get_session() as session:
            # Search with vector similarity
            sql = """
                SELECT
                    id,
                    category,
                    title,
                    content,
                    meta_data,
                    created_at,
                    1 - (content_embedding <=> CAST(:embedding AS vector)) as similarity
                FROM technique_library
                WHERE content_embedding IS NOT NULL
            """

            params = {
                "embedding": str(query_embedding.tolist()),
                "max_distance": 1.0 - similarity_threshold,
                "limit": limit,
            }

            if category:
                sql += " AND category = :category"
                params["category"] = category

            sql += """
                AND (content_embedding <=> CAST(:embedding AS vector)) < :max_distance
                ORDER BY content_embedding <=> CAST(:embedding AS vector)
                LIMIT :limit
            """

            result = await session.execute(text(sql), params)
            rows = result.fetchall()

        # Format results
        techniques = []
        for row in rows:
            row_dict = dict(row._mapping)

            # Parse metadata
            metadata = {}
            if row_dict.get("meta_data"):
                try:
                    metadata = (
                        json.loads(row_dict["meta_data"])
                        if isinstance(row_dict["meta_data"], str)
                        else row_dict["meta_data"]
                    )
                except Exception:
                    metadata = {}

            techniques.append(
                {
                    "id": str(row_dict["id"]),
                    "category": row_dict["category"],
                    "title": row_dict["title"],
                    "content": row_dict["content"],
                    "similarity": round(row_dict["similarity"], 3),
                    "metadata": metadata,
                    "created_at": row_dict["created_at"].isoformat()
                    if row_dict["created_at"]
                    else None,
                }
            )

        return {
            "query": query,
            "techniques": techniques,
            "total_found": len(techniques),
            "filters": {
                "category": category,
                "similarity_threshold": similarity_threshold,
            },
        }

    async def get_library_stats(self) -> dict[str, Any]:
        """Get statistics about the knowledge library."""
        async with await self._get_session() as session:
            # Count by category
            category_sql = """
                SELECT
                    category,
                    COUNT(*) as count
                FROM technique_library
                GROUP BY category
                ORDER BY count DESC
            """

            category_result = await session.execute(text(category_sql))
            categories = category_result.fetchall()

            # Get total count
            total_sql = "SELECT COUNT(*) as total FROM technique_library"
            total_result = await session.execute(text(total_sql))
            total = total_result.scalar()

            # Get recent additions
            recent_sql = """
                SELECT title, category, created_at
                FROM technique_library
                ORDER BY created_at DESC
                LIMIT 5
            """
            recent_result = await session.execute(text(recent_sql))
            recent = recent_result.fetchall()

        return {
            "total_techniques": total,
            "by_category": [
                {"category": cat.category, "count": cat.count} for cat in categories
            ],
            "recent_additions": [
                {
                    "title": r.title,
                    "category": r.category,
                    "added": r.created_at.isoformat() if r.created_at else None,
                }
                for r in recent
            ],
        }
