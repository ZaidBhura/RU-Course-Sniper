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

import logging
from datetime import datetime, timezone

import redis as redis_lib
from sqlalchemy import select

from app.core.config import settings
from app.models.index_state import IndexState
from app.models.notification_log import NotificationLog
from app.models.watched_index import WatchedIndex
from app.services import soc_client
from app.worker.celery_app import celery_app
from app.worker.db import NOTIFIED_KEY, get_worker_redis, get_worker_session
from app.worker.tasks.notify import dispatch_notification

logger = logging.getLogger(__name__)

_LOCK_KEY = "sniper:poll:lock:{semester_code}"
_OPEN_SET_KEY = "sniper:poll:open:{semester_code}"
_OPEN_SET_TTL = 120  # seconds — intentionally longer than poll interval so one missed
                     # cycle doesn't falsely mark all indexes as closed


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
    r = get_worker_redis()
    lock_key = _LOCK_KEY.format(semester_code=semester_code)
    open_set_key = _OPEN_SET_KEY.format(semester_code=semester_code)

    # NX = only set if not exists; EX = auto-expire so a crashed worker never
    # holds the lock forever.
    acquired = r.set(lock_key, "1", nx=True, ex=settings.POLL_LOCK_TTL_SECONDS)
    if not acquired:
        logger.debug("poll_soc(%s): lock held by another worker, skipping", semester_code)
        return {"skipped": True, "reason": "lock_held"}

    try:
        open_sections = soc_client.fetch_open_sections(semester_code)
        current_open: set[int] = {s.index_number for s in open_sections}
        previous_open: set[int] = {int(x) for x in r.smembers(open_set_key)}

        newly_open = current_open - previous_open
        newly_closed = previous_open - current_open

        pipe = r.pipeline()
        pipe.delete(open_set_key)
        if current_open:
            pipe.sadd(open_set_key, *[str(i) for i in current_open])
            pipe.expire(open_set_key, _OPEN_SET_TTL)
        pipe.execute()

        now = datetime.now(tz=timezone.utc)
        watchers_to_notify: list[tuple[str, int]] = []

        if newly_open or newly_closed:
            watchers_to_notify = _persist_state_changes(
                semester_code, newly_open, newly_closed, now, r
            )

        for watched_index_id, index_number in watchers_to_notify:
            dispatch_notification.apply_async(
                args=[watched_index_id, index_number, semester_code],
                task_id=f"notify-{watched_index_id}-{semester_code}",
            )
            logger.info(
                "Enqueued dispatch_notification for watched_index=%s index=%d",
                watched_index_id, index_number,
            )

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
) -> list[tuple[str, int]]:
    """Upsert index_state rows, write close_reset logs, and return watchers to notify.

    Returns a list of (watched_index_id, index_number) tuples for newly-open indexes
    so the caller can enqueue notifications without opening a second DB session.
    """
    with get_worker_session() as session:
        all_transitions = newly_open | newly_closed
        existing_states: dict[int, IndexState] = {
            row.index_number: row
            for row in session.execute(
                select(IndexState).where(
                    IndexState.index_number.in_(all_transitions),
                    IndexState.semester_code == semester_code,
                )
            ).scalars().all()
        }

        for index_number in newly_open:
            row = existing_states.get(index_number)
            if row is None:
                row = IndexState(index_number=index_number, semester_code=semester_code)
                session.add(row)
            row.is_open = True
            row.last_opened_at = now
            row.last_polled_at = now

        for index_number in newly_closed:
            row = existing_states.get(index_number)
            if row is not None:
                row.is_open = False
                row.last_closed_at = now
                row.last_polled_at = now
            _write_close_reset_logs(session, semester_code, index_number, now, r)

        watchers_to_notify: list[tuple[str, int]] = []
        if newly_open:
            watchers = session.execute(
                select(WatchedIndex).where(
                    WatchedIndex.index_number.in_(newly_open),
                    WatchedIndex.semester_code == semester_code,
                    WatchedIndex.is_active.is_(True),
                )
            ).scalars().all()
            watchers_to_notify = [(str(wi.id), wi.index_number) for wi in watchers]

    return watchers_to_notify


def _write_close_reset_logs(
    session,
    semester_code: str,
    index_number: int,
    now: datetime,
    r: redis_lib.Redis,
) -> None:
    """Write close_reset log entries and delete dedup keys for a newly-closed index.

    Deleting the dedup key mirrors watcher.py:129 notified_this_session.discard()
    so users are re-notified if the same index reopens later.
    """
    watchers = session.execute(
        select(WatchedIndex).where(
            WatchedIndex.index_number == index_number,
            WatchedIndex.semester_code == semester_code,
            WatchedIndex.is_active.is_(True),
        )
    ).scalars().all()

    for wi in watchers:
        r.delete(NOTIFIED_KEY.format(
            user_id=str(wi.user_id),
            index_number=index_number,
            semester_code=semester_code,
        ))
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
