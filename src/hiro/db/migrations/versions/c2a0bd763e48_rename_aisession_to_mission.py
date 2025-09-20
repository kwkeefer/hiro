"""rename_aisession_to_mission

Revision ID: c2a0bd763e48
Revises: 01ec0f0735be
Create Date: 2025-01-19 21:45:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c2a0bd763e48"
down_revision: str | None = "01ec0f0735be"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Rename ai_sessions table to missions and add mission-specific fields.
    Also updates all related foreign key constraints and indexes.
    """

    # First, rename the table
    op.rename_table("ai_sessions", "missions")

    # Add new mission-specific columns
    op.add_column(
        "missions",
        sa.Column(
            "mission_type", sa.String(50), nullable=True, server_default="general"
        ),
    )
    op.add_column("missions", sa.Column("hypothesis", sa.Text(), nullable=True))
    op.add_column("missions", sa.Column("goal", sa.Text(), nullable=True))
    op.add_column(
        "missions",
        sa.Column("scope", postgresql.JSONB(), nullable=True, server_default="{}"),
    )
    op.add_column(
        "missions",
        sa.Column("findings", postgresql.JSONB(), nullable=True, server_default="{}"),
    )
    op.add_column(
        "missions",
        sa.Column("patterns", postgresql.JSONB(), nullable=True, server_default="{}"),
    )
    op.add_column(
        "missions",
        sa.Column(
            "successful_techniques",
            postgresql.ARRAY(sa.Text()),
            nullable=True,
            server_default="{}",
        ),
    )
    op.add_column(
        "missions", sa.Column("confidence_score", sa.Numeric(3, 2), nullable=True)
    )

    # Rename 'objective' column to 'goal' if it exists, otherwise we'll use the new 'goal' column
    # Check if objective column exists first
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("missions")]

    if "objective" in columns and "goal" not in columns:
        # Drop the newly added goal column and rename objective instead
        op.drop_column("missions", "goal")
        op.alter_column("missions", "objective", new_column_name="goal")
    elif "objective" in columns:
        # Copy objective data to goal and drop objective
        op.execute("UPDATE missions SET goal = objective WHERE objective IS NOT NULL")
        op.drop_column("missions", "objective")

    # Update foreign key constraints in related tables

    # 1. Update http_requests table - rename session_id to mission_id
    op.alter_column("http_requests", "session_id", new_column_name="mission_id")

    # 2. Update target_attempts table - rename session_id to mission_id
    op.alter_column("target_attempts", "session_id", new_column_name="mission_id")

    # 3. Update session_targets junction table
    op.rename_table("session_targets", "mission_targets")
    op.alter_column("mission_targets", "session_id", new_column_name="mission_id")

    # Update foreign key constraints
    # Drop old constraints
    op.drop_constraint(
        "http_requests_session_id_fkey", "http_requests", type_="foreignkey"
    )
    op.drop_constraint(
        "target_attempts_session_id_fkey", "target_attempts", type_="foreignkey"
    )
    op.drop_constraint(
        "session_targets_session_id_fkey", "mission_targets", type_="foreignkey"
    )

    # Create new constraints with updated names
    op.create_foreign_key(
        "http_requests_mission_id_fkey",
        "http_requests",
        "missions",
        ["mission_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "target_attempts_mission_id_fkey",
        "target_attempts",
        "missions",
        ["mission_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "mission_targets_mission_id_fkey",
        "mission_targets",
        "missions",
        ["mission_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Update indexes
    op.drop_index("ix_http_request_session", "http_requests")
    op.create_index("ix_http_request_mission", "http_requests", ["mission_id"])

    op.drop_index("ix_ai_session_status_created", "missions")
    op.create_index("ix_mission_status_created", "missions", ["status", "created_at"])

    # Create index on mission_type for faster filtering
    op.create_index("ix_missions_mission_type", "missions", ["mission_type"])


def downgrade() -> None:
    """
    Revert the changes - rename missions back to ai_sessions
    and remove mission-specific fields.
    """

    # Revert indexes
    op.drop_index("ix_missions_mission_type", "missions")
    op.drop_index("ix_mission_status_created", "missions")
    op.create_index(
        "ix_ai_session_status_created", "missions", ["status", "created_at"]
    )

    op.drop_index("ix_http_request_mission", "http_requests")
    op.create_index("ix_http_request_session", "http_requests", ["session_id"])

    # Revert foreign key constraints
    op.drop_constraint(
        "http_requests_mission_id_fkey", "http_requests", type_="foreignkey"
    )
    op.drop_constraint(
        "target_attempts_mission_id_fkey", "target_attempts", type_="foreignkey"
    )
    op.drop_constraint(
        "mission_targets_mission_id_fkey", "mission_targets", type_="foreignkey"
    )

    # Recreate old constraints
    op.create_foreign_key(
        "http_requests_session_id_fkey",
        "http_requests",
        "ai_sessions",
        ["session_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "target_attempts_session_id_fkey",
        "target_attempts",
        "ai_sessions",
        ["session_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "session_targets_session_id_fkey",
        "session_targets",
        "ai_sessions",
        ["session_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Rename columns back
    op.alter_column("http_requests", "mission_id", new_column_name="session_id")
    op.alter_column("target_attempts", "mission_id", new_column_name="session_id")
    op.alter_column("mission_targets", "mission_id", new_column_name="session_id")

    # Rename junction table back
    op.rename_table("mission_targets", "session_targets")

    # Rename goal back to objective
    op.alter_column("missions", "goal", new_column_name="objective")

    # Drop mission-specific columns
    op.drop_column("missions", "mission_type")
    op.drop_column("missions", "hypothesis")
    op.drop_column("missions", "scope")
    op.drop_column("missions", "findings")
    op.drop_column("missions", "patterns")
    op.drop_column("missions", "successful_techniques")
    op.drop_column("missions", "confidence_score")

    # Rename table back
    op.rename_table("missions", "ai_sessions")
