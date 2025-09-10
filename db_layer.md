# Database Layer Design for AI-Assisted Ethical Hacking

## Overview
Add PostgreSQL-backed logging system for HTTP requests/responses with AI reasoning tracking and target management, following the project's hybrid architecture approach.

## Database Schema Design

### Core Tables

#### Target Management
1. **`targets`** - Master table for tracking specific hosts/endpoints
2. **`target_notes`** - Detailed reconnaissance notes per target
3. **`target_attempts`** - Specific attack attempts against targets

#### Request/Response Logging
4. **`http_requests`** - All HTTP request/response data
5. **`ai_sessions`** - AI reasoning sessions
6. **`request_tags`** - Flexible labeling system

#### Relationships
7. **`target_requests`** - Link requests to targets
8. **`session_targets`** - Associate sessions with targets

### Detailed Schema Definitions

#### `targets` Table
```sql
CREATE TABLE targets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    host VARCHAR(255) NOT NULL,
    port INTEGER,
    protocol VARCHAR(10) NOT NULL CHECK (protocol IN ('http', 'https')),
    base_url VARCHAR(500) GENERATED ALWAYS AS (
        protocol || '://' || host ||
        CASE WHEN port IS NOT NULL THEN ':' || port ELSE '' END
    ) STORED,
    title VARCHAR(255),
    status VARCHAR(20) NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'inactive', 'blocked', 'completed')),
    discovery_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_activity TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    risk_level VARCHAR(10) DEFAULT 'medium'
        CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(host, port, protocol)
);
```

#### `target_notes` Table
```sql
CREATE TABLE target_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    target_id UUID NOT NULL REFERENCES targets(id) ON DELETE CASCADE,
    note_type VARCHAR(50) NOT NULL
        CHECK (note_type IN ('reconnaissance', 'vulnerability', 'configuration', 'access', 'other')),
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    tags TEXT[] DEFAULT '{}',
    confidence VARCHAR(10) DEFAULT 'medium'
        CHECK (confidence IN ('low', 'medium', 'high')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

#### `target_attempts` Table
```sql
CREATE TABLE target_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    target_id UUID NOT NULL REFERENCES targets(id) ON DELETE CASCADE,
    session_id UUID REFERENCES ai_sessions(id),
    attempt_type VARCHAR(50) NOT NULL
        CHECK (attempt_type IN ('scan', 'exploit', 'enumerate', 'bypass', 'escalate', 'other')),
    technique VARCHAR(255) NOT NULL,
    payload TEXT,
    expected_outcome TEXT NOT NULL,
    actual_outcome TEXT,
    success BOOLEAN,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);
```

#### `http_requests` Table
```sql
CREATE TABLE http_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES ai_sessions(id),
    method VARCHAR(10) NOT NULL,
    url TEXT NOT NULL,
    host VARCHAR(255) NOT NULL,
    path TEXT NOT NULL,
    query_params JSONB,
    headers JSONB NOT NULL DEFAULT '{}',
    cookies JSONB,
    request_body TEXT,
    status_code INTEGER,
    response_headers JSONB,
    response_body TEXT,
    response_size INTEGER,
    elapsed_ms DECIMAL(10,3),
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

#### `ai_sessions` Table
```sql
CREATE TABLE ai_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255),
    description TEXT,
    objective TEXT,
    status VARCHAR(20) DEFAULT 'active'
        CHECK (status IN ('active', 'paused', 'completed', 'failed')),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);
```

#### `request_tags` Table
```sql
CREATE TABLE request_tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID NOT NULL REFERENCES http_requests(id) ON DELETE CASCADE,
    tag VARCHAR(100) NOT NULL,
    value VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(request_id, tag)
);
```

#### `target_requests` Table
```sql
CREATE TABLE target_requests (
    target_id UUID NOT NULL REFERENCES targets(id) ON DELETE CASCADE,
    request_id UUID NOT NULL REFERENCES http_requests(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (target_id, request_id)
);
```

#### `session_targets` Table
```sql
CREATE TABLE session_targets (
    session_id UUID NOT NULL REFERENCES ai_sessions(id) ON DELETE CASCADE,
    target_id UUID NOT NULL REFERENCES targets(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (session_id, target_id)
);
```

## Implementation Structure

### Database Module (`src/code_mcp/db/`)
- `models.py` - SQLAlchemy/Pydantic models
- `connection.py` - Database connection management
- `repositories.py` - Data access layer
- `migrations/` - Alembic migration files
- `schemas.py` - Pydantic schemas for validation

### Integration Points
- **HttpRequestTool** - Auto-log requests/responses transparently
- **New AI Tools** - Target management, session tracking, attempt logging
- **CLI** - Database setup, migration commands
- **Configuration** - Extend existing DatabaseSettings

### New MCP Tools for AI

#### Target Operations
- `create_target(host, port?, protocol?)` - Register new target
- `update_target_status(target_id, status)` - Update target status
- `get_target_summary(host)` - Get complete target overview
- `search_targets(query?, status?, risk_level?)` - Find targets

#### Note Management
- `add_target_note(target_id, type, title, content, tags?)` - Add reconnaissance notes
- `update_target_note(note_id, content)` - Update existing note
- `search_target_notes(query, tags?)` - Search across all target notes
- `get_target_notes(target_id, type?)` - Get notes for specific target

#### Attempt Tracking
- `log_attempt(target_id, type, technique, expected, notes)` - Record attempt
- `update_attempt_outcome(attempt_id, success, actual_outcome)` - Update results
- `get_target_attempts(target_id, technique?)` - Review attempt history
- `get_attempt_details(attempt_id)` - Get specific attempt info

#### Session Management
- `create_session(name?, description?, objective?)` - Start new reasoning session
- `update_session(session_id, status?, description?)` - Update session
- `associate_session_target(session_id, target_id)` - Link session to target
- `get_session_summary(session_id)` - Review session progress

#### Cross-Reference Operations
- `link_request_to_target(request_id, target_id)` - Associate HTTP request with target
- `get_target_requests(target_id, timeframe?)` - Get all requests for target
- `tag_request(request_id, tag, value?)` - Apply tags to HTTP requests
- `search_requests(query?, tags?, target_id?)` - Query logged requests

## Technical Architecture

### Dependencies
- **SQLAlchemy 2.0** (async) - ORM and database toolkit
- **asyncpg** - PostgreSQL async driver
- **Alembic** - Database migration management
- **Pydantic** - Data validation and serialization

### Architecture Patterns
- **Repository Pattern** - Testable data access layer
- **Async/Await** - Non-blocking database operations
- **Connection Pooling** - Efficient database connections
- **Migration Management** - Version-controlled schema changes

### CLI Extensions
- `code_mcp db init` - Initialize database and run migrations
- `code_mcp db migrate` - Run pending migrations
- `code_mcp db reset` - Reset database for testing
- `code_mcp db seed` - Load sample data for development
- `code_mcp serve-ai` - Start server with AI logging tools enabled

### Configuration Extensions
Leverage existing DatabaseSettings in `settings.py`:
- Database URL, connection pooling
- Add AI logging-specific options:
  - Auto-logging enabled/disabled
  - Request body size limits
  - Data retention policies

## Workflow Benefits

### Target-Centric Organization
- AI maintains detailed dossiers on each target
- Track what's been tried, what worked, what failed
- Build comprehensive attack surface maps
- Historical context for decision making

### Automated Logging
- **Transparent HTTP logging** - Requests auto-logged without AI awareness
- **Rich metadata** - Headers, timing, response codes, body content
- **Error tracking** - Failed requests and connection issues

### AI Reasoning Chain
- **Session tracking** - Group related attempts for engagement tracking
- **Attempt documentation** - Record reasoning, expectations, outcomes
- **Knowledge building** - Reference past attempts before trying new techniques
- **Success patterns** - Identify what works against similar targets

### Search and Analysis
- **Full-text search** - Across notes, attempts, request/response bodies
- **Tag-based filtering** - Flexible categorization system
- **Timeline analysis** - Track progression of attacks over time
- **Success metrics** - Measure effectiveness of different techniques

## Example AI Workflow

```python
# Start new engagement
session_id = create_session("WebApp Pentest", "Testing example.com web application")

# Register target
target_id = create_target("example.com", 80, "http")
associate_session_target(session_id, target_id)

# Initial reconnaissance
add_target_note(target_id, "reconnaissance", "Initial scan",
    "Apache 2.4.41, PHP 7.4.28, WordPress detected")

# Plan attack
attempt_id = log_attempt(target_id, "scan", "directory_brute_force",
    "Find hidden directories and files",
    "Starting with common.txt wordlist")

# HTTP requests automatically logged and linked to target during execution

# Record results
update_attempt_outcome(attempt_id, True,
    "Found /admin (403), /backup (200), /wp-admin (302)")

# Document findings
add_target_note(target_id, "vulnerability", "Exposed backup directory",
    "http://example.com/backup/ contains database dumps and source code")

# Continue with targeted attacks based on findings...
```

This design provides a comprehensive foundation for AI-assisted ethical hacking workflows with full traceability and institutional knowledge building.
