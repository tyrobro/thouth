from fastapi import APIRouter
import httpx
from app.core.config import get_settings

router = APIRouter(prefix="/system", tags=["System"])
settings = get_settings()


@router.get("/health")
async def health():
    return {"status": "healthy", "app": settings.app_name, "env": settings.app_env}


@router.get("/models")
async def list_models():
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(f"{settings.ollama_base_url}/api/tags")
            return {"status": "ok", "models": r.json().get("models", [])}
        except Exception as e:
            return {"status": "error", "detail": str(e)}


@router.post("/models/pull")
async def pull_model(model_name: str):
    async with httpx.AsyncClient(timeout=300) as client:
        try:
            r = await client.post(
                f"{settings.ollama_base_url}/api/pull",
                json={"name": model_name},
            )
            return {"status": "ok", "result": r.text}
        except Exception as e:
            return {"status": "error", "detail": str(e)}
