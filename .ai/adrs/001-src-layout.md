# ADR-001: Use src Layout for Python Package

**Status**: Accepted  
**Date**: 2025-09-08  

## Context
Need to organize Python package structure in a way that prevents accidental imports of development code and ensures proper testing isolation.

## Decision
Use `src/` layout where all package code lives under `src/code_mcp/`.

## Consequences
- ✅ Prevents importing from the development directory
- ✅ Clear separation between source and tests
- ✅ Better compatibility with modern Python tooling
- ⚠️ Requires explicit PYTHONPATH configuration in some IDEs