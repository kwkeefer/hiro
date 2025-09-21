# ADR-016: Mission Context Management Architecture

**Status**: Accepted
**Date**: 2025-01-20
**Author**: Development Team

## Context

With the introduction of mission-based testing architecture, we need a clean way to manage mission context across multiple tool calls. The challenge is that MCP tools are typically stateless between calls, but we want to reduce cognitive load on AI agents by not requiring them to pass mission_id to every single tool call.

Key requirements:
1. AI agents should be able to "set and forget" mission context
2. HTTP requests should automatically link to active missions
3. Cookie profiles should be associated with missions
4. System should provide clear feedback about active context
5. Must work within MCP/FastMCP architecture constraints

## Decision

We will implement **Provider-Level Context Management** with the following characteristics:

### 1. Provider-Level State
- Context is stored at the provider instance level
- Context persists for the duration of the MCP session/connection
- Each MCP connection gets its own isolated context (prevents cross-contamination)

### 2. Session-Per-Method Database Pattern
- Each tool method creates its own database session
- Sessions are properly closed after each operation
- Async-safe and prevents connection pool exhaustion

### 3. Context Override Pattern
- Tools accept optional parameters to override global context
- Precedence: explicit parameter > provider context > no context
- Enables both "set and forget" AND explicit control

### 4. Explicit Feedback
- All tools return confirmation of mission linkage
- Response messages include mission ID and human-readable name
- Provides continuous reminders to agent about active context

## Implementation Details

```python
# Provider-level context management
class MissionManagementProvider:
    def __init__(self):
        self._current_mission_id: UUID | None = None
        self._cookie_profile: str | None = None

    async def set_mission_context(self, mission_id: str, cookie_profile: str = None):
        """Set active mission for this MCP session."""
        self._current_mission_id = UUID(mission_id)
        self._cookie_profile = cookie_profile
        return {
            "status": "context_set",
            "mission_id": mission_id,
            "cookie_profile": cookie_profile,
            "message": f"Mission context set. All HTTP requests will be logged to mission {mission_id}"
        }

# HTTP tool integration
class HttpToolProvider:
    async def http_request(self, url: str, mission_id: str = None, ...):
        """HTTP request with optional mission override."""
        active_mission = mission_id or self._current_mission_id

        # ... make request ...

        if active_mission:
            await self._log_to_mission(request_id, active_mission)
            response_msg = f"Request logged to mission: {active_mission} ({mission_name})"

        return {"response": response_data, "mission_context": response_msg}

# Database session pattern
async def get_mission_context(self, mission_id: str):
    """Each method creates its own session."""
    async with self.db_manager.get_session() as session:
        repo = MissionRepository(session)
        vector_search = VectorSearch()

        mission = await repo.get(UUID(mission_id))
        similar = await vector_search.find_similar_actions(
            session=session,
            query=focus,
            mission_id=UUID(mission_id)
        )
        # Session automatically closed when context exits
```

## Consequences

### Positive
- **Simple implementation**: No extra state management infrastructure
- **Clear lifecycle**: Context tied to MCP connection lifecycle
- **Backwards compatible**: Existing tools continue to work
- **Reduced cognitive load**: Agents don't need to track mission_id
- **Explicit feedback**: Agents always know what context is active
- **Async-safe**: Session-per-method prevents async issues
- **Isolated contexts**: Multiple agents don't interfere with each other

### Negative
- **Context loss on disconnect**: Must re-establish context after reconnection
  - *Mitigation*: This is intentional - requires explicit context establishment
- **No cross-session persistence**: Context doesn't survive MCP restarts
  - *Mitigation*: Agents can query current mission state if needed
- **Per-provider state**: Context isn't shared between provider instances
  - *Mitigation*: This is a feature - prevents unintended context sharing

## Alternatives Considered

### 1. Database State Table
Store context in a database table with session IDs.
- **Rejected**: Adds complexity, requires session ID management, cleanup issues

### 2. File-Based State (like cookie sessions)
Store context in XDG config directory files.
- **Rejected**: File I/O overhead, potential race conditions, cleanup complexity

### 3. Require mission_id on Every Call
Make agents pass mission_id to every tool.
- **Rejected**: High cognitive load, verbose tool calls, error-prone

### 4. Global Singleton State
Use a global variable or singleton for context.
- **Rejected**: Not async-safe, breaks with multiple providers, testing difficulties

## Related ADRs

- **ADR-001**: Keep it simple - provider-level state is simpler than alternatives
- **ADR-014**: MCP parameter patterns - consistent with parameter transformation
- **ADR-015**: Cookie session management - extends pattern for mission context
- **ADR-013**: Hybrid FastMCP approach - works within our architecture

## Implementation Notes

1. **Migration Path**:
   - Existing tools continue to work without modification
   - Gradually update tools to be context-aware
   - Add feedback messages incrementally

2. **Testing Strategy**:
   - Mock provider context in unit tests
   - Integration tests for context flow
   - Test context isolation between connections

3. **Documentation Requirements**:
   - Update tool descriptions with context behavior
   - Provide examples of context workflow
   - Document override patterns

## Example Workflow

```python
# 1. Set mission context at start
await set_mission_context(
    mission_id="uuid-here",
    cookie_profile="admin_session"
)
# Returns: "Mission context set. All HTTP requests will be logged to mission uuid-here"

# 2. Make HTTP requests (automatically linked)
await http_request(url="https://api.example.com/test")
# Returns: "Request logged to mission: uuid-here (SQL Injection Test)"

# 3. Record action (uses context)
await record_action(
    technique="SQL injection",
    result="Success"
)
# Returns: "Action recorded for mission: uuid-here (SQL Injection Test)"

# 4. Override when needed
await http_request(
    url="https://different-api.com",
    mission_id="different-uuid"  # Override for this request only
)
# Returns: "Request logged to mission: different-uuid (Different Test)"
```

This architecture provides a clean, simple solution that reduces cognitive load while maintaining flexibility and working within MCP constraints.
