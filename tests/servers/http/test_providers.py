"""Unit tests for HTTP tool providers."""

from unittest.mock import MagicMock

import pytest

from hiro.servers.http.config import HttpConfig
from hiro.servers.http.providers import HttpToolProvider
from hiro.servers.http.tools import HttpRequestTool


class TestHttpToolProvider:
    """Test HTTP tool provider functionality."""

    @pytest.mark.unit
    def test_initialization_without_repositories(self):
        """Test provider initialization without database repositories."""
        # Arrange
        config = HttpConfig()

        # Act
        provider = HttpToolProvider(config)

        # Assert
        assert provider._config == config
        assert provider._http_repo is None
        assert provider._target_repo is None
        assert provider._mission_id is None
        assert isinstance(provider._http_tool, HttpRequestTool)

    @pytest.mark.unit
    def test_initialization_with_repositories(self):
        """Test provider initialization with database repositories."""
        # Arrange
        config = HttpConfig()
        mock_http_repo = MagicMock()
        mock_target_repo = MagicMock()
        mission_id = "test-session-123"

        # Act
        provider = HttpToolProvider(
            config=config,
            http_repo=mock_http_repo,
            target_repo=mock_target_repo,
            mission_id=mission_id,
        )

        # Assert
        assert provider._config == config
        assert provider._http_repo == mock_http_repo
        assert provider._target_repo == mock_target_repo
        assert provider._mission_id == mission_id
        assert isinstance(provider._http_tool, HttpRequestTool)

    @pytest.mark.unit
    def test_config_property_access(self):
        """Test accessing configuration through property."""
        # Arrange
        config = HttpConfig(proxy_url="http://proxy.test:8080", timeout=60.0)

        # Act
        provider = HttpToolProvider(config)

        # Assert
        assert provider.config == config
        assert provider.config.proxy_url == "http://proxy.test:8080"
        assert provider.config.timeout == 60.0

    @pytest.mark.unit
    def test_http_tool_property_access(self):
        """Test accessing HTTP tool through property."""
        # Arrange
        config = HttpConfig()
        provider = HttpToolProvider(config)

        # Act
        tool = provider.http_tool

        # Assert
        assert isinstance(tool, HttpRequestTool)
        assert tool._config == config
        assert tool is provider._http_tool  # Same instance

    @pytest.mark.unit
    def test_tool_inherits_provider_configuration(self):
        """Test that the tool inherits provider's configuration."""
        # Arrange
        config = HttpConfig(
            proxy_url="http://configured.proxy:3128",
            verify_ssl=False,
            tracing_headers={"X-Custom": "header"},
        )
        mock_http_repo = MagicMock()
        mission_id = "session-456"

        # Act
        provider = HttpToolProvider(
            config=config, http_repo=mock_http_repo, mission_id=mission_id
        )

        # Assert
        tool = provider.http_tool
        assert tool._config.proxy_url == "http://configured.proxy:3128"
        assert tool._config.verify_ssl is False
        assert tool._config.tracing_headers == {"X-Custom": "header"}
        assert tool._http_repo == mock_http_repo
        assert tool._mission_id == mission_id

    @pytest.mark.unit
    def test_multiple_providers_independent(self):
        """Test that multiple providers maintain independent configurations."""
        # Arrange
        config1 = HttpConfig(proxy_url="http://proxy1.test:8080")
        config2 = HttpConfig(proxy_url="http://proxy2.test:8080")

        # Act
        provider1 = HttpToolProvider(config1)
        provider2 = HttpToolProvider(config2)

        # Assert
        assert provider1.config != provider2.config
        assert provider1.http_tool != provider2.http_tool
        assert provider1.http_tool._config.proxy_url == "http://proxy1.test:8080"
        assert provider2.http_tool._config.proxy_url == "http://proxy2.test:8080"

    @pytest.mark.unit
    def test_provider_with_lazy_repositories(self):
        """Test provider works with lazy repository pattern."""
        # Arrange
        config = HttpConfig()

        # Create mock lazy repositories
        class MockLazyHttpRepo:
            def __init__(self):
                self.initialized = True

        class MockLazyTargetRepo:
            def __init__(self):
                self.initialized = True

        lazy_http_repo = MockLazyHttpRepo()
        lazy_target_repo = MockLazyTargetRepo()

        # Act
        provider = HttpToolProvider(
            config=config, http_repo=lazy_http_repo, target_repo=lazy_target_repo
        )

        # Assert
        assert provider._http_repo == lazy_http_repo
        assert provider._target_repo == lazy_target_repo
        assert provider._http_tool._http_repo == lazy_http_repo
        assert provider._http_tool._target_repo == lazy_target_repo

    @pytest.mark.unit
    def test_provider_configuration_immutability(self):
        """Test that provider configuration remains immutable after creation."""
        # Arrange
        original_config = HttpConfig(timeout=30.0)
        provider = HttpToolProvider(original_config)

        # Act
        # Try to modify the config reference (shouldn't affect provider)
        new_config = HttpConfig(timeout=60.0)
        original_config = new_config  # This doesn't change provider's config

        # Assert
        assert provider.config.timeout == 30.0  # Still original value
        assert provider.http_tool._config.timeout == 30.0

    @pytest.mark.unit
    def test_provider_mission_id_handling(self):
        """Test session ID is properly passed to tool."""
        # Arrange
        config = HttpConfig()
        mission_id = "550e8400-e29b-41d4-a716-446655440000"

        # Act
        provider = HttpToolProvider(config=config, mission_id=mission_id)

        # Assert
        assert provider._mission_id == mission_id
        assert provider.http_tool._mission_id == mission_id

    @pytest.mark.unit
    def test_provider_none_mission_id(self):
        """Test provider handles None session ID correctly."""
        # Arrange
        config = HttpConfig()

        # Act
        provider = HttpToolProvider(config=config, mission_id=None)

        # Assert
        assert provider._mission_id is None
        assert provider.http_tool._mission_id is None
