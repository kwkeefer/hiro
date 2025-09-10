"""Initial schema with targets, notes, attempts, sessions, requests

Revision ID: 3e86b93dd6ea
Revises:
Create Date: 2025-09-09 10:09:43.314454

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "3e86b93dd6ea"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create targets table
    op.create_table(
        "targets",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("host", sa.String(255), nullable=False),
        sa.Column("port", sa.Integer(), nullable=True),
        sa.Column("protocol", sa.String(10), nullable=False),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column(
            "discovery_date",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "last_activity",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("risk_level", sa.String(10), nullable=False, server_default="medium"),
        sa.Column("extra_data", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("host", "port", "protocol", name="uq_target_endpoint"),
        sa.CheckConstraint("protocol IN ('http', 'https')", name="ck_target_protocol"),
        sa.CheckConstraint(
            "status IN ('active', 'inactive', 'blocked', 'completed')",
            name="ck_target_status",
        ),
        sa.CheckConstraint(
            "risk_level IN ('low', 'medium', 'high', 'critical')",
            name="ck_target_risk_level",
        ),
    )

    # Create ai_sessions table
    op.create_table(
        "ai_sessions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("objective", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("extra_data", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "status IN ('active', 'paused', 'completed', 'failed')",
            name="ck_session_status",
        ),
    )

    # Create target_notes table
    op.create_table(
        "target_notes",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("note_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "tags", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"
        ),
        sa.Column("confidence", sa.String(10), nullable=False, server_default="medium"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["target_id"], ["targets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "note_type IN ('reconnaissance', 'vulnerability', 'configuration', 'access', 'other')",
            name="ck_note_type",
        ),
        sa.CheckConstraint(
            "confidence IN ('low', 'medium', 'high')", name="ck_note_confidence"
        ),
    )

    # Create target_attempts table
    op.create_table(
        "target_attempts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("attempt_type", sa.String(50), nullable=False),
        sa.Column("technique", sa.String(255), nullable=False),
        sa.Column("payload", sa.Text(), nullable=True),
        sa.Column("expected_outcome", sa.Text(), nullable=False),
        sa.Column("actual_outcome", sa.Text(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["ai_sessions.id"],
        ),
        sa.ForeignKeyConstraint(["target_id"], ["targets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "attempt_type IN ('scan', 'exploit', 'enumerate', 'bypass', 'escalate', 'other')",
            name="ck_attempt_type",
        ),
    )

    # Create http_requests table
    op.create_table(
        "http_requests",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("host", sa.String(255), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("query_params", sa.JSON(), nullable=True),
        sa.Column("headers", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("cookies", sa.JSON(), nullable=True),
        sa.Column("request_body", sa.Text(), nullable=True),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("response_headers", sa.JSON(), nullable=True),
        sa.Column("response_body", sa.Text(), nullable=True),
        sa.Column("response_size", sa.Integer(), nullable=True),
        sa.Column("elapsed_ms", sa.Numeric(10, 3), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["ai_sessions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create request_tags table
    op.create_table(
        "request_tags",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tag", sa.String(100), nullable=False),
        sa.Column("value", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["request_id"], ["http_requests.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id", "tag", name="uq_request_tag"),
    )

    # Create target_requests association table
    op.create_table(
        "target_requests",
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["request_id"], ["http_requests.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["target_id"], ["targets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("target_id", "request_id"),
    )

    # Create session_targets association table
    op.create_table(
        "session_targets",
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["session_id"], ["ai_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_id"], ["targets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("session_id", "target_id"),
    )

    # Create indexes for performance
    op.create_index("ix_target_host_activity", "targets", ["host", "last_activity"])
    op.create_index("ix_target_status_risk", "targets", ["status", "risk_level"])
    op.create_index(
        "ix_target_note_target_type", "target_notes", ["target_id", "note_type"]
    )
    op.create_index(
        "ix_target_note_tags", "target_notes", ["tags"], postgresql_using="gin"
    )
    op.create_index(
        "ix_target_attempt_target_success", "target_attempts", ["target_id", "success"]
    )
    op.create_index("ix_target_attempt_technique", "target_attempts", ["technique"])
    op.create_index("ix_target_attempt_created", "target_attempts", ["created_at"])
    op.create_index(
        "ix_ai_session_status_created", "ai_sessions", ["status", "created_at"]
    )
    op.create_index(
        "ix_http_request_host_created", "http_requests", ["host", "created_at"]
    )
    op.create_index(
        "ix_http_request_method_status", "http_requests", ["method", "status_code"]
    )
    op.create_index("ix_http_request_session", "http_requests", ["session_id"])
    op.create_index("ix_request_tag_tag", "request_tags", ["tag"])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index("ix_request_tag_tag", table_name="request_tags")
    op.drop_index("ix_http_request_session", table_name="http_requests")
    op.drop_index("ix_http_request_method_status", table_name="http_requests")
    op.drop_index("ix_http_request_host_created", table_name="http_requests")
    op.drop_index("ix_ai_session_status_created", table_name="ai_sessions")
    op.drop_index("ix_target_attempt_created", table_name="target_attempts")
    op.drop_index("ix_target_attempt_technique", table_name="target_attempts")
    op.drop_index("ix_target_attempt_target_success", table_name="target_attempts")
    op.drop_index("ix_target_note_tags", table_name="target_notes")
    op.drop_index("ix_target_note_target_type", table_name="target_notes")
    op.drop_index("ix_target_status_risk", table_name="targets")
    op.drop_index("ix_target_host_activity", table_name="targets")

    # Drop association tables
    op.drop_table("session_targets")
    op.drop_table("target_requests")

    # Drop main tables (order matters due to foreign keys)
    op.drop_table("request_tags")
    op.drop_table("http_requests")
    op.drop_table("target_attempts")
    op.drop_table("target_notes")
    op.drop_table("ai_sessions")
    op.drop_table("targets")
