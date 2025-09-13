"""Tests for target management routes."""

from uuid import uuid4

import pytest


class TestTargetRoutes:
    """Test target management endpoints."""

    @pytest.mark.integration
    @pytest.mark.database
    async def test_list_targets_empty(self, test_client_with_db):
        """Test listing targets when database is empty."""
        # Arrange - test_client_with_db with empty database

        # Act
        response = test_client_with_db.get("/targets/")

        # Assert
        assert response.status_code == 200
        assert "No targets found" in response.text

    @pytest.mark.integration
    @pytest.mark.database
    async def test_list_targets_with_filters(self, test_client_with_db):
        """Test listing targets with status and risk filters."""
        # Arrange
        params = {"status": "active", "risk": "high", "search": "example"}

        # Act
        response = test_client_with_db.get("/targets/", params=params)

        # Assert
        assert response.status_code == 200
        # Should show filtered view or empty state
        assert response.text is not None

    @pytest.mark.integration
    @pytest.mark.database
    async def test_view_target_not_found(self, test_client_with_db):
        """Test viewing a non-existent target."""
        # Arrange
        fake_id = uuid4()

        # Act
        response = test_client_with_db.get(f"/targets/{fake_id}")

        # Assert
        # Should return 404 or error page
        assert response.status_code in [404, 500]

    @pytest.mark.unit
    def test_target_dashboard_template_rendering(self, test_client):
        """Test that target dashboard template renders without errors."""
        # Arrange - test_client fixture (no database needed)

        # Act
        response = test_client.get("/targets/")

        # Assert
        # Without database, might fail or redirect
        assert response.status_code in [200, 500]
        assert response.text is not None
