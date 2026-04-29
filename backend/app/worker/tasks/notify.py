"""dispatch_notification Celery task — per-user notification delivery.

Task args carry only UUIDs and integers — no credentials, webhook URLs, or PII
are ever placed in the Celery queue (which lives in Redis, unencrypted).
Credentials are loaded from the database inside the task and decrypted using Fernet.

Deduplication flow:
  - Check sniper:notified:{user_id}:{index_number}:{semester_code} (Redis GET)
  - If key exists: this user was already notified for this open event → skip
  - If key absent: send notifications, then SET the key
  - Key is deleted by poll_soc when the index closes (close_reset)
    → ensures re-notification when the index reopens later
"""

import json
import logging
from datetime import datetime, timezone

import redis as redis_lib
from sqlalchemy import select

from app.core.config import settings
from app.core.security import decrypt_credential
from app.services import enricher, notifier
from app.services.notifier import NotificationPayload, build_webreg_url
from app.worker.celery_app import celery_app
from app.worker.db import get_worker_session

logger = logging.getLogger(__name__)

_NOTIFIED_KEY = "sniper:notified:{user_id}:{index_number}:{semester_code}"


def _get_redis() -> redis_lib.Redis:
    return redis_lib.from_url(settings.REDIS_URL, decode_responses=True)


@celery_app.task(
    name="app.worker.tasks.notify.dispatch_notification",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
)
def dispatch_notification(self, watched_index_id: str, index_number: int, semester_code: str) -> dict:
    """Send notifications for a newly-open course index to a single user.

    Idempotent: a Redis dedup key prevents double-sending within the same open event.
    Retries up to 3 times on transient errors (network, DB unavailable).
    """
    r = _get_redis()

    with get_worker_session() as session:
        from app.models.notification_channel import NotificationChannel
        from app.models.notification_log import NotificationLog
        from app.models.watched_index import WatchedIndex

        # --- Load WatchedIndex ---
        wi = session.execute(
            select(WatchedIndex).where(WatchedIndex.id == watched_index_id)
        ).scalar_one_or_none()

        if wi is None or not wi.is_active:
            logger.info("dispatch_notification: watched_index %s not found or inactive, skipping", watched_index_id)
            return {"status": "skipped", "reason": "watched_index_inactive"}

        user_id = str(wi.user_id)
        dedup_key = _NOTIFIED_KEY.format(
            user_id=user_id,
            index_number=index_number,
            semester_code=semester_code,
        )

        # --- Dedup check ---
        if r.get(dedup_key):
            logger.info(
                "dispatch_notification: already notified user=%s index=%d, skipping",
                user_id, index_number,
            )
            return {"status": "skipped", "reason": "already_notified"}

        # --- Build notification payload ---
        course_detail = enricher.get_course_detail(r, semester_code, index_number)
        webreg_url = build_webreg_url(index_number, semester_code)
        payload = NotificationPayload(
            index_number=index_number,
            semester_code=semester_code,
            label=wi.label,
            course_detail=course_detail,
            webreg_url=webreg_url,
        )

        # --- Load active notification channels ---
        channels = session.execute(
            select(NotificationChannel).where(
                NotificationChannel.user_id == wi.user_id,
                NotificationChannel.is_active.is_(True),
            )
        ).scalars().all()

        if not channels:
            logger.warning(
                "dispatch_notification: user=%s has no active channels for index=%d",
                user_id, index_number,
            )
            return {"status": "skipped", "reason": "no_channels"}

        # --- Send to each channel, log result ---
        now = datetime.now(tz=timezone.utc)
        any_success = False

        for channel in channels:
            try:
                result = _send_channel(channel, payload)
            except Exception as exc:
                # Decryption failure or unexpected error — log and continue to next channel
                logger.exception(
                    "dispatch_notification: error on channel %s for index=%d: %s",
                    channel.channel_type, index_number, exc,
                )
                result = notifier.SendResult(success=False, error=str(exc))

            status = "sent" if result.success else "failed"
            if result.success:
                any_success = True

            session.add(NotificationLog(
                tenant_id=wi.tenant_id,
                user_id=wi.user_id,
                watched_index_id=wi.id,
                index_number=index_number,
                semester_code=semester_code,
                channel_type=channel.channel_type,
                event_type="open_notify",
                delivery_status=status,
                error_message=result.error if not result.success else None,
                course_subject=course_detail.subject if course_detail else None,
                course_number=course_detail.course_number if course_detail else None,
                course_title=course_detail.title if course_detail else None,
                webreg_url=webreg_url,
                created_at=now,
            ))

        # --- Set dedup key only after at least one successful send ---
        if any_success:
            r.set(dedup_key, "1")
        else:
            logger.error(
                "dispatch_notification: all channels failed for user=%s index=%d",
                user_id, index_number,
            )

        return {"status": "sent" if any_success else "all_failed", "channels": len(channels)}


def _send_channel(channel, payload: NotificationPayload) -> notifier.SendResult:
    """Decrypt credentials and send to the appropriate channel.

    SECURITY: credential_blob is decrypted here, in task memory only.
    The plaintext value is never stored, logged, or passed to other functions
    except the narrow send_discord / send_pushover call.
    """
    creds = json.loads(decrypt_credential(channel.credential_blob))

    if channel.channel_type == "discord":
        webhook_url = creds["webhook_url"]
        return notifier.send_discord(webhook_url, payload)
    elif channel.channel_type == "pushover":
        return notifier.send_pushover(creds["token"], creds["user_key"], payload)
    else:
        return notifier.SendResult(success=False, error=f"unknown channel_type: {channel.channel_type}")
