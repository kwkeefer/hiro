# Claude Code Instructions for hiro

## Context-Aware File Usage

### Start Here
**ALWAYS read first**: `.ai/quick-reference.md` (1 page summary)

### Read Based on Task
| Task Type | Read These Files |
|-----------|-----------------|
| Simple bug fix | `quick-reference.md` only |
| Writing tests | `quick-reference.md` + `standards/testing.md` |
| New feature | `quick-reference.md` + `architecture-decisions.md` index + relevant ADRs |
| Refactoring | `quick-reference.md` + `standards/python-style.md` |
| Major changes | All relevant `.ai/` files |

### Only When Needed
- `.ai/coding-standards.md` - Full comprehensive guide (rarely needed)
- `.ai/project-context.md` - When unclear about project structure
- `.ai/standards/git-commits.md` - When making commits

## Working with This Project

### Before Making Changes
1. Review the project structure in `project-context.md`
2. Check `architecture-decisions.md` index, then read relevant ADRs in `adrs/`
3. Follow the standards in `coding-standards.md`

### Common Tasks

#### Adding a New Feature
1. Create module in appropriate directory under `src/hiro/`
2. Add corresponding tests in `tests/` (mirror the source structure)
3. Update type hints and add docstrings
4. Run `make format lint typecheck test`
5. Update relevant documentation

#### Fixing a Bug
1. Write a failing test that reproduces the bug
2. Fix the bug in the source code
3. Ensure the test passes
4. Run `make test` to verify no regressions
5. Update changelog if applicable

#### Refactoring Code
1. Ensure comprehensive test coverage exists
2. Make incremental changes
3. Run tests after each change
4. Use `make format` to maintain consistency
5. Update documentation if interfaces change

### Development Workflow

```bash
# Set up environment (first time)
make dev

# Before starting work
git pull
make test  # Ensure clean slate

# During development
make format  # Format code
make lint    # Check for issues
make typecheck  # Verify types
make test-unit  # Run fast tests frequently

# Before committing
make test  # Run all tests
make test-cov  # Check coverage

# Build and distribute
make build
```

### File Navigation Patterns

When looking for code:
- Business logic → `src/hiro/core/`
- API endpoints → `src/hiro/api/`
- Database models → `src/hiro/db/`
- Helper functions → `src/hiro/utils/`
- Tests → `tests/` (mirrors source structure)
- Configuration → `config/`
- Scripts → `scripts/`

### Testing Guidelines

#### Test Organization
- Unit tests: Test single functions/methods in isolation
- Integration tests: Test interaction between components
- Use appropriate markers: `@pytest.mark.unit`, `@pytest.mark.integration`

#### Test Commands
```bash
make test           # Run all tests
make test-unit      # Run only unit tests
make test-integration  # Run only integration tests
make test-cov       # Generate coverage report
```

### Code Quality Checks

Always run before committing:
```bash
make format    # Auto-format code
make lint      # Check code style
make typecheck # Verify type annotations
```

### Working with Dependencies

```bash
# Add a production dependency
uv add package-name

# Add a development dependency
uv add --dev package-name

# Update dependencies
uv sync

# Remove a dependency
uv remove package-name
```

### Common Patterns in This Codebase

#### Error Handling
```python
from hiro.core.exceptions import ValidationError

def process_data(data: dict) -> Result:
    if not validate_data(data):
        raise ValidationError("Invalid data format")
    # Process...
```

#### Logging
```python
import logging

logger = logging.getLogger(__name__)

def some_function():
    logger.info("Starting process")
    try:
        # Do work
        logger.debug("Process details: %s", details)
    except Exception as e:
        logger.error("Process failed: %s", e)
        raise
```

#### Type Hints
```python
from typing import Optional, Union
from hiro.core.models import User

def get_user(user_id: int) -> Optional[User]:
    """Get user by ID, returns None if not found."""
    ...
```

### CLI Development

The CLI is built with click. Main entry point is `src/hiro/cli.py`.

```bash
# Test CLI during development
make run

# Or directly
hiro --help
```

### Important Reminders

1. **Never commit secrets** - Use environment variables
2. **Write tests first** - TDD when possible
3. **Update documentation** - Keep docs in sync with code
4. **Use type hints** - For all function signatures
5. **Handle errors gracefully** - User-friendly messages
6. **Keep commits atomic** - One change per commit
7. **Follow conventions** - Consistency is key

### Getting Help

If you need to:
- Understand a design decision → Check `.ai/architecture-decisions.md` index and relevant ADRs
- Know the code style → Check `.ai/coding-standards.md`
- Find project info → Check `.ai/project-context.md`
- Run a command → Try `make help`

### Specific Instructions for Claude Code

When asked to:

1. **"Implement feature X"**
   - First check if similar features exist
   - Follow established patterns
   - Add comprehensive tests
   - Update documentation

2. **"Fix bug Y"**
   - Reproduce with a test first
   - Fix minimally
   - Verify no regressions

3. **"Refactor Z"**
   - Ensure test coverage
   - Make incremental changes
   - Maintain backwards compatibility if public API

4. **"Add tests"**
   - Mirror source structure
   - Use appropriate markers
   - Test edge cases
   - Aim for >80% coverage

5. **"Update documentation"**
   - Keep it concise
   - Include code examples
   - Update this .ai folder if architectural changes

### Project-Specific Notes

[Add any project-specific instructions here as the project evolves]

---

*Remember: When in doubt, check the existing code for patterns and conventions. Consistency with the existing codebase is more important than following general best practices.*
