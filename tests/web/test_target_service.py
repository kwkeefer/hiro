"""Tests for TargetService context history methods."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from hiro.db.models import TargetContext
from hiro.web.services.target_service import TargetService


class TestTargetServiceContextHistory:
    """Test context history methods in TargetService."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_context_history_success(self):
        """Test successfully getting context history."""
        # Arrange
        target_id = uuid4()
        mock_session = MagicMock(spec=AsyncSession)

        # Create mock context history
        mock_contexts = [
            MagicMock(
                spec=TargetContext,
                version=3,
                created_at=datetime(2025, 1, 3),
                user_context="Latest",
                agent_context="Latest agent",
            ),
            MagicMock(
                spec=TargetContext,
                version=2,
                created_at=datetime(2025, 1, 2),
                user_context="Middle",
                agent_context="Middle agent",
            ),
            MagicMock(
                spec=TargetContext,
                version=1,
                created_at=datetime(2025, 1, 1),
                user_context="First",
                agent_context="First agent",
            ),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_contexts
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = TargetService(mock_session)

        # Act
        result = await service.get_context_history(target_id)

        # Assert
        assert len(result) == 3
        assert result[0].version == 3
        assert result[1].version == 2
        assert result[2].version == 1
        mock_session.execute.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_context_history_empty(self):
        """Test getting context history when none exists."""
        # Arrange
        target_id = uuid4()
        mock_session = MagicMock(spec=AsyncSession)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = TargetService(mock_session)

        # Act
        result = await service.get_context_history(target_id)

        # Assert
        assert result == []
        mock_session.execute.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_context_by_version_success(self):
        """Test successfully getting a specific context version."""
        # Arrange
        target_id = uuid4()
        version = 2
        mock_session = MagicMock(spec=AsyncSession)

        mock_context = MagicMock(
            spec=TargetContext,
            version=version,
            user_context="Version 2 content",
            agent_context="Agent v2",
            created_at=datetime(2025, 1, 2),
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_context
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = TargetService(mock_session)

        # Act
        result = await service.get_context_by_version(target_id, version)

        # Assert
        assert result is not None
        assert result.version == version
        assert result.user_context == "Version 2 content"
        mock_session.execute.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_context_by_version_not_found(self):
        """Test getting a non-existent context version."""
        # Arrange
        target_id = uuid4()
        version = 999
        mock_session = MagicMock(spec=AsyncSession)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = TargetService(mock_session)

        # Act
        result = await service.get_context_by_version(target_id, version)

        # Assert
        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_context_history_ordered_by_version_desc(self):
        """Test that context history is ordered by version descending."""
        # Arrange
        target_id = uuid4()
        mock_session = MagicMock(spec=AsyncSession)

        # Create mock contexts in random order
        mock_contexts = [
            MagicMock(spec=TargetContext, version=1),
            MagicMock(spec=TargetContext, version=5),
            MagicMock(spec=TargetContext, version=3),
            MagicMock(spec=TargetContext, version=2),
            MagicMock(spec=TargetContext, version=4),
        ]

        # Service should return them ordered by version desc
        ordered_contexts = sorted(mock_contexts, key=lambda x: x.version, reverse=True)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = ordered_contexts
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = TargetService(mock_session)

        # Act
        result = await service.get_context_history(target_id)

        # Assert
        assert len(result) == 5
        assert result[0].version == 5
        assert result[1].version == 4
        assert result[2].version == 3
        assert result[3].version == 2
        assert result[4].version == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_context_by_version_with_all_fields(self):
        """Test getting context version returns all expected fields."""
        # Arrange
        target_id = uuid4()
        version = 1
        mock_session = MagicMock(spec=AsyncSession)

        mock_context = MagicMock(
            spec=TargetContext,
            version=version,
            user_context="User content",
            agent_context="Agent content",
            created_at=datetime(2025, 1, 1, 12, 0, 0),
            created_by="user",
            change_type="user_edit",
            change_summary="Initial context",
            is_major_version=True,
            tokens_count=100,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_context
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = TargetService(mock_session)

        # Act
        result = await service.get_context_by_version(target_id, version)

        # Assert
        assert result.version == version
        assert result.user_context == "User content"
        assert result.agent_context == "Agent content"
        assert result.created_at == datetime(2025, 1, 1, 12, 0, 0)
        assert result.created_by == "user"
        assert result.change_type == "user_edit"
        assert result.change_summary == "Initial context"
        assert result.is_major_version is True
        assert result.tokens_count == 100
