"""Integration tests for cookie session management."""

import asyncio
import json
import tempfile
import time
from pathlib import Path

import pytest
import yaml

from hiro.servers.http.cookie_sessions import CookieSessionProvider


class TestCookieSessionIntegration:
    """Integration tests for cookie session functionality."""

    @pytest.mark.integration
    async def test_end_to_end_cookie_session_flow(self):
        """Test complete flow: config loading, resource listing, and fetching."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            config_file = tmppath / "cookie_sessions.yaml"
            cookies_dir = tmppath / "cookies"
            cookies_dir.mkdir()

            # Create test cookie files
            github_cookies = {"gh_session": "abc123", "user_id": "12345"}
            github_file = cookies_dir / "github.json"
            with github_file.open("w") as f:
                json.dump(github_cookies, f)
            github_file.chmod(0o600)

            slack_cookies = {"slack_token": "xoxb-test", "workspace": "test"}
            slack_file = cookies_dir / "slack.json"
            with slack_file.open("w") as f:
                json.dump(slack_cookies, f)
            slack_file.chmod(0o600)

            # Create configuration
            config = {
                "version": "1.0",
                "sessions": {
                    "github": {
                        "description": "GitHub session",
                        "cookie_file": str(github_file),
                        "cache_ttl": 60,
                        "metadata": {"domains": ["github.com"], "account": "testuser"},
                    },
                    "slack": {
                        "description": "Slack workspace",
                        "cookie_file": str(slack_file),
                        "cache_ttl": 30,
                        "metadata": {"workspace": "test-workspace"},
                    },
                },
            }

            with config_file.open("w") as f:
                yaml.dump(config, f)

            # Act
            provider = CookieSessionProvider(config_file)

            # Test resource listing
            resources = provider.get_resources()

            # Assert resources are listed correctly
            assert len(resources) == 2
            resource_uris = {r["uri"] for r in resources}
            assert "cookie-session://github" in resource_uris
            assert "cookie-session://slack" in resource_uris

            # Test fetching GitHub session
            github_data = await provider.get_resource("cookie-session://github")

            # Assert GitHub data
            assert github_data["cookies"] == github_cookies
            assert github_data["session_name"] == "github"
            assert github_data["description"] == "GitHub session"
            assert github_data["metadata"]["account"] == "testuser"
            assert not github_data["from_cache"]

            # Test fetching from cache
            github_cached = await provider.get_resource("cookie-session://github")
            assert github_cached["from_cache"]
            assert github_cached["cookies"] == github_cookies

            # Test fetching Slack session
            slack_data = await provider.get_resource("cookie-session://slack")
            assert slack_data["cookies"] == slack_cookies
            assert slack_data["metadata"]["workspace"] == "test-workspace"

    @pytest.mark.integration
    async def test_configuration_hot_reload(self):
        """Test that configuration changes are picked up dynamically."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            config_file = tmppath / "cookie_sessions.yaml"
            cookies_dir = tmppath / "cookies"
            cookies_dir.mkdir()

            # Create initial configuration with one session
            cookie_file1 = cookies_dir / "session1.json"
            with cookie_file1.open("w") as f:
                json.dump({"cookie1": "value1"}, f)
            cookie_file1.chmod(0o600)

            config_v1 = {
                "version": "1.0",
                "sessions": {
                    "session1": {
                        "description": "First session",
                        "cookie_file": str(cookie_file1),
                    }
                },
            }

            with config_file.open("w") as f:
                yaml.dump(config_v1, f)

            provider = CookieSessionProvider(config_file)

            # Act - Check initial state
            resources_v1 = provider.get_resources()
            assert len(resources_v1) == 1
            assert resources_v1[0]["uri"] == "cookie-session://session1"

            # Sleep to ensure different mtime
            time.sleep(0.1)

            # Update configuration with additional session
            cookie_file2 = cookies_dir / "session2.json"
            with cookie_file2.open("w") as f:
                json.dump({"cookie2": "value2"}, f)
            cookie_file2.chmod(0o600)

            config_v2 = {
                "version": "1.0",
                "sessions": {
                    "session1": {
                        "description": "First session",
                        "cookie_file": str(cookie_file1),
                    },
                    "session2": {
                        "description": "Second session",
                        "cookie_file": str(cookie_file2),
                    },
                },
            }

            with config_file.open("w") as f:
                yaml.dump(config_v2, f)

            # Check that new configuration is loaded
            resources_v2 = provider.get_resources()

            # Assert
            assert len(resources_v2) == 2
            resource_uris = {r["uri"] for r in resources_v2}
            assert "cookie-session://session1" in resource_uris
            assert "cookie-session://session2" in resource_uris

            # Verify new session works
            session2_data = await provider.get_resource("cookie-session://session2")
            assert session2_data["cookies"] == {"cookie2": "value2"}

    @pytest.mark.integration
    async def test_cookie_file_updates(self):
        """Test that cookie file updates are reflected in fetched data."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            config_file = tmppath / "cookie_sessions.yaml"
            cookie_file = tmppath / "cookies.json"

            # Create initial cookie file
            initial_cookies = {"session": "initial"}
            with cookie_file.open("w") as f:
                json.dump(initial_cookies, f)
            cookie_file.chmod(0o600)

            # Create configuration with short cache TTL
            config = {
                "version": "1.0",
                "sessions": {
                    "test": {
                        "description": "Test session",
                        "cookie_file": str(cookie_file),
                        "cache_ttl": 1,  # 1 second cache
                    }
                },
            }

            with config_file.open("w") as f:
                yaml.dump(config, f)

            provider = CookieSessionProvider(config_file)

            # Act - Fetch initial cookies
            data_v1 = await provider.get_resource("cookie-session://test")
            assert data_v1["cookies"] == initial_cookies

            # Update cookie file
            updated_cookies = {"session": "updated", "new_field": "value"}
            with cookie_file.open("w") as f:
                json.dump(updated_cookies, f)

            # Wait for cache to expire
            await asyncio.sleep(1.1)

            # Fetch again after cache expiry
            data_v2 = await provider.get_resource("cookie-session://test")

            # Assert
            assert data_v2["cookies"] == updated_cookies
            assert not data_v2["from_cache"]

    @pytest.mark.integration
    async def test_security_validation_integration(self):
        """Test security features in integration scenario."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            config_file = tmppath / "cookie_sessions.yaml"
            cookies_dir = tmppath / "cookies"
            cookies_dir.mkdir()

            # Create cookie file with insecure permissions
            insecure_file = cookies_dir / "insecure.json"
            with insecure_file.open("w") as f:
                json.dump({"insecure": "data"}, f)
            insecure_file.chmod(0o644)  # World-readable

            # Create cookie file with secure permissions
            secure_file = cookies_dir / "secure.json"
            with secure_file.open("w") as f:
                json.dump({"secure": "data"}, f)
            secure_file.chmod(0o600)  # User-only

            # Try to use path traversal in config
            outside_file = tmppath / "outside.json"
            with outside_file.open("w") as f:
                json.dump({"outside": "data"}, f)
            outside_file.chmod(0o600)

            # Create configuration with various security test cases
            config = {
                "version": "1.0",
                "sessions": {
                    "insecure_perms": {
                        "description": "Insecure permissions test",
                        "cookie_file": str(insecure_file),
                    },
                    "secure": {
                        "description": "Secure session",
                        "cookie_file": str(secure_file),
                    },
                    "invalid_name!@#": {
                        "description": "Invalid name test",
                        "cookie_file": str(secure_file),
                    },
                    "path_traversal": {
                        "description": "Path traversal test",
                        "cookie_file": f"../../{outside_file.name}",
                    },
                },
            }

            with config_file.open("w") as f:
                yaml.dump(config, f)

            provider = CookieSessionProvider(config_file)

            # Act & Assert

            # Check that only valid sessions are loaded
            resources = provider.get_resources()
            resource_uris = {r["uri"] for r in resources}

            # Only "secure" should be loaded
            # - "insecure_perms" has file but will fail on fetch
            # - "invalid_name!@#" has invalid characters
            # - "path_traversal" will fail path validation
            assert "cookie-session://secure" in resource_uris
            assert "cookie-session://invalid_name!@#" not in resource_uris

            # Test fetching secure session works
            secure_data = await provider.get_resource("cookie-session://secure")
            assert secure_data["cookies"] == {"secure": "data"}
            assert "error" not in secure_data

            # Test fetching insecure permissions fails
            if "cookie-session://insecure_perms" in resource_uris:
                insecure_data = await provider.get_resource(
                    "cookie-session://insecure_perms"
                )
                assert insecure_data["cookies"] == {}
                assert "insecure permissions" in insecure_data["error"]

            # Test fetching path traversal fails
            if "cookie-session://path_traversal" in resource_uris:
                traversal_data = await provider.get_resource(
                    "cookie-session://path_traversal"
                )
                assert traversal_data["cookies"] == {}
                assert "error" in traversal_data

    @pytest.mark.integration
    @pytest.mark.slow
    async def test_cache_memory_management(self):
        """Test that cache cleanup prevents memory buildup."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            config_file = tmppath / "cookie_sessions.yaml"

            # Create multiple sessions with short TTL
            sessions_config = {"version": "1.0", "sessions": {}}

            for i in range(10):
                cookie_file = tmppath / f"cookies_{i}.json"
                with cookie_file.open("w") as f:
                    json.dump({f"cookie_{i}": f"value_{i}"}, f)
                cookie_file.chmod(0o600)

                sessions_config["sessions"][f"session_{i}"] = {
                    "description": f"Session {i}",
                    "cookie_file": str(cookie_file),
                    "cache_ttl": 1,  # 1 second TTL
                }

            with config_file.open("w") as f:
                yaml.dump(sessions_config, f)

            provider = CookieSessionProvider(config_file)

            # Act - Access all sessions to populate cache
            for i in range(10):
                data = await provider.get_resource(f"cookie-session://session_{i}")
                assert not data["from_cache"]

            # Verify all are cached
            cached_count = sum(
                1 for s in provider.sessions.values() if s._cached_cookies is not None
            )
            assert cached_count == 10

            # Wait for cache to expire
            await asyncio.sleep(1.1)

            # Trigger cleanup via get_resources
            provider.get_resources()

            # Assert - All caches should be cleared
            cached_count_after = sum(
                1 for s in provider.sessions.values() if s._cached_cookies is not None
            )
            assert cached_count_after == 0
