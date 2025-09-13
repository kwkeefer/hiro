"""Unit tests for HTTP server configuration."""

import pytest

from hiro.servers.http.config import HttpConfig


class TestHttpConfig:
    """Test HTTP configuration handling."""

    @pytest.mark.unit
    def test_default_initialization(self):
        """Test HttpConfig with default values."""
        # Arrange / Act
        config = HttpConfig()

        # Assert
        assert config.proxy_url is None
        assert config.timeout == 30.0
        assert config.verify_ssl is True
        assert config.logging_enabled is True
        assert config.max_request_body_size == 1024 * 1024
        assert config.max_response_body_size == 1024 * 1024
        assert config.sensitive_headers == []
        assert config.cookie_sessions_enabled is True
        assert config.cookie_sessions_config is None
        assert config.cookie_cache_ttl == 60

    @pytest.mark.unit
    def test_custom_configuration(self):
        """Test HttpConfig with custom values."""
        # Arrange
        custom_proxy = "http://proxy.example.com:8080"
        custom_timeout = 60.0
        custom_headers = {"X-Custom": "header", "X-Trace": "12345"}
        sensitive_list = ["Authorization", "X-API-Key"]

        # Act
        config = HttpConfig(
            proxy_url=custom_proxy,
            timeout=custom_timeout,
            verify_ssl=False,
            tracing_headers=custom_headers,
            logging_enabled=False,
            max_request_body_size=2048,
            max_response_body_size=4096,
            sensitive_headers=sensitive_list,
            cookie_sessions_enabled=False,
            cookie_sessions_config="/custom/path.yaml",
            cookie_cache_ttl=120,
        )

        # Assert
        assert config.proxy_url == custom_proxy
        assert config.timeout == custom_timeout
        assert config.verify_ssl is False
        assert config.tracing_headers == custom_headers
        assert config.logging_enabled is False
        assert config.max_request_body_size == 2048
        assert config.max_response_body_size == 4096
        assert config.sensitive_headers == sensitive_list
        assert config.cookie_sessions_enabled is False
        assert config.cookie_sessions_config == "/custom/path.yaml"
        assert config.cookie_cache_ttl == 120

    @pytest.mark.unit
    def test_tracing_headers_initialization(self):
        """Test default tracing headers are set correctly."""
        # Arrange / Act
        config = HttpConfig()

        # Assert
        assert config.tracing_headers is not None
        assert "User-Agent" in config.tracing_headers
        assert config.tracing_headers["User-Agent"] == "hiro-http-server/0.1.0"
        assert "X-MCP-Source" in config.tracing_headers
        assert config.tracing_headers["X-MCP-Source"] == "hiro"

    @pytest.mark.unit
    def test_tracing_headers_custom_override(self):
        """Test that custom tracing headers override defaults."""
        # Arrange
        custom_headers = {"User-Agent": "custom-agent/2.0", "X-Request-ID": "abc123"}

        # Act
        config = HttpConfig(tracing_headers=custom_headers)

        # Assert
        assert config.tracing_headers == custom_headers
        assert config.tracing_headers["User-Agent"] == "custom-agent/2.0"
        assert "X-Request-ID" in config.tracing_headers
        assert "X-MCP-Source" not in config.tracing_headers

    @pytest.mark.unit
    def test_sensitive_headers_default(self):
        """Test that sensitive headers list is empty by default."""
        # Arrange / Act
        config = HttpConfig()

        # Assert
        assert config.sensitive_headers == []

    @pytest.mark.unit
    def test_dataclass_functionality(self):
        """Test dataclass features work correctly."""
        # Arrange
        config1 = HttpConfig(proxy_url="http://proxy1.com")
        config2 = HttpConfig(proxy_url="http://proxy1.com")
        config3 = HttpConfig(proxy_url="http://proxy2.com")

        # Act / Assert
        # Test equality
        assert config1 == config2
        assert config1 != config3

        # Test representation
        repr_str = repr(config1)
        assert "HttpConfig" in repr_str
        assert "proxy_url='http://proxy1.com'" in repr_str

    @pytest.mark.unit
    def test_post_init_with_none_tracing_headers(self):
        """Test post_init sets default headers when None provided."""
        # Arrange / Act
        config = HttpConfig(tracing_headers=None)

        # Assert
        assert config.tracing_headers is not None
        assert len(config.tracing_headers) == 2
        assert "User-Agent" in config.tracing_headers
        assert "X-MCP-Source" in config.tracing_headers

    @pytest.mark.unit
    def test_post_init_with_none_sensitive_headers(self):
        """Test post_init sets empty list when None provided."""
        # Arrange / Act
        config = HttpConfig(sensitive_headers=None)

        # Assert
        assert config.sensitive_headers == []

    @pytest.mark.unit
    def test_cookie_session_configuration(self):
        """Test cookie session related configuration."""
        # Arrange / Act
        config = HttpConfig(
            cookie_sessions_enabled=True,
            cookie_sessions_config="/path/to/sessions.yaml",
            cookie_cache_ttl=300,
        )

        # Assert
        assert config.cookie_sessions_enabled is True
        assert config.cookie_sessions_config == "/path/to/sessions.yaml"
        assert config.cookie_cache_ttl == 300

    @pytest.mark.unit
    def test_body_size_limits(self):
        """Test request and response body size limits."""
        # Arrange
        mb = 1024 * 1024

        # Act
        config = HttpConfig(
            max_request_body_size=5 * mb, max_response_body_size=10 * mb
        )

        # Assert
        assert config.max_request_body_size == 5 * mb
        assert config.max_response_body_size == 10 * mb
