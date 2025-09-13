"""Database module for hiro."""

from .connection import (
    close_database,
    get_db_session,
    get_session_factory,
    initialize_database,
    test_connection,
)
from .models import (
    AiSession,
    AttemptType,
    Base,
    ConfidenceLevel,
    HttpRequest,
    NoteType,
    RequestTag,
    RiskLevel,
    SessionStatus,
    SessionTarget,
    Target,
    TargetAttempt,
    TargetNote,
    TargetRequest,
    # Enums
    TargetStatus,
)
from .repositories import (
    AiSessionRepository,
    HttpRequestRepository,
    RequestTagRepository,
    TargetAttemptRepository,
    TargetNoteRepository,
    TargetRepository,
)
from .schemas import (
    AiSession as AiSessionSchema,
)
from .schemas import (
    # Session schemas
    AiSessionCreate,
    AiSessionUpdate,
    AttemptSearchParams,
    # Request schemas
    HttpRequestCreate,
    HttpRequestUpdate,
    RequestSearchParams,
    # Tag schemas
    RequestTagCreate,
    SessionSummary,
    # Attempt schemas
    TargetAttemptCreate,
    TargetAttemptUpdate,
    # Target schemas
    TargetCreate,
    # Note schemas
    TargetNoteCreate,
    TargetNoteUpdate,
    TargetSearchParams,
    TargetSummary,
    TargetUpdate,
)
from .schemas import (
    HttpRequest as HttpRequestSchema,
)
from .schemas import (
    RequestTag as RequestTagSchema,
)
from .schemas import (
    Target as TargetSchema,
)
from .schemas import (
    TargetAttempt as TargetAttemptSchema,
)
from .schemas import (
    TargetNote as TargetNoteSchema,
)

__all__ = [
    # Connection management
    "initialize_database",
    "close_database",
    "get_db_session",
    "get_session_factory",
    "test_connection",
    # Models
    "Base",
    "Target",
    "TargetNote",
    "TargetAttempt",
    "AiSession",
    "HttpRequest",
    "RequestTag",
    "TargetRequest",
    "SessionTarget",
    # Enums
    "TargetStatus",
    "RiskLevel",
    "NoteType",
    "ConfidenceLevel",
    "AttemptType",
    "SessionStatus",
    # Repositories
    "TargetRepository",
    "TargetNoteRepository",
    "TargetAttemptRepository",
    "AiSessionRepository",
    "HttpRequestRepository",
    "RequestTagRepository",
    # Schemas
    "TargetCreate",
    "TargetUpdate",
    "TargetSchema",
    "TargetSearchParams",
    "TargetSummary",
    "TargetNoteCreate",
    "TargetNoteUpdate",
    "TargetNoteSchema",
    "TargetAttemptCreate",
    "TargetAttemptUpdate",
    "TargetAttemptSchema",
    "AttemptSearchParams",
    "AiSessionCreate",
    "AiSessionUpdate",
    "AiSessionSchema",
    "SessionSummary",
    "HttpRequestCreate",
    "HttpRequestUpdate",
    "HttpRequestSchema",
    "RequestSearchParams",
    "RequestTagCreate",
    "RequestTagSchema",
]
