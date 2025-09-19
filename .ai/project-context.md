# Project Context for hiro

## Overview
Getting started with MCP stuff

## Project Type
- **Name**: hiro
- **Package**: hiro
- **Version**: 0.1.0
- **Python Version**: 3.12
- **Author**: Kyle Keefer (kwkeefer@gmail.com)

## Technology Stack
- **Language**: Python 3.12
- **Package Manager**: uv
- **Build System**: Hatchling
- **Testing Framework**: pytest
- **Linting/Formatting**: ruff
- **Type Checking**: mypy
- **CLI Framework**: click
- **Containerization**: Docker
- **CI/CD**: GitHub Actions
- **Git Hooks**: pre-commit

## Project Structure
```
hiro/
├── src/hiro/   # Main package source code
│   ├── core/                              # Core business logic
│   │   └── config/                        # Configuration management
│   ├── api/                               # API interfaces
│   ├── db/                                # Database modules
│   └── utils/                             # Utility functions
├── tests/                                 # Test suite (mirrors src structure)
├── docs/                                  # Documentation
└── scripts/                               # Utility scripts
```

## Key Design Decisions
1. **Source Layout**: Using `src/` layout for better testing isolation and import clarity
2. **Test Structure**: Tests mirror source structure for easy navigation
3. **Test Markers**: Using pytest markers (@pytest.mark.unit, @pytest.mark.integration) instead of directory separation
4. **Development Workflow**: Makefile as primary interface for common tasks

## Development Commands
- `make dev` - Set up development environment
- `make test` - Run all tests
- `make test-unit` - Run unit tests only
- `make test-integration` - Run integration tests only
- `make lint` - Run linting checks
- `make format` - Format code
- `make typecheck` - Type checking
- `make build` - Build distribution packages
- `make run` - Run the CLI application

## Current State
- [ ] Initial project setup
- [ ] Core functionality implementation
- [ ] API design and implementation
- [ ] Database integration
- [ ] Testing coverage
- [ ] Documentation
- [ ] Deployment configuration

## Important Files
- `pyproject.toml` - Project configuration and dependencies
- `Makefile` - Development automation
- `.ai/` - AI assistant instructions and context
- `.claude/` - Claude Code agents and configuration
- `tests/conftest.py` - Shared test fixtures

## Architecture Notes

### MCP Server Architecture - Unified Server, Multiple Tool Categories

**IMPORTANT**: Despite having multiple directories under `servers/`, there is only **ONE** MCP server.

```
src/hiro/servers/           # Tool collections for the unified server
├── http/                        # HTTP request tools (core functionality)
│   ├── tools.py                 # HTTP request execution with cookie profile support
│   ├── providers.py             # Tool provider with config injection
│   ├── config.py                # HTTP-specific configuration
│   └── cookie_sessions.py       # Cookie session/profile management
├── ai_logging/                  # Target management tools (database features)
│   ├── tools.py                 # Target CRUD operations
│   ├── providers.py             # Tool provider with DB repositories
│   └── (works WITH http/, not separately)
└── prompts/                     # Prompt guides for LLM agents
    ├── provider.py              # MCP resource provider for prompts
    └── guides/                  # Built-in prompt YAML files
        ├── tool_usage_guide.yaml
        ├── quickstart.yaml
        └── context_patterns.yaml
```

When you run `hiro serve-http`:
- **Always includes**: HTTP request tools with cookie profile support
- **When DB configured**: Also includes target management tools
- **Cookie sessions**: MCP resources for pre-configured auth sessions
- **Prompt guides**: MCP resources for agent guidance
- **Result**: Single unified server with multiple tool categories and resources

### FastMCP Integration Philosophy - Hybrid Approach
We use a **hybrid approach** that balances architectural purity with pragmatic simplicity:

#### What We Keep (Protocol Organization)
- **Provider classes** - `HttpToolProvider` and `AiLoggingToolProvider` organize tools with dependency injection
- **Business logic isolation** - Tool implementations (`HttpRequestTool.execute()`) are pure business logic
- **Testable structure** - Can unit test tools without FastMCP dependencies
- **Clear module boundaries** - Tool categories live in separate `servers/` subdirectories

#### What We Simplified (Direct Registration)
- **No generic wrappers** - Register tool functions directly with FastMCP instead of through protocol methods
- **FastMCP-aware registration** - Server adapter knows about specific tool types (HTTP, AI logging, etc.)
- **Pragmatic coupling** - Accept that changing MCP implementations means updating the adapter

#### Why This Works
- **FastMCP is lightweight** - Not a heavy framework requiring full abstraction
- **Registration is simple** - One line per tool, not worth complex generic wrappers
- **Business logic stays clean** - Tools don't know about FastMCP, only providers do
- **Architecture scales** - Easy to add new tool categories with direct registration

**Key principle**: Use protocols for **organization and testing**, direct registration for **simplicity and compatibility**.

### MCP Tool Parameter Pattern
When creating MCP tools, follow the parameter transformation pattern (ADR-014):
- Accept JSON strings for complex types (dicts, lists) in tool signatures
- Use Pydantic models internally for validation and transformation
- Include clear JSON examples in parameter descriptions
- See `HttpRequestTool` and AI logging tools for reference implementations

### Cookie Session Management
The HTTP tools support cookie profiles for maintaining authenticated sessions:
- **Cookie profiles**: Pre-configured authentication sessions stored in JSON files
- **XDG compliant**: Cookie files stored in `~/.local/share/hiro/cookies/`
- **Security enforced**: Files must have 0600 or 0400 permissions
- **Dynamic loading**: Cookies are re-read based on cache TTL
- **Profile merging**: Manual cookies override profile cookies when both provided
- **Usage**: Pass `cookie_profile="session_name"` to `http_request` tool

Configuration file: `~/.config/hiro/cookie_sessions.yaml`
```yaml
sessions:
  admin_session:
    description: "Admin user session"
    cookie_file: "admin_cookies.json"  # Relative to XDG data dir
    cache_ttl: 3600  # Seconds
```

### Prompt Resource System
Provides structured guidance to LLM agents via MCP resources:
- **Built-in guides**: Tool usage, quickstart, and context documentation patterns
- **User customization**: Add custom prompts to `~/.config/hiro/prompts/`
- **Multiple formats**: Available as JSON, YAML, or Markdown
- **Resource URIs**: Access via `prompt://guide_name`
- **Environment override**: Set `HIRO_PROMPTS_DIR` for custom location

The guides emphasize that user instructions always take precedence and provide context on how tools work together rather than prescriptive methodologies.

## Notes for AI Assistants
- Always use the `src/` layout when adding new modules
- Create corresponding test files in the mirrored test structure
- Use type hints for all function signatures
- Follow existing code style and patterns
- Run `make format` and `make lint` before committing
- Update this file when making significant architectural changes
- Claude Code users: Check `.claude/agents/` for specialized agent instructions
- Both `.ai/` and `.claude/` directories contain important context
