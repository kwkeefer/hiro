"""Data access layer for database operations."""

from datetime import UTC, datetime, timedelta
from typing import cast
from urllib.parse import urlparse
from uuid import UUID

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio.session import async_sessionmaker

from .models import (
    AiSession,
    ContextChangeType,
    HttpRequest,
    RequestTag,
    RiskLevel,
    SessionTarget,
    Target,
    TargetAttempt,
    TargetContext,
    TargetNote,
    TargetRequest,
    TargetStatus,
)
from .schemas import (
    AiSessionCreate,
    AiSessionUpdate,
    AttemptSearchParams,
    HttpRequestCreate,
    HttpRequestUpdate,
    RequestSearchParams,
    RequestTagCreate,
    SessionSummary,
    TargetAttemptCreate,
    TargetAttemptUpdate,
    TargetCreate,
    TargetNoteCreate,
    TargetNoteUpdate,
    TargetSearchParams,
    TargetSummary,
    TargetUpdate,
)


class TargetRepository:
    """Repository for target operations."""

    def __init__(
        self, session_or_factory: async_sessionmaker[AsyncSession] | AsyncSession
    ):
        # Support both session factory and direct session for backward compatibility
        self._session = None
        self._session_factory = None

        if isinstance(session_or_factory, AsyncSession):
            self._session = session_or_factory
        else:
            self._session_factory = session_or_factory

    @property
    def session(self) -> AsyncSession:
        """Get the current session."""
        if self._session:
            return self._session
        raise RuntimeError(
            "No session available - use async context manager for session factory"
        )

    async def create(self, target_data: TargetCreate) -> Target:
        """Create a new target."""
        if self._session_factory:
            async with self._session_factory() as session:
                target = Target(**target_data.model_dump())
                session.add(target)
                await session.flush()
                await session.refresh(target)
                await session.commit()
                return target
        else:
            target = Target(**target_data.model_dump())
            self.session.add(target)
            await self.session.flush()
            await self.session.refresh(target)
            # Commit if we own the session
            await self.session.commit()
            return target

    async def get_by_id(self, target_id: UUID) -> Target | None:
        """Get target by ID."""
        if self._session_factory:
            async with self._session_factory() as session:
                result = await session.execute(
                    select(Target).where(Target.id == target_id)
                )
                return cast(Target | None, result.scalar_one_or_none())
        else:
            result = await self.session.execute(
                select(Target).where(Target.id == target_id)
            )
            return cast(Target | None, result.scalar_one_or_none())

    async def get_by_endpoint(
        self, host: str, port: int | None, protocol: str
    ) -> Target | None:
        """Get target by endpoint (host, port, protocol)."""
        if self._session_factory:
            async with self._session_factory() as session:
                result = await session.execute(
                    select(Target).where(
                        and_(
                            Target.host == host,
                            Target.port == port,
                            Target.protocol == protocol,
                        )
                    )
                )
                return cast(Target | None, result.scalar_one_or_none())
        else:
            result = await self.session.execute(
                select(Target).where(
                    and_(
                        Target.host == host,
                        Target.port == port,
                        Target.protocol == protocol,
                    )
                )
            )
            return cast(Target | None, result.scalar_one_or_none())

    async def get_or_create_from_url(self, url: str) -> Target:
        """Get or create target from URL."""
        parsed = urlparse(url)
        host = parsed.hostname or parsed.netloc
        port = parsed.port
        protocol = parsed.scheme or "http"

        # Try to get existing target
        target = await self.get_by_endpoint(host, port, protocol)

        if not target:
            # Create new target
            target_data = TargetCreate(
                title=f"{host}:{port or 'default'}/{protocol}",
                host=host,
                port=port,
                protocol=protocol,
                status=TargetStatus.ACTIVE,
                risk_level=RiskLevel.LOW,  # Default risk level
            )
            target = await self.create(target_data)

        # Update last activity
        if target:
            await self.update_last_activity(target.id)
        return target

    async def update(self, target_id: UUID, target_data: TargetUpdate) -> Target | None:
        """Update target."""
        update_data = target_data.model_dump(exclude_unset=True)
        if not update_data:
            return await self.get_by_id(target_id)

        update_data["updated_at"] = datetime.now(UTC)

        if self._session_factory:
            async with self._session_factory() as session:
                await session.execute(
                    update(Target).where(Target.id == target_id).values(**update_data)
                )
                await session.commit()
        else:
            await self.session.execute(
                update(Target).where(Target.id == target_id).values(**update_data)
            )
            await self.session.commit()

        return await self.get_by_id(target_id)

    async def update_last_activity(self, target_id: UUID) -> None:
        """Update target's last activity timestamp."""
        if self._session_factory:
            async with self._session_factory() as session:
                await session.execute(
                    update(Target)
                    .where(Target.id == target_id)
                    .values(last_activity=datetime.now(UTC))
                )
                await session.commit()
        else:
            await self.session.execute(
                update(Target)
                .where(Target.id == target_id)
                .values(last_activity=datetime.now(UTC))
            )
            await self.session.commit()

    async def search(self, params: TargetSearchParams) -> list[Target]:
        """Search targets with filters."""
        query = select(Target)

        # Text search
        if params.query:
            search_term = f"%{params.query}%"
            query = query.where(
                or_(Target.host.ilike(search_term), Target.title.ilike(search_term))
            )

        # Status filter
        if params.status:
            query = query.where(Target.status.in_(params.status))

        # Risk level filter
        if params.risk_level:
            query = query.where(Target.risk_level.in_(params.risk_level))

        # Protocol filter
        if params.protocol:
            query = query.where(Target.protocol.in_(params.protocol))

        # Pagination
        query = query.offset(params.offset).limit(params.limit)
        query = query.order_by(Target.last_activity.desc())

        if self._session_factory:
            async with self._session_factory() as session:
                result = await session.execute(query)
                return list(result.scalars().all())
        else:
            result = await self.session.execute(query)
            return list(result.scalars().all())

    async def get_summary(self, target_id: UUID) -> TargetSummary | None:
        """Get target summary with related data counts."""
        target = await self.get_by_id(target_id)
        if not target:
            return None

        if self._session_factory:
            async with self._session_factory() as session:
                # Count related records
                notes_count = await session.scalar(
                    select(func.count(TargetNote.id)).where(
                        TargetNote.target_id == target_id
                    )
                )

                attempts_count = await session.scalar(
                    select(func.count(TargetAttempt.id)).where(
                        TargetAttempt.target_id == target_id
                    )
                )

                requests_count = await session.scalar(
                    select(func.count(TargetRequest.request_id)).where(
                        TargetRequest.target_id == target_id
                    )
                )

                # Calculate success rate
                successful_attempts = await session.scalar(
                    select(func.count(TargetAttempt.id)).where(
                        and_(
                            TargetAttempt.target_id == target_id,
                            TargetAttempt.success.is_(True),
                        )
                    )
                )
        else:
            # Count related records
            notes_count = await self.session.scalar(
                select(func.count(TargetNote.id)).where(
                    TargetNote.target_id == target_id
                )
            )

            attempts_count = await self.session.scalar(
                select(func.count(TargetAttempt.id)).where(
                    TargetAttempt.target_id == target_id
                )
            )

            requests_count = await self.session.scalar(
                select(func.count(TargetRequest.request_id)).where(
                    TargetRequest.target_id == target_id
                )
            )

            # Calculate success rate
            successful_attempts = await self.session.scalar(
                select(func.count(TargetAttempt.id)).where(
                    and_(
                        TargetAttempt.target_id == target_id,
                        TargetAttempt.success.is_(True),
                    )
                )
            )

        success_rate = (
            (successful_attempts / attempts_count) if attempts_count > 0 else None
        )

        return TargetSummary(
            target=target,
            notes_count=notes_count or 0,
            attempts_count=attempts_count or 0,
            requests_count=requests_count or 0,
            success_rate=success_rate,
        )

    async def delete(self, target_id: UUID) -> bool:
        """Delete target and all related records."""
        if self._session_factory:
            async with self._session_factory() as session:
                result = await session.execute(
                    delete(Target).where(Target.id == target_id)
                )
                await session.commit()
                return bool(result.rowcount > 0)
        else:
            result = await self.session.execute(
                delete(Target).where(Target.id == target_id)
            )
            await self.session.commit()
            return bool(result.rowcount > 0)


class TargetNoteRepository:
    """Repository for target note operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, note_data: TargetNoteCreate) -> TargetNote:
        """Create a new target note."""
        note = TargetNote(**note_data.model_dump())
        self.session.add(note)
        await self.session.flush()
        await self.session.refresh(note)
        return note

    async def get_by_id(self, note_id: UUID) -> TargetNote | None:
        """Get note by ID."""
        result = await self.session.execute(
            select(TargetNote).where(TargetNote.id == note_id)
        )
        return cast(TargetNote | None, result.scalar_one_or_none())

    async def get_by_target(
        self, target_id: UUID, note_type: str | None = None
    ) -> list[TargetNote]:
        """Get notes for a target."""
        query = select(TargetNote).where(TargetNote.target_id == target_id)

        if note_type:
            query = query.where(TargetNote.note_type == note_type)

        query = query.order_by(TargetNote.created_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(
        self, note_id: UUID, note_data: TargetNoteUpdate
    ) -> TargetNote | None:
        """Update note."""
        update_data = note_data.model_dump(exclude_unset=True)
        if not update_data:
            return await self.get_by_id(note_id)

        update_data["updated_at"] = datetime.now(UTC)

        await self.session.execute(
            update(TargetNote).where(TargetNote.id == note_id).values(**update_data)
        )

        return await self.get_by_id(note_id)

    async def search(
        self, query_text: str, tags: list[str] | None = None
    ) -> list[TargetNote]:
        """Search notes by text and tags."""
        query = select(TargetNote)

        if query_text:
            search_term = f"%{query_text}%"
            query = query.where(
                or_(
                    TargetNote.title.ilike(search_term),
                    TargetNote.content.ilike(search_term),
                )
            )

        if tags:
            query = query.where(TargetNote.tags.overlap(tags))

        query = query.order_by(TargetNote.created_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def delete(self, note_id: UUID) -> bool:
        """Delete note."""
        result = await self.session.execute(
            delete(TargetNote).where(TargetNote.id == note_id)
        )
        return bool(result.rowcount > 0)


class TargetAttemptRepository:
    """Repository for target attempt operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, attempt_data: TargetAttemptCreate) -> TargetAttempt:
        """Create a new target attempt."""
        attempt = TargetAttempt(**attempt_data.model_dump())
        self.session.add(attempt)
        await self.session.flush()
        await self.session.refresh(attempt)
        return attempt

    async def get_by_id(self, attempt_id: UUID) -> TargetAttempt | None:
        """Get attempt by ID."""
        result = await self.session.execute(
            select(TargetAttempt).where(TargetAttempt.id == attempt_id)
        )
        return cast(TargetAttempt | None, result.scalar_one_or_none())

    async def update(
        self, attempt_id: UUID, attempt_data: TargetAttemptUpdate
    ) -> TargetAttempt | None:
        """Update attempt."""
        update_data = attempt_data.model_dump(exclude_unset=True)
        if not update_data:
            return await self.get_by_id(attempt_id)

        await self.session.execute(
            update(TargetAttempt)
            .where(TargetAttempt.id == attempt_id)
            .values(**update_data)
        )

        return await self.get_by_id(attempt_id)

    async def search(self, params: AttemptSearchParams) -> list[TargetAttempt]:
        """Search attempts with filters."""
        query = select(TargetAttempt)

        if params.target_id:
            query = query.where(TargetAttempt.target_id == params.target_id)

        if params.session_id:
            query = query.where(TargetAttempt.session_id == params.session_id)

        if params.attempt_type:
            query = query.where(TargetAttempt.attempt_type.in_(params.attempt_type))

        if params.technique:
            query = query.where(TargetAttempt.technique.ilike(f"%{params.technique}%"))

        if params.success is not None:
            query = query.where(TargetAttempt.success == params.success)

        if params.date_from:
            query = query.where(TargetAttempt.created_at >= params.date_from)

        if params.date_to:
            query = query.where(TargetAttempt.created_at <= params.date_to)

        query = query.order_by(TargetAttempt.created_at.desc())
        query = query.offset(params.offset).limit(params.limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())


class HttpRequestRepository:
    """Repository for HTTP request operations."""

    def __init__(
        self, session_or_factory: async_sessionmaker[AsyncSession] | AsyncSession
    ):
        # Support both session factory and direct session for backward compatibility
        self._session = None
        self._session_factory = None

        if isinstance(session_or_factory, AsyncSession):
            self._session = session_or_factory
        else:
            self._session_factory = session_or_factory

    @property
    def session(self) -> AsyncSession:
        """Get the current session."""
        if self._session:
            return self._session
        raise RuntimeError(
            "No session available - use async context manager for session factory"
        )

    async def create(self, request_data: HttpRequestCreate) -> HttpRequest:
        """Create a new HTTP request record."""
        if self._session_factory:
            async with self._session_factory() as session:
                request = HttpRequest(**request_data.model_dump())
                session.add(request)
                await session.flush()
                await session.refresh(request)
                await session.commit()
                return request
        else:
            request = HttpRequest(**request_data.model_dump())
            self.session.add(request)
            await self.session.flush()
            await self.session.refresh(request)
            await self.session.commit()
            return request

    async def get_by_id(self, request_id: UUID) -> HttpRequest | None:
        """Get request by ID."""
        if self._session_factory:
            async with self._session_factory() as session:
                result = await session.execute(
                    select(HttpRequest).where(HttpRequest.id == request_id)
                )
                return cast(HttpRequest | None, result.scalar_one_or_none())
        else:
            result = await self.session.execute(
                select(HttpRequest).where(HttpRequest.id == request_id)
            )
            return cast(HttpRequest | None, result.scalar_one_or_none())

    async def update(
        self, request_id: UUID, request_data: HttpRequestUpdate
    ) -> HttpRequest | None:
        """Update request with response data."""
        update_data = request_data.model_dump(exclude_unset=True)
        if not update_data:
            return await self.get_by_id(request_id)

        if self._session_factory:
            async with self._session_factory() as session:
                await session.execute(
                    update(HttpRequest)
                    .where(HttpRequest.id == request_id)
                    .values(**update_data)
                )
                await session.commit()
        else:
            await self.session.execute(
                update(HttpRequest)
                .where(HttpRequest.id == request_id)
                .values(**update_data)
            )
            await self.session.commit()

        return await self.get_by_id(request_id)

    async def link_to_target(self, request_id: UUID, target_id: UUID) -> None:
        """Link request to target."""
        if self._session_factory:
            async with self._session_factory() as session:
                # Check if link already exists
                existing = await session.execute(
                    select(TargetRequest).where(
                        and_(
                            TargetRequest.request_id == request_id,
                            TargetRequest.target_id == target_id,
                        )
                    )
                )

                if not existing.scalar_one_or_none():
                    link = TargetRequest(request_id=request_id, target_id=target_id)
                    session.add(link)
                    await session.commit()
        else:
            # Check if link already exists
            existing = await self.session.execute(
                select(TargetRequest).where(
                    and_(
                        TargetRequest.request_id == request_id,
                        TargetRequest.target_id == target_id,
                    )
                )
            )

            if not existing.scalar_one_or_none():
                link = TargetRequest(request_id=request_id, target_id=target_id)
                self.session.add(link)
                await self.session.commit()

    async def search(self, params: RequestSearchParams) -> list[HttpRequest]:
        """Search requests with filters."""
        query = select(HttpRequest)

        if params.query:
            search_term = f"%{params.query}%"
            query = query.where(
                or_(
                    HttpRequest.url.ilike(search_term),
                    HttpRequest.path.ilike(search_term),
                )
            )

        if params.host:
            query = query.where(HttpRequest.host.ilike(f"%{params.host}%"))

        if params.method:
            query = query.where(HttpRequest.method.in_(params.method))

        if params.status_code:
            query = query.where(HttpRequest.status_code.in_(params.status_code))

        if params.session_id:
            query = query.where(HttpRequest.session_id == params.session_id)

        if params.target_id:
            query = query.join(TargetRequest).where(
                TargetRequest.target_id == params.target_id
            )

        if params.date_from:
            query = query.where(HttpRequest.created_at >= params.date_from)

        if params.date_to:
            query = query.where(HttpRequest.created_at <= params.date_to)

        # Tag filtering
        if params.tags:
            query = query.join(RequestTag).where(RequestTag.tag.in_(params.tags))

        query = query.order_by(HttpRequest.created_at.desc())
        query = query.offset(params.offset).limit(params.limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def cleanup_old_requests(self, days: int) -> int:
        """Clean up requests older than specified days."""
        cutoff_date = datetime.now(UTC) - timedelta(days=days)

        result = await self.session.execute(
            delete(HttpRequest).where(HttpRequest.created_at < cutoff_date)
        )

        return int(result.rowcount or 0)


class AiSessionRepository:
    """Repository for AI session operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, session_data: AiSessionCreate) -> AiSession:
        """Create a new AI session."""
        ai_session = AiSession(**session_data.model_dump())
        self.session.add(ai_session)
        await self.session.flush()
        await self.session.refresh(ai_session)
        return ai_session

    async def get_by_id(self, session_id: UUID) -> AiSession | None:
        """Get session by ID."""
        result = await self.session.execute(
            select(AiSession).where(AiSession.id == session_id)
        )
        return cast(AiSession | None, result.scalar_one_or_none())

    async def update(
        self, session_id: UUID, session_data: AiSessionUpdate
    ) -> AiSession | None:
        """Update session."""
        update_data = session_data.model_dump(exclude_unset=True)
        if not update_data:
            return await self.get_by_id(session_id)

        await self.session.execute(
            update(AiSession).where(AiSession.id == session_id).values(**update_data)
        )

        return await self.get_by_id(session_id)

    async def associate_target(self, session_id: UUID, target_id: UUID) -> None:
        """Associate session with target."""
        # Check if association already exists
        existing = await self.session.execute(
            select(SessionTarget).where(
                and_(
                    SessionTarget.session_id == session_id,
                    SessionTarget.target_id == target_id,
                )
            )
        )

        if not existing.scalar_one_or_none():
            link = SessionTarget(session_id=session_id, target_id=target_id)
            self.session.add(link)

    async def get_summary(self, session_id: UUID) -> SessionSummary | None:
        """Get session summary with metrics."""
        session = await self.get_by_id(session_id)
        if not session:
            return None

        # Count related records
        targets_count = await self.session.scalar(
            select(func.count(SessionTarget.target_id)).where(
                SessionTarget.session_id == session_id
            )
        )

        requests_count = await self.session.scalar(
            select(func.count(HttpRequest.id)).where(
                HttpRequest.session_id == session_id
            )
        )

        attempts_count = await self.session.scalar(
            select(func.count(TargetAttempt.id)).where(
                TargetAttempt.session_id == session_id
            )
        )

        successful_attempts = await self.session.scalar(
            select(func.count(TargetAttempt.id)).where(
                and_(
                    TargetAttempt.session_id == session_id,
                    TargetAttempt.success.is_(True),
                )
            )
        )

        # Calculate duration
        duration_minutes = None
        if session.completed_at:
            duration = session.completed_at - session.created_at
            duration_minutes = duration.total_seconds() / 60

        return SessionSummary(
            session=session,
            targets_count=targets_count or 0,
            requests_count=requests_count or 0,
            attempts_count=attempts_count or 0,
            successful_attempts=successful_attempts or 0,
            duration_minutes=duration_minutes,
        )


class RequestTagRepository:
    """Repository for request tag operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, tag_data: RequestTagCreate) -> RequestTag:
        """Create a new request tag."""
        tag = RequestTag(**tag_data.model_dump())
        self.session.add(tag)
        await self.session.flush()
        await self.session.refresh(tag)
        return tag

    async def get_by_request(self, request_id: UUID) -> list[RequestTag]:
        """Get all tags for a request."""
        result = await self.session.execute(
            select(RequestTag).where(RequestTag.request_id == request_id)
        )
        return list(result.scalars().all())

    async def delete_by_request_and_tag(self, request_id: UUID, tag: str) -> bool:
        """Delete specific tag from request."""
        result = await self.session.execute(
            delete(RequestTag).where(
                and_(RequestTag.request_id == request_id, RequestTag.tag == tag)
            )
        )
        return bool(result.rowcount > 0)


class TargetContextRepository:
    """Repository for immutable target context versions."""

    def __init__(
        self, session_or_factory: async_sessionmaker[AsyncSession] | AsyncSession
    ):
        # Support both session factory and direct session for backward compatibility
        if isinstance(session_or_factory, async_sessionmaker):
            self.session_factory = session_or_factory
            self.session = None
        else:
            self.session = session_or_factory
            self.session_factory = None

    async def _get_session(self) -> AsyncSession:
        """Get a database session."""
        if self.session:
            return self.session
        if self.session_factory:
            return self.session_factory()
        raise RuntimeError("No session or session factory available")

    async def create_version(
        self,
        target_id: UUID,
        user_context: str | None = None,
        agent_context: str | None = None,
        created_by: str = "user",
        change_summary: str | None = None,
        change_type: ContextChangeType = ContextChangeType.USER_EDIT,
        parent_version_id: UUID | None = None,
        is_major_version: bool = False,
    ) -> TargetContext:
        """Create a new immutable context version for a target.

        Args:
            target_id: Target UUID
            user_context: User markdown context
            agent_context: Agent markdown context
            created_by: Who created this version ('user' or 'agent')
            change_summary: Description of what changed
            change_type: Type of change
            parent_version_id: Previous version ID (if not provided, uses current)
            is_major_version: Whether this is a major version

        Returns:
            New context version
        """
        session = await self._get_session()

        # Get the next version number
        result = await session.execute(
            select(func.coalesce(func.max(TargetContext.version), 0)).where(
                TargetContext.target_id == target_id
            )
        )
        next_version = result.scalar() + 1

        # If no parent specified, get the current version
        if parent_version_id is None:
            target_result = await session.execute(
                select(Target.current_context_id).where(Target.id == target_id)
            )
            current_id = target_result.scalar_one_or_none()
            if current_id:
                parent_version_id = current_id

        # Count tokens if content provided
        tokens_count = None
        if user_context or agent_context:
            # Simple approximation: ~4 chars per token
            total_text = (user_context or "") + (agent_context or "")
            tokens_count = len(total_text) // 4

        # Create new context version
        context = TargetContext(
            target_id=target_id,
            version=next_version,
            user_context=user_context,
            agent_context=agent_context,
            parent_version_id=parent_version_id,
            change_type=change_type,
            change_summary=change_summary,
            created_by=created_by,
            is_major_version=is_major_version,
            tokens_count=tokens_count,
        )

        session.add(context)
        await session.flush()

        # Update target's current_context_id
        await session.execute(
            update(Target)
            .where(Target.id == target_id)
            .values(current_context_id=context.id)
        )

        if not self.session:
            await session.commit()

        return context

    async def get_current(self, target_id: UUID) -> TargetContext | None:
        """Get the current context version for a target."""
        session = await self._get_session()

        # Get target's current context ID
        target_result = await session.execute(
            select(Target.current_context_id).where(Target.id == target_id)
        )
        current_id = target_result.scalar_one_or_none()

        if not current_id:
            return None

        # Get the context
        result = await session.execute(
            select(TargetContext).where(TargetContext.id == current_id)
        )
        return cast(TargetContext | None, result.scalar_one_or_none())

    async def get_version(self, context_id: UUID) -> TargetContext | None:
        """Get a specific context version by ID."""
        session = await self._get_session()
        result = await session.execute(
            select(TargetContext).where(TargetContext.id == context_id)
        )
        return cast(TargetContext | None, result.scalar_one_or_none())

    async def list_versions(
        self, target_id: UUID, limit: int = 10, offset: int = 0
    ) -> list[TargetContext]:
        """Get version history for a target."""
        session = await self._get_session()

        query = (
            select(TargetContext)
            .where(TargetContext.target_id == target_id)
            .order_by(TargetContext.version.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await session.execute(query)
        return list(result.scalars().all())

    async def search_contexts(
        self,
        query_text: str,
        target_ids: list[UUID] | None = None,
        limit: int = 50,
    ) -> list[tuple[TargetContext, Target]]:
        """Full-text search across context fields.

        Returns list of (context, target) tuples.
        """
        session = await self._get_session()

        # Build search query
        search_term = f"%{query_text}%"
        query = (
            select(TargetContext, Target)
            .join(Target, Target.id == TargetContext.target_id)
            .where(
                or_(
                    TargetContext.user_context.ilike(search_term),
                    TargetContext.agent_context.ilike(search_term),
                    TargetContext.change_summary.ilike(search_term),
                )
            )
        )

        if target_ids:
            query = query.where(TargetContext.target_id.in_(target_ids))

        query = query.order_by(TargetContext.created_at.desc()).limit(limit)

        result = await session.execute(query)
        return list(result.all())

    async def get_version_by_number(
        self, target_id: UUID, version: int
    ) -> TargetContext | None:
        """Get a specific version number for a target."""
        session = await self._get_session()
        result = await session.execute(
            select(TargetContext).where(
                and_(
                    TargetContext.target_id == target_id,
                    TargetContext.version == version,
                )
            )
        )
        return cast(TargetContext | None, result.scalar_one_or_none())

    async def rollback_to_version(
        self, target_id: UUID, version_id: UUID
    ) -> TargetContext:
        """Create a new version that rolls back to a previous version."""
        # Get the version to rollback to
        rollback_to = await self.get_version(version_id)
        if not rollback_to:
            raise ValueError(f"Version {version_id} not found")

        # Create new version with content from old version
        return await self.create_version(
            target_id=target_id,
            user_context=rollback_to.user_context,
            agent_context=rollback_to.agent_context,
            created_by="system",
            change_summary=f"Rolled back to version {rollback_to.version}",
            change_type=ContextChangeType.ROLLBACK,
            parent_version_id=rollback_to.id,
        )
