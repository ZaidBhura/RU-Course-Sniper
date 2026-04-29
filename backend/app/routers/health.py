from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)) -> dict:
    """Liveness + readiness probe.

    Returns 200 if the application is running and the database is reachable.
    Returns 500 (via unhandled exception → FastAPI default handler) if the DB
    connection fails — a deliberate fail-fast so load balancers remove the
    instance from rotation.
    """
    await db.execute(text("SELECT 1"))
    return {"status": "ok", "db": "reachable"}
