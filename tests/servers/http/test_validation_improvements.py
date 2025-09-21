"""Test ADR-018 validation improvements in HTTP tools.

Verifies that common LLM type confusion is handled gracefully.
"""

import pytest

from hiro.core.mcp.exceptions import ToolError
from hiro.servers.http.config import HttpConfig
from hiro.servers.http.tools import HttpRequestTool


class TestHttpToolValidationImprovements:
    """Test ADR-018 improvements to HTTP tool validation."""

    @pytest.mark.unit
    async def test_accepts_string_boolean_for_follow_redirects(self):
        """Test that string booleans are coerced correctly."""
        # Arrange
        config = HttpConfig()
        tool = HttpRequestTool(config=config)

        # Mock the httpx response
        with pytest.MonkeyPatch.context() as m:

            async def mock_request(*_args, **_kwargs):
                class MockResponse:
                    status_code = 200
                    headers = {}
                    content = b'{"success": true}'
                    text = '{"success": true}'

                    def json(self):
                        return {"success": True}

                return MockResponse()

            m.setattr("httpx.AsyncClient.request", mock_request)

            # Act - Pass "false" as string instead of boolean
            result = await tool.execute(
                url="https://example.com",
                method="GET",
                follow_redirects="false",  # String instead of bool
            )

            # Assert - Should work without error
            assert result["status_code"] == 200

    @pytest.mark.unit
    async def test_comprehensive_errors_for_multiple_issues(self):
        """Test that multiple validation errors are reported together."""
        # Arrange
        config = HttpConfig()
        tool = HttpRequestTool(config=config)

        # Act - Multiple errors: invalid JSON and wrong type
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(
                url="https://example.com",
                headers='{"bad json',  # Invalid JSON
                cookies='["should", "be", "object"]',  # Wrong type (array not object)
                auth='{"username": "only"}',  # Missing password field
            )

        # Assert - Should report all errors
        error_msg = str(exc_info.value)
        assert "Invalid HTTP request" in error_msg
        # At minimum should mention the invalid JSON
        assert "headers" in error_msg.lower() or "json" in error_msg.lower()

    @pytest.mark.unit
    async def test_coercion_edge_cases(self):
        """Test edge cases in type coercion."""
        # Arrange
        config = HttpConfig()
        tool = HttpRequestTool(config=config)

        test_cases = [
            ("true", True),
            ("false", False),
            ("True", True),
            ("FALSE", False),
            ("1", True),
            ("0", False),
            ("yes", True),
            ("no", False),
        ]

        for string_val, expected_bool in test_cases:
            # Mock the httpx response
            with pytest.MonkeyPatch.context() as m:
                captured_follow_redirects = None

                async def capture_request(*_args, **kwargs):
                    nonlocal captured_follow_redirects
                    captured_follow_redirects = kwargs.get("follow_redirects")

                    class MockResponse:
                        status_code = 200
                        headers = {}
                        content = b"{}"
                        text = "{}"

                        def json(self):
                            return {}

                    return MockResponse()

                m.setattr("httpx.AsyncClient.request", capture_request)

                # Act
                await tool.execute(
                    url="https://example.com",
                    follow_redirects=string_val,
                )

                # Assert
                assert (
                    captured_follow_redirects == expected_bool
                ), f"Failed to coerce '{string_val}' to {expected_bool}"
