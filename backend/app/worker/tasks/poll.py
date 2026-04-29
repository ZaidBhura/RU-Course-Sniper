"""poll_soc Celery task — core polling state machine.

Preserves all behavioral semantics from legacy/watcher.py:
1. Poll SOC API for currently-open section indexes
2. Detect newly_open = current - previous (closed → open transitions)
3. Detect newly_closed = previous - current (open → closed transitions)
4. Upsert index_state table (durable audit of open/close events)
5. For newly_open: query active watched_indexes, enqueue dispatch_notification per user
6. For newly_closed: write close_reset NotificationLog entries, delete dedup keys
   (mirrors watcher.py:129 notified_this_session.discard — enables re-notification)
7. Acquire distributed lock before polling — prevents concurrent duplicate polls
"""

import json
import logging
import uuid
from datetime import datetime, timezone

import redis as redis_lib
from celery import shared_task
from sqlalchemy import select, text

from app.core.config import settings
from app.services import soc_client
from app.worker.celery_app import celery_app
from app.worker.db import get_worker_session

logger = logging.getLogger(__name__)

_LOCK_KEY = "sniper:poll:lock:{semester_code}"
_OPEN_SET_KEY = "sniper:poll:open:{semester_code}"
_NOTIFIED_KEY = "sniper:notified:{user_id}:{index_number}:{semester_code}"
_OPEN_SET_TTL = 120  # seconds — slightly longer than poll interval


def _get_redis() -> redis_lib.Redis:
    return redis_lib.from_url(settings.REDIS_URL, decode_responses=True)


@celery_app.task(
    name="app.worker.tasks.poll.poll_soc",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    acks_late=True,
)
def poll_soc(self, semester_code: str) -> dict:
    """Poll the Rutgers SOC API and dispatch notifications for newly-open indexes.

    Returns a summary dict with newly_open/newly_closed counts for logging.
    """
    r = _get_redis()
    lock_key = _LOCK_KEY.format(semester_code=semester_code)
    open_set_key = _OPEN_SET_KEY.format(semester_code=semester_code)

    # Acquire distributed lock — skip this cycle if another worker beat us to it.
    # NX = only set if not exists. EX = expire after lock TTL.
    acquired = r.set(lock_key, "1", nx=True, ex=settings.POLL_LOCK_TTL_SECONDS)
    if not acquired:
        logger.debug("poll_soc(%s): lock held by another worker, skipping", semester_code)
        return {"skipped": True, "reason": "lock_held"}

    try:
        # --- Fetch open sections from SOC API ---
        open_sections = soc_client.fetch_open_sections(semester_code)
        current_open: set[int] = {s.index_number for s in open_sections}

        # --- Load previous open set from Redis ---
        previous_open: set[int] = {int(x) for x in r.smembers(open_set_key)}

        # --- Compute transitions ---
        newly_open = current_open - previous_open
        newly_closed = previous_open - current_open

        # --- Atomically update Redis open set ---
        pipe = r.pipeline()
        pipe.delete(open_set_key)
        if current_open:
            pipe.sadd(open_set_key, *[str(i) for i in current_open])
        pipe.expire(open_set_key, _OPEN_SET_TTL)
        pipe.execute()

        # --- Upsert index_state + handle transitions ---
        now = datetime.now(tz=timezone.utc)

        if newly_open or newly_closed:
            _persist_state_changes(semester_code, newly_open, newly_closed, now, r)

        if newly_open:
            _enqueue_notifications(semester_code, newly_open)

        logger.info(
            "poll_soc(%s): total_open=%d newly_open=%d newly_closed=%d",
            semester_code, len(current_open), len(newly_open), len(newly_closed),
        )
        return {
            "semester_code": semester_code,
            "total_open": len(current_open),
            "newly_open": len(newly_open),
            "newly_closed": len(newly_closed),
        }

    except Exception as exc:
        logger.exception("poll_soc(%s) error: %s", semester_code, exc)
        raise self.retry(exc=exc)
    finally:
        r.delete(lock_key)


def _persist_state_changes(
    semester_code: str,
    newly_open: set[int],
    newly_closed: set[int],
    now: datetime,
    r: redis_lib.Redis,
) -> None:
    """Upsert index_state rows and write close_reset NotificationLog entries."""
    from app.models.index_state import IndexState
    from app.models.notification_log import NotificationLog

    with get_worker_session() as session:
        # Upsert newly opened indexes
        for index_number in newly_open:
            row = session.execute(
                select(IndexState).where(
                    IndexState.index_number == index_number,
                    IndexState.semester_code == semester_code,
                )
            ).scalar_one_or_none()

            if row is None:
                row = IndexState(
                    index_number=index_number,
                    semester_code=semester_code,
                )
                session.add(row)

            row.is_open = True
            row.last_opened_at = now
            row.last_polled_at = now

        # Upsert newly closed indexes + write close_reset log entries
        for index_number in newly_closed:
            row = session.execute(
                select(IndexState).where(
                    IndexState.index_number == index_number,
                    IndexState.semester_code == semester_code,
                )
            ).scalar_one_or_none()

            if row is not None:
                row.is_open = False
                row.last_closed_at = now
                row.last_polled_at = now

            # Log the close_reset event for each user watching this index.
            # This mirrors watcher.py:129 — notified_this_session.discard(index_num)
            _write_close_reset_logs(session, semester_code, index_number, now, r)


def _write_close_reset_logs(
    session,
    semester_code: str,
    index_number: int,
    now: datetime,
    r: redis_lib.Redis,
) -> None:
    """Write close_reset log entries for all users watching a newly-closed index
    and delete their dedup keys so they will be notified again if it reopens."""
    from app.models.notification_log import NotificationLog
    from app.models.watched_index import WatchedIndex

    watchers = session.execute(
        select(WatchedIndex).where(
            WatchedIndex.index_number == index_number,
            WatchedIndex.semester_code == semester_code,
            WatchedIndex.is_active.is_(True),
        )
    ).scalars().all()

    for wi in watchers:
        # Delete dedup key — enables re-notification when index reopens
        dedup_key = _NOTIFIED_KEY.format(
            user_id=str(wi.user_id),
            index_number=index_number,
            semester_code=semester_code,
        )
        r.delete(dedup_key)

        # Append-only audit record
        session.add(NotificationLog(
            tenant_id=wi.tenant_id,
            user_id=wi.user_id,
            watched_index_id=wi.id,
            index_number=index_number,
            semester_code=semester_code,
            channel_type="system",
            event_type="close_reset",
            delivery_status="skipped",
            created_at=now,
        ))


def _enqueue_notifications(semester_code: str, newly_open: set[int]) -> None:
    """Find all active WatchedIndex rows for newly-open indexes and enqueue
    dispatch_notification tasks for each user."""
    from app.models.watched_index import WatchedIndex
    from app.worker.tasks.notify import dispatch_notification

    with get_worker_session() as session:
        watchers = session.execute(
            select(WatchedIndex).where(
                WatchedIndex.index_number.in_(newly_open),
                WatchedIndex.semester_code == semester_code,
                WatchedIndex.is_active.is_(True),
            )
        ).scalars().all()

        for wi in watchers:
            dispatch_notification.apply_async(
                args=[str(wi.id), wi.index_number, semester_code],
                # Idempotency key: one task per (watched_index, open event).
                # If beat fires twice before the lock clears, the dedup key
                # in dispatch_notification prevents double-sending.
                task_id=f"notify-{wi.id}-{semester_code}",
            )
            logger.info(
                "Enqueued dispatch_notification for watched_index=%s index=%d",
                wi.id, wi.index_number,
            )
