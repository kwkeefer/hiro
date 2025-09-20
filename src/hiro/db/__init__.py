"""Database module for hiro."""

from .connection import (
    auto_migrate_database,
    close_database,
    get_db_session,
    get_session_factory,
    initialize_database,
    test_connection,
)
from .models import (
    AttemptType,
    Base,
    ConfidenceLevel,
    ContextChangeType,
    HttpRequest,
    Mission,
    MissionTarget,
    NoteType,
    RequestTag,
    RiskLevel,
    SessionStatus,
    Target,
    TargetAttempt,
    TargetContext,
    TargetNote,
    TargetRequest,
    # Enums
    TargetStatus,
)
from .repositories import (
    HttpRequestRepository,
    MissionRepository,
    RequestTagRepository,
    TargetAttemptRepository,
    TargetContextRepository,
    TargetNoteRepository,
    TargetRepository,
)
from .schemas import (
    AttemptSearchParams,
    # Request schemas
    HttpRequestCreate,
    HttpRequestUpdate,
    # Mission schemas
    MissionCreate,
    MissionSummary,
    MissionUpdate,
    RequestSearchParams,
    # Tag schemas
    RequestTagCreate,
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
    Mission as MissionSchema,
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
    "auto_migrate_database",
    "close_database",
    "get_db_session",
    "get_session_factory",
    "test_connection",
    # Models
    "Base",
    "Target",
    "TargetContext",
    "TargetNote",
    "TargetAttempt",
    "Mission",
    "HttpRequest",
    "RequestTag",
    "TargetRequest",
    "MissionTarget",
    # Enums
    "TargetStatus",
    "RiskLevel",
    "NoteType",
    "ConfidenceLevel",
    "ContextChangeType",
    "AttemptType",
    "SessionStatus",
    # Repositories
    "TargetRepository",
    "TargetContextRepository",
    "TargetNoteRepository",
    "TargetAttemptRepository",
    "MissionRepository",
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
    "MissionCreate",
    "MissionUpdate",
    "MissionSchema",
    "MissionSummary",
    "HttpRequestCreate",
    "HttpRequestUpdate",
    "HttpRequestSchema",
    "RequestSearchParams",
    "RequestTagCreate",
    "RequestTagSchema",
]
