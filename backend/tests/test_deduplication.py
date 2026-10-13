"""
backend/tests/test_deduplication.py

KW-6: Concept deduplication agent tests.
Requires: Neo4j running, Ollama running with nomic-embed-text.
"""
import pytest
import uuid
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _insert_concept(session, user_id, title, mastery=0.0):
    cid = str(uuid.uuid4())
    session.run(
        """
        CREATE (n:Concept {
            id: $id, user_id: $user_id,
            title: $title, norm_title: $norm,
            summary: '', subject: 'test',
            mastery_score: $mastery,
            created_at: datetime()
        })
        """,
        id=cid, user_id=user_id, title=title,
        norm=title.lower().strip(), mastery=mastery,
    )
    return cid


@pytest.fixture(scope="module")
def neo4j_session():
    from app.db.neo4j import get_driver
    driver = get_driver()
    with driver.session() as session:
        yield session


def test_dedup_merges_near_duplicates():
    """
    Two near-identical titles should be merged into one node.
    """
    from app.db.neo4j import get_driver
    from app.pipelines.deduplication import deduplicate_concepts

    user_id = "test-kw6-dedup-user"
    driver = get_driver()

    with driver.session() as session:
        # Insert two near-duplicate concepts
        _insert_concept(session, user_id, "Self-Attention Mechanism")
        _insert_concept(session, user_id, "Self Attention Mechanism")  # no hyphen
        # Insert one clearly distinct concept
        _insert_concept(session, user_id, "Gradient Descent Optimization")

    result = deduplicate_concepts(user_id)
    print(f"\nDedup result: {result}")

    assert result["merged"] >= 1, "Should have merged at least one duplicate pair"
    assert result["kept"] >= 1

    # Verify only 2 nodes remain (merged pair → 1, distinct → 1)
    with driver.session() as session:
        count = session.run(
            "MATCH (n:Concept {user_id: $uid}) RETURN count(n) AS c",
            uid=user_id,
        ).single()["c"]
        print(f"Nodes after dedup: {count}")
        assert count == 2

    # Cleanup
    with driver.session() as session:
        session.run("MATCH (n:Concept {user_id: $uid}) DETACH DELETE n", uid=user_id)


def test_dedup_preserves_higher_mastery():
    """
    When merging, the node with higher mastery_score should survive.
    """
    from app.db.neo4j import get_driver
    from app.pipelines.deduplication import deduplicate_concepts

    user_id = "test-kw6-mastery-user"
    driver = get_driver()

    with driver.session() as session:
        _insert_concept(session, user_id, "Neural Network", mastery=0.0)
        _insert_concept(session, user_id, "Neural Networks", mastery=0.8)

    result = deduplicate_concepts(user_id)
    print(f"\nMastery dedup result: {result}")

    with driver.session() as session:
        node = session.run(
            "MATCH (n:Concept {user_id: $uid}) RETURN n.title AS title, n.mastery_score AS score",
            uid=user_id,
        ).single()
        print(f"Surviving node: {node['title']} (mastery={node['score']})")
        assert node["score"] == 0.8, "Higher mastery node should survive"

    # Cleanup
    with driver.session() as session:
        session.run("MATCH (n:Concept {user_id: $uid}) DETACH DELETE n", uid=user_id)


def test_dedup_no_false_positives():
    """
    Clearly distinct concepts should not be merged.
    """
    from app.db.neo4j import get_driver
    from app.pipelines.deduplication import deduplicate_concepts

    user_id = "test-kw6-distinct-user"
    driver = get_driver()

    with driver.session() as session:
        _insert_concept(session, user_id, "Transformer Architecture")
        _insert_concept(session, user_id, "Gradient Descent")
        _insert_concept(session, user_id, "Convolutional Neural Network")

    result = deduplicate_concepts(user_id)
    print(f"\nDistinct concepts dedup result: {result}")

    assert result["merged"] == 0, "Distinct concepts should not be merged"
    assert result["kept"] == 3

    # Cleanup
    with driver.session() as session:
        session.run("MATCH (n:Concept {user_id: $uid}) DETACH DELETE n", uid=user_id)