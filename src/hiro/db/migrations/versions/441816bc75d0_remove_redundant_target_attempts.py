"""remove_redundant_target_attempts

Remove the redundant TargetAttempt table. MissionAction provides
all the same functionality and is actively used via the record_action tool.

Revision ID: 441816bc75d0
Revises: a054a87b8494
Create Date: 2025-01-21 15:19:10.673547

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "441816bc75d0"
down_revision: str | None = "a054a87b8494"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Remove unused TargetAttempt table."""
    # Drop the target_attempts table
    op.drop_table("target_attempts")


def downgrade() -> None:
    """Restore TargetAttempt table (data will be lost)."""
    # Recreate the target_attempts table
    op.create_table(
        "target_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mission_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("attempt_type", sa.String(length=50), nullable=False),
        sa.Column("technique", sa.String(length=255), nullable=False),
        sa.Column("payload", sa.Text(), nullable=True),
        sa.Column("expected_outcome", sa.Text(), nullable=False),
        sa.Column("actual_outcome", sa.Text(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["mission_id"],
            ["missions.id"],
        ),
        sa.ForeignKeyConstraint(["target_id"], ["targets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Recreate indexes
    op.create_index("ix_target_attempt_created", "target_attempts", ["created_at"])
    op.create_index(
        "ix_target_attempt_target_success", "target_attempts", ["target_id", "success"]
    )
    op.create_index("ix_target_attempt_technique", "target_attempts", ["technique"])
