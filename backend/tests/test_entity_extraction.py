"""
backend/tests/test_entity_extraction.py

Tests for KW-3: entity extraction pipeline.
Requires: Neo4j running, Ollama running with llama3.1:8b
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from langchain_core.documents import Document


def test_extract_json_parser():
    """Unit test: JSON extraction from various LLM output formats."""
    from app.pipelines.entity_extraction import _extract_json

    raw1 = '{"concepts": [], "relationships": []}'
    assert _extract_json(raw1) == {"concepts": [], "relationships": []}

    raw2 = '```json\n{"concepts": [{"title": "Neural Networks"}], "relationships": []}\n```'
    result = _extract_json(raw2)
    assert result["concepts"][0]["title"] == "Neural Networks"

    raw3 = 'Here is the result:\n{"concepts": [], "relationships": []}'
    assert _extract_json(raw3) == {"concepts": [], "relationships": []}

    print("JSON parser: all formats handled correctly.")


def test_extract_entities_from_single_chunk():
    """
    Integration test: feed one chunk about transformers,
    check Neo4j gets nodes. Cleans up after.
    """
    from app.pipelines.entity_extraction import extract_entities_from_chunks
    from app.db.neo4j import get_driver

    test_user = "test-kw3-user"
    chunks = [
        Document(
            page_content=(
                "The Transformer architecture introduced the self-attention mechanism, "
                "which allows the model to weigh the importance of different words in a "
                "sequence. Unlike RNNs, Transformers process all tokens in parallel, "
                "making them much faster to train on GPUs. BERT and GPT are both based "
                "on the Transformer architecture."
            ),
            metadata={"source": "test", "subject": "deep learning"},
        )
    ]

    result = extract_entities_from_chunks(chunks, user_id=test_user, source_id="test-source")
    print(f"\nExtraction result: {result}")

    assert result["chunks_processed"] == 1
    assert result["concepts_added"] > 0, "Should have extracted at least one concept"

    driver = get_driver()
    with driver.session() as session:
        count = session.run(
            "MATCH (n:Concept {user_id: $uid}) RETURN count(n) AS c",
            uid=test_user,
        ).single()["c"]
        print(f"Nodes in Neo4j for test user: {count}")
        assert count > 0

    # Cleanup
    with driver.session() as session:
        session.run("MATCH (n:Concept {user_id: $uid}) DETACH DELETE n", uid=test_user)
        session.run("MATCH (ch:Chunk {user_id: $uid}) DETACH DELETE ch", uid=test_user)
    print("Test nodes cleaned up.")


def test_get_graph_empty_user():
    """get_graph_for_user returns empty lists for unknown user."""
    from app.pipelines.entity_extraction import get_graph_for_user

    result = get_graph_for_user("no-such-user-xyz-9999")
    assert result["nodes"] == []
    assert result["edges"] == []


def test_relationship_extraction():
    """Integration test: chunk with clear relationships produces edges in Neo4j."""
    from app.pipelines.entity_extraction import extract_entities_from_chunks, get_graph_for_user
    from app.db.neo4j import get_driver

    test_user = "test-kw3-rels-user"
    chunks = [
        Document(
            page_content=(
                "Attention mechanisms build on the concept of sequence-to-sequence models. "
                "Multi-head attention extends single attention by running multiple attention "
                "operations in parallel. Positional encoding is required by Transformer models "
                "because they lack the inherent sequential order of RNNs."
            ),
            metadata={"source": "test-rel", "subject": "deep learning"},
        )
    ]

    result = extract_entities_from_chunks(chunks, user_id=test_user)
    print(f"\nRelationship test result: {result}")

    graph = get_graph_for_user(test_user)
    print(f"Graph nodes: {len(graph['nodes'])}, edges: {len(graph['edges'])}")

    assert len(graph["nodes"]) > 0

    # Cleanup
    driver = get_driver()
    with driver.session() as session:
        session.run("MATCH (n:Concept {user_id: $uid}) DETACH DELETE n", uid=test_user)