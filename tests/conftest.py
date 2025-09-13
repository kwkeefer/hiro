"""Shared test fixtures and configuration."""

import os
import sys
from pathlib import Path

import pytest

# Add src to path for testing
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


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
