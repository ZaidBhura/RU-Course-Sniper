from datetime import datetime, timezone

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Shared declarative base for all SQLAlchemy models."""

    pass


class TimestampMixin:
    """Adds created_at / updated_at columns to any model.

    Python-side defaults ensure the values are present on the in-memory object
    immediately after insert (without a post-commit refresh), which is required
    because SET LOCAL tenant context clears at transaction end.

    NOT used by notification_log (append-only table — no updated_at).
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        server_default=func.now(),
        onupdate=_utcnow,
        nullable=False,
    )
