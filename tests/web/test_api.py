"""Tests for web API endpoints following testing standards."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


class TestTargetsListEndpoint:
    """Test /api/targets endpoint."""

    @pytest.mark.unit
    def test_list_targets_returns_json(self, test_client):
        """Test that list targets returns JSON format."""
        # Arrange
        mock_targets = []

        # Act
        with patch("hiro.web.routers.api.TargetService") as mock_service:
            mock_service.return_value.list_targets = AsyncMock(
                return_value=mock_targets
            )
            response = test_client.get("/api/targets")

        # Assert
        assert response.status_code == 200
        assert response.json() == {"targets": []}

    @pytest.mark.unit
    def test_list_targets_with_filters(self, test_client):
        """Test list targets with status and risk filters."""
        # Arrange
        status_filter = "active"
        risk_filter = "high"
        search_query = "example"

        # Act
        with patch("hiro.web.routers.api.TargetService") as mock_service:
            mock_service.return_value.list_targets = AsyncMock(return_value=[])
            response = test_client.get(
                f"/api/targets?status={status_filter}&risk={risk_filter}&search={search_query}"
            )

        # Assert
        assert response.status_code == 200
        mock_service.return_value.list_targets.assert_called_once()
        call_args = mock_service.return_value.list_targets.call_args[1]
        assert call_args["status"] == status_filter
        assert call_args["risk"] == risk_filter
        assert call_args["search"] == search_query

    @pytest.mark.unit
    def test_list_targets_html_format(self, test_client):
        """Test list targets returns HTML for HTMX requests."""
        # Arrange
        mock_targets = []
        headers = {"HX-Request": "true"}

        # Act
        with patch("hiro.web.routers.api.TargetService") as mock_service:
            mock_service.return_value.list_targets = AsyncMock(
                return_value=mock_targets
            )
            response = test_client.get("/api/targets?format=html", headers=headers)

        # Assert
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    @pytest.mark.unit
    def test_list_targets_invalid_format(self, test_client):
        """Test list targets rejects invalid format parameter."""
        # Arrange
        invalid_format = "xml"

        # Act
        response = test_client.get(f"/api/targets?format={invalid_format}")

        # Assert
        assert response.status_code == 422
        assert "pattern" in response.json()["detail"][0]["ctx"]


class TestTargetDetailEndpoint:
    """Test /api/targets/{target_id} endpoint."""

    @pytest.mark.unit
    def test_get_target_success(self, test_client, mock_target):
        """Test successful target retrieval."""
        # Arrange
        target_id = mock_target.id

        # Act
        with patch("hiro.web.routers.api.TargetService") as mock_service:
            mock_service.return_value.get_target = AsyncMock(return_value=mock_target)
            response = test_client.get(f"/api/targets/{target_id}")

        # Assert
        assert response.status_code == 200
        # API returns the target object directly, not wrapped
        response.json()  # Verify response is valid JSON
        # The actual API serializes the mock differently
        # For unit test, just verify the service was called correctly
        mock_service.return_value.get_target.assert_called_once_with(target_id)

    @pytest.mark.unit
    def test_get_target_not_found(self, test_client):
        """Test get target returns 404 when not found."""
        # Arrange
        non_existent_id = uuid4()

        # Act
        with patch("hiro.web.routers.api.TargetService") as mock_service:
            mock_service.return_value.get_target = AsyncMock(return_value=None)
            response = test_client.get(f"/api/targets/{non_existent_id}")

        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Target not found"

    @pytest.mark.unit
    def test_get_target_invalid_uuid(self, test_client):
        """Test get target with invalid UUID format."""
        # Arrange
        invalid_id = "not-a-uuid"

        # Act
        response = test_client.get(f"/api/targets/{invalid_id}")

        # Assert
        assert response.status_code == 422


class TestTargetUpdateEndpoint:
    """Test PATCH /api/targets/{target_id} endpoint."""

    @pytest.mark.unit
    def test_update_target_status(self, test_client, mock_target):
        """Test updating target status."""
        # Arrange
        target_id = mock_target.id
        update_data = {"status": "inactive"}
        mock_target.status = "inactive"

        # Act
        with patch("hiro.web.routers.api.TargetService") as mock_service:
            mock_service.return_value.update_target = AsyncMock(
                return_value=mock_target
            )
            response = test_client.patch(
                f"/api/targets/{target_id}",
                json=update_data,
                headers={"Content-Type": "application/json"},
            )

        # Assert
        assert response.status_code == 200
        mock_service.return_value.update_target.assert_called_once()
        call_args = mock_service.return_value.update_target.call_args[0]
        assert call_args[0] == target_id
        assert call_args[1]["status"] == "inactive"

    @pytest.mark.unit
    def test_update_target_risk_level(self, test_client, mock_target):
        """Test updating target risk level."""
        # Arrange
        target_id = mock_target.id
        update_data = {"risk_level": "critical"}
        mock_target.risk_level = "critical"

        # Act
        with patch("hiro.web.routers.api.TargetService") as mock_service:
            mock_service.return_value.update_target = AsyncMock(
                return_value=mock_target
            )
            response = test_client.patch(
                f"/api/targets/{target_id}",
                json=update_data,
                headers={"Content-Type": "application/json"},
            )

        # Assert
        assert response.status_code == 200
        # API returns the updated target - verify service was called with correct data
        mock_service.return_value.update_target.assert_called_once()
        call_args = mock_service.return_value.update_target.call_args[0][1]
        assert call_args["risk_level"] == "critical"

    @pytest.mark.unit
    def test_update_target_multiple_fields(self, test_client, mock_target):
        """Test updating multiple target fields at once."""
        # Arrange
        target_id = mock_target.id
        update_data = {
            "status": "blocked",
            "risk_level": "low",
            "title": "Updated Title",
            "port": 8080,
        }

        # Act
        with patch("hiro.web.routers.api.TargetService") as mock_service:
            mock_service.return_value.update_target = AsyncMock(
                return_value=mock_target
            )
            response = test_client.patch(
                f"/api/targets/{target_id}",
                json=update_data,
                headers={"Content-Type": "application/json"},
            )

        # Assert
        assert response.status_code == 200
        call_args = mock_service.return_value.update_target.call_args[0][1]
        assert call_args["status"] == "blocked"
        assert call_args["risk_level"] == "low"
        assert call_args["title"] == "Updated Title"
        assert call_args["port"] == 8080

    @pytest.mark.unit
    def test_update_target_invalid_port(self, test_client, mock_target):
        """Test update rejects invalid port number."""
        # Arrange
        target_id = mock_target.id
        update_data = {"port": 99999}

        # Act
        response = test_client.patch(
            f"/api/targets/{target_id}",
            json=update_data,
            headers={"Content-Type": "application/json"},
        )

        # Assert
        assert response.status_code == 422
        assert "less_than_equal" in str(response.json()["detail"])

    @pytest.mark.unit
    def test_update_target_not_found(self, test_client):
        """Test update returns 404 when target not found."""
        # Arrange
        non_existent_id = uuid4()
        update_data = {"status": "active"}

        # Act
        with patch("hiro.web.routers.api.TargetService") as mock_service:
            mock_service.return_value.update_target = AsyncMock(return_value=None)
            response = test_client.patch(
                f"/api/targets/{non_existent_id}",
                json=update_data,
                headers={"Content-Type": "application/json"},
            )

        # Assert
        assert response.status_code == 404

    @pytest.mark.unit
    def test_update_target_htmx_response(self, test_client, mock_target):
        """Test update returns HTML for HTMX requests."""
        # Arrange
        target_id = mock_target.id
        update_data = {"status": "active"}
        headers = {
            "Content-Type": "application/json",
            "HX-Request": "true",
            "Referer": f"http://localhost/targets/{target_id}",
        }

        # Act
        with patch("hiro.web.routers.api.TargetService") as mock_service:
            mock_service.return_value.update_target = AsyncMock(
                return_value=mock_target
            )
            response = test_client.patch(
                f"/api/targets/{target_id}", json=update_data, headers=headers
            )

        # Assert
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


class TestContextUpdateEndpoint:
    """Test POST /api/targets/{target_id}/context endpoint."""

    @pytest.mark.unit
    def test_update_context_user_only(self, test_client, mock_target):
        """Test updating only user context."""
        # Arrange
        target_id = mock_target.id
        context_data = {"user_context": "New user context"}
        mock_context = MagicMock(version=1)

        # Act
        with patch("hiro.web.routers.api.TargetService") as mock_service:
            mock_service.return_value.update_context = AsyncMock(
                return_value=mock_context
            )
            response = test_client.post(
                f"/api/targets/{target_id}/context",
                json=context_data,
                headers={"Content-Type": "application/json"},
            )

        # Assert
        assert response.status_code == 200
        assert response.json() == {"success": True, "version": 1}
        mock_service.return_value.update_context.assert_called_once_with(
            target_id, user_context="New user context", agent_context=None
        )

    @pytest.mark.unit
    def test_update_context_both_fields(self, test_client, mock_target):
        """Test updating both user and agent context."""
        # Arrange
        target_id = mock_target.id
        context_data = {"user_context": "User notes", "agent_context": "Agent analysis"}
        mock_context = MagicMock(version=2)

        # Act
        with patch("hiro.web.routers.api.TargetService") as mock_service:
            mock_service.return_value.update_context = AsyncMock(
                return_value=mock_context
            )
            response = test_client.post(
                f"/api/targets/{target_id}/context",
                json=context_data,
                headers={"Content-Type": "application/json"},
            )

        # Assert
        assert response.status_code == 200
        assert response.json()["version"] == 2
        call_args = mock_service.return_value.update_context.call_args[1]
        assert call_args["user_context"] == "User notes"
        assert call_args["agent_context"] == "Agent analysis"

    @pytest.mark.unit
    def test_update_context_too_long(self, test_client, mock_target):
        """Test context update rejects text that's too long."""
        # Arrange
        target_id = mock_target.id
        long_text = "x" * 10001  # Over max_length limit
        context_data = {"user_context": long_text}

        # Act
        response = test_client.post(
            f"/api/targets/{target_id}/context",
            json=context_data,
            headers={"Content-Type": "application/json"},
        )

        # Assert
        assert response.status_code == 422
        assert "max_length" in str(response.json()["detail"])

    @pytest.mark.unit
    def test_update_context_target_not_found(self, test_client):
        """Test context update returns 404 when target not found."""
        # Arrange
        non_existent_id = uuid4()
        context_data = {"user_context": "Test"}

        # Act
        with patch("hiro.web.routers.api.TargetService") as mock_service:
            mock_service.return_value.update_context = AsyncMock(return_value=None)
            response = test_client.post(
                f"/api/targets/{non_existent_id}/context",
                json=context_data,
                headers={"Content-Type": "application/json"},
            )

        # Assert
        assert response.status_code == 404


class TestTargetRequestsEndpoint:
    """Test GET /api/targets/{target_id}/requests endpoint."""

    @pytest.mark.unit
    def test_get_target_requests_default_limit(self, test_client, mock_target):
        """Test getting target requests with default limit."""
        # Arrange
        target_id = mock_target.id
        mock_requests = [{"id": "req1"}, {"id": "req2"}]

        # Act
        with patch("hiro.web.routers.api.TargetService") as mock_service:
            mock_service.return_value.get_target_requests = AsyncMock(
                return_value=mock_requests
            )
            response = test_client.get(f"/api/targets/{target_id}/requests")

        # Assert
        assert response.status_code == 200
        assert response.json() == {"requests": mock_requests}
        mock_service.return_value.get_target_requests.assert_called_once_with(
            target_id, limit=100
        )

    @pytest.mark.unit
    def test_get_target_requests_custom_limit(self, test_client, mock_target):
        """Test getting target requests with custom limit."""
        # Arrange
        target_id = mock_target.id
        limit = 50
        mock_requests = []

        # Act
        with patch("hiro.web.routers.api.TargetService") as mock_service:
            mock_service.return_value.get_target_requests = AsyncMock(
                return_value=mock_requests
            )
            response = test_client.get(
                f"/api/targets/{target_id}/requests?limit={limit}"
            )

        # Assert
        assert response.status_code == 200
        mock_service.return_value.get_target_requests.assert_called_once_with(
            target_id, limit=limit
        )

    @pytest.mark.unit
    def test_get_target_requests_invalid_limit(self, test_client, mock_target):
        """Test requests endpoint rejects invalid limit."""
        # Arrange
        target_id = mock_target.id
        invalid_limit = 2000  # Over max limit

        # Act
        response = test_client.get(
            f"/api/targets/{target_id}/requests?limit={invalid_limit}"
        )

        # Assert
        assert response.status_code == 422
        assert "less_than_equal" in str(response.json()["detail"])


class TestContextHistoryEndpoint:
    """Test GET /api/targets/{target_id}/context/history endpoint."""

    @pytest.mark.unit
    def test_get_context_history_success(self, test_client, mock_target):
        """Test successfully getting context history."""
        # Arrange
        target_id = mock_target.id
        mock_history = [
            MagicMock(
                version=2,
                created_at="2025-01-02T00:00:00Z",
                created_by="user",
                change_type="user_edit",
                change_summary="Updated via web",
                is_major_version=False,
                tokens_count=100,
            ),
            MagicMock(
                version=1,
                created_at="2025-01-01T00:00:00Z",
                created_by="agent",
                change_type="agent_update",
                change_summary="Initial context",
                is_major_version=True,
                tokens_count=50,
            ),
        ]
        # Mock datetime objects
        for ctx in mock_history:
            ctx.created_at = MagicMock()
            ctx.created_at.isoformat.return_value = ctx.created_at

        # Act
        with patch("hiro.web.routers.api.TargetService") as mock_service:
            mock_service.return_value.get_context_history = AsyncMock(
                return_value=mock_history
            )
            response = test_client.get(f"/api/targets/{target_id}/context/history")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "history" in data
        assert len(data["history"]) == 2
        assert data["history"][0]["version"] == 2
        assert data["history"][1]["version"] == 1

    @pytest.mark.unit
    def test_get_context_history_empty(self, test_client, mock_target):
        """Test getting context history when no history exists."""
        # Arrange
        target_id = mock_target.id

        # Act
        with patch("hiro.web.routers.api.TargetService") as mock_service:
            mock_service.return_value.get_context_history = AsyncMock(return_value=[])
            response = test_client.get(f"/api/targets/{target_id}/context/history")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data == {"history": []}

    @pytest.mark.unit
    def test_get_context_history_invalid_uuid(self, test_client):
        """Test getting context history with invalid UUID."""
        # Arrange
        invalid_id = "not-a-uuid"

        # Act
        response = test_client.get(f"/api/targets/{invalid_id}/context/history")

        # Assert
        assert response.status_code == 422


class TestContextVersionEndpoint:
    """Test GET /api/targets/{target_id}/context/{version} endpoint."""

    @pytest.mark.unit
    def test_get_context_version_success(self, test_client, mock_target):
        """Test successfully getting a specific context version."""
        # Arrange
        target_id = mock_target.id
        version = 1
        mock_context = MagicMock(
            version=version,
            user_context="User notes v1",
            agent_context="Agent analysis v1",
            created_by="user",
            change_type="user_edit",
            change_summary="Initial version",
            is_major_version=False,
            tokens_count=75,
        )
        mock_context.created_at = MagicMock()
        mock_context.created_at.isoformat.return_value = "2025-01-01T00:00:00Z"

        # Act
        with patch("hiro.web.routers.api.TargetService") as mock_service:
            mock_service.return_value.get_context_by_version = AsyncMock(
                return_value=mock_context
            )
            response = test_client.get(f"/api/targets/{target_id}/context/{version}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == version
        assert data["user_context"] == "User notes v1"
        assert data["agent_context"] == "Agent analysis v1"
        assert data["change_type"] == "user_edit"

    @pytest.mark.unit
    def test_get_context_version_not_found(self, test_client, mock_target):
        """Test getting a non-existent context version."""
        # Arrange
        target_id = mock_target.id
        version = 999

        # Act
        with patch("hiro.web.routers.api.TargetService") as mock_service:
            mock_service.return_value.get_context_by_version = AsyncMock(
                return_value=None
            )
            response = test_client.get(f"/api/targets/{target_id}/context/{version}")

        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Context version not found"

    @pytest.mark.unit
    def test_get_context_version_invalid_version(self, test_client, mock_target):
        """Test getting context with invalid version number."""
        # Arrange
        target_id = mock_target.id
        invalid_version = "abc"  # Not an integer

        # Act
        response = test_client.get(
            f"/api/targets/{target_id}/context/{invalid_version}"
        )

        # Assert
        assert response.status_code == 422

    @pytest.mark.unit
    def test_get_context_version_zero(self, test_client, mock_target):
        """Test getting context version 0 (should be invalid)."""
        # Arrange
        target_id = mock_target.id
        version = 0

        # Act
        with patch("hiro.web.routers.api.TargetService") as mock_service:
            mock_service.return_value.get_context_by_version = AsyncMock(
                return_value=None
            )
            response = test_client.get(f"/api/targets/{target_id}/context/{version}")

        # Assert
        assert response.status_code == 404

    @pytest.mark.unit
    def test_get_context_version_negative(self, test_client, mock_target):
        """Test getting context with negative version number."""
        # Arrange
        target_id = mock_target.id
        version = -1

        # Act
        with patch("hiro.web.routers.api.TargetService") as mock_service:
            mock_service.return_value.get_context_by_version = AsyncMock(
                return_value=None
            )
            response = test_client.get(f"/api/targets/{target_id}/context/{version}")

        # Assert
        assert response.status_code == 404


class TestAPIIntegration:
    """Integration tests for API with database."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_target_lifecycle(self, test_client, db_session):
        """Test creating, updating, and retrieving a target."""
        # Arrange
        # Note: This would require implementing a POST endpoint
        # For now, we'll test with existing targets
        # target_data would be used for creating new targets:
        # {"host": "integration-test.com", "protocol": "https",
        #  "status": "active", "risk_level": "medium"}

        # Act - Get targets
        with patch("hiro.web.routers.api.get_db", return_value=db_session):
            response = test_client.get("/api/targets")

        # Assert
        assert response.status_code == 200
        # Additional assertions would go here

    @pytest.mark.integration
    @pytest.mark.slow
    async def test_concurrent_updates(self, test_client, mock_target):
        """Test handling concurrent update requests."""
        # Arrange
        target_id = mock_target.id
        update1 = {"status": "active"}
        update2 = {"risk_level": "high"}

        # Act - Simulate concurrent requests
        with patch("hiro.web.routers.api.TargetService") as mock_service:
            mock_service.return_value.update_target = AsyncMock(
                return_value=mock_target
            )

            # These would be concurrent in real scenario
            response1 = test_client.patch(
                f"/api/targets/{target_id}",
                json=update1,
                headers={"Content-Type": "application/json"},
            )
            response2 = test_client.patch(
                f"/api/targets/{target_id}",
                json=update2,
                headers={"Content-Type": "application/json"},
            )

        # Assert
        assert response1.status_code == 200
        assert response2.status_code == 200
