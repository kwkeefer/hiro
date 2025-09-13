# hiro

Getting started with MCP stuff

## Features

- Modern Python 3.12 project with src layout
- Dependency management with [uv](https://github.com/astral-sh/uv)
- Testing with pytest
- Code formatting with ruff
- Type checking with mypy
- CLI interface with click
- Docker support for containerization
- GitHub Actions for CI/CD
- Pre-commit hooks for code quality
- Claude Code agents for automated code review

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

### Cookie Session Management

The HTTP server includes dynamic cookie session management via MCP resources. This allows the LLM to fetch and use authentication cookies from external files, enabling authenticated HTTP requests.

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
