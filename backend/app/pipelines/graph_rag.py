"""
backend/app/pipelines/graph_rag.py

KW-5: Graph RAG retrieval pipeline.
Combines Weaviate hybrid search (KW-4) with Neo4j 2-hop subgraph traversal
to build a rich context window, then feeds it to Llama 3.1 8B for a
grounded answer with citations.
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

RAG_PROMPT = """You are a knowledgeable study assistant. Answer the question using ONLY the context provided below.
Be specific and reference concepts from the context. If the context doesn't contain enough information to answer fully, say so.

## Knowledge Graph Context

### Relevant Concepts:
{concepts_text}

### Related Concept Network (2-hop):
{subgraph_text}

### Source Chunks:
{chunks_text}

## Question:
{question}

## Instructions:
- Answer directly and specifically based on the context above.
- Cite concepts by name when referencing them.
- If relationships between concepts are relevant, mention them.
- End with a "Sources:" line listing the source documents cited.
- Do not hallucinate facts not present in the context.

Answer:"""


def _expand_subgraph(driver, user_id: str, concept_ids: list[str], hops: int = 2) -> list[dict]:
    """
    Expand concept nodes to a 2-hop subgraph via Neo4j.
    Returns list of {from_title, rel_type, to_title, description} dicts.
    """
    if not concept_ids:
        return []

    with driver.session() as session:
        result = session.run(
            """
            MATCH (start:Concept {user_id: $user_id})
            WHERE start.id IN $concept_ids
            MATCH path = (start)-[r*1..2]-(neighbor:Concept {user_id: $user_id})
            UNWIND relationships(path) AS rel
            WITH startNode(rel) AS a, endNode(rel) AS b, rel
            RETURN DISTINCT
                a.title AS from_title,
                type(rel) AS rel_type,
                b.title AS to_title,
                rel.description AS description
            LIMIT 50
            """,
            user_id=user_id,
            concept_ids=concept_ids,
        )
        return [dict(r) for r in result]


def _build_context(chunks: list[dict], concepts: list[dict], subgraph: list[dict]) -> dict[str, str]:
    """Format retrieved data into text sections for the prompt."""

    # Concepts section
    concept_lines = []
    for c in concepts:
        line = f"- **{c['title']}** ({c.get('subject', 'general')}): {c.get('summary', '')}"
        concept_lines.append(line)
    concepts_text = "\n".join(concept_lines) if concept_lines else "No direct concept matches found."

    # Subgraph section
    subgraph_lines = []
    seen = set()
    for edge in subgraph:
        key = (edge["from_title"], edge["rel_type"], edge["to_title"])
        if key not in seen:
            seen.add(key)
            rel_label = edge["rel_type"].replace("_", " ").title()
            desc = f" — {edge['description']}" if edge.get("description") else ""
            subgraph_lines.append(f"- {edge['from_title']} [{rel_label}] {edge['to_title']}{desc}")
    subgraph_text = "\n".join(subgraph_lines) if subgraph_lines else "No relationship network found."

    # Chunks section
    chunk_lines = []
    for i, ch in enumerate(chunks[:5], 1):  # top 5 chunks max
        source = ch.get("source_id") or ch.get("source") or "unknown"
        score = ch.get("score", 0)
        text = ch.get("text", ch.get("page_content", ""))[:600]
        chunk_lines.append(f"[{i}] (source: {source}, relevance: {score:.2f})\n{text}")
    chunks_text = "\n\n".join(chunk_lines) if chunk_lines else "No source chunks found."

    return {
        "concepts_text": concepts_text,
        "subgraph_text": subgraph_text,
        "chunks_text": chunks_text,
    }


def graph_rag_query(
    question: str,
    user_id: str,
    limit: int = 5,
) -> dict:
    """
    Full Graph RAG pipeline:
    1. Hybrid search → top chunks + matching concept nodes (Weaviate + Neo4j)
    2. Expand matched concepts to 2-hop subgraph (Neo4j)
    3. Assemble context window
    4. LLM generates grounded answer (Llama 3.1 8B)

    Returns:
        {
            "answer": str,
            "concepts": [...],
            "subgraph": [...],
            "chunks": [...],
            "sources": [str, ...]
        }
    """
    from app.pipelines.embedding import graph_search
    from app.db.neo4j import get_driver
    from app.db.ollama import get_reasoning_llm

    # Step 1: Hybrid search — chunks + concept nodes
    search_results = graph_search(question, user_id=user_id, limit=limit)
    chunks: list[dict] = search_results.get("chunks", [])
    concepts: list[dict] = search_results.get("concepts", [])

    # Step 2: 2-hop subgraph expansion
    concept_ids = [c["id"] for c in concepts if c.get("id")]
    driver = get_driver()
    subgraph = _expand_subgraph(driver, user_id=user_id, concept_ids=concept_ids)

    # Step 3: Assemble context
    context = _build_context(chunks, concepts, subgraph)

    # Step 4: Generate answer
    llm = get_reasoning_llm()
    prompt = RAG_PROMPT.format(
        question=question,
        **context,
    )

    response = llm.invoke(prompt)
    answer_text = response.content if hasattr(response, "content") else str(response)

    # Extract unique sources from chunks
    sources = list({
        ch.get("source_id") or ch.get("source", "unknown")
        for ch in chunks
        if ch.get("source_id") or ch.get("source")
    })

    return {
        "answer": answer_text.strip(),
        "concepts": concepts,
        "subgraph": subgraph,
        "chunks": chunks,
        "sources": sources,
    }