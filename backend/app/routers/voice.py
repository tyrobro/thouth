from fastapi import APIRouter, Depends, UploadFile, File
from app.core.auth import get_current_user

router = APIRouter(prefix="/voice", tags=["Voice"])


@router.post("/transcribe")
async def transcribe(
    audio: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    # Sprint V-1
    return {
        "status": "ok",
        "action": "transcribe",
        "filename": audio.filename,
        "user": user["email"],
    }
