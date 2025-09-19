# hiro

Getting started with MCP stuff

## Features

### Core Capabilities
- Modern Python 3.12 project with src layout
- MCP (Model Context Protocol) server implementation
- HTTP request tools with proxy support (Burp Suite, OWASP ZAP integration)
- Database-backed target and context management
- Cookie session/profile management for authenticated testing
- Prompt resource system for LLM agent guidance

### Development Tools
- Dependency management with [uv](https://github.com/astral-sh/uv)
- Testing with pytest
- Code formatting with ruff
- Type checking with mypy
- CLI interface with click
- Docker support for containerization
- GitHub Actions for CI/CD
- Pre-commit hooks for code quality

## Installation

### For Development

```bash
# Clone the repository
git clone https://github.com/kwkeefer/hiro.git
cd hiro

# Set up development environment
make dev
```

### For Production

```bash
# Install with uv
uv pip install hiro

# Or install from source
make install
```

## Usage

### Command Line Interface

```bash
# Run the CLI
hiro --help

# Start the HTTP MCP server
hiro serve-http

# Start with proxy routing (e.g., through Burp Suite)
hiro serve-http --proxy http://127.0.0.1:8080

# Or using make
make run
```

### Database Setup for AI-Assisted Ethical Hacking

The HTTP server includes optional PostgreSQL integration for tracking targets and reconnaissance data. When enabled, all HTTP requests are automatically logged and targets are auto-detected.

#### Quick Setup

1. **Start PostgreSQL** (using Docker):
   ```bash
   docker run -d \
     --name hiro-postgres \
     -e POSTGRES_PASSWORD=password \
     -e POSTGRES_DB=hiro \
     -p 5432:5432 \
     postgres:16
   ```

2. **Set DATABASE_URL** and start server:
   ```bash
   export DATABASE_URL="postgresql://postgres:password@localhost:5432/hiro"
   hiro serve-http
   ```

3. **Initialize database** (first time only):
   ```bash
   hiro db init    # Create tables
   hiro db migrate # Run any pending migrations
   ```

That's it! The server now auto-logs all HTTP requests and provides AI tools for target management.

#### Available MCP Tools (6 Total)

When database logging is enabled, these MCP tools become available to AI agents:

**Target Management (4 tools):**
- **`create_target`** - Register a new target to test
  - Parameters: host, port, protocol, title, status, risk_level, notes
  - Example: Create target for "example.com" on port 443 with HTTPS

- **`update_target_status`** - Update target progress and metadata
  - Parameters: target_id, status (active/blocked/completed), risk_level, notes
  - Example: Mark target as "blocked" after WAF detection

- **`get_target_summary`** - Get detailed information about a target
  - Parameters: target_id
  - Returns: Target details, request counts, notes, last activity

- **`search_targets`** - Find targets by various criteria
  - Parameters: query, status, risk_level, protocol, limit
  - Example: Find all "active" targets with "high" risk level

**Context Management (2 tools):**
- **`get_target_context`** - Retrieve findings and notes for a target
  - Parameters: target_id, include_history (optional)
  - Returns: Current context/notes, optionally with version history

- **`update_target_context`** - Store new findings about a target
  - Parameters: target_id, user_context, agent_context, append_mode
  - Creates new version if no context exists, or updates existing
  - All changes are versioned for audit trail

#### Example Ethical Hacking Workflow

```python
# 1. AI creates a target for testing
create_target(host="testsite.com", port=443, protocol="https",
              title="Test Site", risk_level="medium")

# 2. AI makes HTTP requests (auto-logged, no tool needed)
http_request(url="https://testsite.com/admin", method="GET")
http_request(url="https://testsite.com/api/v1/users", method="GET")

# 3. AI stores findings
update_target_context(
    target_id="...",
    user_context="Found exposed /admin endpoint, returns 403. API endpoint at /api/v1/ appears to be REST.",
    append_mode=True
)

# 4. After more testing, AI updates status
update_target_status(
    target_id="...",
    status="blocked",
    notes="WAF detected and blocking after aggressive scanning"
)

# 5. AI retrieves all findings later
get_target_context(target_id="...", include_history=True)
```

#### Key Features

- **Automatic HTTP Logging**: Every HTTP request is logged to the database transparently
- **Target Auto-Detection**: Targets are automatically created from HTTP requests
- **Immutable Versioning**: All context changes create new versions (full audit trail)
- **Lazy Loading**: Database connection only initialized when needed
- **Unified Server**: All features integrated into single `serve-http` command

### Cookie Session Management

The HTTP server includes two cookie management features:

1. **Cookie Profiles in HTTP Requests**: Pass `cookie_profile` parameter to automatically load cookies from pre-configured sessions
2. **Dynamic Cookie Resources**: MCP resources that provide authentication cookies to LLM agents

#### Using Cookie Profiles in Requests

```python
# Use a pre-configured cookie session
http_request(
    url="https://api.example.com/protected",
    cookie_profile="admin_session"  # Automatically loads cookies from profile
)

# Override specific cookies while using a profile
http_request(
    url="https://api.example.com/data",
    cookie_profile="admin_session",
    cookies='{"extra_token": "xyz"}'  # Manual cookies take precedence
)
```

#### Setup

1. **Create configuration file**:
   ```bash
   # Configuration location: $XDG_CONFIG_HOME/hiro/cookie_sessions.yaml
   # (defaults to ~/.config/hiro/cookie_sessions.yaml if XDG_CONFIG_HOME is not set)

   CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/hiro"
   mkdir -p "$CONFIG_DIR"

   cat > "$CONFIG_DIR/cookie_sessions.yaml" << 'EOF'
   version: "1.0"
   sessions:
     github_personal:
       description: "GitHub personal account session"
       cookie_file: "github_personal.json"  # Relative to data directory
       cache_ttl: 3600  # Cache for 1 hour
       metadata:
         domains: ["github.com", "api.github.com"]
   EOF
   ```

2. **Create cookie files** with proper permissions:
   ```bash
   # Cookie storage: $XDG_DATA_HOME/hiro/cookies/
   # (defaults to ~/.local/share/hiro/cookies/ if XDG_DATA_HOME is not set)

   DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/hiro/cookies"
   mkdir -p "$DATA_DIR"

   # Create a cookie file with restricted permissions
   echo '{"session_token": "abc123", "csrf_token": "xyz789"}' > "$DATA_DIR/github_personal.json"
   chmod 600 "$DATA_DIR/github_personal.json"
   ```

3. **Use in MCP**: The LLM can now:
   - List available sessions: `ListMcpResources()`
   - Fetch cookies: `ReadMcpResource("cookie-session://github_personal")`
   - Use cookies in HTTP requests

#### Security Features

- **File permission validation**: Cookie files must have 0600 or 0400 permissions
- **Path traversal protection**: Cookie files must be within allowed directories
- **Caching**: Reduces file I/O with configurable TTL per session
- **Session name validation**: Only alphanumeric, underscore, and hyphen characters allowed

#### External Authentication Scripts

Cookie sessions are designed to work with external authentication scripts that update the JSON files:

```python
#!/usr/bin/env python3
# Example authentication script
import json
import os
from pathlib import Path

def update_cookies(session_name: str, cookies: dict):
    """Update cookie file for a session."""
    # Respect XDG_DATA_HOME if set, otherwise use default
    xdg_data_home = os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))
    cookie_dir = Path(xdg_data_home) / "hiro/cookies"
    cookie_file = cookie_dir / f"{session_name}.json"

    # Create directory if needed
    cookie_dir.mkdir(parents=True, exist_ok=True)

    # Write cookies with secure permissions
    with open(cookie_file, 'w') as f:
        json.dump(cookies, f)
    os.chmod(cookie_file, 0o600)

# Authenticate and get cookies (implementation depends on service)
cookies = authenticate_to_service()
update_cookies("github_personal", cookies)
```

See `cookie_sessions.yaml.example` for a complete configuration example.

### Prompt Resource System

The server provides structured guidance to LLM agents through MCP prompt resources. These guides help agents understand how to use the tools effectively while emphasizing that user instructions always take precedence.

#### Built-in Guides

- **`prompt://tool_usage_guide`** - Comprehensive guide explaining all tools and their parameters
- **`prompt://quickstart`** - Quick reference for getting started
- **`prompt://context_patterns`** - Best practices for documenting findings

#### Accessing Prompts

LLM agents can fetch prompts in multiple formats:

```python
# Get as JSON (default)
ReadMcpResource("prompt://tool_usage_guide")

# Get as YAML
ReadMcpResource("prompt://tool_usage_guide?format=yaml")

# Get as Markdown
ReadMcpResource("prompt://tool_usage_guide?format=markdown")
```

#### Custom Prompts

Add your own prompts to `~/.config/hiro/prompts/`:

```yaml
# ~/.config/hiro/prompts/my_workflow.yaml
name: "Custom Testing Workflow"
version: "1.0"
description: "Organization-specific testing methodology"
role: |
  You are testing according to our company standards.
  Always check for these specific vulnerabilities...
```

Custom prompts override built-in prompts with the same filename. Set `HIRO_PROMPTS_DIR` environment variable to use a different directory.

### As a Library

```python
from hiro import __version__
from hiro.servers.http.cookie_sessions import CookieSessionProvider

# Use cookie sessions programmatically
provider = CookieSessionProvider()
resources = provider.get_resources()
```

## Development

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run only unit tests
make test-unit

# Run only integration tests
make test-integration
```

### Code Quality

```bash
# Run linting
make lint

# Format code
make format

# Type checking
make typecheck
```

### Building

```bash
# Build distribution packages
make build
```

### Docker

```bash
# Build Docker image
make docker-build

# Run Docker container
make docker-run

# Using docker-compose
make docker-compose-up
make docker-compose-down
```

## Project Structure

```
hiro/
├── src/
│   └── hiro/
│       ├── __init__.py
│       ├── core/           # Core business logic
│       ├── api/            # API interfaces
│       ├── db/             # Database models and queries
│       └── utils/          # Utility functions
├── tests/                  # Test suite (mirrors src structure)
│   ├── conftest.py
│   ├── core/
│   ├── api/
│   ├── db/
│   └── utils/
├── docs/                   # Documentation
├── config/                 # Configuration files
├── scripts/                # Utility scripts
├── pyproject.toml          # Project configuration
├── Makefile                # Development commands
└── README.md               # This file
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License
This project is licensed under the MIT License - see the LICENSE file for details.

## Author

Kyle Keefer - kwkeefer@gmail.com

## Acknowledgments

- Built with [cookiecutter-uv](https://github.com/kwkeefer/cookiecutter-uv)
- Package management by [uv](https://github.com/astral-sh/uv)
