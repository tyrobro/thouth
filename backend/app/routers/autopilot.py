from fastapi import APIRouter, Depends
from app.core.auth import get_current_user

router = APIRouter(prefix="/autopilot", tags=["Study Autopilot"])


@router.get("/tasks")
async def get_tasks(user: dict = Depends(get_current_user)):
    return {"status": "ok", "action": "get_tasks"}


@router.post("/tasks")
async def add_task(user: dict = Depends(get_current_user)):
    return {"status": "ok", "action": "add_task"}


@router.patch("/tasks/{task_id}")
async def update_task(task_id: str, user: dict = Depends(get_current_user)):
    return {"status": "ok", "task_id": task_id}


@router.get("/plan/today")
async def today_plan(user: dict = Depends(get_current_user)):
    return {"status": "ok", "action": "today_plan"}


@router.post("/sync")
async def sync(user: dict = Depends(get_current_user)):
    return {"status": "ok", "action": "sync_triggered"}


@router.get("/calendar")
async def calendar(user: dict = Depends(get_current_user)):
    return {"status": "ok", "action": "calendar"}


@router.post("/session/init")
async def init_session(user: dict = Depends(get_current_user)):
    return {"status": "ok", "action": "session_init"}


@router.get("/session/status")
async def session_status(user: dict = Depends(get_current_user)):
    return {"status": "ok", "action": "session_status"}
