from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)) -> dict:
    """Liveness + readiness probe — returns 500 when DB is unreachable."""
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(status_code=500, detail="database unreachable")
    return {"status": "ok", "db": "reachable"}
