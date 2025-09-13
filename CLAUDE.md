# Claude Code Instructions

This project uses centralized AI assistant context and instructions.

## Primary Context Location

**All project context, architecture decisions, and AI assistant instructions are maintained in:**

- **`.ai/project-context.md`** - Main project overview, architecture, and development guidelines
- **`.ai/adrs/`** - Architecture Decision Records with detailed rationale
- **`.ai/claude-code-instructions.md`** - Claude Code specific instructions and patterns

## Quick Reference

### For Claude Code Users
1. **Always read** `.ai/project-context.md` first for current project state
2. **Check** `.ai/adrs/` for architectural decisions and patterns
3. **Follow** the hybrid FastMCP integration approach documented in project context
4. **Use** the development commands listed in project context (`make lint`, `make test`, etc.)

### Key Architectural Principles
- **Hybrid Approach**: Use protocols for organization, direct registration for FastMCP compatibility
- **Module Structure**: Follow `src/` layout with `core/`, `api/`, `db/`, `utils/` organization
- **Configuration**: Located in `src/hiro/core/config/` per ADR-006
- **Testing**: Integration tests verify the hybrid architecture works correctly

### Development Workflow
```bash
make dev        # Setup development environment
make test       # Run all tests
make lint       # Check code quality
make typecheck  # Verify type annotations
```

## Why This Structure?

This approach:
- **Centralizes context** in `.ai/` directory
- **Avoids duplication** between CLAUDE.md and project context
- **Maintains single source of truth** for project architecture
- **Allows detailed ADRs** while keeping this file concise

---

**🔗 Start here:** [`.ai/project-context.md`](.ai/project-context.md)
