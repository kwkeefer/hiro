"""SQLAlchemy database models."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    ARRAY,
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


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
    extra_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
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
    notes: Mapped[list["TargetNote"]] = relationship(
        "TargetNote", back_populates="target", cascade="all, delete-orphan"
    )
    attempts: Mapped[list["TargetAttempt"]] = relationship(
        "TargetAttempt", back_populates="target", cascade="all, delete-orphan"
    )
    requests: Mapped[list["HttpRequest"]] = relationship(
        "HttpRequest", secondary="target_requests", back_populates="targets"
    )
    sessions: Mapped[list["AiSession"]] = relationship(
        "AiSession", secondary="session_targets", back_populates="targets"
    )

    __table_args__ = (
        UniqueConstraint("host", "port", "protocol", name="uq_target_endpoint"),
        Index("ix_target_host_activity", "host", "last_activity"),
        Index("ix_target_status_risk", "status", "risk_level"),
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
    session_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True), ForeignKey("ai_sessions.id"), nullable=True
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
    session: Mapped[Optional["AiSession"]] = relationship(
        "AiSession", back_populates="attempts"
    )

    __table_args__ = (
        Index("ix_target_attempt_target_success", "target_id", "success"),
        Index("ix_target_attempt_technique", "technique"),
        Index("ix_target_attempt_created", "created_at"),
    )


class AiSession(Base):
    """AI reasoning sessions."""

    __tablename__ = "ai_sessions"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    objective: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[SessionStatus] = mapped_column(
        String(20), nullable=False, default=SessionStatus.ACTIVE
    )
    extra_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    requests: Mapped[list["HttpRequest"]] = relationship(
        "HttpRequest", back_populates="session"
    )
    attempts: Mapped[list["TargetAttempt"]] = relationship(
        "TargetAttempt", back_populates="session"
    )
    targets: Mapped[list["Target"]] = relationship(
        "Target", secondary="session_targets", back_populates="sessions"
    )

    __table_args__ = (Index("ix_ai_session_status_created", "status", "created_at"),)


class HttpRequest(Base):
    """HTTP request/response logging."""

    __tablename__ = "http_requests"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    session_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True), ForeignKey("ai_sessions.id"), nullable=True
    )
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    query_params: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    headers: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    cookies: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    request_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_headers: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    elapsed_ms: Mapped[float | None] = mapped_column(Numeric(10, 3), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    session: Mapped[Optional["AiSession"]] = relationship(
        "AiSession", back_populates="requests"
    )
    targets: Mapped[list["Target"]] = relationship(
        "Target", secondary="target_requests", back_populates="requests"
    )
    tags: Mapped[list["RequestTag"]] = relationship(
        "RequestTag", back_populates="request", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_http_request_host_created", "host", "created_at"),
        Index("ix_http_request_method_status", "method", "status_code"),
        Index("ix_http_request_session", "session_id"),
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


class SessionTarget(Base):
    """Association between AI sessions and targets."""

    __tablename__ = "session_targets"

    session_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("ai_sessions.id", ondelete="CASCADE"),
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
