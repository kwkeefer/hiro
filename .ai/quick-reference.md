# Quick Reference - code-mcp

## Essential Rules (Read This First!)

### Code Style
- **FOLLOW PEP 8** - All imports at top of file, proper spacing, etc.
- **Line length**: 88 chars max
- **Imports**: stdlib → third-party → local (alphabetical), ALL AT TOP
- **Naming**: `ClassName`, `function_name`, `CONSTANT_NAME`
- **Always**: Complete type hints (no `Any` shortcuts), write docstrings for public functions

### Project Structure
```
src/code_mcp/
  core/   → Business logic
  api/    → External interfaces
  db/     → Database code
  utils/  → Helpers
tests/    → Mirror src/ structure
```

### Before Committing
```bash
make format    # Auto-format
make lint      # Check style
make typecheck # Verify types
make test      # Run tests
```

### Test Markers
- `@pytest.mark.unit` - Fast, isolated
- `@pytest.mark.integration` - External deps
- `@pytest.mark.slow` - >1 second

### Common Patterns

**Composition Over Inheritance** (See ADR-009):
```python
from typing import Protocol

# Define interface with Protocol
class Repository(Protocol):
    def get(self, id: str) -> Model: ...

# Use composition
class Service:
    def __init__(self, repo: Repository):
        self._repo = repo
```

**Error Handling**:
```python
# Custom exceptions for domain errors
class ValidationError(Exception): pass

# Be specific
except SpecificError as e:
    logger.error(f"Failed: {e}")
    raise
```

**Type Hints** (NO shortcuts - proper types from start):
```python
from typing import Optional
from collections.abc import Sequence

def process(data: dict[str, Any]) -> Optional[Result]:
    ...

# Use specific types, not Any when possible
def handle_items(items: Sequence[Item]) -> list[ProcessedItem]:
    ...
```

## Task-Specific Guides

- **Writing tests?** → See `.ai/standards/testing.md`
- **Adding feature?** → Check `.ai/architecture-decisions.md` index for relevant ADRs
- **Refactoring?** → Follow patterns in `.ai/standards/python-style.md`
- **Git commits?** → Format in `.ai/standards/git-commits.md`

## Commands Cheat Sheet

| Task | Command |
|------|---------|
| Install deps | `make dev` |
| Run tests | `make test` |
| Test coverage | `make test-cov` |
| Format code | `make format` |
| Add dependency | `uv add package` |
| Run Python | `uv run python` or `uv run python script.py` |
| Run CLI | `make run` |

## Don'ts
- ❌ Hardcode secrets
- ❌ Use `Any` type (be specific)
- ❌ Skip tests
- ❌ Files >500 lines
- ❌ Commit without formatting

## Full Details
Only read if needed for complex tasks:
- `.ai/coding-standards.md` - Comprehensive guide
- `.ai/standards/` - Detailed topic guides
