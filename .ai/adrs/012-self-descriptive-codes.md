# ADR-012: Use Self-Descriptive Status Codes

**Status**: Accepted
**Date**: 2025-09-08
**Reference**: https://github.com/zakirullin/cognitive-load

## Context
Numeric codes and cryptic abbreviations require mental translation, increasing cognitive load when debugging or reading logs.

## Decision
Use human-readable, self-descriptive strings for all status codes, error types, and state representations. Combine with descriptive error messages when appropriate.

## Implementation Rules
```python
# ❌ Avoid: Numeric or cryptic codes
if order.status == 3:
    return {"error": 1001}

# ✅ Prefer: Self-descriptive strings
if order.status == "awaiting_payment":
    return {
        "error": "payment_failed",
        "message": "Insufficient funds in account"
    }
```

## Examples
```python
# Status strings
order.status = "payment_pending"
user.state = "email_verification_required"
task.result = "completed_with_warnings"

# Error codes with messages
raise ValidationError(
    code="invalid_email_format",
    message="Email must contain @ symbol"
)
```

## Guidelines
- Use snake_case for consistency
- Include context (e.g., "payment_failed" not just "failed")
- Combine codes with human-readable messages for APIs
- Keep under 40 characters

## Consequences
- ✅ Self-documenting code and logs
- ✅ Easier debugging
- ✅ No mental translation needed
- ⚠️ Slightly more verbose
- ⚠️ May need migration from existing numeric codes
