"""Unit tests for HttpConfig cookie functionality."""

import json

import pytest

from code_mcp.servers.http.config import HttpConfig


class TestHttpConfigCookies:
    """Test HttpConfig cookie loading functionality."""

    @pytest.mark.unit
    def test_default_initialization(self):
        """Test HttpConfig initializes with empty cookies when no file specified."""
        # Arrange & Act
        config = HttpConfig()

        # Assert
        assert config.default_cookies == {}
        assert config.default_cookies_file is None

    @pytest.mark.unit
    def test_cookie_file_loading_success(self, tmp_path):
        """Test successful loading of cookies from JSON file."""
        # Arrange
        cookie_data = {"session_id": "abc123", "auth_token": "token456"}
        cookie_file = tmp_path / "cookies.json"
        cookie_file.write_text(json.dumps(cookie_data))

        # Act
        config = HttpConfig(default_cookies_file=str(cookie_file))

        # Assert
        assert config.default_cookies == cookie_data

    @pytest.mark.unit
    def test_cookie_file_not_found(self, tmp_path):
        """Test graceful handling when cookie file doesn't exist."""
        # Arrange
        nonexistent_file = tmp_path / "missing.json"

        # Act
        config = HttpConfig(default_cookies_file=str(nonexistent_file))

        # Assert
        assert config.default_cookies == {}

    @pytest.mark.unit
    def test_cookie_file_invalid_json(self, tmp_path):
        """Test graceful handling of invalid JSON in cookie file."""
        # Arrange
        cookie_file = tmp_path / "bad.json"
        cookie_file.write_text("invalid json content {")

        # Act
        config = HttpConfig(default_cookies_file=str(cookie_file))

        # Assert
        assert config.default_cookies == {}

    @pytest.mark.unit
    def test_cookie_file_non_dict_json(self, tmp_path):
        """Test handling when JSON file contains non-dictionary data."""
        # Arrange
        cookie_file = tmp_path / "array.json"
        cookie_file.write_text(json.dumps(["not", "a", "dict"]))

        # Act
        config = HttpConfig(default_cookies_file=str(cookie_file))

        # Assert
        assert config.default_cookies == {}

    @pytest.mark.unit
    def test_cookie_values_converted_to_strings(self, tmp_path):
        """Test that cookie values are converted to strings."""
        # Arrange
        cookie_data = {"count": 123, "enabled": True, "name": "test"}
        cookie_file = tmp_path / "cookies.json"
        cookie_file.write_text(json.dumps(cookie_data))

        # Act
        config = HttpConfig(default_cookies_file=str(cookie_file))

        # Assert
        expected = {"count": "123", "enabled": "True", "name": "test"}
        assert config.default_cookies == expected

    @pytest.mark.unit
    def test_direct_cookies_initialization(self):
        """Test initializing with cookies directly instead of file."""
        # Arrange
        cookies = {"direct": "cookie", "test": "value"}

        # Act
        config = HttpConfig(default_cookies=cookies)

        # Assert
        assert config.default_cookies == cookies
        assert config.default_cookies_file is None

    @pytest.mark.unit
    def test_cookie_file_overrides_direct_cookies(self, tmp_path):
        """Test that cookie file takes precedence over direct cookies."""
        # Arrange
        direct_cookies = {"direct": "cookie"}
        file_cookies = {"file": "cookie"}
        cookie_file = tmp_path / "cookies.json"
        cookie_file.write_text(json.dumps(file_cookies))

        # Act
        config = HttpConfig(
            default_cookies=direct_cookies, default_cookies_file=str(cookie_file)
        )

        # Assert
        assert config.default_cookies == file_cookies
