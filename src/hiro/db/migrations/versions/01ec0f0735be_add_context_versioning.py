"""Add context versioning

Revision ID: 01ec0f0735be
Revises: 3e86b93dd6ea
Create Date: 2025-09-12 18:48:02.911165

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "01ec0f0735be"
down_revision: str | Sequence[str] | None = "3e86b93dd6ea"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema to add context versioning."""

    # Create target_contexts table
    op.create_table(
        "target_contexts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("user_context", sa.Text(), nullable=True),
        sa.Column("agent_context", sa.Text(), nullable=True),
        sa.Column("parent_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("change_type", sa.String(20), nullable=False),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(50), nullable=False),
        sa.Column(
            "is_major_version", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column("tokens_count", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["parent_version_id"],
            ["target_contexts.id"],
        ),
        sa.ForeignKeyConstraint(["target_id"], ["targets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("target_id", "version", name="uq_target_context_version"),
    )

    # Create indexes for target_contexts
    op.create_index(
        "ix_target_context_target_version", "target_contexts", ["target_id", "version"]
    )
    op.create_index(
        "ix_target_context_target_created",
        "target_contexts",
        ["target_id", "created_at"],
    )
    op.create_index(
        "ix_target_context_parent", "target_contexts", ["parent_version_id"]
    )

    # Add current_context_id to targets table
    op.add_column(
        "targets",
        sa.Column("current_context_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    # Create index for current_context_id
    op.create_index("ix_target_current_context", "targets", ["current_context_id"])

    # Add foreign key constraint
    op.create_foreign_key(
        "fk_targets_current_context",
        "targets",
        "target_contexts",
        ["current_context_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Downgrade schema to remove context versioning."""

    # Drop foreign key constraint
    op.drop_constraint("fk_targets_current_context", "targets", type_="foreignkey")

    # Drop index and column from targets
    op.drop_index("ix_target_current_context", "targets")
    op.drop_column("targets", "current_context_id")

    # Drop indexes from target_contexts
    op.drop_index("ix_target_context_parent", "target_contexts")
    op.drop_index("ix_target_context_target_created", "target_contexts")
    op.drop_index("ix_target_context_target_version", "target_contexts")

    # Drop target_contexts table
    op.drop_table("target_contexts")
