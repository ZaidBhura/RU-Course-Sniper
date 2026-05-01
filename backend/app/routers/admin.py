import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_superuser
from app.db.session import get_db
from app.models.notification_log import NotificationLog
from app.models.user import User
from app.models.watched_index import WatchedIndex
from app.schemas.log import NotificationLogOut
from app.schemas.user import UserOut, UserPatch
from app.schemas.watchlist import WatchedIndexOut

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[UserOut])
async def list_users(
    admin: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(User.tenant_id == admin.tenant_id).order_by(User.created_at.desc())
    )
    return result.scalars().all()


@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: uuid.UUID,
    body: UserPatch,
    admin: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(User.id == user_id, User.tenant_id == admin.tenant_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    if body.is_active is not None:
        user.is_active = body.is_active
    if body.is_superuser is not None:
        user.is_superuser = body.is_superuser

    await db.commit()
    await db.refresh(user)
    return user


@router.get("/watchlists", response_model=list[WatchedIndexOut])
async def list_all_watchlists(
    admin: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WatchedIndex)
        .where(WatchedIndex.tenant_id == admin.tenant_id)
        .order_by(WatchedIndex.created_at.desc())
    )
    return result.scalars().all()


@router.get("/logs", response_model=list[NotificationLogOut])
async def list_all_logs(
    admin: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(NotificationLog)
        .where(NotificationLog.tenant_id == admin.tenant_id)
        .order_by(NotificationLog.created_at.desc())
        .limit(500)
    )
    return result.scalars().all()
