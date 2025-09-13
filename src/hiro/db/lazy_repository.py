"""Lazy repository wrappers that initialize database connection on first use."""

import asyncio
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio.session import async_sessionmaker

from hiro.core.config.settings import DatabaseSettings

from .connection import get_session_factory, initialize_database
from .repositories import HttpRequestRepository, TargetRepository
from .schemas import (
    HttpRequestCreate,
    HttpRequestUpdate,
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
                # Initialize database in the current event loop
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
                    logger.debug("Initializing database")
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
