import json
import uuid
from datetime import datetime, timezone

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_redis
from app.db.session import get_api_db
from app.models.index_state import IndexState
from app.models.user import User
from app.models.watched_index import WatchedIndex
from app.schemas.watchlist import WatchedIndexCreate, WatchedIndexOut, WatchedIndexPatch
from app.worker.db import NOTIFIED_KEY
from app.worker.tasks.notify import dispatch_notification

router = APIRouter(prefix="/watchlist", tags=["watchlist"])

_OPEN_SET_KEY = "sniper:poll:open:{semester_code}"
_COURSE_CACHE_KEY = "sniper:course:cache:{semester_code}"


async def _lookup_course_name(
    redis: aioredis.Redis,
    index_number: int,
    semester_code: str,
) -> str | None:
    """Return a human-readable course name from the Redis enricher cache, or None."""
    try:
        raw = await redis.hget(  # type: ignore[misc]
            _COURSE_CACHE_KEY.format(semester_code=semester_code),
            str(index_number),
        )
        if not raw:
            return None
        data = json.loads(raw)
        subject = data.get("subject", "")
        course_number = data.get("course_number", "")
        title = data.get("title", "")
        prefix = f"{subject}:{course_number}" if subject and course_number else ""
        parts = [p for p in (prefix, title) if p]
        return " ".join(parts) or None
    except Exception:
        return None


async def _is_index_open(
    db: AsyncSession,
    redis: aioredis.Redis,
    index_number: int,
    semester_code: str,
) -> bool:
    """Return True if the index is currently open.

    Checks both the Redis live open-set (populated every ~20s by poll_soc)
    and the index_state DB table (durable across worker restarts).
    Both are consulted so this works even if the worker has never run yet.
    """
    # Fast path: Redis live set populated by poll_soc
    open_set_key = _OPEN_SET_KEY.format(semester_code=semester_code)
    if await redis.sismember(open_set_key, str(index_number)):  # type: ignore[misc]
        return True

    # Fallback: durable DB state (survives worker restarts, survives cold Redis)
    state_result = await db.execute(
        select(IndexState).where(
            IndexState.index_number == index_number,
            IndexState.semester_code == semester_code,
        )
    )
    state = state_result.scalar_one_or_none()
    return state is not None and state.is_open


@router.get("/", response_model=list[WatchedIndexOut])
async def list_watchlist(
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_api_db),
):
    result = await db.execute(
        select(WatchedIndex)
        .where(
            WatchedIndex.user_id == user.id,
            WatchedIndex.tenant_id == user.tenant_id,
            # Include active watching items and opened items.
            # Soft-deleted items have is_active=False and status='watching' — excluded.
            or_(
                WatchedIndex.is_active.is_(True),
                WatchedIndex.status == "opened",
            ),
        )
        .order_by(WatchedIndex.created_at.desc())
    )
    return result.scalars().all()


@router.post("/", response_model=WatchedIndexOut, status_code=status.HTTP_201_CREATED)
async def create_watched_index(
    body: WatchedIndexCreate,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_api_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    # Check for an existing row with the same (user, index, semester) triple.
    result = await db.execute(
        select(WatchedIndex).where(
            WatchedIndex.user_id == user.id,
            WatchedIndex.index_number == body.index_number,
            WatchedIndex.semester_code == body.semester_code,
        )
    )
    existing = result.scalar_one_or_none()

    course_name = await _lookup_course_name(redis, body.index_number, body.semester_code)

    if existing is not None:
        if not existing.is_active:
            # Previously deleted — reactivate and clear stale dedup key so
            # dispatch_notification isn't skipped for an already-open course.
            existing.status = "watching"
            existing.is_active = True
            existing.created_at = datetime.now(timezone.utc)
            if course_name:
                existing.course_name = course_name
            await db.commit()
            await redis.delete(
                NOTIFIED_KEY.format(
                    user_id=str(existing.user_id),
                    index_number=existing.index_number,
                    semester_code=existing.semester_code,
                )
            )
            wi = existing
        elif existing.status == "watching":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Already watching this index",
            )
        else:
            # status == 'opened'
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This index is in your Opened tab — use Resnipe to watch it again",
            )
    else:
        wi = WatchedIndex(
            tenant_id=user.tenant_id,
            user_id=user.id,
            index_number=body.index_number,
            label=body.label,
            course_name=course_name,
            semester_code=body.semester_code,
            status="watching",
        )
        db.add(wi)
        await db.commit()

    # If the index is already open, notify immediately (once).
    if await _is_index_open(db, redis, body.index_number, body.semester_code):
        dispatch_notification.apply_async(args=[str(wi.id), body.index_number, body.semester_code])

    return wi


@router.post("/{watched_id}/resnipe", response_model=WatchedIndexOut)
async def resnipe_watched_index(
    watched_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_api_db),
    redis: aioredis.Redis = Depends(get_redis),
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

    wi.status = "watching"
    wi.is_active = True
    await db.commit()

    # Delete dedup key so the next poll (or immediate check) can notify again.
    dedup_key = NOTIFIED_KEY.format(
        user_id=str(wi.user_id),
        index_number=wi.index_number,
        semester_code=wi.semester_code,
    )
    await redis.delete(dedup_key)

    # If course is currently open, notify immediately rather than waiting for next poll.
    if await _is_index_open(db, redis, wi.index_number, wi.semester_code):
        dispatch_notification.apply_async(args=[str(wi.id), wi.index_number, wi.semester_code])

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
    redis: aioredis.Redis = Depends(get_redis),
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

    # Clear dedup key so re-adding this index later gets a fresh notification.
    await redis.delete(
        NOTIFIED_KEY.format(
            user_id=str(wi.user_id),
            index_number=wi.index_number,
            semester_code=wi.semester_code,
        )
    )
