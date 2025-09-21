"""Test data factories for database models."""

import random
from typing import Any
from uuid import uuid4

from hiro.db.models import (
    HttpRequest,
    Mission,
    MissionAction,
    RiskLevel,
    SessionStatus,
    Target,
    TargetStatus,
)
from hiro.db.schemas import (
    HttpRequestCreate,
    MissionCreate,
    TargetCreate,
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


class MissionFactory:
    """Factory for creating test missions."""

    @staticmethod
    def create_data(**kwargs) -> MissionCreate:
        """Create mission data for testing."""
        defaults = {
            "name": f"Test Mission {uuid4().hex[:8]}",
            "description": f"Test mission for {random.choice(['auth_bypass', 'prompt_injection', 'api_discovery'])}",
            "goal": "Test the target for vulnerabilities",
            "mission_type": random.choice(
                ["prompt_injection", "business_logic", "auth_bypass", "general"]
            ),
            "hypothesis": "The target may have security vulnerabilities",
            "status": random.choice(list(SessionStatus)),
            "extra_data": {
                "test": True,
                "created_by": "factory",
            },
        }
        defaults.update(kwargs)
        return MissionCreate(**defaults)

    @staticmethod
    def create_model(**kwargs) -> Mission:
        """Create a Mission model instance."""
        data = MissionFactory.create_data(**kwargs)
        return Mission(**data.model_dump())


class HttpRequestFactory:
    """Factory for creating test HTTP requests."""

    @staticmethod
    def create_data(
        mission_id: Any | None = None, target_id: Any | None = None, **kwargs
    ) -> HttpRequestCreate:
        """Create HTTP request data for testing."""
        host = f"api-{uuid4().hex[:8]}.example.com"
        path = f"/api/v1/{random.choice(['users', 'items', 'search'])}"

        defaults = {
            "mission_id": mission_id,
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
        mission_id: Any | None = None, target_id: Any | None = None, **kwargs
    ) -> HttpRequest:
        """Create an HttpRequest model instance."""
        data = HttpRequestFactory.create_data(mission_id, target_id, **kwargs)
        return HttpRequest(**data.model_dump())


class TestDataBuilder:
    """Builder for creating complex test scenarios."""

    @staticmethod
    async def create_target_with_actions(session, **target_kwargs):
        """Create a target with associated mission actions."""
        # Create target
        target_data = TargetFactory.create_data(**target_kwargs)
        target = Target(**target_data.model_dump())
        session.add(target)
        await session.flush()

        # Create mission for the target
        mission = Mission(
            id=uuid4(),
            name=f"Test Mission for {target.host}",
            status=SessionStatus.ACTIVE,
        )
        session.add(mission)

        # Add mission actions
        for i in range(random.randint(1, 3)):
            action = MissionAction(
                id=uuid4(),
                mission_id=mission.id,
                action_type="test",
                technique=f"test_technique_{i}",
                payload="test_payload",
                result="test_result",
                success=random.choice([True, False]),
            )
            session.add(action)

        await session.flush()
        return target

    @staticmethod
    async def create_mission_with_requests(session, num_requests: int = 5):
        """Create a mission with associated HTTP requests."""
        # Create mission
        mission_data = MissionFactory.create_data(status=SessionStatus.ACTIVE)
        mission = Mission(**mission_data.model_dump())
        session.add(mission)
        await session.flush()

        # Create requests
        requests = []
        for _i in range(num_requests):
            request_data = HttpRequestFactory.create_data(mission_id=mission.id)
            request = HttpRequest(**request_data.model_dump())
            session.add(request)
            requests.append(request)

        await session.flush()
        return mission, requests

    @staticmethod
    async def create_complete_test_scenario(session):
        """Create a complete test scenario with all relationships."""
        # Create mission
        mission_data = MissionFactory.create_data(status=SessionStatus.ACTIVE)
        mission = Mission(**mission_data.model_dump())
        session.add(mission)
        await session.flush()

        # Create targets
        targets = []
        for i in range(3):
            target = await TestDataBuilder.create_target_with_actions(
                session,
                title=f"Target {i + 1}",
                status=TargetStatus.ACTIVE,
            )
            targets.append(target)

        # Create HTTP requests linked to mission and targets
        for target in targets:
            for i in range(random.randint(2, 5)):
                request_data = HttpRequestFactory.create_data(
                    mission_id=mission.id,
                    host=target.host,
                    path=f"/test/{i}",
                )
                request = HttpRequest(**request_data.model_dump())
                session.add(request)

        # Create mission actions
        actions = []
        for i in range(5):
            action = MissionAction(
                id=uuid4(),
                mission_id=mission.id,
                action_type="exploit",
                technique=f"Test technique {i}",
                payload=f"Test payload {i}",
                result=f"Result {i}: {'Success' if i % 2 == 0 else 'Failed'}",
                success=i % 2 == 0,
                learning=f"Learned from action {i}",
            )
            session.add(action)
            actions.append(action)

        await session.commit()
        return {
            "mission": mission,
            "targets": targets,
            "actions": actions,
        }
