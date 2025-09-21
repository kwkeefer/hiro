"""AI logging tools for target management and reconnaissance tracking."""

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, ClassVar, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from hiro.core.mcp.exceptions import ToolError
from hiro.db.models import ContextChangeType, RiskLevel, TargetStatus
from hiro.db.repositories import TargetContextRepository, TargetRepository
from hiro.db.schemas import TargetCreate, TargetSearchParams, TargetUpdate

logger = logging.getLogger(__name__)


class CreateTargetParams(BaseModel):
    """Parameters for creating a target."""

    # Define field descriptions as class variables for reuse
    HOST_DESC: ClassVar[str] = "Target hostname or IP address"
    PORT_DESC: ClassVar[str] = (
        "Target port number (optional, defaults to protocol standard)"
    )
    PROTOCOL_DESC: ClassVar[str] = "Network protocol (http, https, tcp, udp)"
    TITLE_DESC: ClassVar[str] = "Descriptive title or service name"
    STATUS_DESC: ClassVar[str] = "Target status (active, inactive, blocked, completed)"
    RISK_LEVEL_DESC: ClassVar[str] = (
        "Risk assessment level (low, medium, high, critical)"
    )
    host: str = Field(description=HOST_DESC)
    port: int | None = Field(None, description=PORT_DESC, ge=1, le=65535)
    protocol: Literal["http", "https", "tcp", "udp"] = Field(
        "http", description=PROTOCOL_DESC
    )
    title: str | None = Field(None, description=TITLE_DESC)
    status: Literal["active", "inactive", "blocked", "completed"] = Field(
        "active", description=STATUS_DESC
    )
    risk_level: Literal["low", "medium", "high", "critical"] = Field(
        "medium", description=RISK_LEVEL_DESC
    )


class CreateTargetTool:
    """Tool for manually registering new targets."""

    def __init__(self, target_repo: TargetRepository | Any | None = None):
        """Initialize create target tool.

        Args:
            target_repo: Repository for managing targets
        """
        self._target_repo = target_repo

    async def execute(
        self,
        host: Annotated[str, Field(description=CreateTargetParams.HOST_DESC)],
        port: Annotated[
            int | None, Field(description=CreateTargetParams.PORT_DESC, ge=1, le=65535)
        ] = None,
        protocol: Annotated[
            Literal["http", "https", "tcp", "udp"],
            Field(description=CreateTargetParams.PROTOCOL_DESC),
        ] = "http",
        title: Annotated[
            str | None, Field(description=CreateTargetParams.TITLE_DESC)
        ] = None,
        status: Annotated[
            Literal["active", "inactive", "blocked", "completed"],
            Field(description=CreateTargetParams.STATUS_DESC),
        ] = "active",
        risk_level: Annotated[
            Literal["low", "medium", "high", "critical"],
            Field(description=CreateTargetParams.RISK_LEVEL_DESC),
        ] = "medium",
    ) -> dict[str, Any]:
        """Register a new target for testing.

        Args:
            host: Target hostname or IP address
            port: Target port number (optional, defaults to protocol standard)
            protocol: Network protocol (http, https, tcp, udp)
            title: Descriptive title or service name
            status: Target status (active, inactive, blocked, completed)
            risk_level: Risk assessment level (low, medium, high, critical)

        Returns:
            Target information including ID, status, and creation details

        Raises:
            ToolError: If target creation fails or target already exists
        """
        # Create and validate parameters using Pydantic model
        try:
            params = CreateTargetParams(
                host=host,
                port=port,
                protocol=protocol,
                title=title,
                status=status,
                risk_level=risk_level,
            )
        except Exception as e:
            raise ToolError("create_target", f"Invalid parameters: {str(e)}") from e

        if not self._target_repo:
            raise ToolError(
                "create_target", "Database not configured for target management"
            )

        try:
            # Check if target already exists
            existing = await self._target_repo.get_by_endpoint(
                params.host, params.port, params.protocol
            )
            if existing:
                return {
                    "status": "exists",
                    "target_id": str(existing.id),
                    "message": f"Target already exists: {params.host}:{params.port or 'default'}/{params.protocol}",
                    "host": existing.host,
                    "port": existing.port,
                    "protocol": existing.protocol,
                    "current_status": existing.status,
                    "risk_level": existing.risk_level,
                    "last_activity": existing.last_activity.isoformat(),
                }

            # Prepare extra data
            extra_data: dict[str, Any] = {}

            # Create new target
            target_data = TargetCreate(
                host=params.host,
                port=params.port,
                protocol=params.protocol,
                title=params.title
                or f"{params.host}:{params.port or 'default'}/{params.protocol}",
                status=TargetStatus(params.status),
                risk_level=RiskLevel(params.risk_level),
                extra_data=extra_data,
            )

            target = await self._target_repo.create(target_data)

            return {
                "status": "created",
                "target_id": str(target.id),
                "message": f"Successfully created target: {target.title}",
                "host": target.host,
                "port": target.port,
                "protocol": target.protocol,
                "target_status": target.status,
                "risk_level": target.risk_level,
                "discovery_date": target.discovery_date.isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to create target: {e}")
            raise ToolError(
                "create_target", f"Failed to create target: {str(e)}"
            ) from e


class UpdateTargetStatusParams(BaseModel):
    """Parameters for updating target status."""

    # Define field descriptions as class variables for reuse
    TARGET_ID_DESC: ClassVar[str] = "UUID of the target to update"
    STATUS_DESC: ClassVar[str] = "New target status (optional)"
    RISK_LEVEL_DESC: ClassVar[str] = "New risk assessment level (optional)"
    TITLE_DESC: ClassVar[str] = "New descriptive title (optional)"

    target_id: str = Field(description=TARGET_ID_DESC)
    status: Literal["active", "inactive", "blocked", "completed"] | None = Field(
        None, description=STATUS_DESC
    )
    risk_level: Literal["low", "medium", "high", "critical"] | None = Field(
        None, description=RISK_LEVEL_DESC
    )
    title: str | None = Field(None, description=TITLE_DESC)


class UpdateTargetStatusTool:
    """Tool for updating target status and metadata."""

    def __init__(self, target_repo: TargetRepository | Any | None = None):
        """Initialize update target tool.

        Args:
            target_repo: Repository for managing targets
        """
        self._target_repo = target_repo

    async def execute(
        self,
        target_id: Annotated[
            str, Field(description=UpdateTargetStatusParams.TARGET_ID_DESC)
        ],
        status: Annotated[
            Literal["active", "inactive", "blocked", "completed"] | None,
            Field(description=UpdateTargetStatusParams.STATUS_DESC),
        ] = None,
        risk_level: Annotated[
            Literal["low", "medium", "high", "critical"] | None,
            Field(description=UpdateTargetStatusParams.RISK_LEVEL_DESC),
        ] = None,
        title: Annotated[
            str | None, Field(description=UpdateTargetStatusParams.TITLE_DESC)
        ] = None,
    ) -> dict[str, Any]:
        """Update target status and metadata.

        Args:
            target_id: UUID of the target to update
            status: New target status (optional)
            risk_level: New risk assessment level (optional)
            title: New descriptive title (optional)

        Returns:
            Updated target information

        Raises:
            ToolError: If target not found or update fails
        """
        # Create and validate parameters using Pydantic model
        try:
            params = UpdateTargetStatusParams(
                target_id=target_id,
                status=status,
                risk_level=risk_level,
                title=title,
            )
        except Exception as e:
            raise ToolError(
                "update_target_status", f"Invalid parameters: {str(e)}"
            ) from e

        if not self._target_repo:
            raise ToolError(
                "update_target_status", "Database not configured for target management"
            )

        try:
            # Validate target ID
            try:
                target_uuid = UUID(params.target_id)
            except ValueError as e:
                raise ToolError(
                    "update_target_status",
                    f"Invalid target ID format: {params.target_id}",
                ) from e

            # Check if target exists
            target = await self._target_repo.get_by_id(target_uuid)
            if not target:
                raise ToolError(
                    "update_target_status", f"Target not found: {params.target_id}"
                )

            # Prepare update data
            update_data = TargetUpdate()
            if params.status:
                update_data.status = TargetStatus(params.status)
            if params.risk_level:
                update_data.risk_level = RiskLevel(params.risk_level)
            if params.title:
                update_data.title = params.title

            # Update target
            updated_target = await self._target_repo.update(target_uuid, update_data)

            if not updated_target:
                raise ToolError("update_target_status", "Failed to update target")

            return {
                "status": "updated",
                "target_id": str(updated_target.id),
                "message": f"Successfully updated target: {updated_target.title}",
                "host": updated_target.host,
                "port": updated_target.port,
                "protocol": updated_target.protocol,
                "current_status": updated_target.status,
                "risk_level": updated_target.risk_level,
                "last_activity": updated_target.last_activity.isoformat(),
                "updated_at": updated_target.updated_at.isoformat(),
            }

        except ToolError:
            raise
        except Exception as e:
            logger.error(f"Failed to update target: {e}")
            raise ToolError(
                "update_target_status", f"Failed to update target: {str(e)}"
            ) from e


class GetTargetSummaryParams(BaseModel):
    """Parameters for getting target summary."""

    # Define field descriptions as class variables for reuse
    TARGET_ID_DESC: ClassVar[str] = "UUID of the target to retrieve"

    target_id: str = Field(description=TARGET_ID_DESC)


class GetTargetSummaryTool:
    """Tool for retrieving comprehensive target information."""

    def __init__(self, target_repo: TargetRepository | Any | None = None):
        """Initialize get target summary tool.

        Args:
            target_repo: Repository for managing targets
        """
        self._target_repo = target_repo

    async def execute(
        self,
        target_id: Annotated[
            str, Field(description=GetTargetSummaryParams.TARGET_ID_DESC)
        ],
    ) -> dict[str, Any]:
        """Get comprehensive target summary with related data counts.

        Args:
            target_id: UUID of the target to retrieve

        Returns:
            Target information including statistics on notes, attempts, and requests

        Raises:
            ToolError: If target not found or query fails
        """
        # Create and validate parameters using Pydantic model
        try:
            params = GetTargetSummaryParams(target_id=target_id)
        except Exception as e:
            raise ToolError(
                "get_target_summary", f"Invalid parameters: {str(e)}"
            ) from e

        if not self._target_repo:
            raise ToolError(
                "get_target_summary", "Database not configured for target management"
            )

        try:
            # Validate target ID
            try:
                target_uuid = UUID(params.target_id)
            except ValueError as e:
                raise ToolError(
                    "get_target_summary",
                    f"Invalid target ID format: {params.target_id}",
                ) from e

            # Get target summary
            summary = await self._target_repo.get_summary(target_uuid)

            if not summary:
                raise ToolError(
                    "get_target_summary", f"Target not found: {params.target_id}"
                )

            # Format response
            response = {
                "target_id": str(summary.target.id),
                "title": summary.target.title,
                "host": summary.target.host,
                "port": summary.target.port,
                "protocol": summary.target.protocol,
                "status": summary.target.status,
                "risk_level": summary.target.risk_level,
                "discovery_date": summary.target.discovery_date.isoformat(),
                "last_activity": summary.target.last_activity.isoformat(),
                "statistics": {
                    "notes_count": summary.notes_count,
                    "attempts_count": summary.attempts_count,
                    "requests_count": summary.requests_count,
                    "success_rate": f"{summary.success_rate * 100:.1f}%"
                    if summary.success_rate is not None
                    else "N/A",
                },
                "extra_data": summary.target.extra_data,
            }

            # Add activity status
            # Handle both timezone-aware and naive datetimes
            now = datetime.now(UTC)
            last_activity = summary.target.last_activity
            if last_activity.tzinfo is None:
                # If naive, assume it's UTC
                last_activity = last_activity.replace(tzinfo=UTC)
            time_since_activity = now - last_activity
            if time_since_activity < timedelta(hours=1):
                response["activity_status"] = "active_now"
            elif time_since_activity < timedelta(days=1):
                response["activity_status"] = "active_today"
            elif time_since_activity < timedelta(days=7):
                response["activity_status"] = "active_this_week"
            else:
                response["activity_status"] = "inactive"

            return response

        except ToolError:
            raise
        except Exception as e:
            logger.error(f"Failed to get target summary: {e}")
            raise ToolError(
                "get_target_summary", f"Failed to get target summary: {str(e)}"
            ) from e


class SearchTargetsParams(BaseModel):
    """Parameters for searching targets."""

    # Define field descriptions as class variables for reuse
    QUERY_DESC: ClassVar[str] = "Text search in host and title fields"
    STATUS_DESC: ClassVar[str] = (
        'Filter by target status as JSON array, e.g. ["active", "inactive"]'
    )
    RISK_LEVEL_DESC: ClassVar[str] = (
        'Filter by risk level as JSON array, e.g. ["high", "critical"]'
    )
    PROTOCOL_DESC: ClassVar[str] = (
        'Filter by protocol as JSON array, e.g. ["http", "https"]'
    )
    LIMIT_DESC: ClassVar[str] = "Maximum number of results (default 50, max 100)"
    OFFSET_DESC: ClassVar[str] = "Results offset for pagination"

    query: str | None = Field(None, description=QUERY_DESC)
    status: str | None = Field(None, description=STATUS_DESC)
    risk_level: str | None = Field(None, description=RISK_LEVEL_DESC)
    protocol: str | None = Field(None, description=PROTOCOL_DESC)
    limit: int = Field(50, description=LIMIT_DESC, ge=1, le=100)
    offset: int = Field(0, description=OFFSET_DESC, ge=0)

    @field_validator("status", "risk_level", "protocol", mode="before")
    @classmethod
    def parse_json_arrays(cls, v: Any) -> str | None:
        """Validate JSON array strings."""
        if v is None:
            return None
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if not isinstance(parsed, list):
                    raise ValueError("Must be a JSON array")
                # Keep as string for now, will parse in execute method
                return v
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON: {e}") from e
        return v  # type: ignore[no-any-return]


class SearchTargetsTool:
    """Tool for searching and filtering targets."""

    def __init__(self, target_repo: TargetRepository | Any | None = None):
        """Initialize search targets tool.

        Args:
            target_repo: Repository for managing targets
        """
        self._target_repo = target_repo

    async def execute(
        self,
        query: Annotated[
            str | None, Field(description=SearchTargetsParams.QUERY_DESC)
        ] = None,
        status: Annotated[
            str | None, Field(description=SearchTargetsParams.STATUS_DESC)
        ] = None,
        risk_level: Annotated[
            str | None, Field(description=SearchTargetsParams.RISK_LEVEL_DESC)
        ] = None,
        protocol: Annotated[
            str | None, Field(description=SearchTargetsParams.PROTOCOL_DESC)
        ] = None,
        limit: Annotated[
            int, Field(description=SearchTargetsParams.LIMIT_DESC, ge=1, le=100)
        ] = 50,
        offset: Annotated[
            int, Field(description=SearchTargetsParams.OFFSET_DESC, ge=0)
        ] = 0,
    ) -> dict[str, Any]:
        """Search targets with various filters.

        Args:
            query: Text search in host and title fields
            status: Filter by target status as JSON array
            risk_level: Filter by risk level as JSON array
            protocol: Filter by protocol as JSON array
            limit: Maximum number of results (default 50, max 100)
            offset: Results offset for pagination

        Returns:
            List of matching targets with summary information

        Raises:
            ToolError: If search fails
        """
        # Create and validate parameters using Pydantic model
        try:
            params = SearchTargetsParams(
                query=query,
                status=status,
                risk_level=risk_level,
                protocol=protocol,
                limit=limit,
                offset=offset,
            )
        except Exception as e:
            raise ToolError("search_targets", f"Invalid parameters: {str(e)}") from e

        if not self._target_repo:
            raise ToolError(
                "search_targets", "Database not configured for target management"
            )

        try:
            # Validate and cap limit
            limit = min(params.limit, 100)

            # Parse JSON arrays and convert to enums
            status_enums = None
            if params.status:
                status_list = json.loads(params.status)
                status_enums = [TargetStatus(s) for s in status_list]

            risk_enums = None
            if params.risk_level:
                risk_list = json.loads(params.risk_level)
                risk_enums = [RiskLevel(r) for r in risk_list]

            protocol_list = None
            if params.protocol:
                protocol_list = json.loads(params.protocol)

            # Create search parameters
            search_params = TargetSearchParams(
                query=params.query,
                status=status_enums,
                risk_level=risk_enums,
                protocol=protocol_list,
                limit=limit,
                offset=params.offset,
            )

            # Search targets
            targets = await self._target_repo.search(search_params)

            # Format results
            results = []
            for target in targets:
                results.append(
                    {
                        "target_id": str(target.id),
                        "title": target.title,
                        "host": target.host,
                        "port": target.port,
                        "protocol": target.protocol,
                        "status": target.status,
                        "risk_level": target.risk_level,
                        "last_activity": target.last_activity.isoformat(),
                    }
                )

            return {
                "status": "success",
                "count": len(results),
                "limit": limit,
                "offset": offset,
                "targets": results,
                "message": f"Found {len(results)} target(s) matching criteria",
            }

        except Exception as e:
            logger.error(f"Failed to search targets: {e}")
            raise ToolError(
                "search_targets", f"Failed to search targets: {str(e)}"
            ) from e


class GetTargetContextTool:
    """Tool for retrieving target context."""

    def __init__(
        self,
        context_repo: TargetContextRepository | Any | None = None,
        target_repo: TargetRepository | Any | None = None,
    ):
        """Initialize get context tool.

        Args:
            context_repo: Repository for managing context versions
            target_repo: Repository for managing targets
        """
        self._context_repo = context_repo
        self._target_repo = target_repo

    async def execute(
        self,
        target_id: Annotated[str, Field(description="UUID of the target")],
        version_id: Annotated[
            str | None, Field(description="Specific version ID to retrieve (optional)")
        ] = None,
        include_history: Annotated[
            bool, Field(description="Include version history")
        ] = False,
    ) -> dict[str, Any]:
        """Get current or specific context version for a target.

        Args:
            target_id: UUID of the target
            version_id: Specific version ID to retrieve (optional)
            include_history: Include version history

        Returns:
            Current context and optionally version history

        Raises:
            ToolError: If retrieval fails or target doesn't exist
        """
        if not self._context_repo:
            raise ToolError(
                "get_target_context", "Database not configured for context management"
            )

        if not self._target_repo:
            raise ToolError(
                "get_target_context", "Database not configured for target management"
            )

        try:
            # Validate UUID format
            target_uuid = UUID(target_id)

            # Check target exists
            target = await self._target_repo.get_by_id(target_uuid)
            if not target:
                raise ToolError("get_target_context", f"Target not found: {target_id}")

            # Get specific version or current
            if version_id:
                context_uuid = UUID(version_id)
                context = await self._context_repo.get_version(context_uuid)
                if not context:
                    raise ToolError(
                        "get_target_context", f"Context version not found: {version_id}"
                    )
            else:
                context = await self._context_repo.get_current(target_uuid)
                if not context:
                    return {
                        "status": "no_context",
                        "target_id": target_id,
                        "message": f"No context found for target {target.host}",
                    }

            result = {
                "status": "success",
                "target_id": str(context.target_id),
                "context_id": str(context.id),
                "version": context.version,
                "user_context": context.user_context,
                "agent_context": context.agent_context,
                "created_at": context.created_at.isoformat(),
                "created_by": context.created_by,
                "change_type": context.change_type,
                "change_summary": context.change_summary,
                "is_major_version": context.is_major_version,
                "tokens_count": context.tokens_count,
            }

            # Optionally include history
            if include_history:
                history = await self._context_repo.list_versions(target_uuid, limit=10)
                result["history"] = [
                    {
                        "version": h.version,
                        "context_id": str(h.id),
                        "created_at": h.created_at.isoformat(),
                        "created_by": h.created_by,
                        "change_type": h.change_type,
                        "change_summary": h.change_summary,
                        "is_major_version": h.is_major_version,
                    }
                    for h in history
                ]

            return result

        except ToolError:
            raise
        except Exception as e:
            logger.error(f"Failed to get target context: {e}")
            raise ToolError(
                "get_target_context", f"Failed to get context: {str(e)}"
            ) from e


class UpdateTargetContextParams(BaseModel):
    """Parameters for updating target context."""

    target_id: str = Field(description="UUID of the target")
    user_context: str | None = Field(
        None, description="Updated user context (replaces existing)"
    )
    agent_context: str | None = Field(
        None, description="Updated agent context (replaces existing)"
    )
    append_mode: bool = Field(
        False,
        description="Append to existing context instead of replacing (accepts true/false or 'true'/'false')",
    )
    change_summary: str | None = Field(None, description="Summary of what changed")
    is_major_version: bool = Field(
        False,
        description="Whether this is a major version (accepts true/false or 'true'/'false')",
    )

    @field_validator("append_mode", "is_major_version", mode="before")
    @classmethod
    def coerce_boolean(cls, v: Any) -> bool:
        """Convert string boolean values to actual booleans."""
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "on")
        return bool(v) if v is not None else False


class UpdateTargetContextTool:
    """Tool for updating target context (creates new version)."""

    def __init__(
        self,
        context_repo: TargetContextRepository | Any | None = None,
        target_repo: TargetRepository | Any | None = None,
    ):
        """Initialize update context tool.

        Args:
            context_repo: Repository for managing context versions
            target_repo: Repository for managing targets
        """
        self._context_repo = context_repo
        self._target_repo = target_repo

    async def execute(
        self,
        target_id: Annotated[str, Field(description="UUID of the target")],
        user_context: Annotated[
            str | None, Field(description="Updated user context (replaces existing)")
        ] = None,
        agent_context: Annotated[
            str | None, Field(description="Updated agent context (replaces existing)")
        ] = None,
        append_mode: Annotated[
            bool | str,
            Field(
                description="Append to existing context instead of replacing (accepts true/false or 'true'/'false')"
            ),
        ] = False,
        change_summary: Annotated[
            str | None, Field(description="Summary of what changed")
        ] = None,
        is_major_version: Annotated[
            bool | str,
            Field(
                description="Whether this is a major version (accepts true/false or 'true'/'false')"
            ),
        ] = False,
    ) -> dict[str, Any]:
        """Update target context (creates new immutable version).

        Args:
            target_id: UUID of the target
            user_context: Updated user context (replaces existing unless append_mode)
            agent_context: Updated agent context (replaces existing unless append_mode)
            append_mode: Append to existing context instead of replacing
            change_summary: Summary of what changed
            is_major_version: Whether this is a major version

        Returns:
            New context version information

        Raises:
            ToolError: If update fails or target doesn't exist
        """
        if not self._context_repo:
            raise ToolError(
                "update_target_context",
                "Database not configured for context management",
            )

        if not self._target_repo:
            raise ToolError(
                "update_target_context", "Database not configured for target management"
            )

        # Create and validate parameters using Pydantic model (handles boolean coercion)
        try:
            # Pydantic will handle string->bool conversion via our validator
            params = UpdateTargetContextParams(
                target_id=target_id,
                user_context=user_context,
                agent_context=agent_context,
                append_mode=append_mode,  # type: ignore[arg-type]
                change_summary=change_summary,
                is_major_version=is_major_version,  # type: ignore[arg-type]
            )
        except Exception as e:
            raise ToolError(
                "update_target_context", f"Invalid parameters: {str(e)}"
            ) from e

        try:
            # Validate UUID format
            target_uuid = UUID(params.target_id)

            # Check target exists
            target = await self._target_repo.get_by_id(target_uuid)
            if not target:
                raise ToolError(
                    "update_target_context", f"Target not found: {params.target_id}"
                )

            # Get current context to potentially append to
            current = await self._context_repo.get_current(target_uuid)

            # Prepare new context values
            new_user_context = params.user_context
            new_agent_context = params.agent_context

            if params.append_mode and current:
                # Append to existing context
                if params.user_context:
                    existing_user = current.user_context or ""
                    new_user_context = (
                        f"{existing_user}\n\n{params.user_context}".strip()
                    )
                else:
                    new_user_context = current.user_context

                if params.agent_context:
                    existing_agent = current.agent_context or ""
                    new_agent_context = (
                        f"{existing_agent}\n\n{params.agent_context}".strip()
                    )
                else:
                    new_agent_context = current.agent_context
            elif not params.append_mode and current:
                # Replace mode but keep unchanged fields
                if params.user_context is None:
                    new_user_context = current.user_context
                if params.agent_context is None:
                    new_agent_context = current.agent_context

            # Determine change type
            if new_user_context and new_agent_context:
                created_by = "both"
                change_type = ContextChangeType.USER_EDIT  # Use USER_EDIT for combined
            elif new_agent_context:
                created_by = "agent"
                change_type = ContextChangeType.AGENT_UPDATE
            else:
                created_by = "user"
                change_type = ContextChangeType.USER_EDIT

            # Create new version
            context = await self._context_repo.create_version(
                target_id=target_uuid,
                user_context=new_user_context,
                agent_context=new_agent_context,
                created_by=created_by,
                change_summary=params.change_summary
                or ("Appended context" if params.append_mode else "Updated context"),
                change_type=change_type,
                parent_version_id=current.id if current else None,
                is_major_version=params.is_major_version,
            )

            return {
                "status": "success",
                "context_id": str(context.id),
                "version": context.version,
                "previous_version": current.version if current else None,
                "target_id": str(context.target_id),
                "created_at": context.created_at.isoformat(),
                "append_mode": params.append_mode,
                "message": f"Updated context to version {context.version} for target {target.host}",
            }

        except ToolError:
            raise
        except Exception as e:
            logger.error(f"Failed to update target context: {e}")
            raise ToolError(
                "update_target_context", f"Failed to update context: {str(e)}"
            ) from e
