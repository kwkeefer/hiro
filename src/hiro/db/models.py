"""SQLAlchemy database models."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    ARRAY,
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func

try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    Vector = None


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all database models."""

    pass


# Enums for database constraints
class TargetStatus(str, Enum):
    """Target status options."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    BLOCKED = "blocked"
    COMPLETED = "completed"


class RiskLevel(str, Enum):
    """Risk level options."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NoteType(str, Enum):
    """Note type options."""

    RECONNAISSANCE = "reconnaissance"
    VULNERABILITY = "vulnerability"
    CONFIGURATION = "configuration"
    ACCESS = "access"
    OTHER = "other"


class ConfidenceLevel(str, Enum):
    """Confidence level options."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AttemptType(str, Enum):
    """Attempt type options."""

    SCAN = "scan"
    EXPLOIT = "exploit"
    ENUMERATE = "enumerate"
    BYPASS = "bypass"
    ESCALATE = "escalate"
    OTHER = "other"


class SessionStatus(str, Enum):
    """Session status options."""

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class ContextChangeType(str, Enum):
    """Context change type options."""

    USER_EDIT = "user_edit"
    AGENT_UPDATE = "agent_update"
    INITIAL = "initial"
    ROLLBACK = "rollback"


# Core Models
class Target(Base):
    """Target hosts/endpoints for testing."""

    __tablename__ = "targets"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    protocol: Mapped[str] = mapped_column(String(10), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[TargetStatus] = mapped_column(
        String(20), nullable=False, default=TargetStatus.ACTIVE
    )
    discovery_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_activity: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    risk_level: Mapped[RiskLevel] = mapped_column(
        String(10), nullable=False, default=RiskLevel.MEDIUM
    )
    extra_data: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )

    # Link to current context version
    current_context_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    current_context: Mapped[Optional["TargetContext"]] = relationship(
        "TargetContext",
        foreign_keys=[current_context_id],
        primaryjoin="Target.current_context_id == TargetContext.id",
        post_update=True,  # Handle circular dependency
    )
    context_versions: Mapped[list["TargetContext"]] = relationship(
        "TargetContext",
        foreign_keys="TargetContext.target_id",
        back_populates="target",
        cascade="all, delete-orphan",
        order_by="desc(TargetContext.version)",
    )
    notes: Mapped[list["TargetNote"]] = relationship(
        "TargetNote", back_populates="target", cascade="all, delete-orphan"
    )
    attempts: Mapped[list["TargetAttempt"]] = relationship(
        "TargetAttempt", back_populates="target", cascade="all, delete-orphan"
    )
    requests: Mapped[list["HttpRequest"]] = relationship(
        "HttpRequest", secondary="target_requests", back_populates="targets"
    )
    missions: Mapped[list["Mission"]] = relationship(
        "Mission", secondary="mission_targets", back_populates="targets"
    )

    __table_args__ = (
        UniqueConstraint("host", "port", "protocol", name="uq_target_endpoint"),
        Index("ix_target_host_activity", "host", "last_activity"),
        Index("ix_target_status_risk", "status", "risk_level"),
        Index("ix_target_current_context", "current_context_id"),
        ForeignKeyConstraint(
            ["current_context_id"],
            ["target_contexts.id"],
            name="fk_targets_current_context",
            use_alter=True,
            ondelete="SET NULL",
        ),
    )


class TargetContext(Base):
    """Immutable context versions for targets."""

    __tablename__ = "target_contexts"

    # Primary key and versioning
    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    target_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("targets.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)

    # Context content
    user_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    agent_context: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Versioning metadata
    parent_version_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("target_contexts.id"),
        nullable=True,
    )
    change_type: Mapped[ContextChangeType] = mapped_column(String(20), nullable=False)
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'user' or 'agent'

    # Metadata
    is_major_version: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    tokens_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    target: Mapped["Target"] = relationship(
        "Target",
        foreign_keys=[target_id],
        back_populates="context_versions",
    )
    parent_version: Mapped[Optional["TargetContext"]] = relationship(
        "TargetContext",
        remote_side=[id],
        foreign_keys=[parent_version_id],
    )

    @hybrid_property
    def combined_context(self) -> str:
        """Get combined user and agent context."""
        parts = []
        if self.user_context:
            parts.append(f"## User Context\n\n{self.user_context}")
        if self.agent_context:
            parts.append(f"## Agent Context\n\n{self.agent_context}")
        return "\n\n---\n\n".join(parts) if parts else ""

    __table_args__ = (
        UniqueConstraint("target_id", "version", name="uq_target_context_version"),
        Index("ix_target_context_target_version", "target_id", "version"),
        Index("ix_target_context_target_created", "target_id", "created_at"),
        Index("ix_target_context_parent", "parent_version_id"),
    )


class TargetNote(Base):
    """Notes and observations about targets."""

    __tablename__ = "target_notes"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    target_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("targets.id", ondelete="CASCADE"),
        nullable=False,
    )
    note_type: Mapped[NoteType] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    confidence: Mapped[ConfidenceLevel] = mapped_column(
        String(10), nullable=False, default=ConfidenceLevel.MEDIUM
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    target: Mapped["Target"] = relationship("Target", back_populates="notes")

    __table_args__ = (
        Index("ix_target_note_target_type", "target_id", "note_type"),
        Index("ix_target_note_tags", "tags", postgresql_using="gin"),
    )


class TargetAttempt(Base):
    """Attack attempts against targets."""

    __tablename__ = "target_attempts"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    target_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("targets.id", ondelete="CASCADE"),
        nullable=False,
    )
    mission_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True), ForeignKey("missions.id"), nullable=True
    )
    attempt_type: Mapped[AttemptType] = mapped_column(String(50), nullable=False)
    technique: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_outcome: Mapped[str] = mapped_column(Text, nullable=False)
    actual_outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    success: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    target: Mapped["Target"] = relationship("Target", back_populates="attempts")
    mission: Mapped[Optional["Mission"]] = relationship(
        "Mission", back_populates="attempts"
    )

    __table_args__ = (
        Index("ix_target_attempt_target_success", "target_id", "success"),
        Index("ix_target_attempt_technique", "technique"),
        Index("ix_target_attempt_created", "created_at"),
    )


class Mission(Base):
    """Security testing missions (formerly AiSession)."""

    __tablename__ = "missions"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    mission_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True, default="general"
    )
    hypothesis: Mapped[str | None] = mapped_column(Text, nullable=True)
    scope: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, default=dict
    )
    findings: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, default=dict
    )
    patterns: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, default=dict
    )
    successful_techniques: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True, default=list
    )
    confidence_score: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)

    # Vector embeddings for semantic search
    goal_embedding = mapped_column(Vector(384) if Vector else None, nullable=True)
    hypothesis_embedding = mapped_column(Vector(384) if Vector else None, nullable=True)

    status: Mapped[SessionStatus] = mapped_column(
        String(20), nullable=False, default=SessionStatus.ACTIVE
    )
    extra_data: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    requests: Mapped[list["HttpRequest"]] = relationship(
        "HttpRequest", back_populates="mission"
    )
    attempts: Mapped[list["TargetAttempt"]] = relationship(
        "TargetAttempt", back_populates="mission"
    )
    targets: Mapped[list["Target"]] = relationship(
        "Target", secondary="mission_targets", back_populates="missions"
    )
    mission_actions: Mapped[list["MissionAction"]] = relationship(
        "MissionAction", back_populates="mission"
    )

    __table_args__ = (Index("ix_mission_status_created", "status", "created_at"),)


class HttpRequest(Base):
    """HTTP request/response logging."""

    __tablename__ = "http_requests"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    mission_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True), ForeignKey("missions.id"), nullable=True
    )
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    query_params: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    headers: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    cookies: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    request_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_headers: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    elapsed_ms: Mapped[float | None] = mapped_column(Numeric(10, 3), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    mission: Mapped[Optional["Mission"]] = relationship(
        "Mission", back_populates="requests"
    )
    targets: Mapped[list["Target"]] = relationship(
        "Target", secondary="target_requests", back_populates="requests"
    )
    tags: Mapped[list["RequestTag"]] = relationship(
        "RequestTag", back_populates="request", cascade="all, delete-orphan"
    )
    mission_actions: Mapped[list["MissionAction"]] = relationship(
        "MissionAction", secondary="action_requests", back_populates="requests"
    )

    __table_args__ = (
        Index("ix_http_request_host_created", "host", "created_at"),
        Index("ix_http_request_method_status", "method", "status_code"),
        Index("ix_http_request_mission", "mission_id"),
    )


class RequestTag(Base):
    """Tags for HTTP requests."""

    __tablename__ = "request_tags"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    request_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("http_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    tag: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    request: Mapped["HttpRequest"] = relationship("HttpRequest", back_populates="tags")

    __table_args__ = (
        UniqueConstraint("request_id", "tag", name="uq_request_tag"),
        Index("ix_request_tag_tag", "tag"),
    )


class MissionAction(Base):
    """Actions taken during security testing missions."""

    __tablename__ = "mission_actions"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    mission_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("missions.id", ondelete="CASCADE"),
        nullable=True,
    )
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    technique: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    learning: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Vector embeddings for semantic search
    action_embedding = mapped_column(Vector(384) if Vector else None, nullable=True)
    result_embedding = mapped_column(Vector(384) if Vector else None, nullable=True)

    meta_data: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    mission: Mapped[Optional["Mission"]] = relationship(
        "Mission", back_populates="mission_actions"
    )
    requests: Mapped[list["HttpRequest"]] = relationship(
        "HttpRequest", secondary="action_requests", back_populates="mission_actions"
    )


class TechniqueLibrary(Base):
    """Library of discovered techniques and patterns."""

    __tablename__ = "technique_library"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Vector embedding for semantic search
    content_embedding = mapped_column(Vector(384) if Vector else None, nullable=True)

    meta_data: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


# Association tables for many-to-many relationships
class TargetRequest(Base):
    """Association between targets and HTTP requests."""

    __tablename__ = "target_requests"

    target_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("targets.id", ondelete="CASCADE"),
        primary_key=True,
    )
    request_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("http_requests.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ActionRequest(Base):
    """Association between mission actions and HTTP requests."""

    __tablename__ = "action_requests"

    action_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("mission_actions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    request_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("http_requests.id", ondelete="CASCADE"),
        primary_key=True,
    )


class MissionTarget(Base):
    """Association between missions and targets."""

    __tablename__ = "mission_targets"

    mission_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("missions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    target_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("targets.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
