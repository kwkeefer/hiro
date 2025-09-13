"""Test fixtures for web interface tests."""

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from hiro.db.database import get_db
from hiro.web.app import app

# Import the existing database test fixtures


@pytest.fixture
def test_client():
    """Create a test client without database (for unit tests)."""
    with TestClient(app) as client:
        yield client


@pytest_asyncio.fixture
async def test_client_with_db(test_db: AsyncSession):
    """Create a test client with database override (for integration tests)."""

    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def mock_target_data():
    """Sample target data for tests."""
    return {
        "host": "example.com",
        "port": 443,
        "protocol": "https",
        "title": "Test Target",
        "status": "active",
        "risk_level": "medium",
    }


@pytest.fixture
def mock_context_data():
    """Sample context data for tests."""
    return {
        "user_context": "## User Notes\nThis is a test target.",
        "agent_context": "## Agent Analysis\nTarget appears to be a web server.",
    }


@pytest.fixture
def mock_request_data():
    """Sample HTTP request data for tests."""
    return {
        "method": "GET",
        "url": "https://example.com/api/test",
        "host": "example.com",
        "path": "/api/test",
        "status_code": 200,
        "response_body": '{"status": "ok"}',
        "elapsed_ms": 123.45,
    }
