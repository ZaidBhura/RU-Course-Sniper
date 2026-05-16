import redis.asyncio as aioredis
import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import decode_access_token
from app.db.session import get_api_db
from app.models.user import User

bearer = HTTPBearer(auto_error=False)

_redis_pool: aioredis.ConnectionPool | None = None


def _get_redis_pool() -> aioredis.ConnectionPool:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_pool


def get_redis() -> aioredis.Redis:
    """FastAPI dependency: returns an async Redis client backed by a shared connection pool."""
    return aioredis.Redis(connection_pool=_get_redis_pool())


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_api_db),
) -> User:
    creds_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not credentials:
        raise creds_exc
    try:
        payload = decode_access_token(credentials.credentials)
    except ValueError:
        raise creds_exc

    user_id: str | None = payload.get("sub")
    tenant_id: str | None = payload.get("tenant_id")
    if not user_id or not tenant_id:
        raise creds_exc

    # Bind tenant/user to structlog context so all logs in this request carry them.
    structlog.contextvars.bind_contextvars(tenant_id=tenant_id, user_id=user_id)

    # Set transaction-local RLS context before any table access.
    # set_config(..., TRUE) = SET LOCAL — auto-cleared at transaction end (commit/rollback).
    await db.execute(
        text("SELECT set_config('app.current_tenant_id', :tid, TRUE)"),
        {"tid": tenant_id},
    )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise creds_exc
    return user


async def get_current_active_user(user: User = Depends(get_current_user)) -> User:
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account deactivated")
    return user


async def get_current_superuser(user: User = Depends(get_current_active_user)) -> User:
    if not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user
