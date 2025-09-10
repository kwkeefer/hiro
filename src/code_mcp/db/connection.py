"""Database connection management."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.ext.asyncio.session import async_sessionmaker
from sqlalchemy.pool import NullPool

from code_mcp.core.config.settings import DatabaseSettings

logger = logging.getLogger(__name__)

# Global database engine
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def create_database_engine(settings: DatabaseSettings) -> AsyncEngine:
    """Create database engine with connection pooling."""
    if not settings.url:
        raise ValueError("Database URL not configured")

    logger.info(
        f"Creating database engine for {settings.host}:{settings.port}/{settings.database}"
    )

    # Configure engine based on settings
    engine_kwargs = {
        "echo": False,  # Set to True for SQL query debugging
        "pool_size": settings.pool_size,
        "max_overflow": settings.max_overflow,
        "pool_timeout": settings.pool_timeout,
        "pool_pre_ping": True,  # Verify connections before use
    }

    # For testing, use NullPool to avoid connection persistence issues
    if "test" in settings.database.lower():
        engine_kwargs["poolclass"] = NullPool
        logger.info("Using NullPool for test database")

    return create_async_engine(settings.url, **engine_kwargs)


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get the session factory for database operations."""
    if _session_factory is None:
        raise RuntimeError(
            "Database not initialized. Call initialize_database() first."
        )
    return _session_factory


def initialize_database(settings: DatabaseSettings) -> None:
    """Initialize database engine and session factory."""
    global _engine, _session_factory

    if _engine is not None:
        logger.warning("Database already initialized")
        return

    _engine = create_database_engine(settings)
    _session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )

    logger.info("Database initialized successfully")


async def close_database() -> None:
    """Close database connections and clean up resources."""
    global _engine, _session_factory

    if _engine is not None:
        logger.info("Closing database connections")
        await _engine.dispose()
        _engine = None
        _session_factory = None


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session with automatic cleanup."""
    session_factory = get_session_factory()

    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def test_connection(settings: DatabaseSettings) -> bool:
    """Test database connection."""
    try:
        engine = create_database_engine(settings)
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        await engine.dispose()
        logger.info("Database connection test successful")
        return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False
