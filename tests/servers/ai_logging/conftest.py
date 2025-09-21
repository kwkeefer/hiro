"""Configuration and fixtures for AI logging tests."""

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from hiro.db.repositories import (
    HttpRequestRepository,
    MissionRepository,
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
    TargetFactory,
    TestDataBuilder,
)

# Re-export fixtures for convenience
__all__ = [
    "db_manager",
    "test_db",
    "target_repo",
    "mission_repo",
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
async def mission_repo(test_db: AsyncSession) -> MissionRepository:
    """Provide MissionRepository with test database."""
    return MissionRepository(test_db)


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
    test_db: AsyncSession,
    target_repo: TargetRepository,
    mission_repo: MissionRepository,
):
    """Create a target with mission actions."""
    from uuid import uuid4

    from hiro.db.models import MissionAction

    # Create target
    target_data = TargetFactory.create_data(
        host="history.example.com",
        title="Target with History",
    )
    target = await target_repo.create(target_data)

    # Create mission
    from hiro.db.models import MissionTarget, SessionStatus
    from hiro.db.schemas import MissionCreate

    mission_data = MissionCreate(
        name="Test Mission",
        status=SessionStatus.ACTIVE,
        target_id=target.id,
    )
    mission = await mission_repo.create(mission_data)

    # Ensure mission is linked to target through MissionTarget
    mission_target = MissionTarget(mission_id=mission.id, target_id=target.id)
    test_db.add(mission_target)
    await test_db.flush()

    # Add mission actions
    actions = []
    for i in range(2):
        action = MissionAction(
            id=uuid4(),
            mission_id=mission.id,
            action_type="scan",
            technique=f"test_scan_{i}",
            payload="test_payload",
            result="Successful scan" if i == 0 else "Failed scan",
            success=i == 0,
        )
        test_db.add(action)
        actions.append(action)

    await test_db.flush()

    return {
        "target": target,
        "mission": mission,
        "actions": actions,
    }


@pytest_asyncio.fixture
async def complete_test_scenario(test_db: AsyncSession):
    """Create a complete test scenario with all relationships."""
    return await TestDataBuilder.create_complete_test_scenario(test_db)
