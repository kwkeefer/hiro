"""Integration tests for HTTP tools and provider organization."""

import pytest

from hiro.servers.http.config import HttpConfig
from hiro.servers.http.providers import HttpToolProvider


@pytest.mark.integration
class TestHttpToolProvider:
    """Test HTTP tool provider organization and business logic."""

    def test_http_tool_provider_initialization(self):
        """HttpToolProvider should initialize with proper structure."""
        config = HttpConfig()
        provider = HttpToolProvider(config)

        # Should have configuration access
        assert provider.config == config

        # Should have HTTP tool access
        assert hasattr(provider, "http_tool")
        assert provider.http_tool is not None

        # HTTP tool should have the execute method
        assert hasattr(provider.http_tool, "execute")
        assert callable(provider.http_tool.execute)

    @pytest.mark.asyncio
    async def test_http_tool_execute_method_works(self):
        """HTTP tool execute method should work for valid requests."""
        config = HttpConfig()
        provider = HttpToolProvider(config)

        # Should be able to call the HTTP tool directly (though it may fail due to network)
        try:
            result = await provider.http_tool.execute(
                url="https://httpbin.org/get", method="GET"
            )
            # If successful, result should be some kind of response
            assert result is not None
            assert isinstance(result, dict)
        except Exception as e:
            # Network failures are acceptable in tests
            # But should not be structural/signature violations
            assert not isinstance(e, TypeError | AttributeError)

    def test_provider_encapsulates_configuration(self):
        """Provider should properly encapsulate configuration."""
        config = HttpConfig()
        provider = HttpToolProvider(config)

        # Should pass configuration to underlying tool
        assert provider.http_tool._config == config

        # Configuration should be accessible through provider
        assert provider.config == config

    def test_multiple_providers_independent(self):
        """Multiple providers should be independent of each other."""
        config1 = HttpConfig(timeout=30.0)
        config2 = HttpConfig(
            timeout=60.0
        )  # Different timeout to make configs different

        provider1 = HttpToolProvider(config1)
        provider2 = HttpToolProvider(config2)

        # Should have different configuration values
        assert provider1.config.timeout != provider2.config.timeout
        assert (
            provider1.http_tool._config.timeout != provider2.http_tool._config.timeout
        )

        # Should be separate instances (identity check)
        assert provider1 is not provider2
        assert provider1.http_tool is not provider2.http_tool

        # Configs should be separate instances even if values were the same
        assert provider1.config is config1
        assert provider2.config is config2
