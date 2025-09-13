"""Integration tests for web UI functionality."""

from uuid import uuid4

import pytest


class TestWebIntegration:
    """Test web UI integration without database."""

    @pytest.mark.integration
    def test_targets_page_loads_without_db(self, test_client):
        """Test that targets page loads even without database."""
        # Arrange - test_client without database

        # Act
        response = test_client.get("/targets/")

        # Assert
        assert response.status_code == 200
        assert "Hiro" in response.text
        assert "Targets" in response.text
        # Should show empty state
        assert "No targets found" in response.text or "target-card" in response.text

    @pytest.mark.integration
    def test_navigation_links_present(self, test_client):
        """Test that navigation links are present and correct."""
        # Arrange

        # Act
        response = test_client.get("/targets/")

        # Assert
        assert response.status_code == 200
        # Check for navigation links
        assert 'href="/targets"' in response.text
        # Check for filter dropdowns
        assert "<select" in response.text
        assert "All Status" in response.text
        assert "All Risk Levels" in response.text

    @pytest.mark.integration
    def test_target_detail_without_db(self, test_client):
        """Test target detail page when database is not available."""
        # Arrange
        fake_id = uuid4()

        # Act
        response = test_client.get(f"/targets/{fake_id}")

        # Assert
        # Should return error page
        assert response.status_code in [404, 503]
        if response.status_code == 503:
            assert (
                "Database not configured" in response.text or "Error" in response.text
            )

    @pytest.mark.integration
    def test_api_endpoints_without_db(self, test_client):
        """Test API endpoints return empty data without database."""
        # Arrange

        # Act
        response = test_client.get("/api/targets")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "targets" in data
        assert data["targets"] == []

    @pytest.mark.integration
    def test_htmx_headers_work(self, test_client):
        """Test that HTMX requests are handled properly."""
        # Arrange
        headers = {"HX-Request": "true", "HX-Trigger": "search-input"}

        # Act
        response = test_client.get("/api/targets?format=html", headers=headers)

        # Assert
        assert response.status_code == 200
        # Should return HTML fragment for HTMX
        assert "No targets found" in response.text or "target-card" in response.text
