"""Configuration and fixtures for AI logging tests."""

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from hiro.db.models import AttemptType
from hiro.db.repositories import (
    AiSessionRepository,
    HttpRequestRepository,
    TargetAttemptRepository,
    TargetNoteRepository,
    TargetRepository,
)
from hiro.servers.ai_logging.tools import (
    CreateTargetTool,
    GetTargetSummaryTool,
    SearchTargetsTool,
    UpdateTargetStatusTool,
)
from tests.fixtures.database import db_manager, test_db  # Re-export for convenience
from tests.fixtures.factories import (
    TargetAttemptFactory,
    TargetFactory,
    TargetNoteFactory,
    TestDataBuilder,
)

# Re-export fixtures for convenience
__all__ = [
    "db_manager",
    "test_db",
    "target_repo",
    "note_repo",
    "attempt_repo",
    "session_repo",
    "request_repo",
    "create_target_tool",
    "update_target_tool",
    "get_summary_tool",
    "search_targets_tool",
]


@pytest_asyncio.fixture
async def target_repo(test_db: AsyncSession) -> TargetRepository:
    """Provide TargetRepository with test database."""
    return TargetRepository(test_db)


@pytest_asyncio.fixture
async def note_repo(test_db: AsyncSession) -> TargetNoteRepository:
    """Provide TargetNoteRepository with test database."""
    return TargetNoteRepository(test_db)


@pytest_asyncio.fixture
async def attempt_repo(test_db: AsyncSession) -> TargetAttemptRepository:
    """Provide TargetAttemptRepository with test database."""
    return TargetAttemptRepository(test_db)


@pytest_asyncio.fixture
async def session_repo(test_db: AsyncSession) -> AiSessionRepository:
    """Provide AiSessionRepository with test database."""
    return AiSessionRepository(test_db)


@pytest_asyncio.fixture
async def request_repo(test_db: AsyncSession) -> HttpRequestRepository:
    """Provide HttpRequestRepository with test database."""
    return HttpRequestRepository(test_db)


@pytest_asyncio.fixture
async def create_target_tool(target_repo: TargetRepository) -> CreateTargetTool:
    """Provide CreateTargetTool with test repository."""
    return CreateTargetTool(target_repo=target_repo)


@pytest_asyncio.fixture
async def update_target_tool(target_repo: TargetRepository) -> UpdateTargetStatusTool:
    """Provide UpdateTargetStatusTool with test repository."""
    return UpdateTargetStatusTool(target_repo=target_repo)


@pytest_asyncio.fixture
async def get_summary_tool(target_repo: TargetRepository) -> GetTargetSummaryTool:
    """Provide GetTargetSummaryTool with test repository."""
    return GetTargetSummaryTool(target_repo=target_repo)


@pytest_asyncio.fixture
async def search_targets_tool(target_repo: TargetRepository) -> SearchTargetsTool:
    """Provide SearchTargetsTool with test repository."""
    return SearchTargetsTool(target_repo=target_repo)


@pytest_asyncio.fixture
async def sample_target(test_db: AsyncSession, target_repo: TargetRepository):  # noqa: ARG001
    """Create a sample target for testing."""
    target_data = TargetFactory.create_data(
        host="test.example.com",
        port=443,
        protocol="https",
        title="Test Target",
        status="active",
        risk_level="medium",
    )
    target = await target_repo.create(target_data)
    return target


@pytest_asyncio.fixture
async def multiple_targets(test_db: AsyncSession, target_repo: TargetRepository):  # noqa: ARG001
    """Create multiple targets for testing."""
    targets = []

    # Create diverse targets for testing search/filter
    test_data = [
        {
            "host": "api.example.com",
            "port": 443,
            "protocol": "https",
            "status": "active",
            "risk_level": "high",
        },
        {
            "host": "web.example.com",
            "port": 80,
            "protocol": "http",
            "status": "active",
            "risk_level": "low",
        },
        {
            "host": "admin.example.com",
            "port": 8080,
            "protocol": "http",
            "status": "inactive",
            "risk_level": "critical",
        },
        {
            "host": "db.example.com",
            "port": 5432,
            "protocol": "tcp",
            "status": "blocked",
            "risk_level": "medium",
        },
        {
            "host": "test.example.com",
            "port": 3000,
            "protocol": "https",
            "status": "completed",
            "risk_level": "low",
        },
    ]

    for data in test_data:
        target_data = TargetFactory.create_data(**data)
        target = await target_repo.create(target_data)
        targets.append(target)

    return targets


@pytest_asyncio.fixture
async def target_with_history(
    test_db: AsyncSession,  # noqa: ARG001
    target_repo: TargetRepository,
    note_repo: TargetNoteRepository,
    attempt_repo: TargetAttemptRepository,
):
    """Create a target with notes and attempts."""
    # Create target
    target_data = TargetFactory.create_data(
        host="history.example.com",
        title="Target with History",
    )
    target = await target_repo.create(target_data)

    # Add notes
    notes = []
    for i in range(3):
        note_data = TargetNoteFactory.create_data(
            target_id=target.id,
            note_type="reconnaissance",
            title=f"Discovery Note {i + 1}",
            content=f"Note {i + 1}: Discovery information",
        )
        note = await note_repo.create(note_data)
        notes.append(note)

    # Add attempts
    attempts = []
    for i in range(2):
        attempt_data = TargetAttemptFactory.create_data(
            target_id=target.id, attempt_type=AttemptType.SCAN
        )
        attempt = await attempt_repo.create(attempt_data)

        # Update first attempt to be successful, second to be failed
        from hiro.db.schemas import TargetAttemptUpdate

        if i == 0:
            update_data = TargetAttemptUpdate(
                success=True, actual_outcome="Successful scan"
            )
            await attempt_repo.update(attempt.id, update_data)
        else:
            update_data = TargetAttemptUpdate(
                success=False, actual_outcome="Failed scan"
            )
            await attempt_repo.update(attempt.id, update_data)

        attempts.append(attempt)

    return {
        "target": target,
        "notes": notes,
        "attempts": attempts,
    }


@pytest_asyncio.fixture
async def complete_test_scenario(test_db: AsyncSession):
    """Create a complete test scenario with all relationships."""
    return await TestDataBuilder.create_complete_test_scenario(test_db)
