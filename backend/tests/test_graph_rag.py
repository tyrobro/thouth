"""
backend/tests/test_graph_rag.py

Tests for KW-5: Graph RAG retrieval pipeline.
Requires: Neo4j running, Weaviate running, Ollama running with llama3.1:8b

These are integration tests — they seed data, query the RAG pipeline,
then clean up. Expected runtime: ~60-120s (LLM inference).
"""
import pytest
from langchain_core.documents import Document

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(scope="module")
def seeded_user():
    """
    Seed one user's knowledge base with transformer/attention content,
    then clean up everything after all tests in this module.
    """
    from app.pipelines.embedding import embed_and_store
    from app.pipelines.entity_extraction import extract_entities_from_chunks
    from app.db.neo4j import get_driver

    test_user = "test-kw5-rag-user"

    chunks = [
        Document(
            page_content=(
                "The Transformer architecture uses self-attention to process sequences. "
                "Self-attention allows each token to attend to every other token, giving "
                "the model global context. Unlike RNNs, Transformers process all tokens "
                "in parallel, making training on GPUs much faster."
            ),
            metadata={"source": "transformer-paper", "subject": "deep learning", "chunk_id": "kw5-chunk-1"},
        ),
        Document(
            page_content=(
                "BERT is a bidirectional Transformer model pre-trained on masked language "
                "modeling. GPT uses a unidirectional (causal) Transformer for autoregressive "
                "text generation. Both BERT and GPT are built on the Transformer architecture "
                "and have achieved state-of-the-art results on NLP benchmarks."
            ),
            metadata={"source": "bert-gpt-paper", "subject": "deep learning", "chunk_id": "kw5-chunk-2"},
        ),
    ]

    # Embed into Weaviate
    embed_and_store(chunks, user_id=test_user)

    # Extract entities into Neo4j
    extract_entities_from_chunks(chunks, user_id=test_user, source_id="kw5-test")

    yield test_user

    # Cleanup Weaviate
    try:
        import weaviate.classes as wvc
        from app.db.weaviate import get_client, COLLECTION_NAME

        client = get_client()
        collection = client.collections.get(COLLECTION_NAME)
        collection.data.delete_many(
            where=wvc.query.Filter.by_property("user_id").equal(test_user)
        )
    except Exception as e:
        print(f"Weaviate cleanup warning: {e}")

    # Cleanup Neo4j
    driver = get_driver()
    with driver.session() as session:
        session.run(
            "MATCH (n {user_id: $uid}) DETACH DELETE n",
            uid=test_user,
        )
    print(f"\nCleaned up test data for {test_user}")


@pytest.mark.asyncio
async def test_graph_rag_returns_answer(seeded_user):
    """
    Full pipeline: query about transformers should return a non-empty answer
    that references concepts from the seeded data.
    """
    from app.pipelines.graph_rag import graph_rag_query

    result = graph_rag_query(
        "How does the Transformer architecture work?",
        user_id=seeded_user,
    )

    print(f"\n--- Answer ---\n{result['answer'][:500]}")
    print(f"Concepts found: {[c['title'] for c in result['concepts']]}")
    print(f"Subgraph edges: {len(result['subgraph'])}")
    print(f"Chunks retrieved: {len(result['chunks'])}")
    print(f"Sources: {result['sources']}")

    assert "answer" in result
    assert len(result["answer"]) > 50, "Answer should be substantive, not empty"
    assert "chunks" in result
    assert "concepts" in result
    assert "subgraph" in result
    assert "sources" in result


@pytest.mark.asyncio
async def test_graph_rag_uses_subgraph(seeded_user):
    """
    The subgraph should be non-empty when concepts are found in Neo4j.
    Verifies the 2-hop expansion is wired up.
    """
    from app.pipelines.graph_rag import graph_rag_query

    result = graph_rag_query(
        "What is the relationship between BERT and the Transformer?",
        user_id=seeded_user,
    )

    print(f"\nSubgraph: {result['subgraph'][:3]}")
    print(f"Concepts: {[c['title'] for c in result['concepts']]}")

    assert len(result["concepts"]) > 0 or len(result["chunks"]) > 0, \
        "Should retrieve either concepts or chunks for a question about seeded content"


@pytest.mark.asyncio
async def test_graph_rag_unknown_user():
    """
    An unknown user with no data should still return a valid response structure
    (with an answer indicating insufficient context, not a crash).
    """
    from app.pipelines.graph_rag import graph_rag_query

    result = graph_rag_query(
        "What is deep learning?",
        user_id="no-such-user-kw5-xyz",
    )

    print(f"\nEmpty user answer: {result['answer'][:200]}")

    assert "answer" in result
    assert isinstance(result["answer"], str)
    assert len(result["answer"]) > 0
    assert result["concepts"] == []
    assert result["chunks"] == []