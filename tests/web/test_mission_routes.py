"""Tests for mission web routes."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from hiro.db.models import Mission, MissionAction, Target
from hiro.web.app import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_db():
    """Create mock database session."""
    mock = AsyncMock(spec=AsyncSession)
    return mock


@pytest.fixture
def sample_target():
    """Create sample target."""
    return Target(
        id=uuid.uuid4(),
        host="example.com",
        protocol="https",
        port=443,
        status="active",
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_mission(sample_target):
    """Create sample mission."""
    mission = Mission(
        id=uuid.uuid4(),
        name="Test Security Scan",
        description="Testing web application security",
        mission_type="security_assessment",
        goal="Identify vulnerabilities",
        hypothesis="Application has SQL injection vulnerabilities",
        created_at=datetime.now(UTC),
        completed_at=None,
    )
    mission.targets = [sample_target]
    return mission


@pytest.fixture
def sample_actions(sample_mission):
    """Create sample mission actions."""
    return [
        MissionAction(
            id=uuid.uuid4(),
            mission_id=sample_mission.id,
            action_type="exploit",
            technique="SQL injection",
            payload="admin' OR '1'='1",
            result="Authentication bypassed",
            success=True,
            learning="Login form vulnerable",
            created_at=datetime.now(UTC),
        ),
        MissionAction(
            id=uuid.uuid4(),
            mission_id=sample_mission.id,
            action_type="recon",
            technique="Port scanning",
            payload=None,
            result="Found open ports 80, 443",
            success=True,
            learning="Standard web ports open",
            created_at=datetime.now(UTC),
        ),
    ]


@pytest.mark.asyncio
async def test_list_missions_empty(client, monkeypatch):
    """Test listing missions when database is empty."""

    # Mock the database dependency
    async def mock_get_db():
        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.execute = AsyncMock(
            return_value=MagicMock(
                scalars=MagicMock(
                    return_value=MagicMock(all=MagicMock(return_value=[]))
                )
            )
        )
        mock_db.scalar = AsyncMock(return_value=0)
        yield mock_db

    monkeypatch.setattr("hiro.web.routers.missions.get_db", mock_get_db)

    response = client.get("/missions/")
    assert response.status_code == 200
    assert "missions/list.html" in response.text or "No missions" in response.text


@pytest.mark.asyncio
async def test_list_missions_with_data(client, sample_mission, monkeypatch):
    """Test listing missions with data."""

    async def mock_get_db():
        mock_db = AsyncMock(spec=AsyncSession)

        # Mock the query result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_mission]
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.scalar = AsyncMock(side_effect=[2, 5])  # action_count, request_count

        yield mock_db

    monkeypatch.setattr("hiro.web.routers.missions.get_db", mock_get_db)

    response = client.get("/missions/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_create_mission_form(client, sample_target, monkeypatch):
    """Test mission creation form display."""

    async def mock_get_db():
        mock_db = AsyncMock(spec=AsyncSession)

        # Mock target repository list_all
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_target]
        mock_db.execute = AsyncMock(return_value=mock_result)

        yield mock_db

    monkeypatch.setattr("hiro.web.routers.missions.get_db", mock_get_db)

    response = client.get("/missions/create")
    assert response.status_code == 200
    assert "missions/create.html" in response.text or "Create" in response.text


@pytest.mark.asyncio
async def test_create_mission_post(client, sample_target, sample_mission, monkeypatch):
    """Test mission creation via POST."""

    async def mock_get_db():
        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.flush = AsyncMock()

        # Mock the created mission
        sample_mission.id = uuid.uuid4()
        mock_db.execute = AsyncMock(
            return_value=MagicMock(
                scalar_one_or_none=MagicMock(return_value=sample_mission)
            )
        )

        yield mock_db

    monkeypatch.setattr("hiro.web.routers.missions.get_db", mock_get_db)

    form_data = {
        "target_id": str(sample_target.id),
        "name": "Test Mission",
        "mission_type": "security_assessment",
        "goal": "Test application security",
        "hypothesis": "Application may be vulnerable",
    }

    response = client.post("/missions/create", data=form_data, follow_redirects=False)
    # Should redirect to mission detail page
    assert response.status_code == 303 or response.status_code == 302


@pytest.mark.asyncio
async def test_view_mission_detail(client, sample_mission, monkeypatch):
    """Test viewing mission detail."""

    async def mock_get_db():
        mock_db = AsyncMock(spec=AsyncSession)

        # Mock mission repository get
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_mission
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Mock summary
        mock_db.scalar = AsyncMock(
            side_effect=[2, 5, 2]
        )  # action_count, request_count, success_count

        yield mock_db

    monkeypatch.setattr("hiro.web.routers.missions.get_db", mock_get_db)

    response = client.get(f"/missions/{sample_mission.id}")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_view_mission_actions_tab(
    client, sample_mission, sample_actions, monkeypatch
):
    """Test viewing mission actions tab."""

    async def mock_get_db():
        mock_db = AsyncMock(spec=AsyncSession)

        # Mock mission get
        mock_mission_result = MagicMock()
        mock_mission_result.scalar_one_or_none.return_value = sample_mission

        # Mock actions get
        mock_actions_result = MagicMock()
        mock_actions_result.scalars.return_value.all.return_value = sample_actions

        mock_db.execute = AsyncMock(
            side_effect=[mock_mission_result, mock_actions_result]
        )
        mock_db.scalar = AsyncMock(side_effect=[2, 5, 2])

        yield mock_db

    monkeypatch.setattr("hiro.web.routers.missions.get_db", mock_get_db)

    response = client.get(f"/missions/{sample_mission.id}?tab=actions")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_record_action_form(client, sample_mission, monkeypatch):
    """Test action recording form display."""

    async def mock_get_db():
        mock_db = AsyncMock(spec=AsyncSession)

        # Mock mission get
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_mission
        mock_db.execute = AsyncMock(return_value=mock_result)

        yield mock_db

    monkeypatch.setattr("hiro.web.routers.missions.get_db", mock_get_db)

    response = client.get(f"/missions/{sample_mission.id}/record-action")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_record_action_post(client, sample_mission, monkeypatch):
    """Test recording a new action."""

    async def mock_get_db():
        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.flush = AsyncMock()

        # Create a mock action
        new_action = MissionAction(
            id=uuid.uuid4(),
            mission_id=sample_mission.id,
            action_type="exploit",
            technique="XSS",
            payload="<script>alert(1)</script>",
            result="Executed successfully",
            success=True,
            learning="Input not sanitized",
        )

        mock_db.execute = AsyncMock(
            return_value=MagicMock(
                scalar_one_or_none=MagicMock(return_value=new_action)
            )
        )

        yield mock_db

    monkeypatch.setattr("hiro.web.routers.missions.get_db", mock_get_db)

    form_data = {
        "action_type": "exploit",
        "technique": "XSS",
        "payload": "<script>alert(1)</script>",
        "result": "Executed successfully",
        "success": "true",
        "learning": "Input not sanitized",
    }

    response = client.post(
        f"/missions/{sample_mission.id}/record-action",
        data=form_data,
        follow_redirects=False,
    )
    # Should redirect to actions tab
    assert response.status_code == 303 or response.status_code == 302


@pytest.mark.asyncio
async def test_complete_mission(client, sample_mission, monkeypatch):
    """Test completing a mission."""

    async def mock_get_db():
        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.commit = AsyncMock()
        mock_db.flush = AsyncMock()

        # Mock the update
        sample_mission.completed_at = datetime.now(UTC)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_mission
        mock_db.execute = AsyncMock(return_value=mock_result)

        yield mock_db

    monkeypatch.setattr("hiro.web.routers.missions.get_db", mock_get_db)

    response = client.post(
        f"/missions/{sample_mission.id}/complete", follow_redirects=False
    )
    # Should redirect back to mission detail
    assert response.status_code == 303 or response.status_code == 302


@pytest.mark.asyncio
async def test_delete_mission(client, sample_mission, monkeypatch):
    """Test deleting a mission."""

    async def mock_get_db():
        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.delete = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.flush = AsyncMock()

        # Mock mission get
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_mission
        mock_db.execute = AsyncMock(return_value=mock_result)

        yield mock_db

    monkeypatch.setattr("hiro.web.routers.missions.get_db", mock_get_db)

    response = client.delete(f"/missions/{sample_mission.id}")
    assert response.status_code == 200
    assert response.json() == {"status": "deleted"}


@pytest.mark.asyncio
async def test_view_mission_not_found(client, monkeypatch):
    """Test viewing non-existent mission."""

    async def mock_get_db():
        mock_db = AsyncMock(spec=AsyncSession)

        # Mock mission not found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        yield mock_db

    monkeypatch.setattr("hiro.web.routers.missions.get_db", mock_get_db)

    response = client.get(f"/missions/{uuid.uuid4()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_mission_patterns_tab(client, sample_mission, monkeypatch):
    """Test viewing mission patterns tab."""

    async def mock_get_db():
        mock_db = AsyncMock(spec=AsyncSession)

        # Mock mission get
        mock_mission_result = MagicMock()
        mock_mission_result.scalar_one_or_none.return_value = sample_mission

        # Mock patterns query
        mock_patterns_result = MagicMock()
        mock_patterns_result.fetchall.return_value = [
            MagicMock(
                technique="SQL injection",
                count=5,
                success_count=4,
                _mapping={"technique": "SQL injection", "count": 5, "success_count": 4},
            ),
            MagicMock(
                technique="XSS",
                count=3,
                success_count=3,
                _mapping={"technique": "XSS", "count": 3, "success_count": 3},
            ),
        ]

        mock_db.execute = AsyncMock(
            side_effect=[mock_mission_result, mock_patterns_result]
        )
        mock_db.scalar = AsyncMock(side_effect=[2, 5, 2])

        yield mock_db

    monkeypatch.setattr("hiro.web.routers.missions.get_db", mock_get_db)

    response = client.get(f"/missions/{sample_mission.id}?tab=patterns")
    assert response.status_code == 200
