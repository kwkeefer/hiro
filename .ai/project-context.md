# Project Context for code-mcp

## Overview
Getting started with MCP stuff

## Project Type
- **Name**: code-mcp
- **Package**: code_mcp
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
code_mcp/
├── src/code_mcp/   # Main package source code
│   ├── core/                              # Core business logic
│   ├── api/                               # API interfaces
│   ├── db/                                # Database modules
│   └── utils/                             # Utility functions
├── tests/                                 # Test suite (mirrors src structure)
├── docs/                                  # Documentation
├── config/                                # Configuration files
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

## Notes for AI Assistants
- Always use the `src/` layout when adding new modules
- Create corresponding test files in the mirrored test structure
- Use type hints for all function signatures
- Follow existing code style and patterns
- Run `make format` and `make lint` before committing
- Update this file when making significant architectural changes
- Claude Code users: Check `.claude/agents/` for specialized agent instructions
- Both `.ai/` and `.claude/` directories contain important context