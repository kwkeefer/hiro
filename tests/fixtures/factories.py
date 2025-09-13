"""Test data factories for database models."""

import random
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from hiro.db.models import (
    AiSession,
    AttemptType,
    ConfidenceLevel,
    HttpRequest,
    NoteType,
    RiskLevel,
    SessionStatus,
    Target,
    TargetAttempt,
    TargetNote,
    TargetStatus,
)
from hiro.db.schemas import (
    AiSessionCreate,
    HttpRequestCreate,
    TargetAttemptCreate,
    TargetCreate,
    TargetNoteCreate,
)


class TargetFactory:
    """Factory for creating test targets."""

    @staticmethod
    def create_data(**kwargs) -> TargetCreate:
        """Create target data for testing."""
        defaults = {
            "host": f"test-{uuid4().hex[:8]}.example.com",
            "port": random.choice([80, 443, 8080, 8443, None]),
            "protocol": random.choice(["http", "https", "tcp", "udp"]),
            "title": f"Test Target {random.randint(1, 1000)}",
            "status": random.choice(list(TargetStatus)),
            "risk_level": random.choice(list(RiskLevel)),
            "notes": "Test target created by factory",
        }
        defaults.update(kwargs)
        return TargetCreate(**defaults)

    @staticmethod
    def create_model(**kwargs) -> Target:
        """Create a Target model instance."""
        data = TargetFactory.create_data(**kwargs)
        return Target(**data.model_dump())


class TargetNoteFactory:
    """Factory for creating test target notes."""

    @staticmethod
    def create_data(target_id: Any | None = None, **kwargs) -> TargetNoteCreate:
        """Create target note data for testing."""
        defaults = {
            "target_id": target_id or uuid4(),
            "note_type": random.choice(list(NoteType)),
            "title": f"Test Note {uuid4().hex[:8]}",
            "content": f"Test note content: {uuid4().hex[:16]}",
            "confidence": random.choice(list(ConfidenceLevel)),
            "tags": ["test", "factory"],
        }
        defaults.update(kwargs)
        return TargetNoteCreate(**defaults)

    @staticmethod
    def create_model(target_id: Any | None = None, **kwargs) -> TargetNote:
        """Create a TargetNote model instance."""
        data = TargetNoteFactory.create_data(target_id, **kwargs)
        return TargetNote(**data.model_dump())


class TargetAttemptFactory:
    """Factory for creating test target attempts."""

    @staticmethod
    def create_data(target_id: Any | None = None, **kwargs) -> TargetAttemptCreate:
        """Create target attempt data for testing."""
        defaults = {
            "target_id": target_id or uuid4(),
            "attempt_type": random.choice(list(AttemptType)),
            "technique": f"test_technique_{uuid4().hex[:8]}",
            "payload": "test_payload",  # Should be string, not dict
            "expected_outcome": "Expected test outcome",
            "notes": "Test attempt notes",
        }
        defaults.update(kwargs)
        return TargetAttemptCreate(**defaults)

    @staticmethod
    def create_model(target_id: Any | None = None, **kwargs) -> TargetAttempt:
        """Create a TargetAttempt model instance."""
        data = TargetAttemptFactory.create_data(target_id, **kwargs)
        return TargetAttempt(**data.model_dump())


class AiSessionFactory:
    """Factory for creating test AI sessions."""

    @staticmethod
    def create_data(**kwargs) -> AiSessionCreate:
        """Create AI session data for testing."""
        started_at = datetime.utcnow() - timedelta(hours=random.randint(1, 24))
        defaults = {
            "name": f"Test Session {uuid4().hex[:8]}",
            "status": random.choice(list(SessionStatus)),
            "metadata": {
                "test": True,
                "created_by": "factory",
            },
            "started_at": started_at,
            "ended_at": started_at + timedelta(hours=random.randint(1, 8))
            if random.choice([True, False])
            else None,
        }
        defaults.update(kwargs)
        return AiSessionCreate(**defaults)

    @staticmethod
    def create_model(**kwargs) -> AiSession:
        """Create an AiSession model instance."""
        data = AiSessionFactory.create_data(**kwargs)
        return AiSession(**data.model_dump())


class HttpRequestFactory:
    """Factory for creating test HTTP requests."""

    @staticmethod
    def create_data(
        session_id: Any | None = None, target_id: Any | None = None, **kwargs
    ) -> HttpRequestCreate:
        """Create HTTP request data for testing."""
        host = f"api-{uuid4().hex[:8]}.example.com"
        path = f"/api/v1/{random.choice(['users', 'items', 'search'])}"

        defaults = {
            "session_id": session_id,
            "method": random.choice(["GET", "POST", "PUT", "DELETE", "PATCH"]),
            "url": f"https://{host}{path}",
            "host": host,
            "path": path,
            "query_params": {"page": "1", "limit": "10"}
            if random.choice([True, False])
            else None,
            "headers": {
                "User-Agent": "TestBot/1.0",
                "Accept": "application/json",
            },
            "cookies": {"session": uuid4().hex}
            if random.choice([True, False])
            else None,
            "request_body": '{"test": "data"}'
            if kwargs.get("method") in ["POST", "PUT", "PATCH"]
            else None,
        }
        defaults.update(kwargs)
        return HttpRequestCreate(**defaults)

    @staticmethod
    def create_model(
        session_id: Any | None = None, target_id: Any | None = None, **kwargs
    ) -> HttpRequest:
        """Create an HttpRequest model instance."""
        data = HttpRequestFactory.create_data(session_id, target_id, **kwargs)
        return HttpRequest(**data.model_dump())


class TestDataBuilder:
    """Builder for creating complex test scenarios."""

    @staticmethod
    async def create_target_with_notes_and_attempts(session, **target_kwargs):
        """Create a target with associated notes and attempts."""
        # Create target
        target_data = TargetFactory.create_data(**target_kwargs)
        target = Target(**target_data.model_dump())
        session.add(target)
        await session.flush()

        # Add notes
        for _i in range(random.randint(1, 5)):
            note_data = TargetNoteFactory.create_data(target_id=target.id)
            note = TargetNote(**note_data.model_dump())
            session.add(note)

        # Add attempts
        for _i in range(random.randint(1, 3)):
            attempt_data = TargetAttemptFactory.create_data(target_id=target.id)
            attempt = TargetAttempt(**attempt_data.model_dump())
            session.add(attempt)

        await session.flush()
        return target

    @staticmethod
    async def create_session_with_requests(session, num_requests: int = 5):
        """Create an AI session with associated HTTP requests."""
        # Create AI session
        ai_session_data = AiSessionFactory.create_data(status=SessionStatus.ACTIVE)
        ai_session = AiSession(**ai_session_data.model_dump())
        session.add(ai_session)
        await session.flush()

        # Create requests
        requests = []
        for _i in range(num_requests):
            request_data = HttpRequestFactory.create_data(session_id=ai_session.id)
            request = HttpRequest(**request_data.model_dump())
            session.add(request)
            requests.append(request)

        await session.flush()
        return ai_session, requests

    @staticmethod
    async def create_complete_test_scenario(session):
        """Create a complete test scenario with all relationships."""
        # Create AI session
        ai_session_data = AiSessionFactory.create_data(status=SessionStatus.ACTIVE)
        ai_session = AiSession(**ai_session_data.model_dump())
        session.add(ai_session)
        await session.flush()

        # Create targets
        targets = []
        for i in range(3):
            target = await TestDataBuilder.create_target_with_notes_and_attempts(
                session,
                title=f"Target {i+1}",
                status=TargetStatus.ACTIVE,
            )
            targets.append(target)

        # Create HTTP requests linked to targets
        for target in targets:
            for i in range(random.randint(2, 5)):
                request_data = HttpRequestFactory.create_data(
                    session_id=ai_session.id,
                    host=target.host,
                    path=f"/test/{i}",
                )
                request = HttpRequest(**request_data.model_dump())
                session.add(request)

        await session.commit()
        return {
            "session": ai_session,
            "targets": targets,
        }
