from fastapi import APIRouter, Depends
from app.core.auth import get_current_user

router = APIRouter(prefix="/knowledge", tags=["Knowledge Weaver"])


@router.post("/ingest")
async def ingest(user: dict = Depends(get_current_user)):
    # Sprint KW-1
    return {"status": "ok", "module": "knowledge", "action": "ingest", "user": user["email"]}


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
