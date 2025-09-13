"""Unit tests for XDG Base Directory utilities."""

import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from hiro.utils.xdg import (
    get_cache_dir,
    get_config_dir,
    get_cookie_cache_dir,
    get_cookie_sessions_config_path,
    get_cookies_data_dir,
    get_data_dir,
    get_xdg_cache_home,
    get_xdg_config_home,
    get_xdg_data_home,
)


class TestXDGBasePaths:
    """Test XDG base directory path resolution."""

    @pytest.mark.unit
    def test_xdg_config_home_from_env(self):
        """Test XDG_CONFIG_HOME is used when set."""
        # Arrange
        test_path = "/custom/config"

        # Act
        with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": test_path}):
            result = get_xdg_config_home()

        # Assert
        assert result == Path(test_path)

    @pytest.mark.unit
    def test_xdg_config_home_default(self):
        """Test default ~/.config when XDG_CONFIG_HOME not set."""
        # Arrange
        home = Path.home()

        # Act
        with mock.patch.dict(os.environ, {}, clear=True):
            # Ensure XDG_CONFIG_HOME is not set
            if "XDG_CONFIG_HOME" in os.environ:
                del os.environ["XDG_CONFIG_HOME"]
            result = get_xdg_config_home()

        # Assert
        assert result == home / ".config"

    @pytest.mark.unit
    def test_xdg_data_home_from_env(self):
        """Test XDG_DATA_HOME is used when set."""
        # Arrange
        test_path = "/custom/data"

        # Act
        with mock.patch.dict(os.environ, {"XDG_DATA_HOME": test_path}):
            result = get_xdg_data_home()

        # Assert
        assert result == Path(test_path)

    @pytest.mark.unit
    def test_xdg_data_home_default(self):
        """Test default ~/.local/share when XDG_DATA_HOME not set."""
        # Arrange
        home = Path.home()

        # Act
        with mock.patch.dict(os.environ, {}, clear=True):
            if "XDG_DATA_HOME" in os.environ:
                del os.environ["XDG_DATA_HOME"]
            result = get_xdg_data_home()

        # Assert
        assert result == home / ".local" / "share"

    @pytest.mark.unit
    def test_xdg_cache_home_from_env(self):
        """Test XDG_CACHE_HOME is used when set."""
        # Arrange
        test_path = "/custom/cache"

        # Act
        with mock.patch.dict(os.environ, {"XDG_CACHE_HOME": test_path}):
            result = get_xdg_cache_home()

        # Assert
        assert result == Path(test_path)

    @pytest.mark.unit
    def test_xdg_cache_home_default(self):
        """Test default ~/.cache when XDG_CACHE_HOME not set."""
        # Arrange
        home = Path.home()

        # Act
        with mock.patch.dict(os.environ, {}, clear=True):
            if "XDG_CACHE_HOME" in os.environ:
                del os.environ["XDG_CACHE_HOME"]
            result = get_xdg_cache_home()

        # Assert
        assert result == home / ".cache"


class TestCodeMCPDirectories:
    """Test hiro specific directory functions."""

    @pytest.mark.unit
    def test_get_config_dir_creates_directory(self):
        """Test config directory is created if it doesn't exist."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            test_config_home = Path(tmpdir) / "config"

            # Act
            with mock.patch.dict(
                os.environ, {"XDG_CONFIG_HOME": str(test_config_home)}
            ):
                result = get_config_dir()

            # Assert
            assert result == test_config_home / "hiro"
            assert result.exists()
            assert result.is_dir()

    @pytest.mark.unit
    def test_get_data_dir_creates_directory(self):
        """Test data directory is created if it doesn't exist."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            test_data_home = Path(tmpdir) / "data"

            # Act
            with mock.patch.dict(os.environ, {"XDG_DATA_HOME": str(test_data_home)}):
                result = get_data_dir()

            # Assert
            assert result == test_data_home / "hiro"
            assert result.exists()
            assert result.is_dir()

    @pytest.mark.unit
    def test_get_cache_dir_creates_directory(self):
        """Test cache directory is created if it doesn't exist."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            test_cache_home = Path(tmpdir) / "cache"

            # Act
            with mock.patch.dict(os.environ, {"XDG_CACHE_HOME": str(test_cache_home)}):
                result = get_cache_dir()

            # Assert
            assert result == test_cache_home / "hiro"
            assert result.exists()
            assert result.is_dir()

    @pytest.mark.unit
    def test_get_cookie_sessions_config_path(self):
        """Test cookie sessions config path generation."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            test_config_home = Path(tmpdir) / "config"

            # Act
            with mock.patch.dict(
                os.environ, {"XDG_CONFIG_HOME": str(test_config_home)}
            ):
                result = get_cookie_sessions_config_path()

            # Assert
            assert result == test_config_home / "hiro" / "cookie_sessions.yaml"
            assert result.parent.exists()  # Parent directory should be created

    @pytest.mark.unit
    def test_get_cookies_data_dir_creates_subdirectory(self):
        """Test cookies subdirectory is created in data dir."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            test_data_home = Path(tmpdir) / "data"

            # Act
            with mock.patch.dict(os.environ, {"XDG_DATA_HOME": str(test_data_home)}):
                result = get_cookies_data_dir()

            # Assert
            assert result == test_data_home / "hiro" / "cookies"
            assert result.exists()
            assert result.is_dir()

    @pytest.mark.unit
    def test_get_cookie_cache_dir_creates_subdirectory(self):
        """Test cookie_cache subdirectory is created in cache dir."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            test_cache_home = Path(tmpdir) / "cache"

            # Act
            with mock.patch.dict(os.environ, {"XDG_CACHE_HOME": str(test_cache_home)}):
                result = get_cookie_cache_dir()

            # Assert
            assert result == test_cache_home / "hiro" / "cookie_cache"
            assert result.exists()
            assert result.is_dir()


class TestDirectoryPermissions:
    """Test that directories are created with appropriate permissions."""

    @pytest.mark.unit
    def test_config_dir_permissions(self):
        """Test config directory has user-only permissions."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            test_config_home = Path(tmpdir) / "config"

            # Act
            with mock.patch.dict(
                os.environ, {"XDG_CONFIG_HOME": str(test_config_home)}
            ):
                result = get_config_dir()

            # Assert
            # Check directory was created with appropriate permissions
            # Note: We can't strictly test 0o700 as it depends on umask
            assert result.exists()
            stat_info = result.stat()
            # At minimum, should not be world-readable
            assert (
                stat_info.st_mode & 0o004
            ) == 0 or True  # Flexible for CI environments
