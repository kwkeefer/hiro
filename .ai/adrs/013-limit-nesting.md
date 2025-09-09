# ADR-013: Limit Nested Control Flow

**Status**: Accepted  
**Date**: 2025-09-08  
**Reference**: https://github.com/zakirullin/cognitive-load

## Context
Deeply nested code is hard to follow, test, and maintain. Each level of nesting increases cognitive load exponentially.

## Decision
Limit nesting to maximum 2 levels. Use early returns, guard clauses, and extracted functions to flatten control flow.

## Implementation Rules
```python
# ❌ Avoid: Deep nesting
def process_order(order, user, payment):
    if order:
        if order.items:
            if user.is_verified:
                if payment.is_valid:
                    # actual logic here
                    return process()

# ✅ Prefer: Early returns (guard clauses)
def process_order(order, user, payment):
    if not order:
        return None
    if not order.items:
        raise ValueError("Order has no items")
    if not user.is_verified:
        raise PermissionError("User not verified")
    if not payment.is_valid:
        raise PaymentError("Invalid payment")
    
    return process()

# ✅ Also good: Extract complex conditions
def process_order(order, user, payment):
    validate_order(order)
    validate_user(user)
    validate_payment(payment)
    return process()
```

## Guidelines
- Use guard clauses at function start
- Extract nested loops into separate functions
- Replace nested ifs with early returns
- Consider extracting complex conditions into well-named functions
- For unavoidable nesting, add blank lines between levels

## Consequences
- ✅ Linear, easy-to-follow code
- ✅ Clearer happy path
- ✅ Easier to test edge cases
- ✅ Reduced cognitive load
- ⚠️ More functions (but simpler ones)
- ⚠️ Multiple return points (acceptable trade-off)