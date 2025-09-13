"""Target service for web interface."""

from typing import Any
from uuid import UUID

from sqlalchemy import String, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from hiro.db.models import (
    ContextChangeType,
    HttpRequest,
    RiskLevel,
    Target,
    TargetContext,
    TargetStatus,
)


class TargetService:
    """Service for target operations."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session."""
        self.db = db

    async def list_targets(
        self,
        status: TargetStatus | None = None,
        risk: RiskLevel | None = None,
        search: str | None = None,
        limit: int = 100,
    ) -> list[Target]:
        """List targets with optional filters."""
        query = select(Target).options(
            selectinload(Target.notes),
            selectinload(Target.requests),
        )

        # Apply filters
        if status:
            query = query.where(Target.status == status)
        if risk:
            query = query.where(Target.risk_level == risk)
        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    Target.host.ilike(search_term),
                    Target.title.ilike(search_term),
                    func.cast(Target.id, String).ilike(search_term),
                )
            )

        # Order by last activity
        query = query.order_by(desc(Target.last_activity)).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_target(self, target_id: UUID) -> Target | None:
        """Get target by ID."""
        query = (
            select(Target)
            .where(Target.id == target_id)
            .options(
                selectinload(Target.notes),
                selectinload(Target.current_context),
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()  # type: ignore

    async def update_target(
        self, target_id: UUID, updates: dict[str, Any]
    ) -> Target | None:
        """Update target attributes."""
        target = await self.get_target(target_id)
        if not target:
            return None

        for key, value in updates.items():
            if hasattr(target, key):
                setattr(target, key, value)

        # Update last activity
        target.last_activity = func.now()

        await self.db.commit()
        await self.db.refresh(target)
        return target

    async def get_target_context(self, target_id: UUID) -> TargetContext | None:
        """Get current context for target."""
        query = (
            select(TargetContext)
            .join(Target, Target.current_context_id == TargetContext.id)
            .where(Target.id == target_id)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()  # type: ignore

    async def update_context(
        self,
        target_id: UUID,
        user_context: str | None = None,
        agent_context: str | None = None,
    ) -> TargetContext | None:
        """Update target context, creating a new version."""
        target = await self.get_target(target_id)
        if not target:
            return None

        # Get current context or create initial
        current_context = await self.get_target_context(target_id)

        # Determine version number
        if current_context:
            new_version = current_context.version + 1
            parent_id = current_context.id
        else:
            new_version = 1
            parent_id = None

        # Create new context version
        new_context = TargetContext(
            target_id=target_id,
            version=new_version,
            user_context=user_context
            or (current_context.user_context if current_context else None),
            agent_context=agent_context
            or (current_context.agent_context if current_context else None),
            parent_version_id=parent_id,
            change_type=ContextChangeType.USER_EDIT,
            change_summary="Updated via web interface",
            created_by="user",
        )

        self.db.add(new_context)
        await self.db.flush()

        # Update target's current context
        target.current_context_id = new_context.id
        target.last_activity = func.now()

        await self.db.commit()
        await self.db.refresh(new_context)
        return new_context

    async def get_target_requests(
        self, target_id: UUID, limit: int = 100
    ) -> list[HttpRequest]:
        """Get HTTP requests for a target."""
        # First get the target to find its host
        target = await self.get_target(target_id)
        if not target:
            return []

        # Query requests by host
        query = (
            select(HttpRequest)
            .where(HttpRequest.host == target.host)
            .order_by(desc(HttpRequest.created_at))
            .limit(limit)
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_context_history(self, target_id: UUID) -> list[TargetContext]:
        """Get all context versions for a target, ordered by version desc."""
        query = (
            select(TargetContext)
            .where(TargetContext.target_id == target_id)
            .order_by(desc(TargetContext.version))
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_context_by_version(
        self, target_id: UUID, version: int
    ) -> TargetContext | None:
        """Get a specific context version for a target."""
        query = (
            select(TargetContext)
            .where(TargetContext.target_id == target_id)
            .where(TargetContext.version == version)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()  # type: ignore
