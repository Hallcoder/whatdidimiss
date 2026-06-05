from fastapi import APIRouter
from sqlalchemy import text

from app.database import async_session_factory

router = APIRouter()


@router.get("/health")
async def health_check():
    status = {"status": "ok", "version": "0.1.0"}

    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        status["db"] = "connected"
    except Exception:
        status["db"] = "disconnected"
        status["status"] = "degraded"

    return status
