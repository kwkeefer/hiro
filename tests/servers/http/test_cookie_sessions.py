"""Unit tests for cookie session management."""

import json
import string
import tempfile
import time
from pathlib import Path
from unittest import mock

import pytest
import yaml

from hiro.core.mcp.exceptions import ResourceError
from hiro.servers.http.cookie_sessions import (
    SESSION_NAME_ALLOWED_CHARS,
    CookieSession,
    CookieSessionProvider,
)


class TestCookieSession:
    """Test CookieSession class functionality."""

    @pytest.mark.unit
    def test_session_initialization(self):
        """Test basic session initialization."""
        # Arrange
        name = "test_session"
        description = "Test session"
        cookie_file = Path("/tmp/cookies.json")
        cache_ttl = 120
        metadata = {"domain": "example.com"}

        # Act
        session = CookieSession(
            name=name,
            description=description,
            cookie_file=cookie_file,
            cache_ttl=cache_ttl,
            metadata=metadata,
        )

        # Assert
        assert session.name == name
        assert session.description == description
        assert session.cookie_file == cookie_file
        assert session.cache_ttl == cache_ttl
        assert session.metadata == metadata
        assert session._cached_cookies is None
        assert session._cache_timestamp == 0

    @pytest.mark.unit
    def test_expand_cookie_path_absolute(self):
        """Test path expansion for absolute paths."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            absolute_path = Path(tmpdir) / "cookies.json"
            session = CookieSession(
                name="test", description="Test", cookie_file=absolute_path
            )

            # Act
            result = session.expand_cookie_path()

            # Assert
            assert result == absolute_path.resolve()

    @pytest.mark.unit
    def test_expand_cookie_path_home_relative(self):
        """Test path expansion for ~ paths."""
        # Arrange
        session = CookieSession(
            name="test", description="Test", cookie_file=Path("~/test/cookies.json")
        )

        # Act
        result = session.expand_cookie_path()

        # Assert
        assert str(result).startswith(str(Path.home()))
        assert result.name == "cookies.json"

    @pytest.mark.unit
    def test_expand_cookie_path_traversal_blocked(self):
        """Test that path traversal attempts are blocked."""
        # Arrange
        # Try to access /etc/passwd using an absolute path
        session = CookieSession(
            name="test",
            description="Test",
            cookie_file=Path("/etc/passwd"),  # Absolute path outside allowed dirs
        )

        # Act & Assert
        with pytest.raises(ValueError, match="outside allowed directories"):
            session.expand_cookie_path()

    @pytest.mark.unit
    def test_get_cookies_file_not_found(self):
        """Test handling of missing cookie file."""
        # Arrange
        # Use a path within home directory that doesn't exist
        nonexistent_path = (
            Path.home() / ".config" / "test" / "nonexistent" / "cookies.json"
        )
        session = CookieSession(
            name="test", description="Test", cookie_file=nonexistent_path
        )

        # Act
        result = session.get_cookies()

        # Assert
        assert result["cookies"] == {}
        assert result["error"] == "Cookie file not found"
        assert result["session_name"] == "test"

    @pytest.mark.unit
    def test_get_cookies_invalid_permissions(self):
        """Test that files with invalid permissions are rejected."""
        # Arrange
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"test": "cookie"}, f)
            cookie_file = Path(f.name)

        try:
            # Set insecure permissions
            cookie_file.chmod(0o644)

            session = CookieSession(
                name="test", description="Test", cookie_file=cookie_file
            )

            # Act
            result = session.get_cookies()

            # Assert
            assert result["cookies"] == {}
            assert "insecure permissions" in result["error"]

        finally:
            cookie_file.unlink()

    @pytest.mark.unit
    def test_get_cookies_valid_file(self):
        """Test successful cookie loading."""
        # Arrange
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            test_cookies = {"session_id": "abc123", "token": "xyz789"}
            json.dump(test_cookies, f)
            cookie_file = Path(f.name)

        try:
            # Set secure permissions
            cookie_file.chmod(0o600)

            session = CookieSession(
                name="test", description="Test", cookie_file=cookie_file, cache_ttl=60
            )

            # Act
            result = session.get_cookies()

            # Assert
            assert result["cookies"] == test_cookies
            assert result["session_name"] == "test"
            assert not result["from_cache"]
            assert "error" not in result
            assert "file_modified" in result

        finally:
            cookie_file.unlink()

    @pytest.mark.unit
    def test_get_cookies_caching(self):
        """Test that cookies are cached properly."""
        # Arrange
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            test_cookies = {"cached": "value"}
            json.dump(test_cookies, f)
            cookie_file = Path(f.name)

        try:
            cookie_file.chmod(0o600)

            session = CookieSession(
                name="test", description="Test", cookie_file=cookie_file, cache_ttl=60
            )

            # Act
            result1 = session.get_cookies()
            result2 = session.get_cookies()

            # Assert
            assert not result1["from_cache"]
            assert result2["from_cache"]
            assert result1["cookies"] == result2["cookies"]

        finally:
            cookie_file.unlink()

    @pytest.mark.unit
    def test_get_cookies_cache_expiry(self):
        """Test that cache expires after TTL."""
        # Arrange
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            test_cookies = {"expiry": "test"}
            json.dump(test_cookies, f)
            cookie_file = Path(f.name)

        try:
            cookie_file.chmod(0o600)

            session = CookieSession(
                name="test",
                description="Test",
                cookie_file=cookie_file,
                cache_ttl=0,  # Immediate expiry
            )

            # Act
            result1 = session.get_cookies()
            time.sleep(0.1)  # Wait longer than TTL
            result2 = session.get_cookies()

            # Assert
            assert not result1["from_cache"]
            assert not result2["from_cache"]  # Should re-read from file

        finally:
            cookie_file.unlink()

    @pytest.mark.unit
    def test_get_cookies_invalid_json(self):
        """Test handling of invalid JSON in cookie file."""
        # Arrange
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not valid json{")
            cookie_file = Path(f.name)

        try:
            cookie_file.chmod(0o600)

            session = CookieSession(
                name="test", description="Test", cookie_file=cookie_file
            )

            # Act
            result = session.get_cookies()

            # Assert
            assert result["cookies"] == {}
            assert "Invalid JSON" in result["error"]

        finally:
            cookie_file.unlink()


class TestCookieSessionProvider:
    """Test CookieSessionProvider class functionality."""

    @pytest.mark.unit
    def test_provider_initialization_default_path(self):
        """Test provider initialization with default config path."""
        # Arrange & Act
        with mock.patch(
            "hiro.servers.http.cookie_sessions.get_cookie_sessions_config_path"
        ) as mock_path:
            mock_path.return_value = Path("/mock/config.yaml")
            provider = CookieSessionProvider()

        # Assert
        assert provider.config_path == Path("/mock/config.yaml")
        assert provider.sessions == {}
        assert provider._config_mtime == 0

    @pytest.mark.unit
    def test_provider_initialization_custom_path(self):
        """Test provider initialization with custom config path."""
        # Arrange
        custom_path = Path("/custom/config.yaml")

        # Act
        provider = CookieSessionProvider(custom_path)

        # Assert
        assert provider.config_path == custom_path

    @pytest.mark.unit
    def test_validate_session_name_valid(self):
        """Test session name validation with valid names."""
        # Arrange
        provider = CookieSessionProvider(Path("/mock/config.yaml"))
        valid_names = [
            "simple",
            "with_underscore",
            "with-hyphen",
            "MixedCase123",
            "a",  # Single character
            "very_long_name_with_many_characters_123",
        ]

        # Act & Assert
        for name in valid_names:
            assert provider._validate_session_name(name), f"'{name}' should be valid"

    @pytest.mark.unit
    def test_validate_session_name_invalid(self):
        """Test session name validation with invalid names."""
        # Arrange
        provider = CookieSessionProvider(Path("/mock/config.yaml"))
        invalid_names = [
            "",  # Empty
            "with spaces",
            "with/slash",
            "with\\backslash",
            "with.dot",
            "with@special",
            "../traversal",
            "emoji😀",
        ]

        # Act & Assert
        for name in invalid_names:
            assert not provider._validate_session_name(
                name
            ), f"'{name}' should be invalid"

    @pytest.mark.unit
    def test_allowed_characters_constant(self):
        """Test that SESSION_NAME_ALLOWED_CHARS contains expected characters."""
        # Arrange
        expected_chars = set(string.ascii_letters + string.digits + "_-")

        # Act & Assert
        assert expected_chars == SESSION_NAME_ALLOWED_CHARS

    @pytest.mark.unit
    def test_load_configuration_missing_file(self):
        """Test configuration loading when file doesn't exist."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "nonexistent.yaml"
            provider = CookieSessionProvider(config_path)

            # Act
            provider._load_configuration()

            # Assert
            assert provider.sessions == {}
            assert provider._config_mtime == 0

    @pytest.mark.unit
    def test_load_configuration_valid_sessions(self):
        """Test loading valid session configurations."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            cookie_file = Path(tmpdir) / "cookies.json"

            # Create cookie file with proper permissions
            with cookie_file.open("w") as f:
                json.dump({"test": "cookie"}, f)
            cookie_file.chmod(0o600)

            config = {
                "version": "1.0",
                "sessions": {
                    "test_session": {
                        "description": "Test session",
                        "cookie_file": str(cookie_file),
                        "cache_ttl": 120,
                        "metadata": {"domain": "example.com"},
                    }
                },
            }

            with config_path.open("w") as f:
                yaml.dump(config, f)

            provider = CookieSessionProvider(config_path)

            # Act
            provider._load_configuration()

            # Assert
            assert "test_session" in provider.sessions
            session = provider.sessions["test_session"]
            assert session.name == "test_session"
            assert session.description == "Test session"
            assert session.cache_ttl == 120

    @pytest.mark.unit
    def test_load_configuration_invalid_session_name(self):
        """Test that sessions with invalid names are rejected."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"

            config = {
                "version": "1.0",
                "sessions": {
                    "invalid name with spaces": {
                        "description": "Invalid session",
                        "cookie_file": "/tmp/cookies.json",
                    }
                },
            }

            with config_path.open("w") as f:
                yaml.dump(config, f)

            provider = CookieSessionProvider(config_path)

            # Act
            provider._load_configuration()

            # Assert
            assert len(provider.sessions) == 0

    @pytest.mark.unit
    def test_get_resources_returns_session_list(self):
        """Test that get_resources returns proper resource definitions."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"

            config = {
                "version": "1.0",
                "sessions": {
                    "session1": {
                        "description": "First session",
                        "cookie_file": "/tmp/s1.json",
                    },
                    "session2": {
                        "description": "Second session",
                        "cookie_file": "/tmp/s2.json",
                    },
                },
            }

            with config_path.open("w") as f:
                yaml.dump(config, f)

            provider = CookieSessionProvider(config_path)

            # Act
            resources = provider.get_resources()

            # Assert
            assert len(resources) == 2

            # Check first resource
            assert resources[0]["uri"] == "cookie-session://session1"
            assert resources[0]["name"] == "Cookie Session: session1"
            assert resources[0]["description"] == "First session"
            assert resources[0]["mimeType"] == "application/json"

    @pytest.mark.unit
    async def test_get_resource_invalid_uri(self):
        """Test get_resource with invalid URI format."""
        # Arrange
        provider = CookieSessionProvider(Path("/mock/config.yaml"))

        # Act & Assert
        with pytest.raises(ResourceError, match="Invalid cookie session URI"):
            await provider.get_resource("invalid://uri")

    @pytest.mark.unit
    async def test_get_resource_missing_session(self):
        """Test get_resource with non-existent session."""
        # Arrange
        provider = CookieSessionProvider(Path("/mock/config.yaml"))

        # Act & Assert
        with pytest.raises(ResourceError, match="Cookie session not found"):
            await provider.get_resource("cookie-session://nonexistent")

    @pytest.mark.unit
    def test_clear_cache(self):
        """Test that clear_cache removes all cached data."""
        # Arrange
        provider = CookieSessionProvider(Path("/mock/config.yaml"))

        # Create mock sessions with cache
        session1 = CookieSession("s1", "Session 1", Path("/tmp/s1.json"))
        session1._cached_cookies = {"test": "data"}
        session1._cache_timestamp = time.time()

        session2 = CookieSession("s2", "Session 2", Path("/tmp/s2.json"))
        session2._cached_cookies = {"other": "data"}
        session2._cache_timestamp = time.time()

        provider.sessions = {"s1": session1, "s2": session2}

        # Act
        provider.clear_cache()

        # Assert
        assert session1._cached_cookies is None
        assert session1._cache_timestamp == 0
        assert session2._cached_cookies is None
        assert session2._cache_timestamp == 0

    @pytest.mark.unit
    def test_cleanup_expired_cache(self):
        """Test that cleanup_expired_cache only removes expired entries."""
        # Arrange
        provider = CookieSessionProvider(Path("/mock/config.yaml"))
        current_time = time.time()

        # Create sessions with different cache states
        expired_session = CookieSession(
            "expired", "Expired", Path("/tmp/e.json"), cache_ttl=10
        )
        expired_session._cached_cookies = {"old": "data"}
        expired_session._cache_timestamp = current_time - 20  # Expired

        valid_session = CookieSession(
            "valid", "Valid", Path("/tmp/v.json"), cache_ttl=60
        )
        valid_session._cached_cookies = {"fresh": "data"}
        valid_session._cache_timestamp = current_time - 10  # Still valid

        provider.sessions = {"expired": expired_session, "valid": valid_session}

        # Act
        provider.cleanup_expired_cache()

        # Assert
        assert expired_session._cached_cookies is None
        assert expired_session._cache_timestamp == 0
        assert valid_session._cached_cookies == {"fresh": "data"}
        assert valid_session._cache_timestamp == current_time - 10
