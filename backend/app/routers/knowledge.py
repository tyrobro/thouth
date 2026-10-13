from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from typing import Optional
from pydantic import BaseModel, HttpUrl
from app.core.auth import get_current_user
from app.pipelines.ingestion import ingest_text, ingest_pdf, ingest_url
from app.pipelines.embedding import embed_and_store, semantic_search
from app.pipelines.entity_extraction import extract_entities_from_chunks, get_graph_for_user
from app.models.ingest import IngestResponse
from app.pipelines.graph_rag import graph_rag_query
from app.pipelines.deduplication import deduplicate_concepts
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/knowledge", tags=["Knowledge Weaver"])


# ─── Request schemas ──────────────────────────────────────────────────────────

class IngestTextRequest(BaseModel):
    text: str
    title: Optional[str] = "Untitled Note"
    subject: Optional[str] = "general"
    source: Optional[str] = "manual"


class IngestURLRequest(BaseModel):
    url: HttpUrl
    title: Optional[str] = None
    subject: Optional[str] = "general"


# ─── Ingest endpoints ─────────────────────────────────────────────────────────

@router.post("/ingest/text", response_model=IngestResponse)
async def ingest_text_endpoint(
    request: IngestTextRequest,
    user: dict = Depends(get_current_user)
):
    user_id = user["id"]
    metadata = {
        "user_id": user_id,
        "subject": request.subject or "general",
        "title": request.title or "Untitled Note",
        "source": request.source or "manual",
        "content_type": "text",
    }
    try:
        chunks = ingest_text(request.text, metadata=metadata)
        embed_and_store(chunks, user_id=user_id)
        extraction = extract_entities_from_chunks(chunks, user_id=user_id, source_id=metadata["source"])
        deduplicate_concepts(user_id)
    except Exception as e:
        logger.error(f"Text ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    return IngestResponse(
        status="ok",
        chunks_created=len(chunks),
        source=metadata["source"],
        subject=request.subject,
        message=f"Ingested {len(chunks)} chunks, extracted {extraction['concepts_added']} concepts"
    )


@router.post("/ingest/pdf", response_model=IngestResponse)
async def ingest_pdf_endpoint(
    file: UploadFile = File(...),
    subject: Optional[str] = Form(None),
    user: dict = Depends(get_current_user)
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    user_id = user["id"]
    metadata = {
        "user_id": user_id,
        "subject": subject or "general",
        "title": file.filename,
        "source": file.filename,
        "content_type": "pdf",
    }
    try:
        file_bytes = await file.read()
        chunks = ingest_pdf(file_bytes, file.filename, metadata=metadata)
        embed_and_store(chunks, user_id=user_id)
        extraction = extract_entities_from_chunks(chunks, user_id=user_id, source_id=file.filename)
        deduplicate_concepts(user_id)
    except Exception as e:
        logger.error(f"PDF ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    return IngestResponse(
        status="ok",
        chunks_created=len(chunks),
        source=file.filename,
        subject=subject,
        message=f"Ingested {len(chunks)} chunks, extracted {extraction['concepts_added']} concepts"
    )


@router.post("/ingest/url", response_model=IngestResponse)
async def ingest_url_endpoint(
    request: IngestURLRequest,
    user: dict = Depends(get_current_user)
):
    user_id = user["id"]
    url_str = str(request.url)
    metadata = {
        "user_id": user_id,
        "subject": request.subject or "general",
        "title": request.title or url_str,
        "source": url_str,
        "content_type": "url",
    }
    try:
        chunks = ingest_url(url_str, metadata=metadata)
        embed_and_store(chunks, user_id=user_id)
        extraction = extract_entities_from_chunks(chunks, user_id=user_id, source_id=url_str)
        deduplicate_concepts(user_id)
    except Exception as e:
        logger.error(f"URL ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    return IngestResponse(
        status="ok",
        chunks_created=len(chunks),
        source=url_str,
        subject=request.subject,
        message=f"Ingested {len(chunks)} chunks, extracted {extraction['concepts_added']} concepts"
    )


# ─── Graph + Search ───────────────────────────────────────────────────────────

@router.get("/graph")
async def get_graph(user: dict = Depends(get_current_user)):
    try:
        return get_graph_for_user(user["id"])
    except Exception as e:
        logger.error(f"Graph fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_knowledge(
    q: str,
    limit: int = 5,
    rag: bool = True,
    user: dict = Depends(get_current_user),
):
    """
    Search the user's knowledge base.
    rag=true (default): Graph RAG — returns LLM answer + supporting evidence.
    rag=false: raw hybrid search results only (faster, no LLM).
    """
    user_id = user["id"]
    try:
        if rag:
            result = graph_rag_query(q, user_id=user_id, limit=limit)
            return {"query": q, **result}
        else:
            from app.pipelines.embedding import semantic_search
            results = semantic_search(q, user_id=user_id, limit=limit)
            return {"query": q, "results": results}
    except Exception as e:
        logger.error("Search error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ─── Stub routes (future sprints) ─────────────────────────────────────────────

@router.get("/concept/{concept_id}")
async def get_concept(concept_id: str, user: dict = Depends(get_current_user)):
    # KW-7
    return {"status": "ok", "concept_id": concept_id}


@router.delete("/concept/{concept_id}")
async def delete_concept(concept_id: str, user: dict = Depends(get_current_user)):
    # KW-7
    return {"status": "ok", "deleted": concept_id}


@router.post("/merge")
async def merge_concepts(user: dict = Depends(get_current_user)):
    # KW-6 dedup agent
    return {"status": "ok", "action": "merge"}

@router.post("/deduplicate")
async def deduplicate(user: dict = Depends(get_current_user)):
    """Merge near-duplicate concept nodes for the current user."""
    user_id = user["id"]
    try:
        result = deduplicate_concepts(user_id)
        return result
    except Exception as e:
        logger.error("Dedup error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))