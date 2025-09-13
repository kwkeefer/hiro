"""Database fixtures for testing with real PostgreSQL."""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from hiro.core.config.settings import DatabaseSettings
from hiro.db.models import Base


class TestDatabaseManager:
    """Manages test database connections and cleanup."""

    def __init__(self, database_url: str | None = None):
        """Initialize test database manager.

        Args:
            database_url: Override database URL for testing
        """
        self.database_url = database_url or os.getenv(
            "TEST_DATABASE_URL",
            "postgresql+asyncpg://test_user:test_pass@localhost:5433/hiro_test",
        )
        self.engine: AsyncEngine | None = None
        self.session_factory: async_sessionmaker[AsyncSession] | None = None

    async def setup(self) -> None:
        """Set up test database engine and run migrations."""
        # Create engine with NullPool for test isolation
        self.engine = create_async_engine(
            self.database_url,
            echo=False,  # Set to True for SQL debugging
            poolclass=NullPool,  # Disable connection pooling for tests
        )

        # Create session factory
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )

        # Create all tables (for testing, we use create_all instead of alembic)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def teardown(self) -> None:
        """Clean up test database."""
        if self.engine:
            # Just dispose of the engine - Docker will handle cleanup
            await self.engine.dispose()
            self.engine = None
            self.session_factory = None

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a test database session with automatic cleanup."""
        if not self.session_factory:
            raise RuntimeError("Database not initialized. Call setup() first.")

        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def clear_tables(self) -> None:
        """Clear all data from tables without dropping them."""
        if not self.engine:
            return

        async with self.engine.begin() as conn:
            # Get all table names
            result = await conn.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            )
            tables = result.fetchall()

            # Disable foreign key checks and truncate all tables
            for table in tables:
                if table[0] != "alembic_version":  # Don't truncate migration table
                    await conn.execute(text(f"TRUNCATE TABLE {table[0]} CASCADE"))


# Global test database manager
_test_db_manager: TestDatabaseManager | None = None


@pytest_asyncio.fixture(scope="session")
async def db_manager() -> AsyncGenerator[TestDatabaseManager, None]:
    """Provide database manager for the test session."""
    global _test_db_manager

    if _test_db_manager is None:
        _test_db_manager = TestDatabaseManager()
        await _test_db_manager.setup()

    yield _test_db_manager

    # Cleanup after all tests
    if _test_db_manager:
        await _test_db_manager.teardown()
        _test_db_manager = None


@pytest_asyncio.fixture
async def test_db(
    db_manager: TestDatabaseManager,
) -> AsyncGenerator[AsyncSession, None]:
    """Provide a test database session with automatic cleanup.

    Each test gets a fresh database session with all tables cleared.
    """
    # Clear all tables before each test
    await db_manager.clear_tables()

    # Provide session for the test
    async with db_manager.get_session() as session:
        yield session


@pytest_asyncio.fixture
async def test_db_with_rollback(
    db_manager: TestDatabaseManager,
) -> AsyncGenerator[AsyncSession, None]:
    """Provide a test database session that rolls back after the test.

    Useful for tests that should not persist any changes.
    """
    async with db_manager.session_factory() as session, session.begin():
        yield session
        # Automatic rollback when context exits


@pytest.fixture
def test_database_settings() -> DatabaseSettings:
    """Provide test database settings."""
    return DatabaseSettings(
        host="localhost",
        port=5433,
        database="hiro_test",
        username="test_user",
        password="test_pass",
        pool_size=5,
        max_overflow=10,
    )


@pytest_asyncio.fixture
async def isolated_test_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide completely isolated database for a single test.

    Creates a new database connection just for this test.
    """
    database_url = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://test_user:test_pass@localhost:5433/hiro_test",
    )

    # Create isolated engine
    engine = create_async_engine(
        database_url,
        echo=False,
        poolclass=NullPool,
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


# Pytest marker for database tests
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "database: mark test as requiring database access"
    )
