# ADR-003: Use uv for Dependency Management

**Status**: Accepted  
**Date**: 2025-09-08  

## Context
Need a fast, reliable Python package manager that supports modern workflows.

## Decision
Use uv instead of pip/poetry/pipenv for all dependency management.

## Consequences
- ✅ Extremely fast dependency resolution
- ✅ Built-in virtual environment management  
- ✅ Compatible with pip requirements
- ⚠️ Newer tool with smaller ecosystem