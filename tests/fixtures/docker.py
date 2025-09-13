"""Docker container management for testing."""

import asyncio
import logging
import os
import subprocess
import time
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)


class DockerTestDatabase:
    """Manages Docker test database container lifecycle."""

    def __init__(self):
        """Initialize Docker test database manager."""
        self.project_root = Path(__file__).parent.parent.parent
        self.compose_file = self.project_root / "docker-compose.test.yml"
        self.container_name = "hiro-test-db"
        self.max_wait_seconds = 30

    def is_container_running(self) -> bool:
        """Check if the test database container is running."""
        try:
            result = subprocess.run(
                [
                    "docker",
                    "ps",
                    "--filter",
                    f"name={self.container_name}",
                    "--format",
                    "{{.Names}}",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            return self.container_name in result.stdout
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def start_container(self) -> None:
        """Start the test database container."""
        if self.is_container_running():
            logger.info("Test database container already running")
            return

        logger.info("Starting test database container...")
        try:
            subprocess.run(
                ["docker-compose", "-f", str(self.compose_file), "up", "-d"],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to start container: {e.stderr}")
            raise

        # Wait for container to be healthy
        self._wait_for_database()

    def stop_container(self, remove_volumes: bool = False) -> None:
        """Stop the test database container.

        Args:
            remove_volumes: If True, also remove the volumes (for clean slate)
        """
        if not self.is_container_running():
            return

        logger.info("Stopping test database container...")
        try:
            cmd = ["docker-compose", "-f", str(self.compose_file), "down"]
            if remove_volumes:
                cmd.append("-v")
                logger.info("Also removing volumes for clean slate")

            subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to stop container: {e.stderr}")

    def _wait_for_database(self) -> None:
        """Wait for the database to be ready to accept connections."""
        database_url = "postgresql://test_user:test_pass@localhost:5433/hiro_test"

        logger.info("Waiting for database to be ready...")
        start_time = time.time()

        while time.time() - start_time < self.max_wait_seconds:
            try:
                # Try to connect using synchronous engine (for simplicity in waiting)
                engine = create_engine(database_url)
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                engine.dispose()
                logger.info("Database is ready!")
                return
            except Exception:
                time.sleep(1)
                continue

        raise TimeoutError(
            f"Database did not become ready within {self.max_wait_seconds} seconds"
        )

    def cleanup_container(self) -> None:
        """Stop and remove the container and its volumes."""
        logger.info("Cleaning up test database container and volumes...")
        try:
            subprocess.run(
                ["docker-compose", "-f", str(self.compose_file), "down", "-v"],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to cleanup container: {e.stderr}")


# Global Docker manager instance
_docker_manager: DockerTestDatabase | None = None


@pytest.fixture(scope="session", autouse=True)
def docker_test_db():
    """Automatically manage Docker test database for all tests.

    This fixture:
    1. Starts the test database container at the beginning of the test session
    2. Keeps it running for all tests
    3. Optionally stops it at the end (based on KEEP_TEST_DB env var)
    """
    global _docker_manager

    print("Docker fixture: Starting...")

    # Skip if explicitly disabled
    if os.getenv("SKIP_DOCKER_TESTS") == "1":
        print("Docker fixture: Skipping (SKIP_DOCKER_TESTS=1)")
        yield
        return

    # Check if Docker is available
    try:
        subprocess.run(["docker", "--version"], capture_output=True, check=True)
        print("Docker fixture: Docker is available")
    except (subprocess.SubprocessError, FileNotFoundError):
        print("Docker fixture: Docker not available, skipping")
        yield
        return

    # Initialize and start container
    _docker_manager = DockerTestDatabase()

    try:
        # Always start with fresh volume for test isolation
        print("Docker fixture: Cleaning up any existing container...")
        _docker_manager.stop_container(remove_volumes=True)

        print("Docker fixture: Starting fresh container...")
        _docker_manager.start_container()
        print("Docker fixture: Container started successfully")
        yield _docker_manager
    finally:
        # Only stop if not keeping for development
        if os.getenv("KEEP_TEST_DB") != "1":
            print("Docker fixture: Stopping container and removing volume...")
            _docker_manager.stop_container(remove_volumes=True)
        else:
            print("Docker fixture: Keeping test database running (KEEP_TEST_DB=1)")


@pytest.fixture
def ensure_test_db(docker_test_db):
    """Ensure test database is available for a specific test.

    Use this fixture in tests that require database access to make
    the dependency explicit.
    """
    if docker_test_db is None:
        pytest.skip("Test database not available")
    return docker_test_db


@pytest_asyncio.fixture
async def wait_for_db():
    """Async fixture to ensure database is ready."""
    # Give a moment for any container operations to complete
    await asyncio.sleep(0.1)
    return True
