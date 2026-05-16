"""Redis-backed course detail cache.

Replaces the in-memory dict + threading.Thread from legacy/enricher.py.
The Celery refresh_course_cache task writes to the cache; poll_soc and
dispatch_notification tasks read from it.

Redis key: sniper:course:cache:{semester_code}
Type:      Hash  (field = str(index_number), value = JSON-encoded CourseDetail dict)
TTL:       ENRICH_INTERVAL_SECONDS + 100s buffer so data is always available
           even if a refresh task is delayed.
"""

import json
from typing import Optional

import redis as redis_lib
import structlog

from app.services.soc_client import CourseDetail

log = structlog.get_logger(__name__)

_CACHE_KEY_PREFIX = "sniper:course:cache"


def _cache_key(semester_code: str) -> str:
    return f"{_CACHE_KEY_PREFIX}:{semester_code}"


def store_course_details(
    r: redis_lib.Redis,
    semester_code: str,
    course_map: dict[int, CourseDetail],
    ttl_seconds: int = 700,
) -> None:
    """Write course map to Redis hash and set TTL.

    Uses a pipeline for atomic multi-HSET + EXPIRE.
    Clears stale entries by deleting the old key first.
    """
    key = _cache_key(semester_code)
    if not course_map:
        log.warning("enricher.store_skipped_empty_map", semester_code=semester_code)
        return

    mapping = {
        str(index_number): json.dumps(
            {
                "subject": detail.subject,
                "course_number": detail.course_number,
                "section": detail.section,
                "title": detail.title,
                "instructors": detail.instructors,
                "meeting_times": detail.meeting_times,
                "index_number": detail.index_number,
            }
        )
        for index_number, detail in course_map.items()
    }
    pipe = r.pipeline()
    pipe.delete(key)
    pipe.hset(key, mapping=mapping)
    pipe.expire(key, ttl_seconds)
    pipe.execute()
    log.info("enricher.cache_written", semester_code=semester_code, count=len(course_map))


def get_course_detail(
    r: redis_lib.Redis,
    semester_code: str,
    index_number: int,
) -> Optional[CourseDetail]:
    """Retrieve a single course detail from the Redis cache.

    Returns None if the cache is cold or the index is not found.
    Never raises — enrichment is always optional.
    """
    key = _cache_key(semester_code)
    try:
        raw = r.hget(key, str(index_number))
        if raw is None:
            return None
        data = json.loads(raw)
        return CourseDetail(
            subject=data["subject"],
            course_number=data["course_number"],
            section=data["section"],
            title=data["title"],
            instructors=data["instructors"],
            meeting_times=data["meeting_times"],
            index_number=data["index_number"],
        )
    except Exception as exc:
        log.warning("enricher.cache_read_failed", index_number=index_number, error=str(exc))
        return None
