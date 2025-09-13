"""FastMCP integration tests for cookie session provider.

Tests the cookie session provider through the actual MCP protocol
using FastMCP server instances.
"""

import asyncio
import json
import tempfile
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
import yaml

from hiro.api.mcp.server import FastMcpServerAdapter
from hiro.core.mcp.exceptions import ResourceError
from hiro.servers.http.cookie_sessions import CookieSessionProvider
from tests.utils.mcp_test_helpers import BaseMcpProviderTest, create_test_resource


@pytest.mark.integration
class TestCookieSessionMcpIntegration(BaseMcpProviderTest):
    """Test cookie session provider through MCP protocol."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary directory for test configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def cookie_session_config(self, temp_config_dir):
        """Create a test cookie session configuration."""
        config_path = temp_config_dir / "cookie_sessions.yaml"
        cookies_dir = temp_config_dir / "cookies"
        cookies_dir.mkdir()

        # Create test cookie files
        github_cookies = {"gh_session": "test123", "user": "testuser"}
        github_file = cookies_dir / "github.json"
        with github_file.open("w") as f:
            json.dump(github_cookies, f)
        github_file.chmod(0o600)

        slack_cookies = {"token": "xoxb-test", "workspace_id": "W123"}
        slack_file = cookies_dir / "slack.json"
        with slack_file.open("w") as f:
            json.dump(slack_cookies, f)
        slack_file.chmod(0o600)

        # Create configuration
        config = {
            "version": "1.0",
            "sessions": {
                "github": {
                    "description": "GitHub authentication session",
                    "cookie_file": str(github_file),
                    "cache_ttl": 60,
                    "metadata": {
                        "domains": ["github.com", "api.github.com"],
                        "account": "testuser",
                    },
                },
                "slack": {
                    "description": "Slack workspace session",
                    "cookie_file": str(slack_file),
                    "cache_ttl": 30,
                    "metadata": {"workspace": "test-workspace", "team_id": "T123"},
                },
            },
        }

        with config_path.open("w") as f:
            yaml.dump(config, f)

        return {
            "config_path": config_path,
            "cookies_dir": cookies_dir,
            "github_file": github_file,
            "slack_file": slack_file,
            "github_cookies": github_cookies,
            "slack_cookies": slack_cookies,
        }

    async def test_mcp_resource_listing(self, cookie_session_config):
        """Test listing cookie session resources through MCP."""
        # Arrange
        provider = CookieSessionProvider(cookie_session_config["config_path"])

        async with self.create_test_server(resource_provider=provider) as (server, mcp):
            # Act
            resources = await self.get_resources_from_server(server)

            # Assert
            assert len(resources) == 2

            # Check GitHub resource
            github_resource = next(
                (r for r in resources if r["uri"] == "cookie-session://github"), None
            )
            assert github_resource is not None
            self.assert_resource_valid(github_resource)
            assert github_resource["name"] == "Cookie Session: github"
            assert github_resource["description"] == "GitHub authentication session"
            assert github_resource["mimeType"] == "application/json"

            # Check Slack resource
            slack_resource = next(
                (r for r in resources if r["uri"] == "cookie-session://slack"), None
            )
            assert slack_resource is not None
            self.assert_resource_valid(slack_resource)
            assert slack_resource["name"] == "Cookie Session: slack"
            assert slack_resource["description"] == "Slack workspace session"

    async def test_mcp_resource_reading(self, cookie_session_config):
        """Test reading cookie session resources through MCP."""
        # Arrange
        provider = CookieSessionProvider(cookie_session_config["config_path"])

        async with self.create_test_server(resource_provider=provider) as (server, mcp):
            # Act - Read GitHub session
            github_data = await self.read_resource_from_server(
                server, "cookie-session://github"
            )

            # Assert GitHub data
            self.assert_resource_contents_valid(github_data)
            assert github_data["cookies"] == cookie_session_config["github_cookies"]
            assert github_data["session_name"] == "github"
            assert github_data["description"] == "GitHub authentication session"
            assert github_data["metadata"]["account"] == "testuser"
            assert not github_data["from_cache"]

            # Act - Read Slack session
            slack_data = await self.read_resource_from_server(
                server, "cookie-session://slack"
            )

            # Assert Slack data
            self.assert_resource_contents_valid(slack_data)
            assert slack_data["cookies"] == cookie_session_config["slack_cookies"]
            assert slack_data["session_name"] == "slack"
            assert slack_data["metadata"]["workspace"] == "test-workspace"

    async def test_mcp_resource_caching(self, cookie_session_config):
        """Test that cookie caching works through MCP."""
        # Arrange
        provider = CookieSessionProvider(cookie_session_config["config_path"])

        async with self.create_test_server(resource_provider=provider) as (server, mcp):
            # Act - First read (not cached)
            data1 = await self.read_resource_from_server(
                server, "cookie-session://github"
            )
            assert not data1["from_cache"]

            # Act - Second read (should be cached)
            data2 = await self.read_resource_from_server(
                server, "cookie-session://github"
            )
            assert data2["from_cache"]
            assert data2["cookies"] == data1["cookies"]

    async def test_mcp_resource_update_detection(self, cookie_session_config):
        """Test that cookie file updates are detected through MCP."""
        # Arrange
        provider = CookieSessionProvider(cookie_session_config["config_path"])

        async with self.create_test_server(resource_provider=provider) as (server, mcp):
            # Act - Initial read
            initial_data = await self.read_resource_from_server(
                server, "cookie-session://github"
            )
            assert initial_data["cookies"]["gh_session"] == "test123"

            # Update the cookie file
            updated_cookies = {"gh_session": "updated456", "user": "newuser"}
            with cookie_session_config["github_file"].open("w") as f:
                json.dump(updated_cookies, f)

            # Clear cache to force re-read
            provider.clear_cache()

            # Act - Read after update
            updated_data = await self.read_resource_from_server(
                server, "cookie-session://github"
            )

            # Assert
            assert updated_data["cookies"]["gh_session"] == "updated456"
            assert updated_data["cookies"]["user"] == "newuser"
            assert not updated_data["from_cache"]

    async def test_mcp_config_hot_reload(self, cookie_session_config):
        """Test configuration hot reload through MCP."""
        # Arrange
        provider = CookieSessionProvider(cookie_session_config["config_path"])

        async with self.create_test_server(resource_provider=provider) as (server, mcp):
            # Act - Initial resource list
            initial_resources = await self.get_resources_from_server(server)
            assert len(initial_resources) == 2

            # Add a new session to config
            time.sleep(0.1)  # Ensure different mtime

            new_cookie_file = cookie_session_config["cookies_dir"] / "new.json"
            with new_cookie_file.open("w") as f:
                json.dump({"new_cookie": "value"}, f)
            new_cookie_file.chmod(0o600)

            # Update configuration
            with cookie_session_config["config_path"].open("r") as f:
                config = yaml.safe_load(f)

            config["sessions"]["new_service"] = {
                "description": "New service session",
                "cookie_file": str(new_cookie_file),
                "cache_ttl": 60,
            }

            with cookie_session_config["config_path"].open("w") as f:
                yaml.dump(config, f)

            # Act - Get resources after config update
            updated_resources = await self.get_resources_from_server(server)

            # Assert
            assert len(updated_resources) == 3
            new_resource = next(
                (
                    r
                    for r in updated_resources
                    if r["uri"] == "cookie-session://new_service"
                ),
                None,
            )
            assert new_resource is not None
            assert new_resource["description"] == "New service session"

    async def test_mcp_error_handling(self, cookie_session_config):
        """Test error handling through MCP protocol."""
        # Arrange
        provider = CookieSessionProvider(cookie_session_config["config_path"])

        async with self.create_test_server(resource_provider=provider) as (server, mcp):
            # Test invalid URI
            with pytest.raises(ResourceError, match="Invalid cookie session URI"):
                await provider.get_resource("invalid://uri")

            # Test non-existent session
            with pytest.raises(ResourceError, match="Cookie session not found"):
                await provider.get_resource("cookie-session://nonexistent")

            # Test file with wrong permissions
            bad_file = cookie_session_config["cookies_dir"] / "bad.json"
            with bad_file.open("w") as f:
                json.dump({"bad": "cookie"}, f)
            bad_file.chmod(0o644)  # Wrong permissions

            # Add to config
            with cookie_session_config["config_path"].open("r") as f:
                config = yaml.safe_load(f)

            config["sessions"]["bad_perms"] = {
                "description": "Bad permissions test",
                "cookie_file": str(bad_file),
            }

            with cookie_session_config["config_path"].open("w") as f:
                yaml.dump(config, f)

            # Should load the session but fail when reading
            resources = await self.get_resources_from_server(server)
            bad_resource = next(
                (r for r in resources if r["uri"] == "cookie-session://bad_perms"), None
            )

            if bad_resource:
                # Reading should return error
                data = await self.read_resource_from_server(
                    server, "cookie-session://bad_perms"
                )
                assert data["cookies"] == {}
                assert "insecure permissions" in data["error"]

    async def test_mcp_concurrent_access(self, cookie_session_config):
        """Test concurrent resource access through MCP."""
        # Arrange
        provider = CookieSessionProvider(cookie_session_config["config_path"])

        async with self.create_test_server(resource_provider=provider) as (server, mcp):
            # Act - Concurrent reads
            tasks = []
            for _ in range(10):
                tasks.append(
                    self.read_resource_from_server(server, "cookie-session://github")
                )
                tasks.append(
                    self.read_resource_from_server(server, "cookie-session://slack")
                )

            results = await asyncio.gather(*tasks)

            # Assert - All reads should succeed
            assert len(results) == 20
            for i, result in enumerate(results):
                self.assert_resource_contents_valid(result)
                if i % 2 == 0:
                    assert result["session_name"] == "github"
                else:
                    assert result["session_name"] == "slack"

    async def test_mcp_server_adapter_integration(self, cookie_session_config):
        """Test full integration with FastMcpServerAdapter."""
        # Arrange
        server = FastMcpServerAdapter()
        provider = CookieSessionProvider(cookie_session_config["config_path"])

        # Act - Add provider to server
        server.add_resource_provider(provider)

        # Assert - Provider is registered
        assert provider in server._resource_providers

        # Mock FastMCP instance to verify registration
        mock_mcp = MagicMock()
        mock_mcp.resource = MagicMock()
        server._mcp = mock_mcp

        # Trigger setup
        server._register_resources(provider)

        # Verify resource handler was registered
        assert mock_mcp.resource.called

        # The resource handler should list our sessions
        resources = provider.get_resources()
        assert len(resources) == 2
        assert any(r["uri"] == "cookie-session://github" for r in resources)
        assert any(r["uri"] == "cookie-session://slack" for r in resources)

    async def test_mcp_metadata_preservation(self, cookie_session_config):
        """Test that metadata is preserved through MCP protocol."""
        # Arrange
        provider = CookieSessionProvider(cookie_session_config["config_path"])

        async with self.create_test_server(resource_provider=provider) as (server, mcp):
            # Act
            github_data = await self.read_resource_from_server(
                server, "cookie-session://github"
            )

            # Assert - Check all metadata is preserved
            assert "metadata" in github_data
            metadata = github_data["metadata"]
            assert metadata["domains"] == ["github.com", "api.github.com"]
            assert metadata["account"] == "testuser"

            # Check other fields
            assert "last_updated" in github_data
            assert "file_modified" in github_data
            assert "description" in github_data
            assert github_data["description"] == "GitHub authentication session"


@pytest.mark.integration
class TestMcpHelperReusability(BaseMcpProviderTest):
    """Test that the MCP test helpers are reusable for other providers."""

    class MockResourceProvider:
        """Mock resource provider for testing reusability."""

        def get_resources(self) -> list[dict[str, Any]]:
            return [
                create_test_resource(
                    "mock://resource1",
                    "Mock Resource 1",
                    "text/plain",
                    "First mock resource",
                ),
                create_test_resource(
                    "mock://resource2",
                    "Mock Resource 2",
                    "application/json",
                    "Second mock resource",
                ),
            ]

        async def get_resource(self, uri: str) -> dict[str, Any]:
            if uri == "mock://resource1":
                return {"type": "mock", "data": "resource1"}
            elif uri == "mock://resource2":
                return {"type": "mock", "data": "resource2"}
            raise ValueError(f"Unknown resource: {uri}")

    async def test_reusable_for_other_providers(self):
        """Test that base test class works for other providers."""
        # Arrange
        mock_provider = self.MockResourceProvider()

        async with self.create_test_server(resource_provider=mock_provider) as (
            server,
            mcp,
        ):
            # Act - List resources
            resources = await self.get_resources_from_server(server)

            # Assert
            assert len(resources) == 2
            for resource in resources:
                self.assert_resource_valid(resource)

            # Act - Read resources
            data1 = await self.read_resource_from_server(server, "mock://resource1")
            data2 = await self.read_resource_from_server(server, "mock://resource2")

            # Assert
            self.assert_resource_contents_valid(data1)
            self.assert_resource_contents_valid(data2)
            assert data1["data"] == "resource1"
            assert data2["data"] == "resource2"
