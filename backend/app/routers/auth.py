import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_redis
from app.core.config import settings
from app.core.rate_limit import limiter
from app.core.security import (
    create_access_token,
    hash_password,
    make_refresh_token,
    refresh_token_key,
    verify_password,
)
from app.db.session import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserOut

router = APIRouter(prefix="/auth", tags=["auth"])

_REFRESH_TTL = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400


def _derive_slug(email: str) -> str:
    local = email.split("@")[0]
    slug = re.sub(r"[^a-z0-9]+", "-", local.lower()).strip("-") or "user"
    return f"{slug}-{uuid.uuid4().hex[:8]}"


async def _issue_tokens(user: User, redis) -> TokenResponse:
    access_token = create_access_token(
        sub=str(user.id),
        tenant_id=str(user.tenant_id),
        is_superuser=user.is_superuser,
    )
    refresh = make_refresh_token()
    await redis.set(refresh_token_key(refresh), str(user.id), ex=_REFRESH_TTL)
    return TokenResponse(access_token=access_token, refresh_token=refresh)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/hour")
async def register(
    request: Request,
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    tenant = Tenant(slug=_derive_slug(body.email), display_name=body.email.split("@")[0])
    db.add(tenant)
    await db.flush()

    user = User(
        tenant_id=tenant.id,
        email=body.email,
        hashed_password=hash_password(body.password),
        is_superuser=True,
    )
    db.add(user)
    await db.commit()

    return await _issue_tokens(user, redis)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account deactivated")

    return await _issue_tokens(user, redis)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    key = refresh_token_key(body.refresh_token)
    user_id = await redis.get(key)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        await redis.delete(key)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    new_refresh = make_refresh_token()
    async with redis.pipeline(transaction=True) as pipe:
        await pipe.delete(key)
        await pipe.set(refresh_token_key(new_refresh), str(user.id), ex=_REFRESH_TTL)
        await pipe.execute()

    access_token = create_access_token(
        sub=str(user.id),
        tenant_id=str(user.tenant_id),
        is_superuser=user.is_superuser,
    )
    return TokenResponse(access_token=access_token, refresh_token=new_refresh)


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_active_user)):
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: RefreshRequest, redis=Depends(get_redis)):
    await redis.delete(refresh_token_key(body.refresh_token))
