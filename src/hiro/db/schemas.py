"""Pydantic schemas for database models validation."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .models import (
    AttemptType,
    ConfidenceLevel,
    NoteType,
    RiskLevel,
    SessionStatus,
    TargetStatus,
)


# Base schemas
class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(from_attributes=True)


# Target schemas
class TargetBase(BaseSchema):
    """Base target schema."""

    host: str = Field(..., description="Target hostname or IP")
    port: int | None = Field(None, description="Target port number")
    protocol: str = Field(..., description="Protocol (http/https)")
    title: str | None = Field(None, description="Target title or service name")
    status: TargetStatus = Field(TargetStatus.ACTIVE, description="Target status")
    risk_level: RiskLevel = Field(RiskLevel.MEDIUM, description="Risk assessment level")
    extra_data: dict = Field(
        default_factory=dict, description="Additional target metadata"
    )


class TargetCreate(TargetBase):
    """Schema for creating targets."""

    pass


class TargetUpdate(BaseSchema):
    """Schema for updating targets."""

    title: str | None = None
    status: TargetStatus | None = None
    risk_level: RiskLevel | None = None
    extra_data: dict | None = None


class Target(TargetBase):
    """Complete target schema."""

    id: UUID
    discovery_date: datetime
    last_activity: datetime
    created_at: datetime
    updated_at: datetime


# Target Note schemas
class TargetNoteBase(BaseSchema):
    """Base target note schema."""

    note_type: NoteType = Field(..., description="Type of note")
    title: str = Field(..., description="Note title")
    content: str = Field(..., description="Note content")
    tags: list[str] = Field(default_factory=list, description="Note tags")
    confidence: ConfidenceLevel = Field(
        ConfidenceLevel.MEDIUM, description="Confidence level"
    )


class TargetNoteCreate(TargetNoteBase):
    """Schema for creating target notes."""

    target_id: UUID = Field(..., description="Target ID")


class TargetNoteUpdate(BaseSchema):
    """Schema for updating target notes."""

    title: str | None = None
    content: str | None = None
    tags: list[str] | None = None
    confidence: ConfidenceLevel | None = None


class TargetNote(TargetNoteBase):
    """Complete target note schema."""

    id: UUID
    target_id: UUID
    created_at: datetime
    updated_at: datetime


# Target Attempt schemas
class TargetAttemptBase(BaseSchema):
    """Base target attempt schema."""

    attempt_type: AttemptType = Field(..., description="Type of attempt")
    technique: str = Field(..., description="Technique used")
    payload: str | None = Field(None, description="Payload used")
    expected_outcome: str = Field(..., description="Expected result")
    notes: str | None = Field(None, description="Additional notes")


class TargetAttemptCreate(TargetAttemptBase):
    """Schema for creating target attempts."""

    target_id: UUID = Field(..., description="Target ID")
    session_id: UUID | None = Field(None, description="AI session ID")


class TargetAttemptUpdate(BaseSchema):
    """Schema for updating target attempts."""

    actual_outcome: str | None = None
    success: bool | None = None
    notes: str | None = None
    completed_at: datetime | None = None


class TargetAttempt(TargetAttemptBase):
    """Complete target attempt schema."""

    id: UUID
    target_id: UUID
    session_id: UUID | None
    actual_outcome: str | None
    success: bool | None
    created_at: datetime
    completed_at: datetime | None


# AI Session schemas
class AiSessionBase(BaseSchema):
    """Base AI session schema."""

    name: str | None = Field(None, description="Session name")
    description: str | None = Field(None, description="Session description")
    objective: str | None = Field(None, description="Session objective")
    status: SessionStatus = Field(SessionStatus.ACTIVE, description="Session status")
    extra_data: dict = Field(default_factory=dict, description="Session metadata")


class AiSessionCreate(AiSessionBase):
    """Schema for creating AI sessions."""

    pass


class AiSessionUpdate(BaseSchema):
    """Schema for updating AI sessions."""

    name: str | None = None
    description: str | None = None
    objective: str | None = None
    status: SessionStatus | None = None
    extra_data: dict | None = None
    completed_at: datetime | None = None


class AiSession(AiSessionBase):
    """Complete AI session schema."""

    id: UUID
    created_at: datetime
    completed_at: datetime | None


# HTTP Request schemas
class HttpRequestBase(BaseSchema):
    """Base HTTP request schema."""

    method: str = Field(..., description="HTTP method")
    url: str = Field(..., description="Request URL")
    host: str = Field(..., description="Target host")
    path: str = Field(..., description="Request path")
    query_params: dict | None = Field(None, description="Query parameters")
    headers: dict = Field(default_factory=dict, description="Request headers")
    cookies: dict | None = Field(None, description="Request cookies")
    request_body: str | None = Field(None, description="Request body")


class HttpRequestCreate(HttpRequestBase):
    """Schema for creating HTTP requests."""

    session_id: UUID | None = Field(None, description="AI session ID")


class HttpRequestUpdate(BaseSchema):
    """Schema for updating HTTP requests with response data."""

    status_code: int | None = None
    response_headers: dict | None = None
    response_body: str | None = None
    response_size: int | None = None
    elapsed_ms: float | None = None
    error_message: str | None = None


class HttpRequest(HttpRequestBase):
    """Complete HTTP request schema."""

    id: UUID
    session_id: UUID | None
    status_code: int | None
    response_headers: dict | None
    response_body: str | None
    response_size: int | None
    elapsed_ms: float | None
    error_message: str | None
    created_at: datetime


# Request Tag schemas
class RequestTagBase(BaseSchema):
    """Base request tag schema."""

    tag: str = Field(..., description="Tag name")
    value: str | None = Field(None, description="Tag value")


class RequestTagCreate(RequestTagBase):
    """Schema for creating request tags."""

    request_id: UUID = Field(..., description="Request ID")


class RequestTag(RequestTagBase):
    """Complete request tag schema."""

    id: UUID
    request_id: UUID
    created_at: datetime


# Search and filter schemas
class TargetSearchParams(BaseSchema):
    """Parameters for target search."""

    query: str | None = Field(None, description="Text search query")
    status: list[TargetStatus] | None = Field(None, description="Filter by status")
    risk_level: list[RiskLevel] | None = Field(None, description="Filter by risk level")
    protocol: list[str] | None = Field(None, description="Filter by protocol")
    limit: int = Field(50, ge=1, le=1000, description="Result limit")
    offset: int = Field(0, ge=0, description="Result offset")


class RequestSearchParams(BaseSchema):
    """Parameters for request search."""

    query: str | None = Field(None, description="Text search query")
    host: str | None = Field(None, description="Filter by host")
    method: list[str] | None = Field(None, description="Filter by HTTP method")
    status_code: list[int] | None = Field(None, description="Filter by status code")
    tags: list[str] | None = Field(None, description="Filter by tags")
    session_id: UUID | None = Field(None, description="Filter by session")
    target_id: UUID | None = Field(None, description="Filter by target")
    date_from: datetime | None = Field(None, description="Filter from date")
    date_to: datetime | None = Field(None, description="Filter to date")
    limit: int = Field(50, ge=1, le=1000, description="Result limit")
    offset: int = Field(0, ge=0, description="Result offset")


class AttemptSearchParams(BaseSchema):
    """Parameters for attempt search."""

    target_id: UUID | None = Field(None, description="Filter by target")
    session_id: UUID | None = Field(None, description="Filter by session")
    attempt_type: list[AttemptType] | None = Field(
        None, description="Filter by attempt type"
    )
    technique: str | None = Field(None, description="Filter by technique")
    success: bool | None = Field(None, description="Filter by success")
    date_from: datetime | None = Field(None, description="Filter from date")
    date_to: datetime | None = Field(None, description="Filter to date")
    limit: int = Field(50, ge=1, le=1000, description="Result limit")
    offset: int = Field(0, ge=0, description="Result offset")


# Summary schemas
class TargetSummary(BaseSchema):
    """Target summary with related data counts."""

    target: Target
    notes_count: int = Field(..., description="Number of notes")
    attempts_count: int = Field(..., description="Number of attempts")
    requests_count: int = Field(..., description="Number of requests")
    success_rate: float | None = Field(None, description="Success rate of attempts")


class SessionSummary(BaseSchema):
    """Session summary with progress metrics."""

    session: AiSession
    targets_count: int = Field(..., description="Number of targets")
    requests_count: int = Field(..., description="Number of requests")
    attempts_count: int = Field(..., description="Number of attempts")
    successful_attempts: int = Field(..., description="Number of successful attempts")
    duration_minutes: float | None = Field(
        None, description="Session duration in minutes"
    )
