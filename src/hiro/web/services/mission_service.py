"""Mission service for web interface."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Integer, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from hiro.db.models import (
    HttpRequest,
    Mission,
    MissionAction,
    MissionTarget,
    Target,
)
from hiro.db.repositories import (
    HttpRequestRepository,
    MissionActionRepository,
    MissionRepository,
)
from hiro.db.schemas import MissionActionCreate, MissionCreate


class MissionService:
    """Service for mission operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.mission_repo = MissionRepository(db)
        self.action_repo = MissionActionRepository(db)
        self.request_repo = HttpRequestRepository(db)

    async def list_missions(
        self,
        mission_type: str | None = None,
        search: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """List missions with filters."""
        query = select(Mission).options(selectinload(Mission.targets))

        if mission_type:
            query = query.where(Mission.mission_type == mission_type)

        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                Mission.name.ilike(search_pattern)
                | Mission.goal.ilike(search_pattern)
                | Mission.hypothesis.ilike(search_pattern)
            )

        query = query.order_by(Mission.created_at.desc()).limit(limit)

        result = await self.db.execute(query)
        missions = result.scalars().all()

        # Convert to dict with additional stats
        mission_list = []
        for mission in missions:
            # Count actions and requests
            action_count = await self.db.scalar(
                select(func.count(MissionAction.id)).where(
                    MissionAction.mission_id == mission.id
                )
            )

            request_count = await self.db.scalar(
                select(func.count(HttpRequest.id)).where(
                    HttpRequest.mission_id == mission.id
                )
            )

            mission_dict = {
                "id": mission.id,
                "name": mission.name,
                "type": mission.mission_type,
                "goal": mission.goal,
                "hypothesis": mission.hypothesis,
                "created_at": mission.created_at,
                "completed_at": mission.completed_at,
                "action_count": action_count or 0,
                "request_count": request_count or 0,
                "targets": [t.host for t in mission.targets]
                if hasattr(mission, "targets")
                else [],
                "status": "completed" if mission.completed_at else "active",
            }
            mission_list.append(mission_dict)

        return mission_list

    async def create_mission(self, mission_data: MissionCreate) -> Mission:
        """Create a new mission."""
        mission = await self.mission_repo.create(mission_data)

        # Associate with target
        if mission_data.target_id:
            await self.mission_repo.associate_target(mission.id, mission_data.target_id)

        return mission

    async def get_mission_detail(self, mission_id: UUID) -> dict:
        """Get detailed mission information."""
        mission = await self.mission_repo.get(mission_id)
        if not mission:
            raise ValueError(f"Mission {mission_id} not found")

        # Get summary statistics
        summary = await self.mission_repo.get_summary(mission_id)

        # Get target details
        result = await self.db.execute(
            select(Target)
            .join(MissionTarget)
            .where(MissionTarget.mission_id == mission_id)
        )
        targets = result.scalars().all()

        return {
            "mission": mission,
            "summary": summary,
            "targets": targets,
        }

    async def get_mission_actions(
        self,
        mission_id: UUID,
        limit: int = 50,
    ) -> list[MissionAction]:
        """Get actions for a mission."""
        return await self.action_repo.get_by_mission(mission_id, limit)

    async def get_mission_requests(
        self,
        mission_id: UUID,
        limit: int = 100,
    ) -> list[HttpRequest]:
        """Get HTTP requests for a mission."""
        result = await self.db.execute(
            select(HttpRequest)
            .where(HttpRequest.mission_id == mission_id)
            .order_by(HttpRequest.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_success_patterns(
        self,
        mission_id: UUID,
    ) -> list[dict]:
        """Get success patterns for a mission."""
        # Get successful actions grouped by technique
        result = await self.db.execute(
            select(
                MissionAction.technique,
                func.count(MissionAction.id).label("count"),
                func.sum(MissionAction.success.cast(Integer)).label("success_count"),
            )
            .where(MissionAction.mission_id == mission_id)
            .group_by(MissionAction.technique)
            .order_by(func.count(MissionAction.id).desc())
        )

        patterns = []
        for row in result:
            count = row[1]  # Access by index since 'count' is a built-in
            success_count = row.success_count
            success_rate = success_count / count if count > 0 else 0
            patterns.append(
                {
                    "technique": row.technique,
                    "usage_count": count,
                    "success_count": row.success_count or 0,
                    "success_rate": round(success_rate, 2),
                }
            )

        return patterns

    async def record_action(
        self,
        action_data: MissionActionCreate,
        link_requests: int = 5,
    ) -> MissionAction:
        """Record a new action."""
        action = await self.action_repo.create(action_data)

        # Link recent requests if specified
        if link_requests > 0:
            await self.action_repo.link_recent_requests(
                action.id,
                action_data.mission_id,
                link_requests,
            )

        return action

    async def complete_mission(self, mission_id: UUID) -> Mission:
        """Mark mission as completed."""
        await self.db.execute(
            select(Mission).where(Mission.id == mission_id).with_for_update()
        )

        from hiro.db.schemas import MissionUpdate

        update_data = MissionUpdate(completed_at=datetime.now(UTC))

        mission = await self.mission_repo.update(mission_id, update_data)
        if not mission:
            raise ValueError(f"Mission {mission_id} not found")

        return mission

    async def delete_mission(self, mission_id: UUID) -> None:
        """Delete a mission (cascade deletes actions and associations)."""
        mission = await self.mission_repo.get(mission_id)
        if not mission:
            raise ValueError(f"Mission {mission_id} not found")

        # Delete is handled by cascade in database
        await self.db.delete(mission)
        await self.db.flush()
