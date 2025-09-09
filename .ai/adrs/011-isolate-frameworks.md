# ADR-011: Isolate Framework Dependencies

**Status**: Accepted
**Date**: 2025-09-08
**Reference**: https://github.com/zakirullin/cognitive-load

## Context
Framework-specific code mixed with business logic creates tight coupling, makes testing difficult, and prevents framework migration.

## Decision
Separate business logic from framework code using ports and adapters pattern. Business logic should be pure Python that knows nothing about the framework.

## Implementation Rules
```python
# ❌ Avoid: Business logic tied to framework
from fastapi import Depends, HTTPException

class UserService:
    def create_user(self, data: dict, db: Session = Depends(get_db)):
        if not data.get("email"):
            raise HTTPException(status_code=400, detail="Email required")
        # Business logic mixed with FastAPI

# ✅ Prefer: Framework-agnostic business logic
# core/user.py - Pure business logic
class UserService:
    def create_user(self, data: UserData, repository: UserRepository) -> User:
        if not data.email:
            raise ValidationError("Email required")
        return repository.save(user)

# api/fastapi_adapter.py - Framework adapter
@router.post("/users")
def create_user_endpoint(data: dict, db: Session = Depends(get_db)):
    try:
        service = UserService()
        user = service.create_user(UserData(**data), SQLUserRepository(db))
        return user
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

## Guidelines
- Core business logic has zero framework imports
- Adapters translate between framework and domain
- Dependency injection at adapter boundary
- Test business logic without framework

## Consequences
- ✅ Framework-independent business logic
- ✅ Easier unit testing
- ✅ Possible framework migration
- ✅ Clear architectural boundaries
- ⚠️ Additional adapter layer
- ⚠️ Some boilerplate for translation
