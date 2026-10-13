"""
backend/app/pipelines/deduplication.py

KW-6: Concept deduplication agent.
Embeds all concept titles for a user, finds near-duplicate pairs via
cosine similarity, merges weaker nodes into stronger ones in Neo4j.
"""
from __future__ import annotations

import logging
import numpy as np
from typing import Optional

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.92


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    va, vb = np.array(a), np.array(b)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)


def _merge_concepts(session, user_id: str, keep_id: str, drop_id: str) -> None:
    """
    Repoint all relationships from drop → keep using plain Cypher (no APOC).
    For each relationship type, we MERGE a new edge then delete the old one.
    """
    # Collect all outgoing edges from drop node
    out_edges = session.run(
        """
        MATCH (drop:Concept {user_id: $user_id, id: $drop_id})-[r]->(other:Concept)
        WHERE other.id <> $keep_id
        RETURN type(r) AS rel_type, other.id AS other_id, properties(r) AS props
        """,
        user_id=user_id, drop_id=drop_id, keep_id=keep_id,
    ).data()

    # Collect all incoming edges to drop node
    in_edges = session.run(
        """
        MATCH (other:Concept)-[r]->(drop:Concept {user_id: $user_id, id: $drop_id})
        WHERE other.id <> $keep_id
        RETURN type(r) AS rel_type, other.id AS other_id, properties(r) AS props
        """,
        user_id=user_id, drop_id=drop_id, keep_id=keep_id,
    ).data()

    # Recreate outgoing edges from keep node (dynamic rel type needs separate queries)
    for edge in out_edges:
        rel_type = edge["rel_type"]
        session.run(
            f"""
            MATCH (keep:Concept {{user_id: $user_id, id: $keep_id}})
            MATCH (other:Concept {{id: $other_id}})
            MERGE (keep)-[r:{rel_type}]->(other)
            ON CREATE SET r = $props
            ON MATCH SET r.strength = coalesce(r.strength, 1) + 1
            """,
            user_id=user_id, keep_id=keep_id,
            other_id=edge["other_id"], props=edge["props"],
        )

    # Recreate incoming edges to keep node
    for edge in in_edges:
        rel_type = edge["rel_type"]
        session.run(
            f"""
            MATCH (other:Concept {{id: $other_id}})
            MATCH (keep:Concept {{user_id: $user_id, id: $keep_id}})
            MERGE (other)-[r:{rel_type}]->(keep)
            ON CREATE SET r = $props
            ON MATCH SET r.strength = coalesce(r.strength, 1) + 1
            """,
            user_id=user_id, keep_id=keep_id,
            other_id=edge["other_id"], props=edge["props"],
        )

    # Delete the duplicate node and all its remaining edges
    session.run(
        "MATCH (n:Concept {user_id: $user_id, id: $drop_id}) DETACH DELETE n",
        user_id=user_id, drop_id=drop_id,
    )

def deduplicate_concepts(user_id: str, threshold: float = SIMILARITY_THRESHOLD) -> dict:
    """
    Find and merge near-duplicate concept nodes for a user.

    Algorithm:
      1. Fetch all concept nodes from Neo4j
      2. Embed all titles in one batch (nomic-embed-text)
      3. Cosine similarity matrix — merge pairs above threshold
      4. Keep the node with higher mastery_score (older on tie)

    Returns: { merged: int, kept: int, pairs: [(title_a, title_b), ...] }
    """
    from app.db.neo4j import get_driver
    from app.db.ollama import get_embeddings

    driver = get_driver()

    # Step 1: Fetch all concepts
    with driver.session() as session:
        result = session.run(
            """
            MATCH (n:Concept {user_id: $user_id})
            RETURN n.id AS id, n.title AS title, n.mastery_score AS mastery_score,
                   n.created_at AS created_at
            ORDER BY n.created_at ASC
            """,
            user_id=user_id,
        )
        concepts = [dict(r) for r in result]

    if len(concepts) < 2:
        return {"merged": 0, "kept": len(concepts), "pairs": []}

    # Step 2: Embed all titles
    embeddings_model = get_embeddings()
    titles = [c["title"] for c in concepts]
    vectors = embeddings_model.embed_documents(titles)

    # Step 3: Find duplicate pairs (upper triangle only to avoid double-processing)
    merged_ids: set[str] = set()
    merge_pairs: list[tuple[str, str]] = []

    for i in range(len(concepts)):
        if concepts[i]["id"] in merged_ids:
            continue
        for j in range(i + 1, len(concepts)):
            if concepts[j]["id"] in merged_ids:
                continue

            sim = _cosine_similarity(vectors[i], vectors[j])
            if sim >= threshold:
                # Keep higher mastery_score; on tie keep older (lower index = earlier created)
                score_i = concepts[i].get("mastery_score") or 0.0
                score_j = concepts[j].get("mastery_score") or 0.0
                if score_j > score_i:
                    keep, drop = concepts[j], concepts[i]
                else:
                    keep, drop = concepts[i], concepts[j]

                merge_pairs.append((keep["title"], drop["title"]))
                merged_ids.add(drop["id"])

                logger.info(
                    "Merging '%s' → '%s' (sim=%.3f)",
                    drop["title"], keep["title"], sim,
                )

                with driver.session() as session:
                    _merge_concepts(session, user_id, keep["id"], drop["id"])

    kept = len(concepts) - len(merged_ids)
    return {
        "merged": len(merged_ids),
        "kept": kept,
        "pairs": merge_pairs,
    }