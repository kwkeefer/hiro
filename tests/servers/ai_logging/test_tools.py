"""Unit tests for AI logging tools with real database."""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from hiro.core.mcp.exceptions import ToolError
from hiro.db.models import RiskLevel, TargetStatus
from hiro.db.repositories import TargetRepository
from hiro.servers.ai_logging.tools import (
    CreateTargetTool,
    GetTargetSummaryTool,
    SearchTargetsTool,
    UpdateTargetStatusTool,
)


@pytest.mark.database
class TestCreateTargetTool:
    """Test CreateTargetTool with real database."""

    @pytest.mark.asyncio
    async def test_create_target_success(self, create_target_tool: CreateTargetTool):
        """Test successful target creation."""
        # Arrange
        host = "test-api.example.com"
        port = 443
        protocol = "https"
        title = "Test API Server"

        # Act
        result = await create_target_tool.execute(
            host=host,
            port=port,
            protocol=protocol,
            title=title,
            status="active",
            risk_level="medium",
        )

        # Assert
        assert result["status"] == "created"
        assert result["host"] == host
        assert result["port"] == port
        assert result["protocol"] == protocol
        # Note: Enum values are serialized as strings in tool responses
        assert result["target_status"] == "active"
        assert result["risk_level"] == "medium"
        assert "target_id" in result
        # TODO: Consider if checking exact message text is necessary
        # For now, just verify message exists and contains key info
        assert "message" in result
        assert title in result["message"]

    @pytest.mark.asyncio
    async def test_create_target_minimal(self, create_target_tool: CreateTargetTool):
        """Test target creation with minimal required fields."""
        # Arrange
        host = "minimal.example.com"

        # Act
        result = await create_target_tool.execute(host=host)

        # Assert
        assert result["status"] == "created"
        assert result["host"] == host
        assert result["port"] is None
        assert result["protocol"] == "http"  # Default
        # Note: Enum values are serialized as strings in tool responses
        assert result["target_status"] == "active"  # Default
        assert result["risk_level"] == "medium"  # Default

    @pytest.mark.asyncio
    async def test_create_duplicate_target(
        self, create_target_tool: CreateTargetTool, sample_target
    ):
        """Test that duplicate targets are handled correctly."""
        # Arrange - sample_target already exists with host "test.example.com"

        # Act - Try to create duplicate
        result = await create_target_tool.execute(
            host=sample_target.host, port=sample_target.port, protocol="https"
        )

        # Assert - Should return existing
        assert result["status"] == "exists"
        assert result["host"] == sample_target.host

    @pytest.mark.asyncio
    async def test_create_target_invalid_port(
        self, create_target_tool: CreateTargetTool
    ):
        """Test target creation with invalid port number."""
        # Act & Assert - Just verify it raises ToolError for invalid input
        with pytest.raises(ToolError):
            await create_target_tool.execute(
                host="test.example.com",
                port=99999,  # Invalid port
            )

    @pytest.mark.asyncio
    async def test_create_target_all_statuses(
        self, create_target_tool: CreateTargetTool
    ):
        """Test target creation with all valid status values."""
        statuses = ["active", "inactive", "blocked", "completed"]

        for status in statuses:
            # Act
            result = await create_target_tool.execute(
                host=f"{status}.example.com", status=status
            )

            # Assert
            assert result["status"] == "created"
            assert result["target_status"] == status

    @pytest.mark.asyncio
    async def test_create_target_all_risk_levels(
        self, create_target_tool: CreateTargetTool
    ):
        """Test target creation with all valid risk levels."""
        risk_levels = ["low", "medium", "high", "critical"]

        for risk_level in risk_levels:
            # Act
            result = await create_target_tool.execute(
                host=f"{risk_level}-risk.example.com", risk_level=risk_level
            )

            # Assert
            assert result["status"] == "created"
            assert result["risk_level"] == risk_level


@pytest.mark.database
class TestUpdateTargetStatusTool:
    """Test UpdateTargetStatusTool with real database."""

    @pytest.mark.asyncio
    async def test_update_target_status_success(
        self, update_target_tool: UpdateTargetStatusTool, sample_target
    ):
        """Test successful target status update."""
        # Arrange
        new_status = "completed"
        new_risk = "high"

        # Act
        result = await update_target_tool.execute(
            target_id=str(sample_target.id),
            status=new_status,
            risk_level=new_risk,
        )

        # Assert
        assert result["status"] == "updated"
        assert result["target_id"] == str(sample_target.id)
        assert result["current_status"] == new_status
        assert result["risk_level"] == new_risk
        # TODO: Consider if checking exact message text is necessary
        # For now, just verify message exists and contains key info
        assert "message" in result
        assert sample_target.title in result["message"]

    @pytest.mark.asyncio
    async def test_update_target_partial(
        self, update_target_tool: UpdateTargetStatusTool, sample_target
    ):
        """Test partial target update (only status)."""
        # Arrange
        new_status = "blocked"

        # Act
        result = await update_target_tool.execute(
            target_id=str(sample_target.id), status=new_status
        )

        # Assert
        assert result["status"] == "updated"
        assert result["current_status"] == new_status
        # Other fields should remain unchanged
        assert result["risk_level"] == sample_target.risk_level
        assert result["host"] == sample_target.host

    @pytest.mark.asyncio
    async def test_update_nonexistent_target(
        self, update_target_tool: UpdateTargetStatusTool
    ):
        """Test updating a target that doesn't exist."""
        # Arrange
        fake_id = str(uuid4())

        # Act & Assert - Verify it raises ToolError for nonexistent target
        with pytest.raises(ToolError):
            await update_target_tool.execute(target_id=fake_id, status="active")

    @pytest.mark.asyncio
    async def test_update_invalid_target_id(
        self, update_target_tool: UpdateTargetStatusTool
    ):
        """Test updating with invalid target ID format."""
        # Act & Assert - Verify it raises ToolError for invalid UUID format
        with pytest.raises(ToolError):
            await update_target_tool.execute(target_id="not-a-uuid", status="active")


@pytest.mark.database
class TestGetTargetSummaryTool:
    """Test GetTargetSummaryTool with real database."""

    @pytest.mark.asyncio
    async def test_get_target_summary_simple(
        self, get_summary_tool: GetTargetSummaryTool, sample_target
    ):
        """Test getting summary for a simple target."""
        # Act
        result = await get_summary_tool.execute(target_id=str(sample_target.id))

        # Assert
        assert result["target_id"] == str(sample_target.id)
        assert result["host"] == sample_target.host
        assert result["statistics"]["notes_count"] == 0
        assert result["statistics"]["attempts_count"] == 0
        assert result["statistics"]["requests_count"] == 0

    @pytest.mark.asyncio
    async def test_get_target_summary_with_history(
        self, get_summary_tool: GetTargetSummaryTool, target_with_history
    ):
        """Test getting summary for a target with mission actions."""
        # Arrange
        target = target_with_history["target"]
        actions = target_with_history["actions"]

        # Act
        result = await get_summary_tool.execute(target_id=str(target.id))

        # Assert
        assert result["target_id"] == str(target.id)
        assert result["statistics"]["notes_count"] == 0
        assert result["statistics"]["attempts_count"] == len(actions)
        # Success rate would be 50% (1 success, 1 failure)
        assert result["statistics"]["success_rate"] == "50.0%"

    @pytest.mark.asyncio
    async def test_get_summary_nonexistent_target(
        self, get_summary_tool: GetTargetSummaryTool
    ):
        """Test getting summary for nonexistent target."""
        # Arrange
        fake_id = str(uuid4())

        # Act & Assert - Verify it raises ToolError for nonexistent target
        with pytest.raises(ToolError):
            await get_summary_tool.execute(target_id=fake_id)


@pytest.mark.database
class TestSearchTargetsTool:
    """Test SearchTargetsTool with real database."""

    @pytest.mark.asyncio
    async def test_search_all_targets(
        self, search_targets_tool: SearchTargetsTool, multiple_targets
    ):
        """Test searching without filters returns all targets."""
        # Act
        result = await search_targets_tool.execute()

        # Assert
        assert result["status"] == "success"
        assert result["count"] == len(multiple_targets)
        assert len(result["targets"]) == len(multiple_targets)

    @pytest.mark.asyncio
    async def test_search_by_status(
        self, search_targets_tool: SearchTargetsTool, multiple_targets
    ):
        """Test searching targets by status."""
        # Act
        result = await search_targets_tool.execute(status='["active"]')

        # Assert
        assert result["status"] == "success"
        active_targets = [
            t for t in multiple_targets if t.status == TargetStatus.ACTIVE
        ]
        assert result["count"] == len(active_targets)
        # Note: Enum values are serialized as strings in tool responses
        assert all(t["status"] == "active" for t in result["targets"])

    @pytest.mark.asyncio
    async def test_search_by_risk_level(
        self, search_targets_tool: SearchTargetsTool, multiple_targets
    ):
        """Test searching targets by risk level."""
        # Act
        result = await search_targets_tool.execute(risk_level='["high"]')

        # Assert
        assert result["status"] == "success"
        high_risk = [t for t in multiple_targets if t.risk_level == RiskLevel.HIGH]
        assert result["count"] == len(high_risk)
        # Note: Enum values are serialized as strings in tool responses
        assert all(t["risk_level"] == "high" for t in result["targets"])

    @pytest.mark.asyncio
    async def test_search_by_protocol(
        self, search_targets_tool: SearchTargetsTool, multiple_targets
    ):
        """Test searching targets by protocol."""
        # Arrange - Create targets with specific protocol

        # Act
        result = await search_targets_tool.execute(protocol='["https"]')

        # Assert
        assert result["status"] == "success"
        https_targets = [t for t in multiple_targets if t.protocol == "https"]
        assert result["count"] == len(https_targets)

    @pytest.mark.asyncio
    async def test_search_by_query(
        self, search_targets_tool: SearchTargetsTool, multiple_targets
    ):
        """Test searching targets by text query."""
        # Act
        result = await search_targets_tool.execute(query="api")

        # Assert
        assert result["status"] == "success"
        assert result["count"] > 0
        assert all("api" in t["host"] for t in result["targets"])

    @pytest.mark.asyncio
    async def test_search_with_limit(
        self, search_targets_tool: SearchTargetsTool, multiple_targets
    ):
        """Test searching with result limit."""
        # Act
        limit = 2
        result = await search_targets_tool.execute(limit=limit)

        # Assert
        assert result["status"] == "success"
        assert len(result["targets"]) <= limit
        # Count should equal the limited result count, not the total
        assert result["count"] == len(result["targets"])

    @pytest.mark.asyncio
    async def test_search_combined_filters(
        self, search_targets_tool: SearchTargetsTool, multiple_targets
    ):
        """Test searching with multiple filters combined."""
        # Act
        result = await search_targets_tool.execute(
            status='["active"]', risk_level='["low"]', limit=10
        )

        # Assert
        assert result["status"] == "success"
        matching = [
            t
            for t in multiple_targets
            if t.status == TargetStatus.ACTIVE and t.risk_level == RiskLevel.LOW
        ]
        assert result["count"] == len(matching)

    @pytest.mark.asyncio
    async def test_search_no_results(
        self, search_targets_tool: SearchTargetsTool, multiple_targets
    ):
        """Test search that returns no results."""
        # Act
        result = await search_targets_tool.execute(query="nonexistent.domain")

        # Assert
        assert result["status"] == "success"
        assert result["count"] == 0
        assert result["targets"] == []
        # Message text is informational, just verify it exists
        assert "message" in result

    @pytest.mark.asyncio
    async def test_search_empty_database(self, test_db: AsyncSession):
        """Test searching when database is empty."""
        # Arrange
        tool = SearchTargetsTool(target_repo=TargetRepository(test_db))

        # Act
        result = await tool.execute()

        # Assert
        assert result["status"] == "success"
        assert result["count"] == 0
        assert result["targets"] == []
