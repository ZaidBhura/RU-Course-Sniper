import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.db.session import get_api_db
from app.models.user import User
from app.models.watched_index import WatchedIndex
from app.schemas.watchlist import WatchedIndexCreate, WatchedIndexOut, WatchedIndexPatch

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@router.get("/", response_model=list[WatchedIndexOut])
async def list_watchlist(
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_api_db),
):
    result = await db.execute(
        select(WatchedIndex)
        .where(WatchedIndex.user_id == user.id, WatchedIndex.tenant_id == user.tenant_id)
        .order_by(WatchedIndex.created_at.desc())
    )
    return result.scalars().all()


@router.post("/", response_model=WatchedIndexOut, status_code=status.HTTP_201_CREATED)
async def create_watched_index(
    body: WatchedIndexCreate,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_api_db),
):
    wi = WatchedIndex(
        tenant_id=user.tenant_id,
        user_id=user.id,
        index_number=body.index_number,
        label=body.label,
        semester_code=body.semester_code,
    )
    db.add(wi)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already watching this index")
    return wi


@router.patch("/{watched_id}", response_model=WatchedIndexOut)
async def update_watched_index(
    watched_id: uuid.UUID,
    body: WatchedIndexPatch,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_api_db),
):
    result = await db.execute(
        select(WatchedIndex).where(
            WatchedIndex.id == watched_id,
            WatchedIndex.user_id == user.id,
            WatchedIndex.tenant_id == user.tenant_id,
        )
    )
    wi = result.scalar_one_or_none()
    if not wi:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    if body.label is not None:
        wi.label = body.label
    if body.is_active is not None:
        wi.is_active = body.is_active

    await db.commit()
    return wi


@router.delete("/{watched_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_watched_index(
    watched_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_api_db),
):
    result = await db.execute(
        select(WatchedIndex).where(
            WatchedIndex.id == watched_id,
            WatchedIndex.user_id == user.id,
            WatchedIndex.tenant_id == user.tenant_id,
        )
    )
    wi = result.scalar_one_or_none()
    if not wi:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    wi.is_active = False
    await db.commit()
