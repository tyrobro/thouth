"""
backend/app/pipelines/entity_extraction.py

KW-3: LLM entity + relationship extraction → Neo4j
Feeds document chunks through Llama 3.1 8B, extracts concept nodes
and typed relationship edges, writes them to Neo4j.
"""
from __future__ import annotations

import json
import re
import uuid
from typing import Optional
import logging

from langchain_core.documents import Document

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """You are a knowledge graph builder. Extract concepts and relationships from the text below.

Return ONLY valid JSON in this exact format:
{{
  "concepts": [
    {{
      "title": "concept name (2-5 words, noun phrase)",
      "summary": "one sentence description",
      "subject": "academic subject or domain"
    }}
  ],
  "relationships": [
    {{
      "from": "concept title (must match a concept above)",
      "to": "concept title (must match a concept above)",
      "type": "RELATES_TO | BUILDS_ON | CONTRASTS_WITH | IS_PART_OF | REQUIRES",
      "description": "brief description of how they relate"
    }}
  ]
}}

Rules:
- Extract 2-8 key concepts per chunk. Be selective — quality over quantity.
- Only create relationships between concepts you extracted (not external ones).
- Concept titles must be noun phrases, not full sentences.
- Return [] for relationships if only one concept is found.
- Return ONLY the JSON object, no other text.

Text:
{text}

JSON:"""


def _extract_json(raw: str) -> dict:
    """Pull JSON out of LLM output even if it wraps it in markdown fences."""
    text = raw.strip()
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence_match:
        text = fence_match.group(1).strip()
    brace_match = re.search(r"\{[\s\S]*\}", text)
    if brace_match:
        text = brace_match.group(0)
    return json.loads(text)


def extract_entities_from_chunks(
    chunks: list[Document],
    user_id: str,
    source_id: Optional[str] = None,
) -> dict:
    """
    Run entity extraction on a list of chunks.
    Returns a summary dict: { concepts_added, relationships_added, errors }.
    Writes directly to Neo4j.
    """
    from app.db.ollama import get_reasoning_llm
    from app.db.neo4j import get_driver

    llm = get_reasoning_llm()
    driver = get_driver()

    total_concepts = 0
    total_rels = 0
    errors = []

    for i, chunk in enumerate(chunks):
        try:
            prompt = EXTRACTION_PROMPT.format(text=chunk.page_content[:3000])
            response = llm.invoke(prompt)
            raw = response.content if hasattr(response, "content") else str(response)

            data = _extract_json(raw)
            concepts = data.get("concepts", [])
            relationships = data.get("relationships", [])

            if not concepts:
                continue

            for c in concepts:
                c["_norm"] = c["title"].lower().strip()

            with driver.session() as session:
                for c in concepts:
                    session.run(
                        """
                        MERGE (n:Concept {user_id: $user_id, norm_title: $norm_title})
                        ON CREATE SET
                            n.id        = $id,
                            n.title     = $title,
                            n.summary   = $summary,
                            n.subject   = $subject,
                            n.created_at = datetime(),
                            n.mastery_score = 0.0
                        ON MATCH SET
                            n.summary   = CASE WHEN n.summary = '' THEN $summary ELSE n.summary END,
                            n.subject   = CASE WHEN n.subject  = '' THEN $subject  ELSE n.subject  END
                        """,
                        user_id=user_id,
                        norm_title=c["_norm"],
                        id=str(uuid.uuid4()),
                        title=c["title"],
                        summary=c.get("summary", ""),
                        subject=c.get("subject", "general"),
                    )
                total_concepts += len(concepts)

                norm_map = {c["_norm"]: c["title"] for c in concepts}

                for r in relationships:
                    from_norm = r.get("from", "").lower().strip()
                    to_norm = r.get("to", "").lower().strip()

                    if from_norm not in norm_map or to_norm not in norm_map:
                        continue

                    rel_type = r.get("type", "RELATES_TO").upper()
                    if rel_type not in {
                        "RELATES_TO", "BUILDS_ON", "CONTRASTS_WITH",
                        "IS_PART_OF", "REQUIRES",
                    }:
                        rel_type = "RELATES_TO"

                    session.run(
                        f"""
                        MATCH (a:Concept {{user_id: $user_id, norm_title: $from_norm}})
                        MATCH (b:Concept {{user_id: $user_id, norm_title: $to_norm}})
                        MERGE (a)-[rel:{rel_type}]->(b)
                        ON CREATE SET
                            rel.description = $description,
                            rel.strength    = 1,
                            rel.created_at  = datetime()
                        ON MATCH SET
                            rel.strength = rel.strength + 1
                        """,
                        user_id=user_id,
                        from_norm=from_norm,
                        to_norm=to_norm,
                        description=r.get("description", ""),
                    )
                total_rels += len(relationships)

                if source_id:
                    chunk_id = chunk.metadata.get("chunk_id") or str(uuid.uuid4())
                    session.run(
                        """
                        MERGE (ch:Chunk {id: $chunk_id})
                        ON CREATE SET
                            ch.text       = $text,
                            ch.source_id  = $source_id,
                            ch.user_id    = $user_id,
                            ch.created_at = datetime()
                        """,
                        chunk_id=chunk_id,
                        text=chunk.page_content[:1000],
                        source_id=source_id,
                        user_id=user_id,
                    )
                    for c in concepts:
                        session.run(
                            """
                            MATCH (n:Concept {user_id: $user_id, norm_title: $norm_title})
                            MATCH (ch:Chunk   {id: $chunk_id})
                            MERGE (n)-[:CONTAINS]->(ch)
                            """,
                            user_id=user_id,
                            norm_title=c["_norm"],
                            chunk_id=chunk_id,
                        )

        except json.JSONDecodeError as e:
            msg = f"Chunk {i}: JSON parse error — {e}"
            logger.warning(msg)
            errors.append(msg)
        except Exception as e:
            msg = f"Chunk {i}: {type(e).__name__}: {e}"
            logger.error(msg)
            errors.append(msg)

    return {
        "concepts_added": total_concepts,
        "relationships_added": total_rels,
        "chunks_processed": len(chunks),
        "errors": errors,
    }


def get_graph_for_user(user_id: str) -> dict:
    """
    Fetch the full knowledge graph for a user.
    Returns { nodes: [...], edges: [...] } ready for the React Flow / Three.js frontend.
    """
    from app.db.neo4j import get_driver

    driver = get_driver()
    with driver.session() as session:
        node_result = session.run(
            """
            MATCH (n:Concept {user_id: $user_id})
            RETURN n.id AS id, n.title AS title, n.summary AS summary,
                   n.subject AS subject, n.mastery_score AS mastery_score,
                   n.created_at AS created_at
            ORDER BY n.created_at DESC
            LIMIT 500
            """,
            user_id=user_id,
        )
        nodes = [dict(r) for r in node_result]

        edge_result = session.run(
            """
            MATCH (a:Concept {user_id: $user_id})-[r]->(b:Concept {user_id: $user_id})
            RETURN a.id AS source, b.id AS target,
                   type(r) AS rel_type, r.strength AS strength,
                   r.description AS description
            LIMIT 2000
            """,
            user_id=user_id,
        )
        edges = [dict(r) for r in edge_result]

    return {"nodes": nodes, "edges": edges}