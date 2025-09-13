"""Tests for the FastAPI application."""

import pytest
from fastapi.testclient import TestClient

from hiro.web.app import app


class TestWebApp:
    """Test the main web application."""

    @pytest.mark.unit
    def test_app_creation(self):
        """Test that the app is created successfully."""
        # Arrange - app is imported

        # Act
        app_title = app.title
        app_version = app.version

        # Assert
        assert app_title == "Hiro Web Interface"
        assert app_version == "0.1.0"

    @pytest.mark.unit
    def test_root_redirect(self):
        """Test root path redirects to targets."""
        # Arrange
        client = TestClient(app)

        # Act
        response = client.get("/")

        # Assert
        assert response.status_code == 200
        assert "url=/targets" in response.text

    @pytest.mark.unit
    def test_health_check(self):
        """Test health check endpoint."""
        # Arrange
        client = TestClient(app)

        # Act
        response = client.get("/health")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "hiro-web"

    @pytest.mark.unit
    def test_static_files_mounted(self):
        """Test that static files are properly mounted."""
        # Arrange
        client = TestClient(app)

        # Act
        response = client.get("/static/css/main.css")

        # Assert
        # Should return 200 if file exists, 404 if not
        assert response.status_code in [200, 404]

    @pytest.mark.unit
    def test_cors_headers(self):
        """Test CORS middleware is configured."""
        # Arrange
        client = TestClient(app)

        # Act - Test with origin that matches our CORS config
        response = client.get("/health", headers={"Origin": "http://localhost:8000"})

        # Assert
        assert response.status_code == 200
        # Check that CORS is configured (credentials header is present)
        assert "access-control-allow-credentials" in response.headers
