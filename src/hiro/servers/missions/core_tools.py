"""Core mission operation tools for security testing."""

import json
import logging
from typing import Annotated, Any, ClassVar, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from hiro.core.mcp.exceptions import ToolError
from hiro.core.vector.search import VectorSearch
from hiro.db.models import SessionStatus
from hiro.db.repositories import MissionActionRepository, MissionRepository
from hiro.db.schemas import MissionActionCreate, MissionCreate

logger = logging.getLogger(__name__)


class CreateMissionParams(BaseModel):
    """Parameters for creating a mission."""

    TARGET_ID_DESC: ClassVar[str] = "UUID of the target system to test"
    MISSION_TYPE_DESC: ClassVar[str] = (
        "Type of mission: prompt_injection, business_logic, auth_bypass, recon, general"
    )
    NAME_DESC: ClassVar[str] = "Human-readable name for the mission"
    GOAL_DESC: ClassVar[str] = "Clear, specific objective for this mission"
    HYPOTHESIS_DESC: ClassVar[str] = (
        "Initial hypothesis about vulnerabilities or approach"
    )
    SCOPE_DESC: ClassVar[str] = (
        'JSON object defining mission scope, e.g. {"endpoints": ["/api/*"], "excluded": ["/health"]}'
    )

    target_id: str = Field(description=TARGET_ID_DESC)
    mission_type: Literal[
        "prompt_injection", "business_logic", "auth_bypass", "recon", "general"
    ] = Field(description=MISSION_TYPE_DESC)
    name: str = Field(description=NAME_DESC)
    goal: str = Field(description=GOAL_DESC)
    hypothesis: str | None = Field(None, description=HYPOTHESIS_DESC)
    scope: dict[str, Any] | None = Field(None, description=SCOPE_DESC)

    @field_validator("target_id", mode="before")
    @classmethod
    def validate_uuid(cls, v: Any) -> str:
        """Validate and convert UUID string."""
        if v is None:
            raise ValueError("target_id is required")
        try:
            UUID(str(v))
            return str(v)
        except ValueError as e:
            raise ValueError(f"Invalid UUID format: {str(v)}") from e

    @field_validator("scope", mode="before")
    @classmethod
    def parse_scope_json(cls, v: Any) -> dict[str, Any] | None:
        """Parse JSON string to dict if needed."""
        if v is None:
            return None
        if isinstance(v, str):
            try:
                return json.loads(v)  # type: ignore[no-any-return]
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in scope: {e}") from e
        return v  # type: ignore[no-any-return]


class RecordActionParams(BaseModel):
    """Parameters for recording a mission action."""

    MISSION_ID_DESC: ClassVar[str] = "UUID of the mission this action belongs to"
    ACTION_TYPE_DESC: ClassVar[str] = (
        "Type of action: payload_test, recon, exploit, analysis"
    )
    TECHNIQUE_DESC: ClassVar[str] = "Description of the technique used"
    PAYLOAD_DESC: ClassVar[str] = "The payload or input used (if applicable)"
    RESULT_DESC: ClassVar[str] = "The result or output obtained"
    SUCCESS_DESC: ClassVar[str] = "Whether the action achieved its goal"
    LEARNING_DESC: ClassVar[str] = "What was learned from this action"
    LINK_RECENT_REQUESTS_DESC: ClassVar[str] = (
        "Number of recent HTTP requests to link to this action (0 to disable)"
    )

    mission_id: str = Field(description=MISSION_ID_DESC)
    action_type: Literal["payload_test", "recon", "exploit", "analysis"] = Field(
        description=ACTION_TYPE_DESC
    )
    technique: str = Field(description=TECHNIQUE_DESC)
    payload: str | None = Field(None, description=PAYLOAD_DESC)
    result: str | None = Field(None, description=RESULT_DESC)
    success: bool = Field(False, description=SUCCESS_DESC)
    learning: str | None = Field(None, description=LEARNING_DESC)
    link_recent_requests: int = Field(
        5, description=LINK_RECENT_REQUESTS_DESC, ge=0, le=20
    )

    @field_validator("mission_id", mode="before")
    @classmethod
    def validate_mission_uuid(cls, v: Any) -> str:
        """Validate and convert UUID string."""
        if v is None:
            raise ValueError("mission_id is required")
        try:
            UUID(str(v))
            return str(v)
        except ValueError as e:
            raise ValueError(f"Invalid UUID format: {str(v)}") from e

    @field_validator("success", mode="before")
    @classmethod
    def parse_bool(cls, v: Any) -> bool:
        """Parse string booleans if needed."""
        if isinstance(v, str):
            if v.lower() in ("true", "1", "yes"):
                return True
            elif v.lower() in ("false", "0", "no"):
                return False
            else:
                raise ValueError(f"Cannot parse '{v}' as boolean")
        return bool(v)


class MissionCoreTool:
    """Core tools for mission operations during active testing."""

    def __init__(
        self,
        mission_repo: MissionRepository,
        action_repo: MissionActionRepository,
        vector_search: VectorSearch | None = None,
    ) -> None:
        """Initialize the core mission tool."""
        self._mission_repo = mission_repo
        self._action_repo = action_repo
        self._vector_search = vector_search
        self._current_mission_id: UUID | None = None

    async def create_mission(
        self,
        target_id: Annotated[
            str, Field(description=CreateMissionParams.TARGET_ID_DESC)
        ],
        mission_type: Annotated[
            str, Field(description=CreateMissionParams.MISSION_TYPE_DESC)
        ],
        name: Annotated[str, Field(description=CreateMissionParams.NAME_DESC)],
        goal: Annotated[str, Field(description=CreateMissionParams.GOAL_DESC)],
        hypothesis: Annotated[
            str | None, Field(description=CreateMissionParams.HYPOTHESIS_DESC)
        ] = None,
        scope: Annotated[
            str | None, Field(description=CreateMissionParams.SCOPE_DESC)
        ] = None,
    ) -> dict[str, Any]:
        """Create a new testing mission."""
        try:
            # Parse scope if it's a JSON string
            parsed_scope = None
            if scope:
                if isinstance(scope, str):
                    try:
                        parsed_scope = json.loads(scope)
                    except json.JSONDecodeError:
                        parsed_scope = {"raw": scope}  # Wrap non-JSON as dict
                else:
                    parsed_scope = scope

            params = CreateMissionParams(
                target_id=target_id,
                mission_type=mission_type,  # type: ignore
                name=name,
                goal=goal,
                hypothesis=hypothesis,
                scope=parsed_scope,
            )
        except Exception as e:
            if hasattr(e, "errors"):
                error_details = []
                for error in e.errors():
                    field = ".".join(str(loc) for loc in error["loc"])
                    msg = error["msg"]
                    error_details.append(f"{field}: {msg}")
                error_msg = "Invalid parameters:\n" + "\n".join(error_details)
            else:
                error_msg = f"Invalid parameters: {str(e)}"
            raise ToolError("create_mission", error_msg) from e

        # Create mission
        mission_create = MissionCreate(
            target_id=UUID(params.target_id),
            name=params.name,
            description=params.goal,
            mission_type=params.mission_type,
            hypothesis=params.hypothesis,
            goal=params.goal,
            status=SessionStatus.ACTIVE,
            # Note: scope is stored in extra_data
            extra_data=params.scope or {},
        )

        mission = await self._mission_repo.create(mission_create)

        # Generate embeddings if vector search is available
        if self._vector_search and params.goal:
            goal_embedding = await self._vector_search.encode_text(params.goal)
            await self._mission_repo.update_embeddings(
                mission.id, goal_embedding=goal_embedding.tolist()
            )

        if self._vector_search and params.hypothesis:
            hypothesis_embedding = await self._vector_search.encode_text(
                params.hypothesis
            )
            await self._mission_repo.update_embeddings(
                mission.id, hypothesis_embedding=hypothesis_embedding.tolist()
            )

        return {
            "mission_id": str(mission.id),
            "name": mission.name,
            "type": mission.mission_type,
            "status": "created",
            "message": f"Mission '{mission.name}' created successfully",
        }

    async def set_mission_context(
        self,
        mission_id: Annotated[
            str, Field(description="UUID of the mission to set as context")
        ],
        cookie_profile: Annotated[
            str | None,
            Field(
                description="Optional cookie profile to use for this mission's HTTP requests"
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Set the current mission context for HTTP requests."""
        try:
            mission_uuid = UUID(mission_id)
        except ValueError as e:
            raise ToolError(
                "set_mission_context", f"Invalid UUID format: {mission_id}"
            ) from e

        # Verify mission exists
        mission = await self._mission_repo.get(mission_uuid)
        if not mission:
            raise ToolError("set_mission_context", f"Mission {mission_id} not found")

        self._current_mission_id = mission_uuid

        message = f"Mission context set to '{mission.name}' ({mission.id})"
        if cookie_profile:
            message += f" with cookie profile: {cookie_profile}"

        return {
            "mission_id": str(mission.id),
            "name": mission.name,
            "status": "context_set",
            "message": message,
        }

    async def get_mission_context(
        self,
        mission_id: Annotated[
            str | None, Field(description="Mission ID, or None for current")
        ] = None,
    ) -> dict[str, Any]:
        """Get mission context including basic stats.

        If mission_id is not provided, returns the current mission context.
        """
        # Use provided mission_id or fall back to current
        if mission_id:
            try:
                mission_uuid = UUID(mission_id)
            except ValueError as e:
                raise ToolError(
                    "get_mission_context", f"Invalid UUID format: {mission_id}"
                ) from e
        else:
            if not self._current_mission_id:
                return {
                    "mission_id": None,
                    "message": "No mission context currently set",
                }
            mission_uuid = self._current_mission_id

        # Get mission details
        mission = await self._mission_repo.get(mission_uuid)
        if not mission:
            return {
                "mission_id": None,
                "message": f"Mission {mission_uuid} not found",
            }

        # Get recent actions for stats
        recent_actions = await self._action_repo.get_by_mission(mission_uuid, limit=100)

        # Calculate basic statistics
        total_actions = len(recent_actions)
        successful_actions = sum(1 for a in recent_actions if a.success)
        success_rate = successful_actions / total_actions if total_actions > 0 else 0

        # Get unique techniques tried
        techniques_tried = {a.technique for a in recent_actions if a.technique}

        # Get last 5 actions for context
        last_actions = []
        for action in recent_actions[:5]:
            last_actions.append(
                {
                    "technique": action.technique,
                    "success": action.success,
                    "learning": action.learning,
                    "timestamp": action.created_at.isoformat()
                    if action.created_at
                    else None,
                }
            )

        return {
            "mission": {
                "id": str(mission.id),
                "name": mission.name,
                "type": mission.mission_type,
                "goal": mission.goal,
                "hypothesis": mission.hypothesis,
                "scope": mission.scope,
            },
            "stats": {
                "total_actions": total_actions,
                "successful_actions": successful_actions,
                "success_rate": round(success_rate, 2),
                "unique_techniques": len(techniques_tried),
            },
            "recent_actions": last_actions,
        }

    async def record_action(
        self,
        mission_id: Annotated[
            str, Field(description=RecordActionParams.MISSION_ID_DESC)
        ],
        action_type: Annotated[
            str, Field(description=RecordActionParams.ACTION_TYPE_DESC)
        ],
        technique: Annotated[str, Field(description=RecordActionParams.TECHNIQUE_DESC)],
        payload: Annotated[
            str | None, Field(description=RecordActionParams.PAYLOAD_DESC)
        ] = None,
        result: Annotated[
            str | None, Field(description=RecordActionParams.RESULT_DESC)
        ] = None,
        success: Annotated[
            bool | str, Field(description=RecordActionParams.SUCCESS_DESC)
        ] = False,
        learning: Annotated[
            str | None, Field(description=RecordActionParams.LEARNING_DESC)
        ] = None,
        link_recent_requests: Annotated[
            int, Field(description=RecordActionParams.LINK_RECENT_REQUESTS_DESC)
        ] = 5,
    ) -> dict[str, Any]:
        """Record a test action and optionally link recent HTTP requests."""
        try:
            params = RecordActionParams(
                mission_id=mission_id,
                action_type=action_type,  # type: ignore
                technique=technique,
                payload=payload,
                result=result,
                success=success,  # type: ignore
                learning=learning,
                link_recent_requests=link_recent_requests,
            )
        except Exception as e:
            if hasattr(e, "errors"):
                error_details = []
                for error in e.errors():
                    field = ".".join(str(loc) for loc in error["loc"])
                    msg = error["msg"]
                    error_details.append(f"{field}: {msg}")
                error_msg = "Invalid parameters:\n" + "\n".join(error_details)
            else:
                error_msg = f"Invalid parameters: {str(e)}"
            raise ToolError("record_action", error_msg) from e

        # Create action
        action_create = MissionActionCreate(
            mission_id=UUID(params.mission_id),
            action_type=params.action_type,
            technique=params.technique,
            payload=params.payload,
            result=params.result,
            success=params.success,
            learning=params.learning,
            metadata=None,
        )

        action = await self._action_repo.create(action_create)

        # Generate embeddings if vector search is available
        if self._vector_search:
            if params.technique:
                action_embedding = await self._vector_search.encode_text(
                    f"{params.action_type}: {params.technique}"
                )
                await self._action_repo.update_embeddings(
                    action.id, action_embedding=action_embedding.tolist()
                )

            if params.result:
                result_embedding = await self._vector_search.encode_text(params.result)
                await self._action_repo.update_embeddings(
                    action.id, result_embedding=result_embedding.tolist()
                )

        # Link recent HTTP requests if requested
        linked_count = 0
        if params.link_recent_requests > 0:
            linked_count = await self._action_repo.link_recent_requests(
                action.id, UUID(params.mission_id), params.link_recent_requests
            )

        return {
            "action_id": str(action.id),
            "mission_id": str(action.mission_id),
            "technique": action.technique,
            "success": action.success,
            "linked_requests": linked_count,
            "message": f"Action recorded: {action.technique} ({'success' if action.success else 'failed'})",
        }
