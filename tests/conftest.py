"""Shared test fixtures and configuration."""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

# Add src to path for testing
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from tests.fixtures.database import (  # noqa: F401, E402
    db_manager,
    isolated_test_db,
    test_database_settings,
    test_db,
    test_db_with_rollback,
)
from tests.fixtures.docker import docker_test_db  # noqa: F401, E402


def pytest_configure(config):  # noqa: ARG001
    """Configure pytest environment before tests run."""
    # Set default test database URL if not already set
    # This way you don't need to pass it every time
    if "TEST_DATABASE_URL" not in os.environ:
        os.environ["TEST_DATABASE_URL"] = (
            "postgresql+asyncpg://test_user:test_pass@localhost:5433/hiro_test"
        )

    # Also set DATABASE_URL for any code that uses it directly
    if "DATABASE_URL" not in os.environ:
        os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]


@pytest.fixture
def sample_data():
    """Provide sample data for tests."""
    return {
        "id": 1,
        "name": "test",
        "value": 42,
    }


@pytest.fixture
def temp_file(tmp_path):
    """Create a temporary file for testing."""
    file_path = tmp_path / "test_file.txt"
    file_path.write_text("test content")
    return file_path


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    from hiro.web.app import app

    return TestClient(app)


@pytest.fixture
def mock_target():
    """Create a mock target for testing."""
    target = MagicMock()
    target.id = uuid4()
    target.host = "test.example.com"
    target.protocol = "https"
    target.status = "active"
    target.risk_level = "medium"
    target.port = None
    target.title = "Test Target"
    target.notes = []
    target.requests = []
    target.created_at = "2025-01-01T00:00:00Z"
    target.updated_at = "2025-01-01T00:00:00Z"
    target.to_dict = lambda: {
        "id": str(target.id),
        "host": target.host,
        "protocol": target.protocol,
        "status": target.status,
        "risk_level": target.risk_level,
        "port": target.port,
        "title": target.title,
        "notes": [],
        "requests": [],
    }
    return target


# Note: db_session fixture removed - use test_db from database fixtures instead
