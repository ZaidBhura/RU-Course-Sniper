"""Celery application and Beat schedule for the RU Course Sniper worker."""

from celery import Celery
from celery.signals import worker_process_init

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
    # Prevent Celery from hijacking the root logger — we own that via structlog.
    worker_hijack_root_logger=False,
    worker_log_color=False,
    beat_schedule={
        "poll-soc": {
            "task": "app.worker.tasks.poll.poll_soc",
            "schedule": settings.POLL_INTERVAL_SECONDS,
            "args": (settings.SEMESTER_CODE,),
        },
        "refresh-course-cache": {
            "task": "app.worker.tasks.enrich.refresh_course_cache",
            "schedule": settings.ENRICH_INTERVAL_SECONDS,
            "args": (settings.SEMESTER_CODE,),
        },
    },
)

if settings.SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        send_default_pii=False,
        integrations=[CeleryIntegration()],
    )


@worker_process_init.connect
def _configure_worker_logging(**kwargs) -> None:
    from app.core.logging import configure_logging

    configure_logging()
