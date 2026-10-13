from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from typing import Optional
from app.core.auth import get_current_user
from app.pipelines.ingestion import ingest_text, ingest_pdf, ingest_url
from app.models.ingest import IngestTextRequest, IngestURLRequest, IngestResponse
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/knowledge", tags=["Knowledge Weaver"])


@router.post("/ingest/text", response_model=IngestResponse)
async def ingest_text_endpoint(
    request: IngestTextRequest,
    user: dict = Depends(get_current_user)
):
    try:
        metadata = {
            "user_id": user["id"],
            "subject": request.subject or "general",
            "title": request.title or "Untitled Note",
        }
        chunks = ingest_text(request.text, metadata=metadata)
        return IngestResponse(
            status="ok",
            chunks_created=len(chunks),
            source="text",
            subject=request.subject,
            message=f"Successfully ingested {len(chunks)} chunks"
        )
    except Exception as e:
        logger.error(f"Text ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest/pdf", response_model=IngestResponse)
async def ingest_pdf_endpoint(
    file: UploadFile = File(...),
    subject: Optional[str] = Form(None),
    user: dict = Depends(get_current_user)
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    try:
        file_bytes = await file.read()
        metadata = {
            "user_id": user["id"],
            "subject": subject or "general",
            "title": file.filename,
        }
        chunks = ingest_pdf(file_bytes, file.filename, metadata=metadata)
        return IngestResponse(
            status="ok",
            chunks_created=len(chunks),
            source=file.filename,
            subject=subject,
            message=f"Successfully ingested {len(chunks)} chunks from {file.filename}"
        )
    except Exception as e:
        logger.error(f"PDF ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest/url", response_model=IngestResponse)
async def ingest_url_endpoint(
    request: IngestURLRequest,
    user: dict = Depends(get_current_user)
):
    try:
        metadata = {
            "user_id": user["id"],
            "subject": request.subject or "general",
            "title": request.title or request.url,
        }
        chunks = ingest_url(request.url, metadata=metadata)
        return IngestResponse(
            status="ok",
            chunks_created=len(chunks),
            source=request.url,
            subject=request.subject,
            message=f"Successfully ingested {len(chunks)} chunks from {request.url}"
        )
    except Exception as e:
        logger.error(f"URL ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph")
async def get_graph(user: dict = Depends(get_current_user)):
    # Sprint KW-7
    return {"status": "ok", "module": "knowledge", "action": "graph"}


@router.get("/search")
async def search(q: str, user: dict = Depends(get_current_user)):
    # Sprint KW-5
    return {"status": "ok", "module": "knowledge", "action": "search", "query": q}


@router.get("/concept/{concept_id}")
async def get_concept(concept_id: str, user: dict = Depends(get_current_user)):
    return {"status": "ok", "concept_id": concept_id}


@router.delete("/concept/{concept_id}")
async def delete_concept(concept_id: str, user: dict = Depends(get_current_user)):
    return {"status": "ok", "deleted": concept_id}


@router.post("/merge")
async def merge_concepts(user: dict = Depends(get_current_user)):
    return {"status": "ok", "action": "merge"}
