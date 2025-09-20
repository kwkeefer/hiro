"""Integration tests for mission management tools following ADR-017."""

import json
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from hiro.core.vector import VectorSearch
from hiro.db.models import Mission, Target
from hiro.db.repositories import (
    HttpRequestRepository,
    MissionActionRepository,
    MissionRepository,
)
from hiro.servers.missions.core_tools import MissionCoreTool
from hiro.servers.missions.library_tools import KnowledgeLibraryTool
from hiro.servers.missions.search_tools import MissionSearchTool


@pytest.fixture
async def mission_tools(test_db: AsyncSession):
    """Create mission tool instances with database session."""
    mission_repo = MissionRepository(test_db)
    action_repo = MissionActionRepository(test_db)
    # request_repo unused but needed for creating mission tools structure
    request_repo = HttpRequestRepository(test_db)  # noqa: F841
    vector_search = VectorSearch()

    core_tool = MissionCoreTool(
        mission_repo=mission_repo,
        action_repo=action_repo,
        vector_search=vector_search,
    )

    # Create a wrapper action repo with session factory for search tool
    class ActionRepoWithFactory:
        def __init__(self, session):
            self.session = session
            self._session_factory = lambda: session
            self._delegate = action_repo

        def __getattr__(self, name):
            return getattr(self._delegate, name)

    action_repo_with_factory = ActionRepoWithFactory(test_db)

    search_tool = MissionSearchTool(
        action_repo=action_repo_with_factory, vector_search=vector_search
    )

    library_tool = KnowledgeLibraryTool(
        vector_search=vector_search, session_factory=lambda: test_db
    )

    return {
        "core": core_tool,
        "search": search_tool,
        "library": library_tool,
        "session": test_db,
    }


@pytest.mark.asyncio
async def test_mission_lifecycle(mission_tools):
    """Test complete mission lifecycle: create, set context, record action."""
    core_tool = mission_tools["core"]
    session = mission_tools["session"]

    # Create a target first
    target = Target(
        host="api.example.com", port=443, protocol="https", title="Test API"
    )
    session.add(target)
    await session.commit()

    # 1. Create mission
    mission_result = await core_tool.create_mission(
        target_id=str(target.id),
        mission_type="auth_bypass",
        name="Test auth bypass techniques",
        goal="Find ways to bypass authentication",
        hypothesis="JWT manipulation might work",
    )

    assert mission_result["status"] == "created"
    assert "mission_id" in mission_result
    mission_id = mission_result["mission_id"]

    # 2. Set mission context
    context_result = await core_tool.set_mission_context(mission_id=mission_id)
    assert context_result["status"] == "context_set"
    assert context_result["mission_id"] == mission_id

    # 3. Get mission context
    context = await core_tool.get_mission_context()
    assert context["mission"]["id"] == mission_id
    assert context["mission"]["name"] == "Test auth bypass techniques"
    assert context["stats"]["total_actions"] == 0

    # 4. Record an action
    action_result = await core_tool.record_action(
        mission_id=mission_id,
        action_type="payload_test",
        technique="JWT kid parameter injection",
        payload='{"kid": "../../../etc/passwd"}',
        result="Server error 500 - potential path traversal",
        success=True,
        learning="Kid parameter is vulnerable to path traversal",
    )

    assert "action_id" in action_result
    assert action_result["mission_id"] == mission_id
    assert action_result["success"] is True

    # Commit the action so it's visible in context stats
    await session.commit()

    # 5. Verify context updated
    updated_context = await core_tool.get_mission_context()
    assert updated_context["stats"]["total_actions"] == 1
    assert updated_context["stats"]["success_rate"] == 1.0
    assert (
        updated_context["stats"]["unique_techniques"] == 1
    )  # Count of unique techniques


@pytest.mark.asyncio
async def test_technique_search(mission_tools):
    """Test searching for similar techniques using vector similarity."""
    core_tool = mission_tools["core"]
    search_tool = mission_tools["search"]
    session = mission_tools["session"]

    # Create test data
    target = Target(
        host="api.example.com", port=443, protocol="https", title="Test API"
    )
    session.add(target)
    await session.commit()

    # Use the core tool to create mission properly
    mission_result = await core_tool.create_mission(
        target_id=str(target.id),
        mission_type="general",  # Use valid mission type
        name="SQL injection testing",
        goal="Find SQL injection vulnerabilities",
    )
    mission_id = mission_result["mission_id"]

    # Get the mission from DB
    mission = await session.get(Mission, UUID(mission_id))

    # Set context
    await core_tool.set_mission_context(mission_id=str(mission.id))

    # Record multiple actions with different techniques
    techniques = [
        ("SQL injection with UNION", "' UNION SELECT * FROM users--", True),
        ("SQL injection with error-based", "' AND 1=CONVERT(int, @@version)--", True),
        ("XSS attempt", "<script>alert(1)</script>", False),
        ("SQL injection with time-based", "' AND SLEEP(5)--", True),
    ]

    for technique, payload, success in techniques:
        await core_tool.record_action(
            mission_id=str(mission.id),
            action_type="payload_test",
            technique=technique,
            payload=payload,
            success=success,
        )

    # Commit the actions to the database
    await session.commit()

    # Search for similar SQL techniques
    similar = await search_tool.find_similar_techniques(
        technique="SQL injection with boolean-based", limit=5
    )

    assert "similar_techniques" in similar
    assert len(similar["similar_techniques"]) > 0
    # Should find at least one SQL injection technique
    sql_techniques = [
        t for t in similar["similar_techniques"] if "SQL" in t["technique"]
    ]
    assert len(sql_techniques) >= 1

    # Get stats for a specific technique
    stats = await search_tool.get_technique_stats(technique="SQL injection with UNION")

    assert stats["found"] is True
    assert stats["stats"]["total_uses"] == 1
    assert stats["stats"]["success_rate"] == 1.0


@pytest.mark.asyncio
async def test_knowledge_library(mission_tools):
    """Test adding and searching the curated knowledge library."""
    library_tool = mission_tools["library"]
    session = mission_tools["session"]

    # Add a technique to the library
    add_result = await library_tool.add_to_library(
        category="auth",
        title="JWT Algorithm Confusion",
        content="""
        Exploit JWT signature verification by changing algorithm from RS256 to HS256.
        This allows using the public key as HMAC secret.

        Example:
        1. Get public key from /jwks endpoint
        2. Change alg to HS256
        3. Sign with public key as secret
        """,
        metadata=json.dumps(
            {"tags": ["jwt", "auth", "bypass"], "cve": "CVE-2016-10555"}
        ),
    )

    assert add_result["status"] == "added"
    technique_id = add_result["technique_id"]  # noqa: F841

    # Commit so the entry is visible for duplicate detection
    await session.commit()

    # Search the library
    search_result = await library_tool.search_library(
        query="JWT signature bypass", category="auth", limit=5
    )

    assert search_result["total_found"] > 0
    found_technique = search_result["techniques"][0]
    assert found_technique["title"] == "JWT Algorithm Confusion"
    assert found_technique["category"] == "auth"

    # Try adding duplicate (should detect similarity) - make it very similar
    duplicate_result = await library_tool.add_to_library(
        category="auth",
        title="JWT Algorithm Confusion Attack",
        content="""
        Exploit JWT signature verification by changing algorithm from RS256 to HS256.
        This allows using the public key as HMAC secret.

        Example:
        1. Get public key from /jwks endpoint
        2. Change alg to HS256
        """,
    )

    assert duplicate_result["status"] == "duplicate"
    assert "similarity" in duplicate_result

    # Get library stats
    stats = await library_tool.get_library_stats()
    assert stats["total_techniques"] >= 1
    assert any(cat["category"] == "auth" for cat in stats["by_category"])


@pytest.mark.asyncio
async def test_mission_context_switching(mission_tools):
    """Test switching between multiple mission contexts."""
    core_tool = mission_tools["core"]
    session = mission_tools["session"]

    # Create target
    target = Target(
        host="multi.example.com", port=443, protocol="https", title="Multi-Test API"
    )
    session.add(target)
    await session.commit()

    # Create two missions
    mission1 = await core_tool.create_mission(
        target_id=str(target.id),
        mission_type="general",
        name="XSS testing",
        goal="Find XSS vulnerabilities",
    )
    mission1_id = mission1["mission_id"]

    mission2 = await core_tool.create_mission(
        target_id=str(target.id),
        mission_type="general",
        name="SQL injection testing",
        goal="Find SQL injection points",
    )
    mission2_id = mission2["mission_id"]

    # Set context to mission1
    await core_tool.set_mission_context(mission_id=mission1_id)
    context1 = await core_tool.get_mission_context()
    assert context1["mission"]["name"] == "XSS testing"

    # Record action for mission1
    await core_tool.record_action(
        mission_id=mission1_id,
        action_type="payload_test",
        technique="Reflected XSS",
        success=True,
    )
    await session.commit()  # Commit the action

    # Switch to mission2
    await core_tool.set_mission_context(mission_id=mission2_id)
    context2 = await core_tool.get_mission_context()
    assert context2["mission"]["name"] == "SQL injection testing"
    assert context2["stats"]["total_actions"] == 0  # No actions for mission2 yet

    # Record action for mission2
    await core_tool.record_action(
        mission_id=mission2_id,
        action_type="payload_test",
        technique="UNION SELECT",
        success=False,
    )
    await session.commit()  # Commit the action

    # Verify mission2 has 1 action
    context2_updated = await core_tool.get_mission_context()
    assert context2_updated["stats"]["total_actions"] == 1
    assert context2_updated["stats"]["success_rate"] == 0.0

    # Switch back to mission1 and verify it still has its action
    await core_tool.set_mission_context(mission_id=mission1_id)
    context1_final = await core_tool.get_mission_context()
    assert context1_final["stats"]["total_actions"] == 1
    assert context1_final["stats"]["success_rate"] == 1.0


@pytest.mark.asyncio
async def test_search_techniques_by_criteria(mission_tools):
    """Test searching techniques by various criteria."""
    core_tool = mission_tools["core"]
    search_tool = mission_tools["search"]
    session = mission_tools["session"]

    # Setup test data
    target = Target(
        host="search.example.com", port=443, protocol="https", title="Search Test API"
    )
    session.add(target)
    await session.commit()

    # Use the core tool to create mission properly
    mission_result = await core_tool.create_mission(
        target_id=str(target.id),
        mission_type="general",
        name="Comprehensive security test",
        goal="Test all vulnerabilities",
    )
    mission_id = mission_result["mission_id"]

    # Get the mission from DB
    mission = await session.get(Mission, UUID(mission_id))

    await core_tool.set_mission_context(mission_id=str(mission.id))

    # Create varied test actions
    test_actions = [
        ("payload_test", "XSS <script>", True),
        ("payload_test", "XSS <img>", False),
        ("recon", "Directory enumeration", True),
        ("exploit", "RCE via command injection", True),
        ("payload_test", "SQL injection", True),
        ("recon", "Port scanning", False),
    ]

    for action_type, technique, success in test_actions:
        await core_tool.record_action(
            mission_id=str(mission.id),
            action_type=action_type,
            technique=technique,
            success=success,
        )
    await session.commit()  # Commit all actions

    # Search by success rate
    successful_techniques = await search_tool.search_techniques(min_success_rate=0.5)
    assert (
        len(successful_techniques["techniques"]) >= 3
    )  # At least 3 successful techniques

    # Search by success rate
    successful_only = await search_tool.search_techniques(min_success_rate=1.0)
    # All techniques should have 100% success rate
    assert all(t["success_rate"] == 1.0 for t in successful_only["techniques"])

    # Search by minimum usage
    frequently_used = await search_tool.search_techniques(min_usage_count=1)
    assert len(frequently_used["techniques"]) > 0
