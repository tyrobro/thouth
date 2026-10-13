from app.pipelines.ingestion import ingest_text
from app.pipelines.embedding import embed_and_store, semantic_search, embed_query
import pytest

TEST_USER_ID = "test-user-embedding-123"


def test_embed_query():
    vector = embed_query("What is a transformer neural network?")
    assert isinstance(vector, list)
    assert len(vector) == 768  # nomic-embed-text dimension
    print(f"✓ Query embedding: {len(vector)}-dim vector")


def test_embed_and_store():
    text = """
    Attention mechanisms allow neural networks to focus on relevant parts of the input.
    Self-attention, used in transformers, computes relationships between all positions
    in a sequence simultaneously. This parallelism makes training much faster than
    recurrent approaches like LSTMs and GRUs.
    """
    chunks = ingest_text(text, metadata={
        "subject": "deep_learning",
        "title": "Attention Mechanisms",
        "user_id": TEST_USER_ID,
    })
    ids = embed_and_store(chunks, user_id=TEST_USER_ID)
    assert len(ids) > 0
    assert all(isinstance(id, str) for id in ids)
    print(f"✓ Stored {len(ids)} chunks in Weaviate")


def test_semantic_search():
    # First store something
    text = """
    Backpropagation is the algorithm used to train neural networks.
    It computes gradients of the loss function with respect to each weight
    by applying the chain rule of calculus backwards through the network layers.
    """
    chunks = ingest_text(text, metadata={
        "subject": "deep_learning",
        "title": "Backpropagation",
        "user_id": TEST_USER_ID,
    })
    embed_and_store(chunks, user_id=TEST_USER_ID)

    # Now search for it
    results = semantic_search(
        "how do neural networks learn using gradients",
        user_id=TEST_USER_ID,
        limit=3
    )
    assert len(results) > 0
    assert all("text" in r for r in results)
    print(f"✓ Semantic search returned {len(results)} results")
    print(f"  Top result: {results[0]['text'][:80]}...")


if __name__ == "__main__":
    test_embed_query()
    test_embed_and_store()
    test_semantic_search()
    print("\nAll embedding tests passed!")
