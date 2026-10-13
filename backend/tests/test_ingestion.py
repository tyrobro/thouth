from app.pipelines.ingestion import ingest_text, ingest_pdf, ingest_url
import pytest


def test_ingest_text_basic():
    text = """
    Transformers are a type of neural network architecture introduced in the paper
    'Attention is All You Need'. They use self-attention mechanisms to process
    sequential data in parallel, making them much faster to train than RNNs.
    The key components are the encoder, decoder, and multi-head attention layers.
    """
    chunks = ingest_text(text, metadata={"subject": "deep_learning"})
    assert len(chunks) > 0
    assert all(len(c.page_content) <= 600 for c in chunks)
    assert chunks[0].metadata["subject"] == "deep_learning"
    print(f"✓ Text ingestion: {len(chunks)} chunks created")


def test_ingest_text_large():
    # Simulate a full lecture note
    text = " ".join(["This is a sentence about machine learning concepts."] * 100)
    chunks = ingest_text(text)
    assert len(chunks) > 1  # Should be split into multiple chunks
    print(f"✓ Large text ingestion: {len(chunks)} chunks created")


def test_ingest_url():
    chunks = ingest_url(
        "https://en.wikipedia.org/wiki/Transformer_(deep_learning_architecture)",
        metadata={"subject": "deep_learning"}
    )
    assert len(chunks) > 0
    print(f"✓ URL ingestion: {len(chunks)} chunks from Wikipedia")


if __name__ == "__main__":
    test_ingest_text_basic()
    test_ingest_text_large()
    test_ingest_url()
    print("\nAll ingestion tests passed!")
