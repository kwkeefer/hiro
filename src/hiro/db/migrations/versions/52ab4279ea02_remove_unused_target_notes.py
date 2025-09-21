"""remove_unused_target_notes

Remove the unused TargetNote table and notes field references.
The context system (TargetContext) provides better functionality.

Revision ID: 52ab4279ea02
Revises: c2a0bd763e48
Create Date: 2025-01-21 14:47:59.251415

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "52ab4279ea02"
down_revision: str | None = "c2a0bd763e48"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Remove unused TargetNote table and related fields."""
    # Drop the target_notes table
    op.drop_table("target_notes")

    # Remove notes field from target_attempts if it exists
    # (keeping this for now as it might contain data)
    # op.drop_column('target_attempts', 'notes')


def downgrade() -> None:
    """Restore TargetNote table (data will be lost)."""
    # Recreate the target_notes table
    op.create_table(
        "target_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("note_type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["target_id"], ["targets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Note: We don't restore the notes field in target_attempts
    # as it wasn't removed in the upgrade
