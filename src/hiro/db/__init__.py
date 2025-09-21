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
    Base,
    ContextChangeType,
    HttpRequest,
    Mission,
    MissionTarget,
    RequestTag,
    RiskLevel,
    SessionStatus,
    Target,
    TargetContext,
    TargetRequest,
    # Enums
    TargetStatus,
)
from .repositories import (
    HttpRequestRepository,
    MissionRepository,
    RequestTagRepository,
    TargetContextRepository,
    TargetRepository,
)
from .schemas import (
    HttpRequest as HttpRequestSchema,
)
from .schemas import (
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
    # Target schemas
    TargetCreate,
    TargetSearchParams,
    TargetSummary,
    TargetUpdate,
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
    "Mission",
    "HttpRequest",
    "RequestTag",
    "TargetRequest",
    "MissionTarget",
    # Enums
    "TargetStatus",
    "RiskLevel",
    "ContextChangeType",
    "SessionStatus",
    # Repositories
    "TargetRepository",
    "TargetContextRepository",
    "MissionRepository",
    "HttpRequestRepository",
    "RequestTagRepository",
    # Schemas
    "TargetCreate",
    "TargetUpdate",
    "TargetSchema",
    "TargetSearchParams",
    "TargetSummary",
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
