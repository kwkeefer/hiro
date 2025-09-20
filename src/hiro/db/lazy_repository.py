"""Lazy repository wrappers that initialize database connection on first use."""

import asyncio
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio.session import async_sessionmaker

from hiro.core.config.settings import DatabaseSettings

from .connection import auto_migrate_database, get_session_factory, initialize_database
from .models import ContextChangeType
from .repositories import (
    HttpRequestRepository,
    MissionActionRepository,
    MissionRepository,
    TargetContextRepository,
    TargetRepository,
)
from .schemas import (
    HttpRequestCreate,
    HttpRequestUpdate,
    MissionActionCreate,
    MissionCreate,
    MissionUpdate,
    TargetCreate,
    TargetSearchParams,
    TargetUpdate,
)

logger = logging.getLogger(__name__)


class LazyHttpRequestRepository:
    """Lazy wrapper for HttpRequestRepository that initializes on first use."""

    def __init__(self, db_settings: DatabaseSettings):
        self._db_settings = db_settings
        self._real_repo: HttpRequestRepository | None = None
        self._initialized = False
        self._init_lock = asyncio.Lock()

    async def _ensure_initialized(self) -> HttpRequestRepository:
        """Ensure the repository is initialized in the current event loop."""
        if self._initialized and self._real_repo:
            return self._real_repo

        async with self._init_lock:
            # Double-check after acquiring lock
            if self._initialized and self._real_repo:
                return self._real_repo

            try:
                logger.debug(
                    "Initializing database connection for HttpRequestRepository"
                )
                # Initialize database with auto-migration
                success = await auto_migrate_database(self._db_settings)
                if not success:
                    logger.warning(
                        "Auto-migration failed, falling back to basic initialization"
                    )
                    initialize_database(self._db_settings)
                session_factory = get_session_factory()

                # Test the connection
                async with session_factory() as session:
                    from sqlalchemy import text

                    await session.execute(text("SELECT 1"))
                    await session.commit()

                # Create the real repository with the session factory
                self._real_repo = HttpRequestRepository(session_factory)
                self._initialized = True
                logger.info("HttpRequestRepository initialized successfully")
                return self._real_repo
            except Exception as e:
                logger.error(
                    f"Failed to initialize HttpRequestRepository: {e}", exc_info=True
                )
                raise

    async def create(self, request_data: HttpRequestCreate) -> Any:
        """Create a new HTTP request record."""
        repo = await self._ensure_initialized()
        return await repo.create(request_data)

    async def update(self, request_id: Any, request_data: HttpRequestUpdate) -> Any:
        """Update an HTTP request record."""
        repo = await self._ensure_initialized()
        return await repo.update(request_id, request_data)

    async def link_to_target(self, request_id: Any, target_id: Any) -> None:
        """Link request to target."""
        repo = await self._ensure_initialized()
        return await repo.link_to_target(request_id, target_id)


class LazyTargetRepository:
    """Lazy wrapper for TargetRepository that initializes on first use."""

    def __init__(self, db_settings: DatabaseSettings):
        self._db_settings = db_settings
        self._real_repo: TargetRepository | None = None
        self._initialized = False
        self._init_lock = asyncio.Lock()
        # Share the session factory with HttpRequestRepository if possible
        self._shared_session_factory: async_sessionmaker[AsyncSession] | None = None

    async def _ensure_initialized(self) -> TargetRepository:
        """Ensure the repository is initialized in the current event loop."""
        if self._initialized and self._real_repo:
            return self._real_repo

        async with self._init_lock:
            # Double-check after acquiring lock
            if self._initialized and self._real_repo:
                return self._real_repo

            try:
                logger.debug("Initializing database connection for TargetRepository")

                # Try to reuse existing session factory if database is already initialized
                try:
                    session_factory = get_session_factory()
                    logger.debug("Reusing existing session factory")
                except RuntimeError:
                    # Database not initialized yet, initialize it now
                    logger.debug("Initializing database with auto-migration")
                    success = await auto_migrate_database(self._db_settings)
                    if not success:
                        logger.warning(
                            "Auto-migration failed, falling back to basic initialization"
                        )
                        initialize_database(self._db_settings)
                    session_factory = get_session_factory()

                # Test the connection
                async with session_factory() as session:
                    from sqlalchemy import text

                    await session.execute(text("SELECT 1"))
                    await session.commit()

                # Create the real repository with the session factory
                self._real_repo = TargetRepository(session_factory)
                self._initialized = True
                logger.info("TargetRepository initialized successfully")
                return self._real_repo
            except Exception as e:
                logger.error(
                    f"Failed to initialize TargetRepository: {e}", exc_info=True
                )
                raise

    async def get_or_create_from_url(self, url: str) -> Any:
        """Get or create target from URL."""
        repo = await self._ensure_initialized()
        return await repo.get_or_create_from_url(url)

    async def create(self, target_data: TargetCreate) -> Any:
        """Create a new target."""
        repo = await self._ensure_initialized()
        return await repo.create(target_data)

    async def update_last_activity(self, target_id: Any) -> None:
        """Update target's last activity timestamp."""
        repo = await self._ensure_initialized()
        return await repo.update_last_activity(target_id)

    async def get_by_id(self, target_id: Any) -> Any:
        """Get target by ID."""
        repo = await self._ensure_initialized()
        return await repo.get_by_id(target_id)

    async def get_by_endpoint(self, host: str, port: int | None, protocol: str) -> Any:
        """Get target by endpoint (host, port, protocol)."""
        repo = await self._ensure_initialized()
        return await repo.get_by_endpoint(host, port, protocol)

    async def update(self, target_id: Any, target_data: TargetUpdate) -> Any:
        """Update target."""
        repo = await self._ensure_initialized()
        return await repo.update(target_id, target_data)

    async def search(self, params: TargetSearchParams) -> Any:
        """Search targets with filters."""
        repo = await self._ensure_initialized()
        return await repo.search(params)

    async def get_summary(self, target_id: Any) -> Any:
        """Get target summary with related data counts."""
        repo = await self._ensure_initialized()
        return await repo.get_summary(target_id)


class LazyTargetContextRepository:
    """Lazy wrapper for TargetContextRepository that initializes on first use."""

    def __init__(self, db_settings: DatabaseSettings):
        self._db_settings = db_settings
        self._real_repo: TargetContextRepository | None = None
        self._initialized = False
        self._init_lock = asyncio.Lock()
        # Share the session factory with other repositories if possible
        self._shared_session_factory: async_sessionmaker[AsyncSession] | None = None

    async def _ensure_initialized(self) -> TargetContextRepository:
        """Ensure the repository is initialized in the current event loop."""
        if self._initialized and self._real_repo:
            return self._real_repo

        async with self._init_lock:
            # Double-check after acquiring lock
            if self._initialized and self._real_repo:
                return self._real_repo

            try:
                logger.debug(
                    "Initializing database connection for TargetContextRepository"
                )
                # Check if database is already initialized
                session_factory = get_session_factory()
                if not session_factory:
                    # Initialize database in the current event loop
                    initialize_database(self._db_settings)
                    session_factory = get_session_factory()

                # Test the connection
                async with session_factory() as session:
                    from sqlalchemy import text

                    await session.execute(text("SELECT 1"))
                    await session.commit()

                # Create the real repository with the session factory
                self._real_repo = TargetContextRepository(session_factory)
                self._initialized = True
                logger.info("TargetContextRepository initialized successfully")
                return self._real_repo
            except Exception as e:
                logger.error(
                    f"Failed to initialize TargetContextRepository: {e}", exc_info=True
                )
                raise

    async def create_version(
        self,
        target_id: Any,
        user_context: str | None = None,
        agent_context: str | None = None,
        created_by: str = "user",
        change_summary: str | None = None,
        change_type: ContextChangeType = ContextChangeType.USER_EDIT,
        parent_version_id: Any | None = None,
        is_major_version: bool = False,
    ) -> Any:
        """Create a new immutable context version."""
        repo = await self._ensure_initialized()
        return await repo.create_version(
            target_id=target_id,
            user_context=user_context,
            agent_context=agent_context,
            created_by=created_by,
            change_summary=change_summary,
            change_type=change_type,
            parent_version_id=parent_version_id,
            is_major_version=is_major_version,
        )

    async def get_current(self, target_id: Any) -> Any:
        """Get current context version for a target."""
        repo = await self._ensure_initialized()
        return await repo.get_current(target_id)

    async def get_version(self, context_id: Any) -> Any:
        """Get specific context version."""
        repo = await self._ensure_initialized()
        return await repo.get_version(context_id)

    async def list_versions(
        self, target_id: Any, limit: int = 10, offset: int = 0
    ) -> Any:
        """Get version history for a target."""
        repo = await self._ensure_initialized()
        return await repo.list_versions(target_id, limit, offset)

    async def search_contexts(
        self,
        query_text: str,
        target_ids: list[Any] | None = None,
        limit: int = 50,
    ) -> Any:
        """Full-text search across context fields."""
        repo = await self._ensure_initialized()
        return await repo.search_contexts(query_text, target_ids, limit)


class LazyMissionRepository:
    """Lazy wrapper for MissionRepository that initializes on first use."""

    def __init__(self, db_settings: DatabaseSettings):
        self._db_settings = db_settings
        self._real_repo: MissionRepository | None = None
        self._initialized = False
        self._init_lock = asyncio.Lock()
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    async def _ensure_initialized(self) -> MissionRepository:
        """Ensure the repository is initialized in the current event loop."""
        if self._initialized and self._real_repo:
            return self._real_repo

        async with self._init_lock:
            # Double-check after acquiring lock
            if self._initialized and self._real_repo:
                return self._real_repo

            try:
                logger.debug("Initializing database connection for MissionRepository")
                # Check if database is already initialized
                session_factory = get_session_factory()
                if not session_factory:
                    # Initialize database with auto-migration
                    success = await auto_migrate_database(self._db_settings)
                    if not success:
                        logger.warning(
                            "Auto-migration failed, falling back to basic initialization"
                        )
                        initialize_database(self._db_settings)
                    session_factory = get_session_factory()

                self._session_factory = session_factory

                # Test the connection
                async with session_factory() as session:
                    from sqlalchemy import text

                    await session.execute(text("SELECT 1"))
                    await session.commit()

                # Create the real repository with a session
                # Note: MissionRepository expects a session, not a factory
                # We'll create a new session for each method call
                async with session_factory() as session:
                    self._real_repo = MissionRepository(session)

                self._initialized = True
                logger.info("MissionRepository initialized successfully")
                return self._real_repo
            except Exception as e:
                logger.error(
                    f"Failed to initialize MissionRepository: {e}", exc_info=True
                )
                raise

    async def create(self, mission_data: MissionCreate) -> Any:
        """Create a new mission."""
        await self._ensure_initialized()
        assert self._session_factory is not None
        # Create new session for this operation (ADR-016: session-per-method)
        async with self._session_factory() as session:
            repo = MissionRepository(session)
            result = await repo.create(mission_data)
            await session.commit()
            return result

    async def get(self, mission_id: Any) -> Any:
        """Get a mission by ID."""
        await self._ensure_initialized()
        assert self._session_factory is not None
        async with self._session_factory() as session:
            repo = MissionRepository(session)
            return await repo.get(mission_id)

    async def update(self, mission_id: Any, mission_data: MissionUpdate) -> Any:
        """Update a mission."""
        await self._ensure_initialized()
        assert self._session_factory is not None
        async with self._session_factory() as session:
            repo = MissionRepository(session)
            result = await repo.update(mission_id, mission_data)
            await session.commit()
            return result

    async def update_embeddings(
        self,
        mission_id: Any,
        goal_embedding: list[float] | None = None,
        hypothesis_embedding: list[float] | None = None,
    ) -> Any:
        """Update mission embeddings."""
        await self._ensure_initialized()
        assert self._session_factory is not None
        async with self._session_factory() as session:
            repo = MissionRepository(session)
            await repo.update_embeddings(
                mission_id, goal_embedding, hypothesis_embedding
            )
            await session.commit()

    async def list_missions(
        self,
        target_id: Any | None = None,  # noqa: ARG002
        mission_type: str | None = None,  # noqa: ARG002
        status: str | None = None,  # noqa: ARG002
        limit: int = 50,  # noqa: ARG002
        offset: int = 0,  # noqa: ARG002
    ) -> Any:
        """List missions with optional filters."""
        await self._ensure_initialized()
        assert self._session_factory is not None
        async with self._session_factory() as session:
            # MissionRepository doesn't have list_missions, return empty for now
            # TODO: Implement proper mission listing
            _ = MissionRepository(session)  # Created for future use
            return []


class LazyMissionActionRepository:
    """Lazy wrapper for MissionActionRepository that initializes on first use."""

    def __init__(self, db_settings: DatabaseSettings):
        self._db_settings = db_settings
        self._real_repo: MissionActionRepository | None = None
        self._initialized = False
        self._init_lock = asyncio.Lock()
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    async def _ensure_initialized(self) -> MissionActionRepository:
        """Ensure the repository is initialized in the current event loop."""
        if self._initialized and self._real_repo:
            return self._real_repo

        async with self._init_lock:
            # Double-check after acquiring lock
            if self._initialized and self._real_repo:
                return self._real_repo

            try:
                logger.debug(
                    "Initializing database connection for MissionActionRepository"
                )
                # Check if database is already initialized
                session_factory = get_session_factory()
                if not session_factory:
                    # Initialize database with auto-migration
                    success = await auto_migrate_database(self._db_settings)
                    if not success:
                        logger.warning(
                            "Auto-migration failed, falling back to basic initialization"
                        )
                        initialize_database(self._db_settings)
                    session_factory = get_session_factory()

                self._session_factory = session_factory

                # Test the connection
                async with session_factory() as session:
                    from sqlalchemy import text

                    await session.execute(text("SELECT 1"))
                    await session.commit()

                # Create the real repository
                async with session_factory() as session:
                    self._real_repo = MissionActionRepository(session)

                self._initialized = True
                logger.info("MissionActionRepository initialized successfully")
                return self._real_repo
            except Exception as e:
                logger.error(
                    f"Failed to initialize MissionActionRepository: {e}", exc_info=True
                )
                raise

    async def create(self, action_data: MissionActionCreate) -> Any:
        """Create a new mission action."""
        await self._ensure_initialized()
        assert self._session_factory is not None
        # Create new session for this operation (ADR-016: session-per-method)
        async with self._session_factory() as session:
            repo = MissionActionRepository(session)
            result = await repo.create(action_data)
            await session.commit()
            return result

    async def get(self, action_id: Any) -> Any:
        """Get a mission action by ID."""
        await self._ensure_initialized()
        assert self._session_factory is not None
        async with self._session_factory() as session:
            repo = MissionActionRepository(session)
            return await repo.get(action_id)

    async def link_requests(self, action_id: Any, request_ids: list[Any]) -> None:  # noqa: ARG002
        """Link HTTP requests to an action."""
        await self._ensure_initialized()
        assert self._session_factory is not None
        async with self._session_factory() as session:
            # TODO: link_recent_requests needs mission_id which we don't have here
            # For now, skip linking requests
            _ = MissionActionRepository(session)  # Created for future use
            await session.commit()

    async def get_recent_requests_for_mission(
        self,
        mission_id: Any,  # noqa: ARG002
        limit: int = 5,  # noqa: ARG002
    ) -> Any:
        """Get recent HTTP requests for a mission."""
        await self._ensure_initialized()
        assert self._session_factory is not None
        async with self._session_factory() as session:
            # This method doesn't exist in MissionActionRepository
            # TODO: Implement proper request fetching
            _ = MissionActionRepository(session)  # Created for future use
            return []

    async def list_actions(
        self,
        mission_id: Any | None = None,  # noqa: ARG002
        action_type: str | None = None,  # noqa: ARG002
        success_only: bool = False,  # noqa: ARG002
        limit: int = 50,  # noqa: ARG002
        offset: int = 0,  # noqa: ARG002
    ) -> Any:
        """List mission actions with optional filters."""
        await self._ensure_initialized()
        assert self._session_factory is not None
        async with self._session_factory() as session:
            # This method doesn't exist in MissionActionRepository
            # TODO: Implement proper action listing
            _ = MissionActionRepository(session)  # Created for future use
            return []
