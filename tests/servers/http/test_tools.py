"""Unit tests for HTTP tools and parameter handling."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from hiro.core.mcp.exceptions import ToolError
from hiro.servers.http.config import HttpConfig
from hiro.servers.http.tools import HttpRequestParams, HttpRequestTool


class TestHttpRequestParams:
    """Test HTTP request parameter validation and transformation."""

    @pytest.mark.unit
    def test_basic_initialization(self):
        """Test basic parameter initialization."""
        # Arrange
        url = "https://api.example.com/test"

        # Act
        params = HttpRequestParams(url=url)

        # Assert
        assert params.url == url
        assert params.method == "GET"
        assert params.headers is None
        assert params.data is None
        assert params.params is None
        assert params.cookies is None
        assert params.follow_redirects is True
        assert params.auth is None

    @pytest.mark.unit
    def test_json_string_parsing_headers(self):
        """Test JSON string parsing for headers."""
        # Arrange
        headers_json = '{"User-Agent": "TestBot", "Accept": "application/json"}'

        # Act
        params = HttpRequestParams(url="http://test.com", headers=headers_json)

        # Assert
        assert params.headers == {"User-Agent": "TestBot", "Accept": "application/json"}

    @pytest.mark.unit
    def test_json_string_parsing_params(self):
        """Test JSON string parsing for URL parameters."""
        # Arrange
        params_json = '{"page": "1", "limit": "10", "sort": "desc"}'

        # Act
        params = HttpRequestParams(url="http://test.com", params=params_json)

        # Assert
        assert params.params == {"page": "1", "limit": "10", "sort": "desc"}

    @pytest.mark.unit
    def test_json_string_parsing_cookies(self):
        """Test JSON string parsing for cookies."""
        # Arrange
        cookies_json = '{"session_id": "abc123", "theme": "dark"}'

        # Act
        params = HttpRequestParams(url="http://test.com", cookies=cookies_json)

        # Assert
        assert params.cookies == {"session_id": "abc123", "theme": "dark"}

    @pytest.mark.unit
    def test_json_string_parsing_auth(self):
        """Test JSON string parsing for authentication."""
        # Arrange
        auth_json = '{"username": "testuser", "password": "testpass"}'

        # Act
        params = HttpRequestParams(url="http://test.com", auth=auth_json)

        # Assert
        assert params.auth == {"username": "testuser", "password": "testpass"}

    @pytest.mark.unit
    def test_invalid_json_handling(self):
        """Test handling of invalid JSON strings."""
        # Arrange
        invalid_json = '{"key": invalid}'

        # Act / Assert
        with pytest.raises(ValueError, match="Invalid JSON"):
            HttpRequestParams(url="http://test.com", headers=invalid_json)

    @pytest.mark.unit
    def test_non_dict_json_handling(self):
        """Test that non-dictionary JSON is rejected."""
        # Arrange
        array_json = '["item1", "item2"]'

        # Act / Assert
        with pytest.raises(ValueError, match="Must be a JSON object"):
            HttpRequestParams(url="http://test.com", headers=array_json)

    @pytest.mark.unit
    def test_dict_input_handling(self):
        """Test that dict inputs are accepted directly."""
        # Arrange
        headers_dict = {"Content-Type": "application/json", "X-API-Key": "secret"}

        # Act
        params = HttpRequestParams(url="http://test.com", headers=headers_dict)

        # Assert
        assert params.headers == headers_dict

    @pytest.mark.unit
    def test_value_string_conversion(self):
        """Test that all values are converted to strings."""
        # Arrange
        mixed_dict = {"string": "value", "number": 123, "bool": True}

        # Act
        params = HttpRequestParams(url="http://test.com", params=mixed_dict)

        # Assert
        assert params.params == {"string": "value", "number": "123", "bool": "True"}

    @pytest.mark.unit
    def test_method_upper_property(self):
        """Test method_upper property returns uppercase method."""
        # Arrange / Act
        params = HttpRequestParams(url="http://test.com", method="POST")

        # Assert
        assert params.method_upper == "POST"

    @pytest.mark.unit
    def test_params_dict_property(self):
        """Test params_dict property returns dict or empty dict."""
        # Arrange
        params_with = HttpRequestParams(url="http://test.com", params={"key": "value"})
        params_without = HttpRequestParams(url="http://test.com")

        # Act / Assert
        assert params_with.params_dict == {"key": "value"}
        assert params_without.params_dict == {}

    @pytest.mark.unit
    def test_url_parsing_properties(self):
        """Test URL parsing properties."""
        # Arrange
        url = "https://api.example.com:8080/v1/users?page=1"

        # Act
        params = HttpRequestParams(url=url)

        # Assert
        assert params.host == "api.example.com"
        assert params.path == "/v1/users"
        parsed = params.parsed_url
        assert parsed.scheme == "https"
        assert parsed.port == 8080

    @pytest.mark.unit
    def test_path_default_slash(self):
        """Test that path defaults to / when empty."""
        # Arrange
        url = "https://example.com"

        # Act
        params = HttpRequestParams(url=url)

        # Assert
        assert params.path == "/"

    @pytest.mark.unit
    def test_auth_tuple_property(self):
        """Test auth_tuple property conversion."""
        # Arrange
        params_with_auth = HttpRequestParams(
            url="http://test.com", auth={"username": "user", "password": "pass"}
        )
        params_incomplete = HttpRequestParams(
            url="http://test.com", auth={"username": "user"}
        )
        params_without = HttpRequestParams(url="http://test.com")

        # Act / Assert
        assert params_with_auth.auth_tuple == ("user", "pass")
        assert params_incomplete.auth_tuple is None
        assert params_without.auth_tuple is None

    @pytest.mark.unit
    def test_get_json_data(self):
        """Test JSON data parsing."""
        # Arrange
        json_data = '{"key": "value", "number": 42}'
        params_json = HttpRequestParams(url="http://test.com", data=json_data)
        params_text = HttpRequestParams(url="http://test.com", data="plain text")
        params_none = HttpRequestParams(url="http://test.com")

        # Act / Assert
        assert params_json.get_json_data() == {"key": "value", "number": 42}
        assert params_text.get_json_data() is None
        assert params_none.get_json_data() is None

    @pytest.mark.unit
    def test_is_json_data_property(self):
        """Test is_json_data property."""
        # Arrange
        params_json = HttpRequestParams(url="http://test.com", data='{"valid": "json"}')
        params_text = HttpRequestParams(url="http://test.com", data="not json")

        # Act / Assert
        assert params_json.is_json_data is True
        assert params_text.is_json_data is False

    @pytest.mark.unit
    def test_merge_headers(self):
        """Test header merging functionality."""
        # Arrange
        base_headers = {"User-Agent": "BaseAgent", "Accept": "text/html"}
        request_headers = {"Accept": "application/json", "X-Custom": "value"}
        params = HttpRequestParams(url="http://test.com", headers=request_headers)

        # Act
        merged = params.merge_headers(base_headers)

        # Assert
        assert merged == {
            "User-Agent": "BaseAgent",
            "Accept": "application/json",  # Request overrides base
            "X-Custom": "value",
        }

    @pytest.mark.unit
    def test_merge_headers_with_none(self):
        """Test header merging with None values."""
        # Arrange
        params = HttpRequestParams(url="http://test.com", headers={"X-Test": "value"})

        # Act
        merged_none_base = params.merge_headers(None)
        params_no_headers = HttpRequestParams(url="http://test.com")
        merged_none_request = params_no_headers.merge_headers({"Base": "header"})

        # Assert
        assert merged_none_base == {"X-Test": "value"}
        assert merged_none_request == {"Base": "header"}

    @pytest.mark.unit
    def test_all_http_methods(self):
        """Test all supported HTTP methods."""
        # Arrange
        methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]

        # Act / Assert
        for method in methods:
            params = HttpRequestParams(url="http://test.com", method=method)
            assert params.method == method
            assert params.method_upper == method.upper()


class TestHttpRequestTool:
    """Test HTTP request tool functionality."""

    @pytest.fixture
    def http_config(self):
        """Provide test HTTP configuration."""
        return HttpConfig(
            proxy_url="http://proxy.test:8080",
            timeout=10.0,
            verify_ssl=False,
            tracing_headers={"X-Trace": "test123"},
        )

    @pytest.fixture
    def mock_http_repo(self):
        """Provide mock HTTP request repository."""
        repo = AsyncMock()
        repo.create = AsyncMock(return_value=MagicMock(id=1))
        repo.update = AsyncMock()
        repo.link_to_target = AsyncMock()
        return repo

    @pytest.fixture
    def mock_target_repo(self):
        """Provide mock target repository."""
        repo = AsyncMock()
        repo.get_by_endpoint = AsyncMock(
            return_value=MagicMock(id=1, host="example.com")
        )
        return repo

    @pytest.mark.unit
    async def test_tool_initialization(self, http_config):
        """Test HTTP request tool initialization."""
        # Arrange / Act
        tool = HttpRequestTool(config=http_config)

        # Assert
        assert tool._config == http_config
        assert tool._http_repo is None
        assert tool._target_repo is None
        assert tool._mission_id is None

    @pytest.mark.unit
    async def test_tool_with_repositories(
        self, http_config, mock_http_repo, mock_target_repo
    ):
        """Test tool initialization with repositories."""
        # Arrange
        mission_id = "test-mission-123"

        # Act
        tool = HttpRequestTool(
            config=http_config,
            http_repo=mock_http_repo,
            target_repo=mock_target_repo,
            mission_id=mission_id,
        )

        # Assert
        assert tool._http_repo == mock_http_repo
        assert tool._target_repo == mock_target_repo
        assert tool._mission_id == mission_id

    @pytest.mark.unit
    async def test_execute_basic_get_request(self, http_config):
        """Test executing a basic GET request."""
        # Arrange
        tool = HttpRequestTool(config=http_config)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.url = "https://api.example.com/test"
        mock_response.cookies = {}
        mock_response.elapsed.total_seconds.return_value = 0.5
        mock_response.encoding = "utf-8"
        mock_response.text = '{"result": "success"}'
        mock_response.json.return_value = {"result": "success"}
        mock_response.content = b'{"result": "success"}'

        # Act
        with patch("hiro.servers.http.tools.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await tool.execute(url="https://api.example.com/test")

        # Assert
        assert result["status_code"] == 200
        assert result["json"] == {"result": "success"}
        assert result["text"] == '{"result": "success"}'
        assert result["elapsed_ms"] == 500.0
        assert result["request"]["proxy_used"] == "http://proxy.test:8080"

        # Verify client was configured correctly
        mock_client_class.assert_called_once_with(
            timeout=10.0,
            verify=False,
            follow_redirects=True,
            proxy="http://proxy.test:8080",
        )

    @pytest.mark.unit
    async def test_execute_post_with_json_data(self, http_config):
        """Test POST request with JSON data."""
        # Arrange
        tool = HttpRequestTool(config=http_config)
        json_data = '{"name": "test", "value": 123}'

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.headers = {}
        mock_response.url = "https://api.example.com/create"
        mock_response.cookies = {}
        mock_response.elapsed.total_seconds.return_value = 0.2
        mock_response.encoding = "utf-8"
        mock_response.text = "Created"
        mock_response.json.side_effect = json.JSONDecodeError("", "", 0)

        # Act
        with patch("hiro.servers.http.tools.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await tool.execute(
                url="https://api.example.com/create", method="POST", data=json_data
            )

        # Assert
        assert result["status_code"] == 201
        assert result["json"] is None
        assert result["text"] == "Created"

        # Verify JSON data was passed correctly
        mock_client.request.assert_called_once()
        call_kwargs = mock_client.request.call_args[1]
        assert "json" in call_kwargs
        assert call_kwargs["json"] == {"name": "test", "value": 123}

    @pytest.mark.unit
    async def test_execute_with_headers_merge(self, http_config):
        """Test that headers are merged correctly."""
        # Arrange
        tool = HttpRequestTool(config=http_config)
        user_headers = '{"Accept": "application/json", "X-Custom": "value"}'

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.url = "https://api.example.com"
        mock_response.cookies = {}
        mock_response.elapsed.total_seconds.return_value = 0.1
        mock_response.encoding = "utf-8"
        mock_response.text = "OK"
        mock_response.json.side_effect = Exception()

        # Act
        with patch("hiro.servers.http.tools.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await tool.execute(url="https://api.example.com", headers=user_headers)

        # Assert
        call_kwargs = mock_client.request.call_args[1]
        headers = call_kwargs["headers"]
        assert headers["X-Trace"] == "test123"  # From config
        assert headers["Accept"] == "application/json"  # From user
        assert headers["X-Custom"] == "value"  # From user

    @pytest.mark.unit
    async def test_execute_with_auth(self, http_config):
        """Test request with basic authentication."""
        # Arrange
        tool = HttpRequestTool(config=http_config)
        auth_json = '{"username": "testuser", "password": "testpass"}'

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.url = "https://api.example.com"
        mock_response.cookies = {}
        mock_response.elapsed.total_seconds.return_value = 0.1
        mock_response.encoding = "utf-8"
        mock_response.text = "Authenticated"
        mock_response.json.side_effect = Exception()

        # Act
        with patch("hiro.servers.http.tools.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await tool.execute(url="https://api.example.com", auth=auth_json)

        # Assert
        call_kwargs = mock_client.request.call_args[1]
        assert "auth" in call_kwargs
        assert call_kwargs["auth"] == ("testuser", "testpass")

    @pytest.mark.unit
    async def test_execute_timeout_error(self, http_config):
        """Test handling of timeout errors."""
        # Arrange
        tool = HttpRequestTool(config=http_config)

        # Act / Assert
        with patch("hiro.servers.http.tools.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(
                side_effect=httpx.TimeoutException("Request timed out")
            )
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(ToolError) as exc_info:
                await tool.execute(url="https://slow.example.com")

            assert "Request timed out after 10.0s" in str(exc_info.value)

    @pytest.mark.unit
    async def test_execute_connection_error(self, http_config):
        """Test handling of connection errors."""
        # Arrange
        tool = HttpRequestTool(config=http_config)

        # Act / Assert
        with patch("hiro.servers.http.tools.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(
                side_effect=httpx.ConnectError("Connection refused")
            )
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(ToolError) as exc_info:
                await tool.execute(url="https://unreachable.example.com")

            assert "Connection failed" in str(exc_info.value)

    @pytest.mark.unit
    async def test_execute_invalid_parameters(self, http_config):
        """Test handling of invalid parameters."""
        # Arrange
        tool = HttpRequestTool(config=http_config)

        # Act / Assert
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(
                url="https://api.example.com", headers='{"invalid": json syntax}'
            )

        assert "Invalid parameters" in str(exc_info.value)

    @pytest.mark.unit
    async def test_execute_binary_response(self, http_config):
        """Test handling of binary response content."""
        # Arrange
        tool = HttpRequestTool(config=http_config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/octet-stream"}
        mock_response.url = "https://api.example.com/binary"
        mock_response.cookies = {}
        mock_response.elapsed.total_seconds.return_value = 0.1
        mock_response.encoding = None
        mock_response.content = b"\x00\x01\x02\x03"

        # Simulate text property that raises UnicodeDecodeError
        def raise_unicode_error():
            raise UnicodeDecodeError("utf-8", b"", 0, 1, "invalid")

        # Make text property raise error when accessed
        type(mock_response).text = property(lambda _: raise_unicode_error())
        mock_response.json.side_effect = Exception()

        # Act
        with patch("hiro.servers.http.tools.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await tool.execute(url="https://api.example.com/binary")

        # Assert
        assert result["status_code"] == 200
        assert result["text"] == "[Binary content - not displayable]"
        assert result["json"] is None

    @pytest.mark.unit
    async def test_database_logging_enabled(
        self, http_config, mock_http_repo, mock_target_repo
    ):
        """Test that database logging works when enabled."""
        # Arrange
        http_config.logging_enabled = True
        mission_id = "550e8400-e29b-41d4-a716-446655440000"
        tool = HttpRequestTool(
            config=http_config,
            http_repo=mock_http_repo,
            target_repo=mock_target_repo,
            mission_id=mission_id,
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "text/plain"}
        mock_response.url = "https://api.example.com/test"
        mock_response.cookies = {}
        mock_response.elapsed.total_seconds.return_value = 0.5
        mock_response.encoding = "utf-8"
        mock_response.text = "Success"
        mock_response.json.side_effect = Exception()
        mock_response.content = b"Success"

        # Act
        with patch("hiro.servers.http.tools.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await tool.execute(url="https://api.example.com/test")

        # Assert
        mock_target_repo.get_by_endpoint.assert_called_once_with(
            "api.example.com", None, "https"
        )
        mock_http_repo.create.assert_called_once()
        mock_http_repo.update.assert_called_once()
        mock_http_repo.link_to_target.assert_called_once()

    @pytest.mark.unit
    async def test_database_logging_disabled(
        self, http_config, mock_http_repo, mock_target_repo
    ):
        """Test that database logging is skipped when disabled."""
        # Arrange
        http_config.logging_enabled = False
        tool = HttpRequestTool(
            config=http_config, http_repo=mock_http_repo, target_repo=mock_target_repo
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.url = "https://api.example.com"
        mock_response.cookies = {}
        mock_response.elapsed.total_seconds.return_value = 0.1
        mock_response.encoding = "utf-8"
        mock_response.text = "OK"
        mock_response.json.side_effect = Exception()
        mock_response.content = b"OK"

        # Act
        with patch("hiro.servers.http.tools.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await tool.execute(url="https://api.example.com")

        # Assert
        mock_http_repo.create.assert_not_called()
        mock_target_repo.get_by_endpoint.assert_not_called()

    @pytest.mark.unit
    async def test_sensitive_headers_filtering(self, http_config, mock_http_repo):
        """Test that sensitive headers are filtered in logs."""
        # Arrange
        http_config.logging_enabled = True
        http_config.sensitive_headers = ["Authorization", "X-API-Key"]
        tool = HttpRequestTool(config=http_config, http_repo=mock_http_repo)

        # Act
        filtered = tool._filter_sensitive_data(
            {
                "Authorization": "Bearer secret123",
                "X-API-Key": "supersecret",
                "Content-Type": "application/json",
            }
        )

        # Assert
        assert filtered["Authorization"] == "[FILTERED]"
        assert filtered["X-API-Key"] == "[FILTERED]"
        assert filtered["Content-Type"] == "application/json"

    @pytest.mark.unit
    async def test_request_body_truncation(
        self, http_config, mock_http_repo, mock_target_repo
    ):
        """Test that large request bodies are truncated in logs."""
        # Arrange
        http_config.logging_enabled = True
        http_config.max_request_body_size = 100
        tool = HttpRequestTool(
            config=http_config, http_repo=mock_http_repo, target_repo=mock_target_repo
        )

        large_data = "x" * 200

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.url = "https://api.example.com"
        mock_response.cookies = {}
        mock_response.elapsed.total_seconds.return_value = 0.1
        mock_response.encoding = "utf-8"
        mock_response.text = "OK"
        mock_response.json.side_effect = Exception()
        mock_response.content = b"OK"

        # Act
        with patch("hiro.servers.http.tools.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await tool.execute(
                url="https://api.example.com", method="POST", data=large_data
            )

        # Assert
        create_call = mock_http_repo.create.call_args[0][0]
        assert create_call.request_body.endswith("... [TRUNCATED]")
        assert len(create_call.request_body) < 200
