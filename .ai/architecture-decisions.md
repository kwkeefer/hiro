# Architecture Decisions for code-mcp

This document provides a quick reference to all architectural decisions. For detailed information, see the individual ADR files in `.ai/adrs/`.

## Quick Reference

| ADR | Title | Status | One-line Summary |
|-----|-------|--------|-----------------|
| [001](adrs/001-src-layout.md) | Use src Layout | Accepted | Organize code under `src/` for proper isolation |
| [002](adrs/002-mirror-test-structure.md) | Mirror Test Structure | Accepted | Tests mirror source structure for easy discovery |
| [003](adrs/003-uv-dependency-management.md) | Use uv for Dependencies | Accepted | Fast, modern Python package management with uv |
| [004](adrs/004-makefile-interface.md) | Makefile Interface | Accepted | Consistent developer interface via Make commands |
| [005](adrs/005-cli-framework.md) | CLI Framework Choice | Accepted | CLI implementation approach for the project |
| [006](adrs/006-module-organization.md) | Module Organization | Proposed | Separate core, api, db, and utils modules |
| [007](adrs/007-configuration-management.md) | Configuration Management | Proposed | Environment variables for secrets, config files for settings |
| [008](adrs/008-error-handling.md) | Error Handling Strategy | Proposed | Custom exceptions with meaningful messages |
| [009](adrs/009-composition-over-inheritance.md) | Composition Over Inheritance | Accepted | Use composition and Protocol for flexibility |
| [010](adrs/010-deep-modules.md) | Prefer Deep Modules | Accepted | Fewer files with rich functionality over many shallow files |
| [011](adrs/011-isolate-frameworks.md) | Isolate Framework Dependencies | Accepted | Keep business logic framework-agnostic |
| [012](adrs/012-self-descriptive-codes.md) | Self-Descriptive Status Codes | Accepted | Human-readable strings over numeric codes |
| [013](adrs/013-limit-nesting.md) | Limit Nested Control Flow | Accepted | Max 2 levels of nesting for readability |

## Cognitive Load Principles

ADRs 010-013 are based on reducing cognitive load from [zakirullin/cognitive-load](https://github.com/zakirullin/cognitive-load).

## How to Use This Document

1. **For LLMs/AI Assistants**: Start with this index, then read specific ADR files as needed
2. **For Developers**: Review relevant ADRs before making architectural changes
3. **For New Team Members**: Read ADRs 001-004 first for project setup

## Adding New ADRs

1. Copy `adrs/template.md` to `adrs/XXX-brief-name.md`
2. Fill in the template
3. Update this index table
4. Set status to "Proposed" until team review

## Status Definitions

- **Proposed**: Under consideration
- **Accepted**: Approved and in effect
- **Deprecated**: No longer recommended
- **Superseded**: Replaced by another ADR
