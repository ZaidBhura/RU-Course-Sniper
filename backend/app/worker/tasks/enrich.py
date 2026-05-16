"""refresh_course_cache Celery task — periodic course detail cache writer.

Runs every ENRICH_INTERVAL_SECONDS (default 600s / 10 min) via Celery Beat.
Fetches all course data from the Rutgers SOC API and stores it in the Redis
hash used by dispatch_notification to enrich notifications with course names,
instructors, and meeting times.

Failure is non-fatal — notifications still fire with just the index number
(preserves legacy/enricher.py graceful-degradation behaviour).
"""

import structlog

from app.core.config import settings
from app.services import enricher, soc_client
from app.worker.celery_app import celery_app
from app.worker.db import get_worker_redis

log = structlog.get_logger(__name__)


@celery_app.task(
    name="app.worker.tasks.enrich.refresh_course_cache",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def refresh_course_cache(self, semester_code: str) -> dict:
    """Fetch all courses for semester_code and write to Redis course cache.

    TTL is set to ENRICH_INTERVAL_SECONDS + 100s buffer so the cache remains
    warm even if a scheduled refresh fires slightly late.
    """
    try:
        log.info("refresh_course_cache.fetching", semester_code=semester_code)
        course_map = soc_client.fetch_courses(semester_code)

        if not course_map:
            log.warning(
                "refresh_course_cache.empty_response",
                semester_code=semester_code,
            )
            return {"status": "empty", "count": 0}

        r = get_worker_redis()
        ttl = settings.ENRICH_INTERVAL_SECONDS + 100
        enricher.store_course_details(r, semester_code, course_map, ttl_seconds=ttl)

        log.info(
            "refresh_course_cache.complete",
            semester_code=semester_code,
            count=len(course_map),
            ttl_seconds=ttl,
        )
        return {"status": "ok", "count": len(course_map), "semester_code": semester_code}

    except Exception as exc:
        log.exception("refresh_course_cache.error", semester_code=semester_code, error=str(exc))
        raise self.retry(exc=exc)
