# Web Overlay MVP Implementation Plan

## Overview
Minimal web interface for the hiro MCP server, providing essential UI for target management, context editing, and HTTP request viewing. This overlay complements the terminal-based MCP tools with a focused visual interface for the most common operations.

## MVP Scope

### Core Features
1. **Target Management** - View, create, update targets with status and risk levels
2. **Context Editing** - Edit user and agent context with markdown syntax highlighting
3. **HTTP Request Viewing** - Browse requests made against each target
4. **Target Attributes** - Modify status, risk level, port, protocol, and metadata

### Out of Scope (Not MVP)
- AI session management
- Analytics and reporting
- Advanced search
- Collaboration features
- Export functionality
- Mobile support

## Technology Stack

### Backend
- **Framework**: FastAPI (async, already in Python ecosystem)
- **Database**: Existing PostgreSQL (shared with MCP server)
- **Templating**: Jinja2 (Python standard)

### Frontend
- **UI Updates**: HTMX (server-driven, minimal JavaScript)
- **Styling**: Tailwind CSS (utility-first, dark mode support)
- **Markdown Editor**: CodeMirror 6 (with markdown mode)
- **HTTP Highlighting**: Prism.js (lightweight syntax highlighting)

## Project Structure

```
src/hiro/web/
├── __init__.py
├── app.py                      # FastAPI application
├── routers/                    # Route handlers
│   ├── __init__.py
│   ├── targets.py             # Target CRUD endpoints
│   └── api.py                 # JSON API for HTMX
├── services/                   # Business logic
│   ├── __init__.py
│   └── target_service.py      # Target operations
├── templates/                  # Jinja2 templates
│   ├── base.html              # Base layout
│   ├── targets.html           # Target list view
│   ├── target.html            # Target detail view
│   └── components/            # Reusable components
│       ├── target_card.html
│       ├── context_editor.html
│       └── request_viewer.html
└── static/                     # Static assets
    ├── css/
    │   └── main.css           # Tailwind styles
    └── js/
        └── app.js             # Minimal JS for editor setup
```

## Core Dependencies

```toml
# Add to pyproject.toml
fastapi = ">=0.104.0"
uvicorn = {extras = ["standard"], version = ">=0.24.0"}
jinja2 = ">=3.1.0"
python-multipart = ">=0.0.6"  # Form handling
```

## Frontend Dependencies (CDN)
- HTMX - Dynamic UI updates without full page reloads
- Tailwind CSS - Utility-first styling
- CodeMirror 6 - Markdown editing
- Prism.js - Syntax highlighting for HTTP

## Feature Implementation

### 1. Target Dashboard (`/targets`)

**Functionality:**
- List all targets in a responsive grid
- Display key info: host, port, status badge, risk level
- Show quick stats: request count, last activity, notes count
- Quick actions: Edit status, Update risk level, View details, Edit context
- Filter by status and risk level with real-time search
- Sort by last activity or discovery date
- Link to target detail page

**UI Components:**
- Enhanced target cards with clear visual hierarchy:
  - Primary: Host/title prominently displayed
  - Secondary: Protocol, port, and endpoint details
  - Status badges: Color-coded (active=green, blocked=red, inactive=gray, completed=blue)
  - Risk badges: Color-coded (low=green, medium=yellow, high=orange, critical=red)
  - Quick stats bar showing requests, activity, notes
  - Action buttons at bottom with clear separation
- Search bar with instant filtering (300ms debounce)
- Filter dropdown menus for status and risk
- HTMX-powered updates (no page reload)

### 2. Target Detail View (`/targets/{target_id}`)

**Functionality:**
- Display all target information
- Three main sections via tabs:
  - Overview: Basic info, status, risk, metadata
  - Context: Dual-pane markdown editor
  - Requests: HTTP request history

**Context Editor Features:**
- Split view: User Context | Agent Context
- CodeMirror with markdown syntax highlighting
- Auto-save on blur with debouncing
- Visual feedback for save status
- Version number display (read-only)

**Request Viewer Features:**
- List of HTTP requests for this target
- Expandable request/response details
- Syntax highlighting with Prism.js
- Show method, URL, status code, response time
- Sort by timestamp

### 3. API Endpoints

```python
# Target endpoints
GET    /api/targets           # List targets (JSON)
GET    /api/targets/{id}      # Get target details
PATCH  /api/targets/{id}      # Update target fields
POST   /api/targets/{id}/context  # Save context

# Request endpoints
GET    /api/targets/{id}/requests  # Get target's HTTP requests
```

### 4. Database Integration

Use existing SQLAlchemy models:
- `Target` - Main target entity
- `TargetContext` - Context versions
- `HttpRequest` - HTTP request logs
- Leverage existing repositories from MCP server

### 5. Critical UI Components

#### Loading State Component
```html
<!-- Add to base template -->
<div id="loading-indicator" class="htmx-indicator fixed inset-0 bg-black bg-opacity-25 z-50 flex items-center justify-center">
    <div class="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-xl">
        <svg class="animate-spin h-8 w-8 text-blue-600" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
        </svg>
    </div>
</div>
```

#### Error Toast Component
```html
<!-- Toast container in base template -->
<div id="toast-container" class="fixed top-4 right-4 z-50 space-y-2">
    <!-- Toasts inserted here by JavaScript -->
</div>

<script>
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `p-4 rounded-lg shadow-lg text-white ${
        type === 'error' ? 'bg-red-600' :
        type === 'success' ? 'bg-green-600' : 'bg-blue-600'
    }`;
    toast.textContent = message;
    document.getElementById('toast-container').appendChild(toast);
    setTimeout(() => toast.remove(), 5000);
}

// Hook into HTMX events
document.body.addEventListener('htmx:responseError', (evt) => {
    showToast('Operation failed. Please try again.', 'error');
});
</script>
```

#### Empty State Component
```html
<!-- Example: No targets empty state -->
<div class="text-center py-12" id="empty-targets">
    <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M5 12h14M12 5l7 7-7 7"></path>
    </svg>
    <h3 class="mt-2 text-sm font-medium text-gray-900 dark:text-white">No targets found</h3>
    <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
        Get started by adding your first target to begin testing.
    </p>
    <div class="mt-6">
        <button onclick="openNewTargetModal()"
                class="inline-flex items-center px-4 py-2 border border-transparent
                       text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700">
            <svg class="-ml-1 mr-2 h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M10 5a1 1 0 011 1v3h3a1 1 0 110 2h-3v3a1 1 0 11-2 0v-3H6a1 1 0 110-2h3V6a1 1 0 011-1z" clip-rule="evenodd"></path>
            </svg>
            Add Target
        </button>
    </div>
</div>
```

#### Keyboard Navigation Implementation
```javascript
// Add to app.js
class KeyboardNavigation {
    constructor() {
        this.selectedIndex = -1;
        this.setupShortcuts();
    }

    setupShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Don't interfere with input fields
            if (e.target.matches('input, textarea, select')) {
                if (e.key === 'Escape') {
                    e.target.blur();
                }
                return;
            }

            // Global shortcuts
            switch(e.key) {
                case '?':
                    if (e.shiftKey || e.ctrlKey) {
                        e.preventDefault();
                        this.showHelp();
                    }
                    break;
                case 'f':
                case '/':
                    e.preventDefault();
                    document.querySelector('[data-search-input]')?.focus();
                    break;
                case 'n':
                    e.preventDefault();
                    this.openNewTargetModal();
                    break;
                case 'j':
                    e.preventDefault();
                    this.navigateTargets(1);
                    break;
                case 'k':
                    e.preventDefault();
                    this.navigateTargets(-1);
                    break;
                case 'Enter':
                    if (this.selectedIndex >= 0) {
                        e.preventDefault();
                        this.openSelectedTarget();
                    }
                    break;
                case 'Escape':
                    e.preventDefault();
                    this.closeModalsAndClear();
                    break;
            }

            // Combo shortcuts (e.g., g + t)
            if (e.key === 'g') {
                this.waitForNextKey('t', () => {
                    window.location.href = '/targets';
                });
            }
        });
    }

    showHelp() {
        // Show keyboard shortcuts modal
        document.getElementById('shortcuts-modal')?.classList.remove('hidden');
    }

    navigateTargets(direction) {
        const targets = document.querySelectorAll('[data-target-card]');
        this.selectedIndex = Math.max(0, Math.min(targets.length - 1, this.selectedIndex + direction));
        targets.forEach((t, i) => {
            t.classList.toggle('ring-2', i === this.selectedIndex);
            t.classList.toggle('ring-blue-500', i === this.selectedIndex);
        });
    }
}
```

## Implementation Strategy

### Phase 1: Foundation (Day 1)
- [ ] Set up FastAPI app structure
- [ ] Create base template with Tailwind
- [ ] Implement target list endpoint
- [ ] Basic target dashboard UI

### Phase 2: Target Details (Day 2)
- [ ] Target detail page with tabs
- [ ] Context editor integration
- [ ] HTTP request viewer
- [ ] HTMX interactions

### Phase 3: Polish (Day 3)
- [ ] Status/risk level updates
- [ ] Filter and sort functionality
- [ ] Error handling
- [ ] Dark mode support

## UI/UX Guidelines

### Design Principles
- **Minimal**: Focus on essential information
- **Fast**: Server-side rendering with selective updates
- **Keyboard-friendly**: Tab navigation, shortcuts for common actions
- **Responsive**: Works on desktop and tablet (mobile not priority)
- **Feedback**: Clear loading states and error handling
- **Guidance**: Helpful empty states for new users

### Visual Hierarchy
1. Target host/title - Most prominent
2. Status and risk indicators - High visibility
3. Context preview - Subdued but accessible
4. Metadata - Available but not prominent

### Color Scheme
- Use Tailwind's default palette
- Status colors: green (active), gray (inactive), red (blocked), blue (completed)
- Risk colors: green (low), yellow (medium), orange (high), red (critical)
- Dark mode with `dark:` utilities

### Keyboard Navigation
- **Tab order**: Logical flow through all interactive elements
- **Keyboard shortcuts**:
  - `Ctrl+/` or `?` - Show keyboard shortcuts help modal
  - `g t` - Go to targets dashboard
  - `n` - Create new target (opens modal)
  - `f` or `/` - Focus search/filter input
  - `Escape` - Close modals, clear filters, or cancel operations
  - `j/k` - Navigate up/down through target list
  - `Enter` - Open selected target
- **Focus indicators**: Clear visible focus rings on all interactive elements

### Loading & Error States
- **Loading indicators**: Spinner overlay for all HTMX requests
  - Semi-transparent background overlay
  - Centered spinner with smooth animation
  - Prevent multiple simultaneous requests
- **Error handling**:
  - Toast notifications for errors (auto-dismiss after 5 seconds)
  - Inline error messages for form validation
  - Retry buttons for failed operations
- **Success feedback**: Brief success toasts for completed actions

### Empty States
- **No targets**: Welcome message with "Add your first target" CTA
- **No HTTP requests**: Informative message "Requests will appear here after testing"
- **No context**: Prompt to "Add context to help the AI understand this target"
- **No search results**: "No targets match your search" with clear filters button
- Each empty state includes:
  - Relevant icon or illustration
  - Clear explanation text
  - Actionable next step (button or instruction)

## Development Commands

```bash
# Run the web server
uvicorn src.hiro.web.app:app --reload --port 8000

# Or add to existing CLI
hiro web --port 8000
```

## Success Metrics

### Performance
- Page load time: < 500ms
- Context save latency: < 200ms
- Request list load: < 300ms

### Functionality
- All CRUD operations work without page reload
- Context changes persist immediately
- HTTP requests display correctly

## Notes

### Why This Approach
- **HTMX over SPA**: Simpler, faster development, less JavaScript complexity
- **CodeMirror for editing**: Professional editing experience for markdown
- **Server-side first**: Leverages existing Python backend code
- **Minimal dependencies**: Reduces maintenance burden

### Integration with MCP
- Shares database and models
- Web changes immediately visible to MCP tools
- Can run alongside MCP server on different port
- No authentication in MVP (local use only)

### What We're NOT Building (Yet)
- User authentication
- Multi-user support
- Real-time WebSocket updates
- Complex analytics
- Report generation
- Mobile-specific features
- API rate limiting
- File uploads

This MVP focuses on the essential features that provide the most value for managing targets and their context through a web interface, while keeping the implementation simple and maintainable.
