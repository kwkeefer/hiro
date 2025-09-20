"""Integration tests for pgvector functionality."""

import uuid

import numpy as np
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from hiro.core.vector.embeddings import EmbeddingGenerator
from hiro.core.vector.search import VectorSearch
from hiro.db.models import MissionAction, TechniqueLibrary


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.database
async def test_pgvector_extension_exists(test_db: AsyncSession):
    """Test that pgvector extension is installed."""
    result = await test_db.execute(
        text("SELECT * FROM pg_extension WHERE extname = 'vector'")
    )
    extensions = result.fetchall()
    assert len(extensions) == 1
    assert extensions[0][1] == "vector"  # extname column


@pytest.mark.integration
@pytest.mark.asyncio
async def test_embedding_generation():
    """Test that embeddings can be generated."""
    generator = EmbeddingGenerator()

    # Test single text embedding
    text = "SQL injection attack using UNION SELECT"
    embedding = generator.encode_text(text)

    assert isinstance(embedding, np.ndarray)
    assert embedding.shape == (384,)  # MiniLM-L12-v2 dimension
    assert not np.allclose(embedding, 0)  # Not all zeros

    # Test batch embedding
    texts = [
        "Cross-site scripting in search parameter",
        "Authentication bypass via JWT manipulation",
        "Directory traversal using ../ sequences",
    ]
    embeddings = generator.encode_batch(texts)

    assert embeddings.shape == (3, 384)
    # Verify embeddings are different
    assert not np.allclose(embeddings[0], embeddings[1])
    assert not np.allclose(embeddings[1], embeddings[2])


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.database
async def test_mission_action_with_embeddings(test_db: AsyncSession):
    """Test creating and searching mission actions with embeddings."""
    # Create embedding generator and search
    generator = EmbeddingGenerator()
    # Lower similarity threshold for MiniLM-L12-v2
    search = VectorSearch(generator, similarity_threshold=0.3)

    # Create multiple mission actions with varying similarity
    actions_data = [
        {
            "technique": "SQL injection via login form",
            "payload": "admin' OR '1'='1",
            "result": "Successfully bypassed authentication",
            "success": True,
            "action_type": "exploit",
            "learning": "Login form vulnerable to classic SQL injection",
        },
        {
            "technique": "SQL injection using UNION SELECT",
            "payload": "' UNION SELECT username, password FROM users--",
            "result": "Extracted user credentials from database",
            "success": True,
            "action_type": "exploit",
            "learning": "Database allows UNION queries without proper sanitization",
        },
        {
            "technique": "Blind SQL injection with time delays",
            "payload": "admin' AND SLEEP(5)--",
            "result": "Confirmed blind SQL injection via timing analysis",
            "success": True,
            "action_type": "exploit",
            "learning": "Application vulnerable to time-based blind SQLi",
        },
        {
            "technique": "Cross-site scripting in search field",
            "payload": "<script>alert(document.cookie)</script>",
            "result": "XSS payload executed successfully",
            "success": True,
            "action_type": "exploit",
            "learning": "Search field lacks input sanitization",
        },
        {
            "technique": "Directory traversal attack",
            "payload": "../../../../etc/passwd",
            "result": "Successfully read system files",
            "success": True,
            "action_type": "exploit",
            "learning": "File inclusion without path validation",
        },
        {
            "technique": "SQL injection attempt blocked",
            "payload": "admin' OR '1'='1",
            "result": "WAF blocked the injection attempt",
            "success": False,
            "action_type": "exploit",
            "learning": "WAF is configured to block common SQL patterns",
        },
    ]

    # Add all actions to database
    for data in actions_data:
        action = MissionAction(
            id=uuid.uuid4(),
            mission_id=None,  # No mission for this test
            action_type=data["action_type"],
            technique=data["technique"],
            payload=data["payload"],
            result=data["result"],
            success=data["success"],
            learning=data["learning"],
        )

        # Generate embeddings
        action_text = generator.combine_text_for_embedding(
            data["technique"], data["payload"], None
        )
        action.action_embedding = generator.encode_text(action_text).tolist()

        result_text = generator.combine_text_for_embedding(
            data["technique"], None, data["result"]
        )
        action.result_embedding = generator.encode_text(result_text).tolist()

        test_db.add(action)

    await test_db.commit()

    # Test 1: Search for SQL injection attacks
    sql_results = await search.find_similar_actions(
        query="SQL injection attack",
        session=test_db,
        limit=5,
        success_only=True,
    )

    # Should find the 3 successful SQL injection actions
    assert len(sql_results) >= 3
    # Check that SQL injection actions are ranked higher
    assert (
        "SQL injection" in sql_results[0]["technique"].lower()
        or "sql" in sql_results[0]["technique"].lower()
    )

    # Test 2: Search for XSS attacks
    xss_results = await search.find_similar_actions(
        query="cross-site scripting XSS",
        session=test_db,
        limit=3,
        success_only=True,
    )

    # Should find at least the XSS action
    assert len(xss_results) >= 1
    assert (
        "scripting" in xss_results[0]["technique"].lower()
        or "xss" in xss_results[0]["technique"].lower()
    )

    # Test 3: Search including failed attempts
    all_sql_results = await search.find_similar_actions(
        query="SQL injection",
        session=test_db,
        limit=10,
        success_only=False,
    )

    # Should find both successful and failed SQL injection attempts
    assert len(all_sql_results) >= 4  # 3 successful + 1 failed

    # Test 4: Verify similarity scores make sense
    for result in sql_results:
        # SQL injection results should have decent similarity to the query
        assert result["similarity"] > 0.3
        assert result["similarity"] <= 1.0


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.database
async def test_technique_library_search(test_db: AsyncSession):
    """Test technique library with vector search."""
    generator = EmbeddingGenerator()
    # Lower similarity threshold since MiniLM-L12-v2 produces lower similarities
    search = VectorSearch(generator, similarity_threshold=0.3)

    # Add comprehensive techniques to the library
    techniques = [
        # SQL Injection techniques
        {
            "category": "injection",
            "title": "Blind SQL Injection",
            "content": "Use time-based delays to infer database content when no direct output is available. Payload: admin' AND SLEEP(5)--",
        },
        {
            "category": "injection",
            "title": "Error-based SQL Injection",
            "content": "Extract data through database error messages. Use CONVERT() or CAST() to trigger type conversion errors revealing data.",
        },
        {
            "category": "injection",
            "title": "Union-based SQL Injection",
            "content": "Combine results from multiple SELECT statements using UNION. Payload: ' UNION SELECT null, username, password FROM users--",
        },
        # XSS techniques
        {
            "category": "xss",
            "title": "Stored XSS via Comment",
            "content": "Inject JavaScript in comment fields that execute when other users view the page. Payload: <script>alert(document.cookie)</script>",
        },
        {
            "category": "xss",
            "title": "DOM-based XSS",
            "content": "Exploit client-side scripts that unsafely handle URL fragments. Payload: #<img src=x onerror=alert(1)>",
        },
        {
            "category": "xss",
            "title": "Reflected XSS in Search",
            "content": "Inject scripts that reflect immediately in search results. Test with: <svg onload=alert(1)>",
        },
        # Authentication techniques
        {
            "category": "auth",
            "title": "JWT Algorithm Confusion",
            "content": "Change JWT algorithm from RS256 to HS256 and use public key as secret. Allows forging valid tokens.",
        },
        {
            "category": "auth",
            "title": "Session Fixation",
            "content": "Force user to authenticate with attacker-known session ID. Set cookie before victim logs in.",
        },
        {
            "category": "auth",
            "title": "Password Reset Poisoning",
            "content": "Manipulate Host header during password reset to redirect tokens to attacker-controlled domain.",
        },
        # Other techniques
        {
            "category": "traversal",
            "title": "Path Traversal via Zip",
            "content": "Upload malicious zip files with ../ sequences in filenames to write outside intended directory.",
        },
        {
            "category": "injection",
            "title": "Command Injection",
            "content": "Execute OS commands through unsanitized input. Payload: ; cat /etc/passwd",
        },
        {
            "category": "deserialization",
            "title": "Java Deserialization RCE",
            "content": "Exploit unsafe deserialization of Java objects to achieve remote code execution using ysoserial payloads.",
        },
    ]

    for tech in techniques:
        entry = TechniqueLibrary(
            id=uuid.uuid4(),
            category=tech["category"],
            title=tech["title"],
            content=tech["content"],
        )
        entry.content_embedding = generator.encode_text(tech["content"]).tolist()
        test_db.add(entry)

    await test_db.commit()

    # Test 1: Search for SQL injection techniques
    sql_results = await search.search_technique_library(
        session=test_db,
        query="SQL injection timing attack delays",
        limit=5,
    )

    # Should find SQL injection techniques, with Blind SQL being most relevant
    assert len(sql_results) >= 1
    # Blind SQL injection should be in the results
    found_blind_sql = any("Blind" in r["title"] for r in sql_results)
    assert found_blind_sql, "Should find Blind SQL Injection technique"

    # Test 2: Search for XSS techniques
    xss_results = await search.search_technique_library(
        session=test_db,
        query="cross-site scripting javascript injection",
        limit=5,
    )

    assert len(xss_results) >= 2  # Should find multiple XSS techniques
    # Check that XSS techniques are found
    assert all(r["category"] == "xss" for r in xss_results)

    # Test 3: Search by category filter
    auth_results = await search.search_technique_library(
        session=test_db,
        query="authentication bypass token manipulation",
        category="auth",
        limit=3,
    )

    assert len(auth_results) >= 1
    assert all(r["category"] == "auth" for r in auth_results)
    # JWT technique should be highly relevant
    found_jwt = any("JWT" in r["title"] for r in auth_results)
    assert found_jwt, "Should find JWT technique when searching for token manipulation"

    # Test 4: Cross-category search without filter
    injection_results = await search.search_technique_library(
        session=test_db,
        query="injection attack execute code",
        limit=10,
    )

    # Should find various injection techniques
    assert len(injection_results) >= 3
    categories_found = {r["category"] for r in injection_results}
    assert (
        "injection" in categories_found
    )  # Should definitely find SQL/Command injection

    # Test 5: Verify similarity thresholds work
    very_specific_results = await search.search_technique_library(
        session=test_db,
        query="ysoserial java deserialization gadget chain",
        limit=3,
    )

    # Should find the Java deserialization technique as highly relevant
    if len(very_specific_results) > 0:
        assert (
            "Java" in very_specific_results[0]["title"]
            or "deserialization" in very_specific_results[0]["category"]
        )


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.database
async def test_vector_similarity_calculation(test_db: AsyncSession):
    """Test direct vector similarity calculations in PostgreSQL."""
    generator = EmbeddingGenerator()

    # Generate two similar embeddings
    text1 = "Cross-site scripting attack"
    text2 = "XSS vulnerability exploitation"
    embedding1 = generator.encode_text(text1)
    embedding2 = generator.encode_text(text2)

    # Generate a dissimilar embedding
    text3 = "Network port scanning"
    embedding3 = generator.encode_text(text3)

    # Calculate cosine similarity using pgvector
    result = await test_db.execute(
        text("""
            SELECT
                1 - (CAST(:emb1 AS vector) <=> CAST(:emb2 AS vector)) as similarity_1_2,
                1 - (CAST(:emb1 AS vector) <=> CAST(:emb3 AS vector)) as similarity_1_3
        """),
        {
            "emb1": str(embedding1.tolist()),
            "emb2": str(embedding2.tolist()),
            "emb3": str(embedding3.tolist()),
        },
    )

    similarities = result.fetchone()
    similarity_1_2 = float(similarities[0])
    similarity_1_3 = float(similarities[1])

    # Similar texts should have higher similarity
    assert similarity_1_2 > similarity_1_3
    assert similarity_1_2 > 0.5  # XSS and cross-site scripting are similar
    assert similarity_1_3 < 0.5  # XSS and port scanning are different


@pytest.mark.integration
def test_embedding_generator_initialization():
    """Test that the embedding generator initializes correctly."""
    generator = EmbeddingGenerator()

    assert generator.model_name == "sentence-transformers/all-MiniLM-L12-v2"
    assert generator.vector_dim == 384
    assert generator.encoder is not None
