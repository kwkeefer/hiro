# Database Layer Implementation Plan

## Overview
Step-by-step implementation plan for adding PostgreSQL-backed logging system with AI reasoning tracking to the code-mcp project.

**Architecture Decision**: All database features (HTTP logging, target management, AI tools) are integrated into a single unified `serve-http` command. When a database is configured via DATABASE_URL, all features are enabled automatically - no flags required. This provides a seamless experience where HTTP operations auto-log and AI tools can manage the resulting data.

## Phase 1: Database Foundation

### 1.1 Dependencies and Configuration
- [x] Add database dependencies to `pyproject.toml`:
  - `sqlalchemy[asyncio]>=2.0.0`
  - `asyncpg>=0.29.0`
  - `alembic>=1.13.0`
  - `psycopg2-binary>=2.9.10`
- [x] Update `src/code_mcp/core/config/settings.py`:
  - Add database logging configuration options
  - Add connection pool settings
  - Add data retention policies
- [x] Create `.env.example` with database configuration examples

### 1.2 Database Module Structure
- [x] Create `src/code_mcp/db/models.py` - SQLAlchemy models
- [x] Create `src/code_mcp/db/connection.py` - Database connection management
- [x] Create `src/code_mcp/db/schemas.py` - Pydantic validation schemas
- [x] Create `src/code_mcp/db/repositories.py` - Data access layer
- [x] Update `src/code_mcp/db/__init__.py` - Module exports

### 1.3 Migration System
- [x] Initialize Alembic in `src/code_mcp/db/migrations/`
- [x] Create initial migration with all table schemas
- [x] Add indexes for performance:
  - `http_requests(host, created_at)`
  - `target_notes(target_id, note_type)`
  - `target_attempts(target_id, success)`
  - `request_tags(tag)`
- [x] Test migration up/down operations

### 1.4 CLI Database Commands
- [x] Add database command group to `src/code_mcp/cli.py`
- [x] Implement `code_mcp db init` command
- [x] Implement `code_mcp db migrate` command
- [x] Implement `code_mcp db reset` command (dev only)
- [ ] Implement `code_mcp db seed` command (optional sample data)

## Phase 2: Core Logging Integration

### 2.1 HTTP Request Auto-Logging
- [x] Modify `src/code_mcp/servers/http/tools.py`:
  - Add database dependency injection to `HttpRequestTool`
  - Add pre-request logging (method, url, headers, cookies)
  - Add post-request logging (response, timing, status)
  - Handle logging failures gracefully (don't break HTTP requests)
- [x] Update `src/code_mcp/servers/http/config.py`:
  - Add logging enabled/disabled flag
  - Add request body size limits
  - Add sensitive header filtering options
- [x] Update `src/code_mcp/servers/http/providers.py` to inject database dependencies

### 2.2 Target Auto-Detection
- [x] Add target auto-discovery logic:
  - Extract host/port/protocol from request URLs
  - Auto-create target records if they don't exist
  - Link requests to targets automatically
- [x] Add duplicate target handling (same host:port:protocol)
- [x] Add target status tracking (first seen, last activity)

### 2.3 Repository Implementation
- [x] Implement `HttpRequestRepository`:
  - `create_request()` - Log HTTP request/response
  - `get_request()` - Retrieve request by ID
  - `search_requests()` - Query with filters
- [x] Implement `TargetRepository`:
  - `create_target()` - Create new target
  - `get_target()` - Get target by host/port
  - `update_target()` - Update target metadata
  - `list_targets()` - Get targets with filtering

## Phase 3: AI Tools Development

### 3.1 Target Management Tools ✅ COMPLETED
- [x] Create `src/code_mcp/servers/ai_logging/` module
- [x] Create `src/code_mcp/servers/ai_logging/tools.py`:
  - `CreateTargetTool` - Register new targets manually
  - `UpdateTargetStatusTool` - Update target status
  - `GetTargetSummaryTool` - Get complete target overview
  - `SearchTargetsTool` - Find targets by criteria
- [x] Create `src/code_mcp/servers/ai_logging/providers.py`:
  - `AiLoggingToolProvider` class following existing patterns
- [x] Add comprehensive error handling and validation
- [x] Integrate into unified `serve-http` command (no separate server)
- [x] Add clear documentation about unified server architecture

### 3.2 Note Management Tools
- [ ] Add note management tools to `ai_logging/tools.py`:
  - `AddTargetNoteTool` - Add reconnaissance notes
  - `UpdateTargetNoteTool` - Update existing notes
  - `GetTargetNotesTool` - Retrieve notes for target
  - `SearchTargetNotesTool` - Search across all notes
- [ ] Implement `TargetNoteRepository`:
  - Full CRUD operations
  - Search functionality with tags
  - Note versioning considerations

### 3.3 Attempt Tracking Tools
- [ ] Add attempt tracking tools:
  - `LogAttemptTool` - Record new attempts with expectations
  - `UpdateAttemptOutcomeTool` - Record actual results
  - `GetTargetAttemptsTool` - Review attempt history
  - `GetAttemptDetailsTool` - Get specific attempt info
- [ ] Implement `TargetAttemptRepository`:
  - Track success/failure patterns
  - Link attempts to HTTP requests
  - Timeline analysis queries

### 3.4 Session Management Tools
- [ ] Add session management:
  - `CreateSessionTool` - Start new AI reasoning sessions
  - `UpdateSessionTool` - Update session metadata
  - `AssociateSessionTargetTool` - Link sessions to targets
  - `GetSessionSummaryTool` - Get session overview and progress
- [ ] Implement `AiSessionRepository`:
  - Session lifecycle management
  - Target association tracking
  - Progress metrics

## Phase 4: Advanced Features

### 4.1 Cross-Reference and Tagging
- [ ] Add cross-reference tools:
  - `LinkRequestToTargetTool` - Manual request/target association
  - `TagRequestTool` - Apply flexible tags to requests
  - `GetTargetRequestsTool` - Get all requests for target
  - `SearchRequestsTool` - Advanced request querying
- [ ] Implement `RequestTagRepository`:
  - Tag management and search
  - Tag auto-suggestions
  - Bulk tagging operations

### 4.2 Analytics and Reporting
- [ ] Add analytics tools:
  - `GetTargetStatsTool` - Request counts, success rates, timing
  - `GetSessionMetricsTool` - Session progress and effectiveness
  - `GetTechniqueAnalysisTool` - Which techniques work best
  - `GetTimelineAnalysisTool` - Attack progression over time
- [ ] Create dashboard/summary views for common queries

### 4.3 Data Management
- [ ] Add data cleanup tools:
  - `CleanupOldRequestsTool` - Remove old request data
  - `ExportSessionDataTool` - Export session for reporting
  - `ArchiveTargetTool` - Archive completed targets
- [ ] Implement data retention policies
- [ ] Add backup/restore capabilities

## Phase 5: Testing and Integration

### 5.1 Unit Testing
- [x] Create `tests/db/` directory structure
- [x] Test database models and repositories:
  - `tests/db/test_models.py`
  - `tests/db/test_repositories.py`
  - `tests/db/test_connection.py`
- [ ] Test AI logging tools:
  - `tests/servers/ai_logging/test_tools.py`
  - `tests/servers/ai_logging/test_providers.py`
- [ ] Mock database for HTTP request logging tests

### 5.2 Integration Testing
- [x] Test HTTP request auto-logging end-to-end
- [ ] Test AI tool workflows with real database
- [x] Test migration up/down scenarios
- [x] Test CLI database commands
- [ ] Test error handling and edge cases

### 5.3 Performance Testing
- [ ] Test with high request volumes
- [ ] Database query performance optimization
- [ ] Connection pool configuration tuning
- [ ] Memory usage monitoring

## Phase 6: CLI Integration and Documentation

### 6.1 CLI Server Integration
- [x] Update `src/code_mcp/cli.py`:
  - Database initialization already in `serve-http` command
  - AI logging tools integrated into `serve-http` (no separate command needed)
  - Database logging enabled by default when DATABASE_URL is configured
- [x] Update server adapter to register AI logging tools
- [ ] Test CLI integration with database features

### 6.2 Configuration Management
- [ ] Document environment variables in README
- [ ] Add configuration validation
- [ ] Create development vs. production config examples
- [ ] Add database connection troubleshooting guide

### 6.3 Documentation and Examples
- [ ] Update project README with database setup instructions
- [ ] Create AI workflow examples and tutorials
- [ ] Document all new MCP tools and their parameters
- [ ] Create troubleshooting guide for common issues
- [ ] Add performance tuning recommendations

## Implementation Order Rationale

**Phase 1** establishes the foundation - database models, migrations, and CLI tools for setup.

**Phase 2** integrates logging into existing HTTP functionality transparently, ensuring no disruption to current features.

**Phase 3** adds the AI-specific tools in logical order: targets first (foundational), then notes (documentation), then attempts (analysis).

**Phase 4** adds advanced features once core functionality is stable.

**Phase 5** ensures quality and reliability through comprehensive testing.

**Phase 6** polishes the user experience and provides proper documentation.

## Success Criteria

- [x] HTTP requests automatically logged to database without affecting performance
- [x] AI can create and manage targets via MCP tools (partial - notes/attempts pending)
- [x] Search and analysis capabilities enable effective reconnaissance tracking (basic search working)
- [x] CLI commands provide easy database management
- [ ] Comprehensive test coverage ensures reliability (partial - need AI tool tests)
- [ ] Documentation enables easy setup and usage (partial - need README updates)
- [ ] Performance scales to handle realistic ethical hacking workloads

## Estimated Timeline

- **Phase 1-2**: ~1-2 weeks (foundation and core integration)
- **Phase 3**: ~1-2 weeks (AI tools development)
- **Phase 4**: ~1 week (advanced features)
- **Phase 5**: ~1 week (testing and quality assurance)
- **Phase 6**: ~0.5 weeks (documentation and polish)

**Total**: ~4.5-6.5 weeks for complete implementation

This plan provides a systematic approach to building a robust database layer that enhances the AI-assisted ethical hacking capabilities while maintaining the project's existing architecture and quality standards.
