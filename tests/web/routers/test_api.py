"""Tests for API endpoints."""

from uuid import uuid4

import pytest


class TestAPIEndpoints:
    """Test API endpoints for HTMX interactions."""

    @pytest.mark.integration
    @pytest.mark.database
    async def test_get_targets_json(self, test_client_with_db):
        """Test getting targets list as JSON."""
        # Arrange - test_client_with_db with database

        # Act
        response = test_client_with_db.get("/api/targets")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "targets" in data
        assert isinstance(data["targets"], list)

    @pytest.mark.integration
    @pytest.mark.database
    async def test_get_target_not_found(self, test_client_with_db):
        """Test getting non-existent target via API."""
        # Arrange
        fake_id = uuid4()

        # Act
        response = test_client_with_db.get(f"/api/targets/{fake_id}")

        # Assert
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    @pytest.mark.integration
    @pytest.mark.database
    async def test_update_target_not_found(self, test_client_with_db):
        """Test updating non-existent target."""
        # Arrange
        fake_id = uuid4()
        update_data = {"status": "blocked"}

        # Act
        response = test_client_with_db.patch(
            f"/api/targets/{fake_id}", json=update_data
        )

        # Assert
        assert response.status_code == 404

    @pytest.mark.integration
    @pytest.mark.database
    async def test_update_context_not_found(self, test_client_with_db):
        """Test updating context for non-existent target."""
        # Arrange
        fake_id = uuid4()
        context_data = {"user_context": "Test context", "agent_context": None}

        # Act
        response = test_client_with_db.post(
            f"/api/targets/{fake_id}/context", json=context_data
        )

        # Assert
        assert response.status_code == 404

    @pytest.mark.integration
    @pytest.mark.database
    async def test_get_target_requests(self, test_client_with_db):
        """Test getting HTTP requests for a target."""
        # Arrange
        fake_id = uuid4()

        # Act
        response = test_client_with_db.get(f"/api/targets/{fake_id}/requests")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "requests" in data
        assert isinstance(data["requests"], list)
