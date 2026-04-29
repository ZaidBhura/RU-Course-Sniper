"""Celery application and Beat schedule for the RU Course Sniper worker."""

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "course_sniper",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.worker.tasks.poll",
        "app.worker.tasks.notify",
        "app.worker.tasks.enrich",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    # Ack only after the task body completes — ensures at-least-once delivery.
    # Tasks must be idempotent (dedup via Redis).
    task_acks_late=True,
    # One task at a time per worker process to avoid noisy neighbours.
    worker_prefetch_multiplier=1,
    # Route long-running notification tasks to a dedicated queue in future.
    task_default_queue="default",
    beat_schedule={
        "poll-soc": {
            "task": "app.worker.tasks.poll.poll_soc",
            "schedule": float(settings.POLL_INTERVAL_SECONDS),
            "args": (settings.SEMESTER_CODE,),
        },
        "refresh-course-cache": {
            "task": "app.worker.tasks.enrich.refresh_course_cache",
            "schedule": float(settings.ENRICH_INTERVAL_SECONDS),
            "args": (settings.SEMESTER_CODE,),
        },
    },
)
