"""Synchronous SQLAlchemy session for Celery worker tasks.

Celery runs sync tasks. Using asyncio.run() inside Celery tasks is fragile
and creates event-loop conflicts. This module provides a sync engine backed
by psycopg2 so worker tasks can use plain SQLAlchemy sessions.

The async engine in app/db/session.py is used exclusively by the FastAPI app.
"""

from contextlib import contextmanager
from typing import Generator

import redis as redis_lib
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# Shared Redis connection pool — reused across task invocations in the same worker process.
# redis.from_url() creates a new pool each call; a module-level pool avoids that churn.
_redis_pool = redis_lib.ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True)

# Redis key template for per-user notification dedup.
# Defined here (single source of truth) because both poll.py and notify.py use it:
# poll.py deletes it on close_reset; notify.py checks/sets it on open.
NOTIFIED_KEY = "sniper:notified:{user_id}:{index_number}:{semester_code}"


def get_worker_redis() -> redis_lib.Redis:
    """Return a Redis client backed by the shared module-level connection pool."""
    return redis_lib.Redis(connection_pool=_redis_pool)

# SYNC_DATABASE_URL must use postgresql+psycopg2:// driver prefix
_engine = create_engine(
    settings.SYNC_DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_pre_ping=True,
    # Never echo in worker — avoids leaking query values into logs
    echo=False,
)

_SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)


@contextmanager
def get_worker_session() -> Generator[Session, None, None]:
    """Context manager yielding a sync DB session for worker tasks.

    Rolls back on exception and always closes the session.
    """
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
