"""AI logging tools for target management and reconnaissance tracking."""

import logging
from datetime import datetime, timedelta
from typing import Any, Literal
from uuid import UUID

from code_mcp.core.mcp.exceptions import ToolError
from code_mcp.db.models import RiskLevel, TargetStatus
from code_mcp.db.repositories import TargetRepository
from code_mcp.db.schemas import TargetCreate, TargetSearchParams, TargetUpdate

logger = logging.getLogger(__name__)


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
        host: str,
        port: int | None = None,
        protocol: Literal["http", "https", "tcp", "udp"] = "http",
        title: str | None = None,
        status: Literal["active", "inactive", "blocked", "completed"] = "active",
        risk_level: Literal["low", "medium", "high", "critical"] = "medium",
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Register a new target for testing.

        Args:
            host: Target hostname or IP address
            port: Target port number (optional, defaults to protocol standard)
            protocol: Network protocol (http, https, tcp, udp)
            title: Descriptive title or service name
            status: Target status (active, inactive, blocked, completed)
            risk_level: Risk assessment level (low, medium, high, critical)
            notes: Additional notes or metadata about the target

        Returns:
            Target information including ID, status, and creation details

        Raises:
            ToolError: If target creation fails or target already exists
        """
        if not self._target_repo:
            raise ToolError(
                "create_target", "Database not configured for target management"
            )

        try:
            # Check if target already exists
            existing = await self._target_repo.get_by_endpoint(host, port, protocol)
            if existing:
                return {
                    "status": "exists",
                    "target_id": str(existing.id),
                    "message": f"Target already exists: {host}:{port or 'default'}/{protocol}",
                    "host": existing.host,
                    "port": existing.port,
                    "protocol": existing.protocol,
                    "current_status": existing.status,
                    "risk_level": existing.risk_level,
                    "last_activity": existing.last_activity.isoformat(),
                }

            # Prepare extra data
            extra_data = {}
            if notes:
                extra_data["initial_notes"] = notes

            # Create new target
            target_data = TargetCreate(
                host=host,
                port=port,
                protocol=protocol,
                title=title or f"{host}:{port or 'default'}/{protocol}",
                status=TargetStatus(status),
                risk_level=RiskLevel(risk_level),
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
        target_id: str,
        status: Literal["active", "inactive", "blocked", "completed"] | None = None,
        risk_level: Literal["low", "medium", "high", "critical"] | None = None,
        title: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Update target status and metadata.

        Args:
            target_id: UUID of the target to update
            status: New target status (optional)
            risk_level: New risk assessment level (optional)
            title: New descriptive title (optional)
            notes: Additional notes to append to metadata (optional)

        Returns:
            Updated target information

        Raises:
            ToolError: If target not found or update fails
        """
        if not self._target_repo:
            raise ToolError(
                "update_target_status", "Database not configured for target management"
            )

        try:
            # Validate target ID
            try:
                target_uuid = UUID(target_id)
            except ValueError as e:
                raise ToolError(
                    "update_target_status", f"Invalid target ID format: {target_id}"
                ) from e

            # Check if target exists
            target = await self._target_repo.get_by_id(target_uuid)
            if not target:
                raise ToolError(
                    "update_target_status", f"Target not found: {target_id}"
                )

            # Prepare update data
            update_data = TargetUpdate()
            if status:
                update_data.status = TargetStatus(status)
            if risk_level:
                update_data.risk_level = RiskLevel(risk_level)
            if title:
                update_data.title = title

            # Handle notes - append to extra_data
            if notes:
                extra_data = target.extra_data.copy()
                if "notes" not in extra_data:
                    extra_data["notes"] = []
                extra_data["notes"].append(
                    {
                        "timestamp": datetime.utcnow().isoformat(),
                        "content": notes,
                    }
                )
                update_data.extra_data = extra_data

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


class GetTargetSummaryTool:
    """Tool for retrieving comprehensive target information."""

    def __init__(self, target_repo: TargetRepository | Any | None = None):
        """Initialize get target summary tool.

        Args:
            target_repo: Repository for managing targets
        """
        self._target_repo = target_repo

    async def execute(self, target_id: str) -> dict[str, Any]:
        """Get comprehensive target summary with related data counts.

        Args:
            target_id: UUID of the target to retrieve

        Returns:
            Target information including statistics on notes, attempts, and requests

        Raises:
            ToolError: If target not found or query fails
        """
        if not self._target_repo:
            raise ToolError(
                "get_target_summary", "Database not configured for target management"
            )

        try:
            # Validate target ID
            try:
                target_uuid = UUID(target_id)
            except ValueError as e:
                raise ToolError(
                    "get_target_summary", f"Invalid target ID format: {target_id}"
                ) from e

            # Get target summary
            summary = await self._target_repo.get_summary(target_uuid)

            if not summary:
                raise ToolError("get_target_summary", f"Target not found: {target_id}")

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
            time_since_activity = datetime.utcnow() - summary.target.last_activity
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
        query: str | None = None,
        status: list[Literal["active", "inactive", "blocked", "completed"]]
        | None = None,
        risk_level: list[Literal["low", "medium", "high", "critical"]] | None = None,
        protocol: list[str] | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Search targets with various filters.

        Args:
            query: Text search in host and title fields
            status: Filter by target status (can specify multiple)
            risk_level: Filter by risk level (can specify multiple)
            protocol: Filter by protocol (can specify multiple)
            limit: Maximum number of results (default 50, max 100)
            offset: Results offset for pagination

        Returns:
            List of matching targets with summary information

        Raises:
            ToolError: If search fails
        """
        if not self._target_repo:
            raise ToolError(
                "search_targets", "Database not configured for target management"
            )

        try:
            # Validate and cap limit
            limit = min(limit, 100)

            # Convert status and risk level strings to enums
            status_enums = None
            if status:
                status_enums = [TargetStatus(s) for s in status]

            risk_enums = None
            if risk_level:
                risk_enums = [RiskLevel(r) for r in risk_level]

            # Create search parameters
            search_params = TargetSearchParams(
                query=query,
                status=status_enums,
                risk_level=risk_enums,
                protocol=protocol,
                limit=limit,
                offset=offset,
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
