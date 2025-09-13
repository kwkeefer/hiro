"""Tests for context management tools."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from hiro.core.mcp.exceptions import ToolError
from hiro.db.models import ContextChangeType, Target, TargetContext
from hiro.servers.ai_logging.tools import (
    GetTargetContextTool,
    UpdateTargetContextTool,
)


class TestGetTargetContextTool:
    """Tests for GetTargetContextTool."""

    @pytest.mark.unit
    async def test_get_current_context(self):
        """Test retrieving current context version."""
        # Arrange
        target_id = str(uuid4())
        target = MagicMock(spec=Target)
        target.id = UUID(target_id)
        target.host = "example.com"

        context = MagicMock(spec=TargetContext)
        context.id = uuid4()
        context.version = 5
        context.target_id = UUID(target_id)
        context.user_context = "User notes"
        context.agent_context = "Agent notes"
        context.created_at = datetime.now(UTC)
        context.created_by = "user"
        context.change_type = ContextChangeType.USER_EDIT
        context.change_summary = "Updated notes"
        context.is_major_version = False
        context.tokens_count = 100

        target_repo = AsyncMock()
        target_repo.get_by_id = AsyncMock(return_value=target)

        context_repo = AsyncMock()
        context_repo.get_current = AsyncMock(return_value=context)

        tool = GetTargetContextTool(context_repo=context_repo, target_repo=target_repo)

        # Act
        result = await tool.execute(target_id=target_id)

        # Assert
        assert result["status"] == "success"
        assert result["version"] == 5
        assert result["user_context"] == "User notes"
        assert result["agent_context"] == "Agent notes"
        assert result["tokens_count"] == 100

    @pytest.mark.unit
    async def test_get_specific_version(self):
        """Test retrieving specific context version."""
        # Arrange
        target_id = str(uuid4())
        version_id = str(uuid4())
        target = MagicMock(spec=Target)
        target.id = UUID(target_id)
        target.host = "example.com"

        context = MagicMock(spec=TargetContext)
        context.id = UUID(version_id)
        context.version = 3
        context.target_id = UUID(target_id)
        context.user_context = "Old notes"
        context.agent_context = None
        context.created_at = datetime.now(UTC)
        context.created_by = "user"
        context.change_type = ContextChangeType.USER_EDIT
        context.change_summary = "Historical version"
        context.is_major_version = False
        context.tokens_count = 50

        target_repo = AsyncMock()
        target_repo.get_by_id = AsyncMock(return_value=target)

        context_repo = AsyncMock()
        context_repo.get_version = AsyncMock(return_value=context)

        tool = GetTargetContextTool(context_repo=context_repo, target_repo=target_repo)

        # Act
        result = await tool.execute(target_id=target_id, version_id=version_id)

        # Assert
        assert result["status"] == "success"
        assert result["version"] == 3
        assert result["user_context"] == "Old notes"
        assert result["agent_context"] is None
        context_repo.get_version.assert_called_once_with(UUID(version_id))

    @pytest.mark.unit
    async def test_get_context_with_history(self):
        """Test retrieving context with version history."""
        # Arrange
        target_id = str(uuid4())
        target = MagicMock(spec=Target)
        target.id = UUID(target_id)
        target.host = "example.com"

        current = MagicMock(spec=TargetContext)
        current.id = uuid4()
        current.version = 3
        current.target_id = UUID(target_id)
        current.user_context = "Latest"
        current.agent_context = None
        current.created_at = datetime.now(UTC)
        current.created_by = "user"
        current.change_type = ContextChangeType.USER_EDIT
        current.change_summary = "Latest update"
        current.is_major_version = False
        current.tokens_count = 75

        history = []
        for i in range(3, 0, -1):
            h = MagicMock(spec=TargetContext)
            h.version = i
            h.id = uuid4()
            h.created_at = datetime.now(UTC)
            h.created_by = "user"
            h.change_type = ContextChangeType.USER_EDIT
            h.change_summary = f"Version {i}"
            h.is_major_version = i == 1
            history.append(h)

        target_repo = AsyncMock()
        target_repo.get_by_id = AsyncMock(return_value=target)

        context_repo = AsyncMock()
        context_repo.get_current = AsyncMock(return_value=current)
        context_repo.list_versions = AsyncMock(return_value=history)

        tool = GetTargetContextTool(context_repo=context_repo, target_repo=target_repo)

        # Act
        result = await tool.execute(target_id=target_id, include_history=True)

        # Assert
        assert result["status"] == "success"
        assert result["version"] == 3
        assert "history" in result
        assert len(result["history"]) == 3
        assert result["history"][0]["version"] == 3
        assert result["history"][2]["is_major_version"] is True

    @pytest.mark.unit
    async def test_get_context_no_context_exists(self):
        """Test retrieving context when none exists."""
        # Arrange
        target_id = str(uuid4())
        target = MagicMock(spec=Target)
        target.id = UUID(target_id)
        target.host = "example.com"

        target_repo = AsyncMock()
        target_repo.get_by_id = AsyncMock(return_value=target)

        context_repo = AsyncMock()
        context_repo.get_current = AsyncMock(return_value=None)

        tool = GetTargetContextTool(context_repo=context_repo, target_repo=target_repo)

        # Act
        result = await tool.execute(target_id=target_id)

        # Assert
        assert result["status"] == "no_context"
        assert result["target_id"] == target_id
        assert "No context found" in result["message"]

    @pytest.mark.unit
    async def test_get_context_target_not_found(self):
        """Test retrieving context for non-existent target."""
        # Arrange
        target_id = str(uuid4())

        target_repo = AsyncMock()
        target_repo.get_by_id = AsyncMock(return_value=None)

        context_repo = AsyncMock()

        tool = GetTargetContextTool(context_repo=context_repo, target_repo=target_repo)

        # Act & Assert
        with pytest.raises(ToolError) as exc_info:
            await tool.execute(target_id=target_id)
        assert "Target not found" in str(exc_info.value)


class TestUpdateTargetContextTool:
    """Tests for UpdateTargetContextTool."""

    @pytest.mark.unit
    async def test_update_context_replace_mode(self):
        """Test updating context in replace mode."""
        # Arrange
        target_id = str(uuid4())
        target = MagicMock(spec=Target)
        target.id = UUID(target_id)
        target.host = "example.com"

        current = MagicMock(spec=TargetContext)
        current.id = uuid4()
        current.version = 1
        current.user_context = "Old notes"
        current.agent_context = "Old agent notes"

        new_context = MagicMock(spec=TargetContext)
        new_context.id = uuid4()
        new_context.version = 2
        new_context.target_id = UUID(target_id)
        new_context.created_at = datetime.now(UTC)

        target_repo = AsyncMock()
        target_repo.get_by_id = AsyncMock(return_value=target)

        context_repo = AsyncMock()
        context_repo.get_current = AsyncMock(return_value=current)
        context_repo.create_version = AsyncMock(return_value=new_context)

        tool = UpdateTargetContextTool(
            context_repo=context_repo, target_repo=target_repo
        )

        # Act
        result = await tool.execute(
            target_id=target_id,
            user_context="New notes",
            append_mode=False,
        )

        # Assert
        assert result["status"] == "success"
        assert result["version"] == 2
        assert result["previous_version"] == 1
        assert result["append_mode"] is False
        # Verify create_version was called with new content
        context_repo.create_version.assert_called_once()
        call_args = context_repo.create_version.call_args
        assert call_args.kwargs["user_context"] == "New notes"
        assert call_args.kwargs["agent_context"] == "Old agent notes"  # Kept

    @pytest.mark.unit
    async def test_update_context_append_mode(self):
        """Test updating context in append mode."""
        # Arrange
        target_id = str(uuid4())
        target = MagicMock(spec=Target)
        target.id = UUID(target_id)
        target.host = "example.com"

        current = MagicMock(spec=TargetContext)
        current.id = uuid4()
        current.version = 1
        current.user_context = "Existing notes"
        current.agent_context = "Existing agent notes"

        new_context = MagicMock(spec=TargetContext)
        new_context.id = uuid4()
        new_context.version = 2
        new_context.target_id = UUID(target_id)
        new_context.created_at = datetime.now(UTC)

        target_repo = AsyncMock()
        target_repo.get_by_id = AsyncMock(return_value=target)

        context_repo = AsyncMock()
        context_repo.get_current = AsyncMock(return_value=current)
        context_repo.create_version = AsyncMock(return_value=new_context)

        tool = UpdateTargetContextTool(
            context_repo=context_repo, target_repo=target_repo
        )

        # Act
        result = await tool.execute(
            target_id=target_id,
            user_context="Additional notes",
            append_mode=True,
        )

        # Assert
        assert result["status"] == "success"
        assert result["append_mode"] is True
        # Verify create_version was called with appended content
        context_repo.create_version.assert_called_once()
        call_args = context_repo.create_version.call_args
        assert "Existing notes" in call_args.kwargs["user_context"]
        assert "Additional notes" in call_args.kwargs["user_context"]

    @pytest.mark.unit
    async def test_update_context_no_current(self):
        """Test updating context when no current version exists."""
        # Arrange
        target_id = str(uuid4())
        target = MagicMock(spec=Target)
        target.id = UUID(target_id)
        target.host = "example.com"

        new_context = MagicMock(spec=TargetContext)
        new_context.id = uuid4()
        new_context.version = 1
        new_context.target_id = UUID(target_id)
        new_context.created_at = datetime.now(UTC)

        target_repo = AsyncMock()
        target_repo.get_by_id = AsyncMock(return_value=target)

        context_repo = AsyncMock()
        context_repo.get_current = AsyncMock(return_value=None)
        context_repo.create_version = AsyncMock(return_value=new_context)

        tool = UpdateTargetContextTool(
            context_repo=context_repo, target_repo=target_repo
        )

        # Act
        result = await tool.execute(
            target_id=target_id,
            user_context="First notes",
        )

        # Assert
        assert result["status"] == "success"
        assert result["version"] == 1
        assert result["previous_version"] is None

    @pytest.mark.unit
    async def test_update_context_major_version(self):
        """Test creating a major version update."""
        # Arrange
        target_id = str(uuid4())
        target = MagicMock(spec=Target)
        target.id = UUID(target_id)
        target.host = "example.com"

        current = MagicMock(spec=TargetContext)
        current.id = uuid4()
        current.version = 5

        new_context = MagicMock(spec=TargetContext)
        new_context.id = uuid4()
        new_context.version = 6
        new_context.target_id = UUID(target_id)
        new_context.created_at = datetime.now(UTC)

        target_repo = AsyncMock()
        target_repo.get_by_id = AsyncMock(return_value=target)

        context_repo = AsyncMock()
        context_repo.get_current = AsyncMock(return_value=current)
        context_repo.create_version = AsyncMock(return_value=new_context)

        tool = UpdateTargetContextTool(
            context_repo=context_repo, target_repo=target_repo
        )

        # Act
        result = await tool.execute(
            target_id=target_id,
            user_context="Major update",
            change_summary="Significant findings",
            is_major_version=True,
        )

        # Assert
        assert result["status"] == "success"
        # Verify is_major_version was passed
        context_repo.create_version.assert_called_once()
        call_args = context_repo.create_version.call_args
        assert call_args.kwargs["is_major_version"] is True
        assert call_args.kwargs["change_summary"] == "Significant findings"
