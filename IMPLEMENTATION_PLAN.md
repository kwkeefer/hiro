# Mission-Based Security Testing Architecture Implementation Plan

## Current Status

**Last Updated**: 2025-01-21 (Session 4 - Post-cleanup)

| Phase | Status | Completion | Notes |
|-------|--------|------------|-------|
| Phase 0: Refactor Models | ✅ COMPLETED | 100% | AiSession → Mission refactor done |
| Phase 1: pgvector Integration | ✅ COMPLETED | 100% | Vector search fully implemented and tested |
| Phase 2: Mission Management Tools | ✅ COMPLETED | 100% | Full provider-level context with cookie integration |
| Phase 3: Web Interface | ✅ COMPLETED | 100% | Full web UI for mission management |
| Phase 4: Intelligent Assistance | ✅ COMPLETED | 100% | Simplified per ADR-017 - tools provide data, LLMs provide reasoning |
| Phase 5: Performance & Migration | 🔄 NOT NEEDED | N/A | Current performance is acceptable |

## Key Achievements

### Phase 4 Final Implementation (Session 4)
- **Architecture Simplification**: Reduced from 20+ overlapping tools to ~10 tools in 3 clear categories
- **Clean Separation**: Tools provide data only; LLMs handle reasoning and recommendations
- **Terminology Clarification**: Dropped "patterns" in favor of "techniques" throughout
- **Code Cleanup**: Removed 4 obsolete files (intelligent_tools.py, analytics_tools.py, tools.py, providers.py)
- **Testing Complete**: All 5 integration tests passing with proper database session handling
- **Documentation**: Created ADR-017 documenting the separation of concerns

### Technical Implementation Notes
- **Provider Persistence**: Single provider instance per MCP session lifecycle
- **Session Management**: Database sessions created per method call (async-safe via LazyRepositories)
- **Context Precedence**: explicit param > provider context > tool defaults
- **Vector Search**: Using sentence-transformers/all-MiniLM-L12-v2 (384 dims)
- **Database**: PostgreSQL with pgvector extension for semantic search

### Testing Insights
- Each test starts with clean database (truncate all tables)
- Actions must be committed to be visible in subsequent queries
- Column naming: `meta_data` not `metadata` in technique_library
- Similarity threshold for duplicate detection: > 0.9

## Remaining Tasks

### Documentation & Examples
- [ ] Create comprehensive tool usage documentation
- [ ] Add example workflows for common testing scenarios
- [ ] Document the mission-based testing methodology

### Future Enhancements (Optional)
- [ ] Mission templates for common test types
- [ ] Team collaboration features (shared technique library)
- [ ] Advanced analytics dashboard
- [ ] Batch embedding generation for performance
- [ ] Export/import functionality for knowledge sharing

## Architecture Summary

### Current File Structure
```
src/hiro/servers/missions/
├── __init__.py              # Clean exports (4 items)
├── core_tools.py            # Core operations (4 tools)
├── search_tools.py          # Search & discovery (3 tools)
├── library_tools.py         # Knowledge library (3 tools)
└── provider.py              # Single provider (~10 tools total)
```

### Tool Categories (per ADR-017)

**Core Operations**
- `create_mission` - Create new testing mission
- `set_mission_context` - Set active mission for session
- `get_mission_context` - Get current mission with stats
- `record_action` - Record test action with auto-linking

**Search Tools**
- `find_similar_techniques` - Vector similarity search
- `search_techniques` - Filter by criteria
- `get_technique_stats` - Detailed usage statistics

**Library Tools**
- `add_to_library` - Add curated technique (LLM decides what's valuable)
- `search_library` - Semantic search in library
- `get_library_stats` - Library overview

## Key Architectural Decisions

### ADR-017: Tool-LLM Separation
- Tools are purely data retrieval/storage mechanisms
- No "smart" features, recommendations, or guidance in tools
- LLMs responsible for interpretation and decision-making
- Explicit curation for library (no auto-extraction)

### ADR-016: Mission Context Management
- Provider-level context persists during MCP session
- Supports context switching between missions
- Cookie profiles integrated with mission context

### ADR-009: Composition Pattern
- Dependency injection for provider linkage
- Providers can be composed and linked after creation
- HTTP tools aware of mission context via injection

## Database Schema

### Core Tables
- `missions` - Testing missions (refactored from ai_sessions)
- `mission_actions` - Test actions with embeddings
- `action_requests` - Links actions to HTTP requests
- `technique_library` - Curated knowledge base
- `mission_targets` - Many-to-many mission-target relationship

### Vector Columns
- `goal_embedding` / `hypothesis_embedding` (missions)
- `action_embedding` / `result_embedding` (mission_actions)
- `content_embedding` (technique_library)
- All using 384-dimensional vectors with IVFFlat indexes

## Lessons Learned

### What Worked Well
1. **Incremental Refactoring**: Evolving AiSession → Mission preserved functionality
2. **Provider Pattern**: Stateful context management across tool calls
3. **Lazy Repositories**: Clean async session management
4. **Vector Search Integration**: Semantic similarity adds real value

### Challenges Overcome
1. **Tool Overlap**: Initial design had too many similar tools
2. **Smart Tools Anti-pattern**: Tools trying to provide guidance
3. **Session Management**: Ensuring database commits for test visibility
4. **Type Safety**: Pre-existing type issues in codebase (145 errors, mostly unrelated)

### Technical Debt (Acceptable)
- Some unused parameters required by FastMCP framework
- Generic dict type annotations missing in many places
- Web router has unused request parameters
- These don't affect functionality

## Migration Complete

All phases are now complete. The system provides:
- ✅ Mission-based security testing with context management
- ✅ Vector-powered technique discovery
- ✅ Curated knowledge library
- ✅ Clean tool architecture following best practices
- ✅ Full integration test coverage

The architecture successfully separates concerns, with tools providing data and LLMs handling intelligent reasoning about that data.
