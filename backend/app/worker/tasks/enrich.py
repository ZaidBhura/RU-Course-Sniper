"""refresh_course_cache Celery task — periodic course detail cache writer.

Runs every ENRICH_INTERVAL_SECONDS (default 600s / 10 min) via Celery Beat.
Fetches all course data from the Rutgers SOC API and stores it in the Redis
hash used by dispatch_notification to enrich notifications with course names,
instructors, and meeting times.

Failure is non-fatal — notifications still fire with just the index number
(preserves legacy/enricher.py graceful-degradation behaviour).
"""

import logging

import redis as redis_lib

from app.core.config import settings
from app.services import enricher, soc_client
from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


def _get_redis() -> redis_lib.Redis:
    return redis_lib.from_url(settings.REDIS_URL, decode_responses=True)


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
        logger.info("refresh_course_cache(%s): fetching from SOC API", semester_code)
        course_map = soc_client.fetch_courses(semester_code)

        if not course_map:
            logger.warning(
                "refresh_course_cache(%s): SOC API returned empty course map — cache not updated",
                semester_code,
            )
            return {"status": "empty", "count": 0}

        r = _get_redis()
        ttl = settings.ENRICH_INTERVAL_SECONDS + 100
        enricher.store_course_details(r, semester_code, course_map, ttl_seconds=ttl)

        logger.info("refresh_course_cache(%s): cached %d courses (TTL=%ds)", semester_code, len(course_map), ttl)
        return {"status": "ok", "count": len(course_map), "semester_code": semester_code}

    except Exception as exc:
        logger.exception("refresh_course_cache(%s) error: %s", semester_code, exc)
        raise self.retry(exc=exc)
