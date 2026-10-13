from langchain_core.documents import Document
from app.db.ollama import get_embeddings
from app.db.weaviate import get_weaviate_client
from app.db.weaviate_schema import CHUNK_COLLECTION, create_schema
from app.db.neo4j import get_driver
import weaviate.classes as wvc
import uuid
import logging
from typing import List

logger = logging.getLogger(__name__)


def embed_and_store(chunks: List[Document], user_id: str, concept_id: str = None) -> List[str]:
    """
    Takes a list of Document chunks, generates embeddings via Ollama,
    and stores them in Weaviate. Returns list of Weaviate object UUIDs.
    """
    create_schema()

    embedder = get_embeddings()
    client = get_weaviate_client()
    collection = client.collections.get(CHUNK_COLLECTION)

    texts = [chunk.page_content for chunk in chunks]

    logger.info(f"Generating embeddings for {len(texts)} chunks...")
    vectors = embedder.embed_documents(texts)
    logger.info(f"Embeddings generated — {len(vectors)} vectors of dim {len(vectors[0])}")

    stored_ids = []

    with collection.batch.dynamic() as batch:
        for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
            obj_id = str(uuid.uuid4())
            properties = {
                "text": chunk.page_content,
                "source": chunk.metadata.get("source", "unknown"),
                "subject": chunk.metadata.get("subject", "general"),
                "title": chunk.metadata.get("title", "Untitled"),
                "user_id": user_id,
                "content_type": str(chunk.metadata.get("type", "text")),
                "chunk_index": i,
                "concept_id": concept_id or "",
            }
            batch.add_object(
                properties=properties,
                vector=vector,
                uuid=obj_id,
            )
            stored_ids.append(obj_id)

    logger.info(f"Stored {len(stored_ids)} chunks in Weaviate")
    return stored_ids


def embed_query(query: str) -> List[float]:
    """Embeds a single query string for similarity search."""
    embedder = get_embeddings()
    return embedder.embed_query(query)


def semantic_search(query: str, user_id: str, limit: int = 5) -> List[dict]:
    """
    Hybrid search: BM25 (keyword) + vector (semantic) combined via Weaviate's
    hybrid query. Alpha=0.75 weights it 75% semantic, 25% keyword.
    Filters by user_id so users only see their own chunks.
    """
    create_schema()

    query_vector = embed_query(query)
    client = get_weaviate_client()
    collection = client.collections.get(CHUNK_COLLECTION)

    results = collection.query.hybrid(
        query=query,                  # BM25 uses this
        vector=query_vector,          # vector search uses this
        alpha=0.75,                   # 0=pure BM25, 1=pure vector, 0.75=mostly semantic
        limit=limit,
        filters=wvc.query.Filter.by_property("user_id").equal(user_id),
        return_properties=["text", "source", "subject", "title", "content_type", "chunk_index", "concept_id"],
        return_metadata=wvc.query.MetadataQuery(score=True),
    )

    matches = []
    for obj in results.objects:
        matches.append({
            "text": obj.properties.get("text"),
            "source": obj.properties.get("source"),
            "subject": obj.properties.get("subject"),
            "title": obj.properties.get("title"),
            "content_type": obj.properties.get("content_type"),
            "concept_id": obj.properties.get("concept_id"),
            "score": obj.metadata.score if obj.metadata else None,
            "id": str(obj.uuid),
        })

    logger.info(f"Hybrid search returned {len(matches)} results for query: '{query[:50]}'")
    return matches


def graph_search(query: str, user_id: str, limit: int = 5) -> dict:
    from app.db.neo4j import get_driver

    chunks = semantic_search(query, user_id=user_id, limit=limit)

    # Match against any meaningful keyword (>4 chars) from the query
    keywords = [w for w in query.lower().split() if len(w) > 4]
    if not keywords:
        keywords = [query.lower()]

    driver = get_driver()
    with driver.session() as session:
        result = session.run(
            """
            MATCH (n:Concept {user_id: $user_id})
            WHERE ANY(kw IN $keywords WHERE
                toLower(n.title) CONTAINS kw
                OR toLower(n.summary) CONTAINS kw
            )
            RETURN n.id AS id, n.title AS title, n.summary AS summary,
                   n.subject AS subject, n.mastery_score AS mastery_score
            LIMIT $limit
            """,
            user_id=user_id,
            keywords=keywords,
            limit=limit,
        )
        concepts = [dict(r) for r in result]

    return {"chunks": chunks, "concepts": concepts}