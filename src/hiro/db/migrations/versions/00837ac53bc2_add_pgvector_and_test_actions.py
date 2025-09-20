"""add_pgvector_and_mission_actions

Revision ID: 00837ac53bc2
Revises: c2a0bd763e48
Create Date: 2025-09-19 22:06:50.802847

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "00837ac53bc2"
down_revision: str | Sequence[str] | None = "c2a0bd763e48"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add pgvector extension and create test actions tables with vector support."""

    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Add vector columns to missions table (some columns may already exist from previous migration)
    # Only add the vector embedding columns, as other columns were added in previous migration
    op.add_column("missions", sa.Column("goal_embedding", Vector(384), nullable=True))
    op.add_column(
        "missions", sa.Column("hypothesis_embedding", Vector(384), nullable=True)
    )

    # Create mission_actions table
    op.create_table(
        "mission_actions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("mission_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action_type", sa.String(50), nullable=False),
        sa.Column("technique", sa.String(255), nullable=False),
        sa.Column("payload", sa.Text(), nullable=True),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=True, server_default="false"),
        sa.Column("learning", sa.Text(), nullable=True),
        sa.Column("action_embedding", Vector(384), nullable=True),
        sa.Column("result_embedding", Vector(384), nullable=True),
        sa.Column(
            "meta_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default="{}",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["mission_id"], ["missions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create action_requests junction table
    op.create_table(
        "action_requests",
        sa.Column("action_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["action_id"], ["mission_actions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["request_id"], ["http_requests.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("action_id", "request_id"),
    )

    # Create technique_library table
    op.create_table(
        "technique_library",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_embedding", Vector(384), nullable=True),
        sa.Column(
            "meta_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default="{}",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for vector similarity search
    # Using ivfflat for better performance on large datasets
    op.execute("""
        CREATE INDEX mission_actions_action_embedding_idx ON mission_actions
        USING ivfflat (action_embedding vector_cosine_ops)
        WITH (lists = 100)
    """)

    op.execute("""
        CREATE INDEX mission_actions_result_embedding_idx ON mission_actions
        USING ivfflat (result_embedding vector_cosine_ops)
        WITH (lists = 100)
    """)

    op.execute("""
        CREATE INDEX technique_library_embedding_idx ON technique_library
        USING ivfflat (content_embedding vector_cosine_ops)
        WITH (lists = 50)
    """)

    # Create indexes for missions vector columns
    op.execute("""
        CREATE INDEX missions_goal_embedding_idx ON missions
        USING ivfflat (goal_embedding vector_cosine_ops)
        WITH (lists = 100)
    """)

    op.execute("""
        CREATE INDEX missions_hypothesis_embedding_idx ON missions
        USING ivfflat (hypothesis_embedding vector_cosine_ops)
        WITH (lists = 100)
    """)


def downgrade() -> None:
    """Remove pgvector support and test actions tables."""

    # Drop indexes first
    op.execute("DROP INDEX IF EXISTS missions_hypothesis_embedding_idx")
    op.execute("DROP INDEX IF EXISTS missions_goal_embedding_idx")
    op.execute("DROP INDEX IF EXISTS technique_library_embedding_idx")
    op.execute("DROP INDEX IF EXISTS mission_actions_result_embedding_idx")
    op.execute("DROP INDEX IF EXISTS mission_actions_action_embedding_idx")

    # Drop tables
    op.drop_table("technique_library")
    op.drop_table("action_requests")
    op.drop_table("mission_actions")

    # Remove only the vector columns we added
    op.drop_column("missions", "hypothesis_embedding")
    op.drop_column("missions", "goal_embedding")

    # Note: We don't drop the vector extension as other parts might use it
