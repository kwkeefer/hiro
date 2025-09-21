# ADR-018: Comprehensive Validation Error Handling for LLM Tools

## Status
Accepted

## Context
When LLMs (like Claude) call MCP tools with incorrect parameter types, Pydantic validation fails fast on the first error. This creates a frustrating cycle:

1. LLM sends `follow_redirects: "true"` (string instead of boolean)
2. Tool returns error: "Invalid type for follow_redirects"
3. LLM fixes that error, resubmits
4. Tool returns error: "Invalid type for port" (was `"80"` instead of `80`)
5. Multiple round-trips needed to fix all errors

This pattern wastes tokens, increases latency, and degrades user experience.

## Decision
We will implement comprehensive validation error handling that:

1. **Reports ALL validation errors at once** using Pydantic's `ValidationError.errors()`
2. **Provides clear, actionable error messages** showing field names, expected types, and received values
3. **Implements smart type coercion** for common LLM mistakes (string booleans, string numbers)
4. **Standardizes error formatting** across all tools via a utility function

## Implementation

### 1. Validation Utility Function
Create a centralized utility for formatting validation errors:

```python
# src/hiro/core/mcp/validation.py
from pydantic import ValidationError
from typing import Any

def format_validation_errors(error: ValidationError, context: str = "parameters") -> str:
    """Format all Pydantic validation errors into a clear message for LLMs.

    Args:
        error: The Pydantic ValidationError containing all validation failures
        context: Description of what was being validated (e.g., "HTTP request")

    Returns:
        Formatted error message showing all validation errors at once
    """
    errors = error.errors()

    if len(errors) == 1:
        err = errors[0]
        field = ".".join(str(x) for x in err['loc'])
        return f"Invalid {context}: {field} - {err['msg']} (received: {repr(err['input'])})"

    msg_lines = [f"Invalid {context} - {len(errors)} errors:"]
    for err in errors:
        field = ".".join(str(x) for x in err['loc'])
        input_type = type(err['input']).__name__ if 'input' in err else 'unknown'
        msg_lines.append(f"  • {field}: {err['msg']} (received {input_type}: {repr(err.get('input', 'N/A'))})")

    msg_lines.append("\nPlease fix all errors and retry with correct types.")
    return "\n".join(msg_lines)
```

### 2. Common Type Coercers
Add validators to handle common LLM type confusion:

```python
@field_validator("follow_redirects", "success", "is_active", mode="before")
@classmethod
def coerce_bool(cls, v: Any) -> bool | Any:
    """Coerce common string representations to boolean."""
    if isinstance(v, str):
        lower_v = v.lower()
        if lower_v in ("true", "1", "yes", "on"):
            return True
        elif lower_v in ("false", "0", "no", "off"):
            return False
    return v

@field_validator("port", "limit", "offset", mode="before")
@classmethod
def coerce_int(cls, v: Any) -> int | Any:
    """Coerce string numbers to integers."""
    if isinstance(v, str):
        try:
            return int(v)
        except ValueError:
            pass  # Let Pydantic handle the error
    return v
```

### 3. Standardized Tool Pattern
Update all tools to use comprehensive validation:

```python
from pydantic import ValidationError
from hiro.core.mcp.validation import format_validation_errors

async def execute(self, **kwargs) -> dict[str, Any]:
    """Execute the tool with comprehensive error handling."""
    try:
        # This will validate ALL fields and collect ALL errors
        params = HttpRequestParams(**kwargs)
    except ValidationError as e:
        # This will report ALL errors at once
        raise ToolError("http_request", format_validation_errors(e, "HTTP request"))

    # Continue with validated params...
```

## Benefits

1. **Reduced Round-Trips**: LLMs see all errors at once and can fix them in a single retry
2. **Better UX**: Clear, comprehensive error messages reduce frustration
3. **Token Efficiency**: Fewer retries mean fewer tokens consumed
4. **Common Mistakes Handled**: Type coercion prevents errors for typical LLM confusions
5. **Consistency**: Standardized error format across all tools

## Example Error Messages

### Before (Single Error)
```
Invalid parameters: Input should be a valid boolean
```

### After (Comprehensive)
```
Invalid HTTP request - 3 errors:
  • follow_redirects: Input should be a valid boolean (received str: 'true')
  • port: Input should be a valid integer (received str: '80')
  • headers: Invalid JSON: Expecting property name enclosed in double quotes (received str: '{invalid}')

Please fix all errors and retry with correct types.
```

## Trade-offs

1. **Slightly Longer Error Messages**: More comprehensive errors mean longer messages, but this is offset by fewer retries
2. **Coercion Hides Type Issues**: Accepting "true" as boolean might mask systematic issues, but pragmatism wins here
3. **Validation Overhead**: Pydantic already collects all errors internally; we're just exposing them better

## Implementation Order

1. Create validation utility function
2. Add type coercers to HttpRequestParams (most frequently used)
3. Update HTTP tool execute method
4. Gradually roll out to Mission and AI Logging tools
5. Monitor LLM retry rates to measure improvement

## Related ADRs
- ADR-014: MCP Tool Parameter Transformation Pattern (parameter validation strategy)
- ADR-008: Error Handling Strategy (ToolError usage)
- ADR-010: Deep Module Implementation Principle (hiding complexity)

## References
- Pydantic Validation Errors: https://docs.pydantic.dev/latest/errors/validation_errors/
- Common LLM type confusion patterns from production usage
