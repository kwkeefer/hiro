"""Validation utilities for MCP tool parameters.

Implements comprehensive error reporting per ADR-018 to improve LLM tool usage experience.
"""

from typing import Any

from pydantic import ValidationError


def format_validation_errors(
    error: ValidationError, context: str = "parameters"
) -> str:
    """Format all Pydantic validation errors into a clear message for LLMs.

    Per ADR-018, this provides comprehensive error reporting to avoid multiple
    round-trips when LLMs provide incorrect parameter types.

    Args:
        error: The Pydantic ValidationError containing all validation failures
        context: Description of what was being validated (e.g., "HTTP request")

    Returns:
        Formatted error message showing all validation errors at once

    Example:
        >>> try:
        >>>     params = HttpRequestParams(follow_redirects="true", port="80")
        >>> except ValidationError as e:
        >>>     msg = format_validation_errors(e, "HTTP request")
        >>>     # Returns: "Invalid HTTP request - 2 errors:\n  • follow_redirects: ..."
    """
    errors = error.errors()

    if len(errors) == 1:
        err = errors[0]
        field = ".".join(str(x) for x in err["loc"])
        input_val = err.get("input", "N/A")
        return (
            f"Invalid {context}: {field} - {err['msg']} (received: {repr(input_val)})"
        )

    msg_lines = [f"Invalid {context} - {len(errors)} errors:"]
    for err in errors:
        field = ".".join(str(x) for x in err["loc"])
        input_val = err.get("input", "N/A")
        input_type = type(input_val).__name__ if input_val != "N/A" else "unknown"

        # Format the error message with clear information
        msg_lines.append(
            f"  • {field}: {err['msg']} (received {input_type}: {repr(input_val)})"
        )

    msg_lines.append("\nPlease fix all errors and retry with correct types.")
    return "\n".join(msg_lines)


# Common type coercion validators for reuse across models
def coerce_bool(v: Any) -> bool | Any:
    """Coerce common string representations to boolean.

    Per ADR-018, this handles common LLM mistakes like passing "true" instead of true.

    Args:
        v: Value to coerce

    Returns:
        Boolean if coercible, original value otherwise
    """
    if isinstance(v, str):
        lower_v = v.lower()
        if lower_v in ("true", "1", "yes", "on"):
            return True
        elif lower_v in ("false", "0", "no", "off", ""):
            return False
    return v


def coerce_int(v: Any) -> int | Any:
    """Coerce string numbers to integers.

    Per ADR-018, this handles common LLM mistakes like passing "80" instead of 80.

    Args:
        v: Value to coerce

    Returns:
        Integer if coercible, original value otherwise
    """
    if isinstance(v, str):
        try:
            return int(v)
        except ValueError:
            pass  # Let Pydantic handle the error with proper context
    return v


def coerce_float(v: Any) -> float | Any:
    """Coerce string numbers to floats.

    Per ADR-018, this handles number strings that should be floats.

    Args:
        v: Value to coerce

    Returns:
        Float if coercible, original value otherwise
    """
    if isinstance(v, str):
        try:
            return float(v)
        except ValueError:
            pass  # Let Pydantic handle the error with proper context
    return v
