"""Database utilities for FastAPI."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from hiro.core.config.settings import get_settings
from hiro.db.connection import (
    get_db_session,
    get_session_factory,
    initialize_database,
)


# Initialize database on module import if configured
def init_db():
    """Initialize database connection."""
    try:
        settings = get_settings()
        if settings.database and settings.database.url:
            initialize_database(settings.database)
            return get_session_factory()
    except Exception as e:
        print(f"Warning: Could not initialize database: {e}")
        import traceback

        traceback.print_exc()
    return None


# Initialize on import
_session_factory = init_db()

# Create a local SessionLocal for compatibility
SessionLocal = _session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database session in FastAPI."""
    from fastapi import HTTPException

    global _session_factory

    # Try to initialize if not already done
    if _session_factory is None:
        _session_factory = init_db()

    if _session_factory is None:
        # Return generic error without exposing infrastructure details
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")

    async with get_db_session() as session:
        yield session
