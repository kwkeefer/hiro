# ADR-002: Mirror Test Structure to Source

**Status**: Accepted
**Date**: 2025-09-08

## Context
Tests need to be organized in a way that makes it easy to find the tests for any given module.

## Decision
Mirror the source structure in tests/ directory rather than separating by test type (unit/integration).

## Consequences
- ✅ Easy to locate tests for any module
- ✅ Natural organization as project grows
- ✅ Can still use markers for test categorization
- ⚠️ Integration tests mixed with unit tests in same directories
