"""Simple integration test for pgvector functionality."""

import asyncio

import numpy as np
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from hiro.core.vector.embeddings import EmbeddingGenerator


async def test_pgvector_basic():
    """Basic test that pgvector and embeddings work."""
    # Use the main database directly
    DATABASE_URL = (
        "postgresql+asyncpg://code_mcp_user:code_mcp_pass@localhost:5432/code_mcp"
    )

    engine = create_async_engine(DATABASE_URL, echo=False)

    async with AsyncSession(engine) as session:
        # Test 1: Check pgvector extension
        result = await session.execute(
            text(
                "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector'"
            )
        )
        row = result.fetchone()
        assert row is not None, "pgvector extension not found"
        assert row[0] == "vector"
        print(f"✓ pgvector {row[1]} is installed")

        # Test 2: Check our tables exist
        result = await session.execute(
            text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name IN ('mission_actions', 'technique_library', 'action_requests')
                ORDER BY table_name
            """)
        )
        tables = [row[0] for row in result.fetchall()]
        assert "mission_actions" in tables
        assert "technique_library" in tables
        assert "action_requests" in tables
        print(f"✓ Found {len(tables)} vector-enabled tables")

        # Test 3: Check vector columns exist
        result = await session.execute(
            text("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'missions'
                AND column_name IN ('goal_embedding', 'hypothesis_embedding')
                ORDER BY column_name
            """)
        )
        columns = result.fetchall()
        assert len(columns) == 2
        assert columns[0][0] == "goal_embedding"
        assert columns[1][0] == "hypothesis_embedding"
        print("✓ Vector columns exist in missions table")

    # Test 4: Generate embeddings
    generator = EmbeddingGenerator()
    test_text = "SQL injection attack using UNION SELECT"
    embedding = generator.encode_text(test_text)

    assert isinstance(embedding, np.ndarray)
    assert embedding.shape == (384,)
    assert not np.allclose(embedding, 0)
    print(f"✓ Generated embedding with shape {embedding.shape}")

    # Test 5: Test vector operations in PostgreSQL
    async with AsyncSession(engine) as session:
        # Create two test embeddings
        text1 = "Cross-site scripting vulnerability"
        text2 = "XSS attack payload"
        text3 = "Database connection timeout"

        emb1 = generator.encode_text(text1)
        emb2 = generator.encode_text(text2)
        emb3 = generator.encode_text(text3)

        # Calculate similarities (converting to string format for PostgreSQL)
        # pgvector expects string format like '[1.0, 2.0, 3.0]'
        e1_str = str(emb1.tolist())
        e2_str = str(emb2.tolist())
        e3_str = str(emb3.tolist())

        result = await session.execute(
            text("""
                SELECT
                    1 - (CAST(:e1 AS vector) <=> CAST(:e2 AS vector)) as sim_xss,
                    1 - (CAST(:e1 AS vector) <=> CAST(:e3 AS vector)) as sim_diff
            """),
            {"e1": e1_str, "e2": e2_str, "e3": e3_str},
        )

        sims = result.fetchone()
        sim_xss = float(sims[0])
        sim_diff = float(sims[1])

        print(
            f"  XSS similarity: {sim_xss:.3f}, Different topic similarity: {sim_diff:.3f}"
        )
        assert sim_xss > sim_diff, "Similar texts should have higher similarity"
        assert (
            sim_xss > 0.3
        ), "XSS-related texts should be similar (threshold lowered for MiniLM)"
        print("✓ Vector similarity works correctly")

    await engine.dispose()
    print("\n🎉 All pgvector integration tests passed!")


if __name__ == "__main__":
    asyncio.run(test_pgvector_basic())
