"""
backend/tests/test_hybrid_search.py

Tests for KW-4: hybrid search (BM25 + vector) and graph_search.
Requires: Weaviate cloud running, Ollama running, Neo4j running.
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from langchain_core.documents import Document


def test_hybrid_search_returns_results():
    """
    Store a chunk, run hybrid search, confirm it comes back.
    Hybrid score field should be present (replaces distance).
    """
    from app.pipelines.embedding import embed_and_store, semantic_search

    test_user = "test-kw4-user"
    chunks = [
        Document(
            page_content="Backpropagation is the algorithm used to train neural networks by computing gradients.",
            metadata={"source": "test-kw4", "subject": "deep learning", "title": "Backprop"},
        )
    ]

    ids = embed_and_store(chunks, user_id=test_user)
    assert len(ids) == 1

    results = semantic_search("how are neural networks trained", user_id=test_user, limit=3)
    print(f"\nHybrid search results: {results}")

    assert len(results) > 0
    # Hybrid search returns 'score' not 'distance'
    assert "score" in results[0], "Hybrid result should have a score field"
    assert results[0]["score"] is not None


def test_hybrid_search_keyword_boost():
    """
    Hybrid search should surface exact keyword matches even when
    semantic similarity is moderate — BM25 component handles this.
    """
    from app.pipelines.embedding import embed_and_store, semantic_search

    test_user = "test-kw4-keyword-user"
    chunks = [
        Document(
            page_content="Gradient descent optimises the loss function by moving in the direction of steepest descent.",
            metadata={"source": "test-kw4-kw", "subject": "ml", "title": "Gradient Descent"},
        ),
        Document(
            page_content="The sky is blue because of Rayleigh scattering of sunlight.",
            metadata={"source": "test-kw4-kw", "subject": "physics", "title": "Sky Color"},
        ),
    ]

    embed_and_store(chunks, user_id=test_user)

    # Exact keyword "gradient descent" — BM25 should rank it first
    results = semantic_search("gradient descent", user_id=test_user, limit=5)
    print(f"\nKeyword boost results: {[r['title'] for r in results]}")

    assert len(results) > 0
    top_title = results[0]["title"]
    assert top_title == "Gradient Descent", f"Expected 'Gradient Descent' first, got '{top_title}'"


def test_graph_search_returns_both():
    """
    graph_search should return chunks from Weaviate AND concepts from Neo4j.
    """
    from app.pipelines.embedding import embed_and_store, graph_search
    from app.pipelines.entity_extraction import extract_entities_from_chunks
    from app.db.neo4j import get_driver

    test_user = "test-kw4-graph-user"
    chunks = [
        Document(
            page_content="Attention mechanisms allow models to focus on relevant parts of the input sequence dynamically.",
            metadata={"source": "test-kw4-graph", "subject": "nlp", "title": "Attention"},
        )
    ]

    embed_and_store(chunks, user_id=test_user)
    extract_entities_from_chunks(chunks, user_id=test_user)

    result = graph_search("attention", user_id=test_user, limit=5)
    print(f"\nGraph search result: chunks={len(result['chunks'])}, concepts={len(result['concepts'])}")

    assert "chunks" in result
    assert "concepts" in result
    assert len(result["chunks"]) > 0, "Should find Weaviate chunks"

    # Cleanup Neo4j
    driver = get_driver()
    with driver.session() as session:
        session.run("MATCH (n:Concept {user_id: $uid}) DETACH DELETE n", uid=test_user)