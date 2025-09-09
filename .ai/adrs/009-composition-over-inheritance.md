# ADR-009: Prefer Composition Over Inheritance

**Status**: Accepted  
**Date**: 2025-09-08  

## Context
Need to design flexible, maintainable code that avoids the pitfalls of deep inheritance hierarchies and promotes loose coupling between components.

## Decision
Prefer composition over inheritance for code reuse and flexibility. When polymorphism is needed, use `typing.Protocol` for structural subtyping (duck typing with type safety). Add `@runtime_checkable` decorator when runtime validation is needed (e.g., plugin systems, dynamic dispatch). Reserve ABCs for cases requiring method implementation enforcement at instantiation.

## Consequences
- ✅ More flexible and maintainable code structure
- ✅ Easier to test components in isolation
- ✅ Avoids fragile base class problem
- ✅ No inheritance required - works with any class that matches the protocol
- ✅ Better static type checking with mypy/pyright
- ✅ Better adherence to SOLID principles
- ⚠️ May require more initial setup for simple cases
- ⚠️ Developers need to understand composition patterns
- ⚠️ Protocols are only checked statically (no runtime validation unless using runtime_checkable)

## Example
```python
from typing import Protocol, runtime_checkable

# Standard Protocol - static checking only
class MessageSender(Protocol):
    def send(self, message: str) -> None: ...

# Runtime checkable Protocol - when you need isinstance()
@runtime_checkable
class Validator(Protocol):
    def validate(self, data: dict) -> bool: ...

# No inheritance needed - just match the protocol
class EmailService:
    def send(self, message: str) -> None:
        # Implementation
        pass

class JSONValidator:
    def validate(self, data: dict) -> bool:
        # Implementation
        return True

# Static type checking
def notify(sender: MessageSender, msg: str) -> None:
    sender.send(msg)

# Runtime checking (e.g., plugin system)
def process_with_validator(obj: object, data: dict) -> bool:
    if isinstance(obj, Validator):  # Only works with @runtime_checkable
        return obj.validate(data)
    raise TypeError(f"{obj} is not a Validator")

# Composition example
class NotificationService:
    def __init__(self, primary: MessageSender, backup: MessageSender):
        self._primary = primary
        self._backup = backup
```

## Guidelines
- **Default**: Use plain `Protocol` for static type checking
- **Add `@runtime_checkable`**: When you need `isinstance()` checks (plugin systems, dynamic dispatch)
- **Use ABCs**: Only when you must enforce implementation at instantiation time
- **Prefer composition**: Inject dependencies rather than inheriting behavior

## Alternatives Considered
- Abstract Base Classes (ABCs): Reserved for rare cases needing instantiation-time enforcement
- Deep inheritance hierarchies: Rejected due to tight coupling and brittleness
- No abstractions: Rejected as it reduces code reuse and type safety