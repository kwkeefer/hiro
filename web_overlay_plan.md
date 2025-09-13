# Web Overlay Implementation Plan

## Overview
Comprehensive web interface for the hiro MCP server, providing rich UI for target management, context editing, request analysis, and session tracking. This overlay complements the terminal-based MCP tools with a visual interface optimized for complex operations and data exploration.

## Design Philosophy

### Core Principles
1. **Progressive Enhancement** - Terminal tools remain primary, web adds value
2. **Real-time Sync** - Changes in web UI immediately available to MCP tools
3. **Lightweight Stack** - Minimize JavaScript complexity, leverage server-side rendering
4. **Keyboard-First** - Full keyboard navigation for power users
5. **Context Switching** - Seamless movement between terminal and web

### Technology Stack
- **Backend**: FastAPI (async, already in Python ecosystem)
- **Frontend**: HTMX + Alpine.js (server-driven, minimal JS)
- **Templating**: Jinja2 (Python standard)
- **Styling**: Tailwind CSS (utility-first, dark mode support)
- **Editor**: CodeMirror 6 (markdown editing with vim mode)
- **Database**: Existing PostgreSQL (shared with MCP server)

## Phase 1: Foundation & Architecture

### 1.1 Project Structure
```
src/hiro/web/
├── __init__.py
├── app.py                      # FastAPI application
├── config.py                   # Web-specific configuration
├── routers/                    # API and view routers
│   ├── __init__.py
│   ├── targets.py             # Target management endpoints
│   ├── context.py             # Context editing endpoints
│   ├── requests.py            # HTTP request browser
│   ├── sessions.py            # AI session management
│   └── api.py                 # JSON API endpoints
├── services/                   # Business logic layer
│   ├── __init__.py
│   ├── target_service.py      # Target operations
│   ├── context_service.py     # Context management
│   └── analytics_service.py   # Data analysis
├── templates/                  # Jinja2 templates
│   ├── base.html              # Base layout
│   ├── targets/               # Target views
│   ├── requests/              # Request views
│   └── components/            # Reusable components
├── static/                     # Static assets
│   ├── css/                   # Stylesheets
│   ├── js/                    # JavaScript
│   └── img/                   # Images
└── middleware/                 # Custom middleware
    ├── __init__.py
    ├── auth.py                # Authentication (if needed)
    └── logging.py             # Request logging
```

### 1.2 Core Dependencies
```toml
# Add to pyproject.toml
fastapi = ">=0.104.0"
uvicorn = {extras = ["standard"], version = ">=0.24.0"}
jinja2 = ">=3.1.0"
python-multipart = ">=0.0.6"  # Form handling
httpx = ">=0.25.0"            # Async HTTP client
python-markdown = ">=3.5.0"    # Markdown rendering
pygments = ">=2.17.0"          # Syntax highlighting
```

### 1.3 Database Models (Shared)
- Use existing SQLAlchemy models from `db/models.py`
- Add web-specific mixins if needed:
  - `WebViewMixin` - Fields for UI display
  - `SearchMixin` - Full-text search helpers

## Phase 2: Target Management Interface

### 2.1 Target Dashboard
**Route**: `/targets`

**Features**:
- Grid/list view toggle
- Real-time search and filtering
- Bulk operations (status update, risk level)
- Quick actions via HTMX (no page reload)
- Context preview in expandable cards
- Sort by: last activity, risk level, discovery date

**Components**:
- Target card with status indicators
- Risk level badges (color-coded)
- Activity sparkline graph
- Quick edit modals

### 2.2 Target Detail View
**Route**: `/targets/{target_id}`

**Features**:
- Tabbed interface:
  - Overview (basic info, stats)
  - Context (markdown editor)
  - Notes (structured notes)
  - Requests (HTTP history)
  - Attempts (attack attempts)
  - Timeline (activity feed)
- Real-time updates via SSE
- Export options (markdown, JSON)

### 2.3 Target Context Editor
**Route**: `/targets/{target_id}/context`

**Features**:
- Split-pane editor (user context | agent context)
- CodeMirror with:
  - Markdown syntax highlighting
  - Vim key bindings (optional)
  - Auto-save with debouncing
  - Version history sidebar
- Context templates dropdown
- Markdown preview toggle
- Diff view for versions

## Phase 3: Request Browser & Analysis

### 3.1 Request Explorer
**Route**: `/requests`

**Features**:
- Timeline view of all HTTP requests
- Advanced filtering:
  - By target, method, status code
  - Date range picker
  - Response time thresholds
- Request/response viewer:
  - Headers, cookies, body
  - Syntax highlighting
  - Copy as curl command
- Bulk tagging interface

### 3.2 Request Detail View
**Route**: `/requests/{request_id}`

**Features**:
- Full request/response display
- Link to associated target
- Tag management
- Response diff tool (compare requests)
- Export options (HAR, curl)

### 3.3 Request Analytics
**Route**: `/requests/analytics`

**Features**:
- Response time graphs
- Status code distribution
- Most requested endpoints
- Cookie tracking analysis
- Error pattern detection

## Phase 4: AI Session Management

### 4.1 Session Dashboard
**Route**: `/sessions`

**Features**:
- Active/completed session list
- Session progress indicators
- Target association summary
- Success rate metrics

### 4.2 Session Detail View
**Route**: `/sessions/{session_id}`

**Features**:
- Session timeline
- Associated targets
- Attempts summary
- Request correlation
- Objective tracking

## Phase 5: Advanced Features

### 5.1 Search Interface
**Route**: `/search`

**Global search across**:
- Targets (host, title, context)
- Notes (content, tags)
- Requests (URL, headers, body)
- Sessions (objectives, descriptions)

**Features**:
- Faceted search results
- Search history
- Saved searches

### 5.2 Analytics Dashboard
**Route**: `/analytics`

**Visual analytics**:
- Target discovery timeline
- Risk distribution pie chart
- Success rate trends
- Most effective techniques
- Activity heatmap

### 5.3 Quick Command Palette
**Keyboard shortcut**: `Cmd/Ctrl + K`

**Features**:
- Fuzzy search for navigation
- Quick actions (create target, new note)
- Recent items
- Terminal command generation

## Phase 6: Integration & Polish

### 6.1 Terminal Integration
- CLI command to launch web UI: `hiro web`
- Auto-open browser option
- Share port with MCP server
- WebSocket for real-time sync

### 6.2 Authentication & Security
- Optional basic auth
- API key for programmatic access
- CORS configuration for MCP tools
- Rate limiting

### 6.3 Export & Reporting
- Export formats:
  - Markdown reports
  - JSON data dumps
  - CSV for analysis
- Report templates:
  - Target summary
  - Session report
  - Timeline export

### 6.4 User Preferences
- Dark/light theme toggle
- Editor preferences (vim mode, font size)
- Dashboard layout customization
- Notification settings

## Implementation Strategy

### Incremental Rollout
1. **MVP**: Target dashboard + context editor
2. **Phase 2**: Request browser
3. **Phase 3**: Session management
4. **Phase 4**: Analytics & search
5. **Phase 5**: Polish & advanced features

### Development Approach
- Start with server-side rendering (HTMX)
- Add interactivity progressively
- Keep JavaScript minimal
- Focus on keyboard navigation
- Test with real workflow

### Performance Considerations
- Pagination for large datasets
- Lazy loading for request bodies
- Debounced auto-save
- Caching for analytics
- Database query optimization

## Success Metrics

### User Experience
- Time to find specific target: < 3 seconds
- Context save latency: < 500ms
- Page load time: < 1 second
- Keyboard-only navigation possible

### Feature Adoption
- % of targets with context filled
- Web vs terminal tool usage ratio
- Most used web features
- User feedback scores

### Technical Health
- API response times
- Database query performance
- WebSocket connection stability
- Browser compatibility

## Future Enhancements

### Potential Add-ons
1. **Collaboration Features**
   - Multi-user support
   - Comment threads on targets
   - Shared sessions

2. **AI Enhancements**
   - Context suggestions
   - Pattern recognition
   - Automated tagging

3. **Visualization**
   - Network topology graphs
   - Attack path visualization
   - 3D timeline view

4. **Mobile Support**
   - Responsive design
   - Touch gestures
   - Mobile-specific views

## Notes

### Design Decisions
- **HTMX over SPA**: Reduces complexity, leverages server-side rendering
- **CodeMirror over simple textarea**: Professional editing experience
- **FastAPI over Flask**: Async support, better performance
- **Tailwind over custom CSS**: Rapid development, consistent design

### Integration Points
- Shares database with MCP server
- Uses same repository classes
- Respects MCP tool changes
- Can trigger MCP tool execution

### Development Priority
Focus on features that are painful in terminal:
1. Markdown editing (context)
2. Visual data browsing (requests)
3. Bulk operations (targets)
4. Analytics (patterns)

This plan provides a comprehensive web overlay that enhances rather than replaces the terminal workflow, giving users the best tool for each task.
