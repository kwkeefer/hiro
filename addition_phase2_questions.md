
  1. Mission Context Manager Architecture

  The current implementation has _current_mission_id stored in the MissionManagementTool class,
   but this won't persist across tool calls. Should we:
  - Store it in a database table (like a "session state" table)?
  - Use a file-based approach (similar to cookie sessions)?
  - Or implement it differently?

  This is a great question.. the thought was to abstrat the current mission id from the agent, so it has less to remember and can focus on its individual task.. but I think implementing this might be challenging, especially if multiple agents are using this service.. maybe we could randomly assign each agent a "name" and create a state db that can track state for that agent's session?  Or maybe we revert this functionality and make the agent remember things like what session it's working on.  Let's think this through and discuss more.

  2. HTTP Tool Integration

  Currently, HttpRequestTool accepts a mission_id parameter at initialization. For the global
  context approach:
  - Should we modify the HTTP tool to check a global mission context on each request?
  - How should we handle the transition - keep the parameter as an override option?
  - Should the context be shared across ALL provider instances or per-provider?

    The implementation on this is dependent on the previous question's answer.. Let's have a larger discussion and decide on how we'll implement.


  3. Database Session Management

  The mission tools currently don't have database sessions. Should we:
  - Follow the pattern from ai_logging/providers.py where we create sessions in each method?
  - Or pass a session from the provider level?
  - How should this work with the MCP server's async context?

  Creataing sessions for each method would work better within async contexts, correct?  I *think* that should be fine, assuming we're only creating a few tool calls per second, what do you think?

  4. Cookie Profile Integration Priority

  You mentioned cookie profiles should be set in mission context with per-request overrides.
  Should we:
  - Implement this now as part of Phase 2 completion?
  - Or focus on getting basic mission context working first, then add cookies?


    Let's implement this now.

  5. Vector Search Session Issue

  The VectorSearch class methods expect a session parameter but the mission tools don't provide
   one. Should we:
  - Create a session within each tool method that needs vector search?
  - Pass a persistent session to the VectorSearch instance?
  - Modify VectorSearch to handle its own sessions?


    This is very similar to the earlier question.  Let's chat some more and think through the best approach.

  6. Testing Approach

  The web route tests are failing due to async/database issues. Should we:
  - Focus on fixing these tests now?
  - Or proceed with implementation and fix tests after?
  - Skip the web route tests and focus on integration tests for the MCP tools?

  These clarifications will help ensure I implement exactly what you're envisioning for the
  mission-based testing system.

    Let's focus on implementation and fix the tests when we have a better foundation to work on.
