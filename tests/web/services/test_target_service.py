"""Tests for target service."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from hiro.db.models import RiskLevel, TargetStatus
from hiro.web.services.target_service import TargetService


class TestTargetService:
    """Test target service operations."""

    @pytest.mark.unit
    async def test_service_initialization(self):
        """Test service initialization with database session."""
        # Arrange
        mock_session = AsyncMock()

        # Act
        service = TargetService(mock_session)

        # Assert
        assert service.db == mock_session

    @pytest.mark.integration
    @pytest.mark.database
    async def test_list_targets_empty(self, test_db):
        """Test listing targets with empty database."""
        # Arrange
        service = TargetService(test_db)

        # Act
        targets = await service.list_targets()

        # Assert
        assert targets == []

    @pytest.mark.integration
    @pytest.mark.database
    async def test_list_targets_with_filters(self, test_db):
        """Test listing targets with various filters."""
        # Arrange
        service = TargetService(test_db)

        # Act
        targets = await service.list_targets(
            status=TargetStatus.ACTIVE, risk=RiskLevel.HIGH, search="test"
        )

        # Assert
        assert isinstance(targets, list)

    @pytest.mark.integration
    @pytest.mark.database
    async def test_get_target_not_found(self, test_db):
        """Test getting non-existent target."""
        # Arrange
        service = TargetService(test_db)
        fake_id = uuid4()

        # Act
        target = await service.get_target(fake_id)

        # Assert
        assert target is None

    @pytest.mark.integration
    @pytest.mark.database
    async def test_update_target_not_found(self, test_db):
        """Test updating non-existent target."""
        # Arrange
        service = TargetService(test_db)
        fake_id = uuid4()
        updates = {"status": TargetStatus.BLOCKED}

        # Act
        result = await service.update_target(fake_id, updates)

        # Assert
        assert result is None

    @pytest.mark.integration
    @pytest.mark.database
    async def test_get_target_context_not_found(self, test_db):
        """Test getting context for non-existent target."""
        # Arrange
        service = TargetService(test_db)
        fake_id = uuid4()

        # Act
        context = await service.get_target_context(fake_id)

        # Assert
        assert context is None

    @pytest.mark.integration
    @pytest.mark.database
    async def test_update_context_target_not_found(self, test_db):
        """Test updating context for non-existent target."""
        # Arrange
        service = TargetService(test_db)
        fake_id = uuid4()

        # Act
        result = await service.update_context(
            fake_id, user_context="Test", agent_context="Test"
        )

        # Assert
        assert result is None

    @pytest.mark.integration
    @pytest.mark.database
    async def test_get_target_requests_not_found(self, test_db):
        """Test getting requests for non-existent target."""
        # Arrange
        service = TargetService(test_db)
        fake_id = uuid4()

        # Act
        requests = await service.get_target_requests(fake_id)

        # Assert
        assert requests == []
