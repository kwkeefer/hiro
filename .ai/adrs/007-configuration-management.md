# ADR-007: Configuration Management

**Status**: Proposed  
**Date**: 2025-09-08  

## Context
Need a way to manage configuration across different environments.

## Decision
- Use environment variables for secrets
- Use `config/` directory for non-secret configuration
- Support `.env` files for local development

## Consequences
- ✅ Secrets never in version control
- ✅ Easy deployment configuration
- ✅ Local development convenience
- ⚠️ Need to document all environment variables