# Python Style Guide

## Project-Specific Conventions

### Type Hints
**Required** for all functions. Use `mypy --strict` to verify.

### Docstrings
Required for:
- Public API functions
- Complex business logic
- Any function >10 lines

Skip for:
- Simple getters/setters
- Obvious test functions
- Private helpers with clear names

### Project Patterns

**Module Boundaries**:
- `core/` → Never import from `api/` or `db/`
- `api/` → Can import from `core/` and `db/`
- `utils/` → No imports from other app modules

**Error Handling**:
```python
# Always use custom exceptions
from code_mcp.core.exceptions import ValidationError

# Never catch bare Exception
# Always log before re-raising
```

**Logging Pattern**:
```python
logger = logging.getLogger(__name__)  # At module level
logger.debug("Details: %s", data)      # Use %s formatting
```

## Enforced by Tools
- Line length: 88 (ruff)
- Import order: automatic (ruff)
- Formatting: automatic (ruff format)

Run `make format` before committing.