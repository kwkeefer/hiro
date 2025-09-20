  Questions about Phase 2: Mission Management Tools

  1. Tool Parameter Design

  Given ADR-014's pattern for MCP parameter transformation, should the
  mission management tools follow the same pattern? Specifically:
  - Should scope in create_mission be a JSON string (as shown in the plan)
  or a structured parameter?
  - Should we apply the same JSON string pattern to other complex
  parameters?

  An my experience, anything more complex than a int or string has been problematic for the agent.  In fact, the LLM struggles with even passing boolean values, often passing them in as "true" or "false".  So we should try to accept strings OR the correct type of it's a simple type.  For complex types, JSON will have to do, then we pass them to a Pydantic evaluator.  I think we could actually improve the ADR to make this more clear if it's not.  We should also update our Pydantic evaluators to return an error saying all of the fields that errored and what type we are expecting, since currently the LLM will have to send several requests that fail and change one parameter at a time.

  2. Mission Context vs Current HTTP Tool Integration

  The plan mentions "automatically linked to mission if context set" for
  HTTP requests. How should we establish this context?
  - Should we add a mission_id parameter to the existing HTTP tool?
  - Or use a session/context manager pattern where the mission is set
  globally?
  - How does this integrate with the existing cookie session management from ADR-015?

  We need to think about this some more.. I like the idea of an LLM setting a global context manager and havig the HTTP requests all be tagged appropriately.  If we go this route we should have the tool responses indicate that the http_request was logged to "mision x" (the id or better the id and the human readable name of the mission) so that they get reminders that we're working on X mission as they send requests.

  3. Action-Request Linking Strategy

  The record_action tool has link_recent_requests=True. What defines
  "recent"?
  - Time-based (last N seconds)?
  - Count-based (last N requests)?
  - Since last action recorded?
  - Should this be configurable?

Let's make it configuraable.  I think count based is probably better?  Since two sessions could happen far apart in time.

  4. Vector Search Integration

  For get_mission_context and find_similar_techniques:
  - Should these tools return raw vector similarity scores or convert them
  to more user-friendly formats?
  - What should be the default similarity threshold?
  - How many results should we return by default?

  We should probably return both the user fiendly values and the similarity scores.  Maybe we can configure it to return X results where the similarity score is above a certain threshold.  Of course, we would have to be careful about not overloading the context of the LLM.  Maybe we could return the similarity score, a human readable shorter description, and the id of the match so they can look up the full details?  And the size of each match, so they know how big it will be and they don't overload their context.

  5. Cookie Profile Integration

  ADR-015 describes cookie sessions as MCP resources. For Phase 2's cookie
  integration:
  - Should we automatically associate cookie sessions with missions?
  - Should the mission tools be aware of which cookie sessions were used?
  - How do we track "which cookies worked for which endpoints"?

  We can have cookie profiles set within the mission context.. but we should also allow actions / http request to pass in a session manually to overwrite this to allow for testing cross-tenant auth issues.  Since we're loggin http requests for each action, we'll be able to go back and identify the cookies were used.

  6. Tool Naming Convention

  Should we follow a specific naming pattern for the mission tools? The plan
   shows snake_case but existing tools might use different conventions.

  Please clarify these points so I can implement Phase 2 correctly according
   to your vision.

    I like snake case.. if there are other conventions let's identify them and modify them accordingly.
