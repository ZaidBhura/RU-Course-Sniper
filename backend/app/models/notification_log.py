from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.watched_index import WatchedIndex

EVENT_TYPES = ("open_notify", "close_reset")
DELIVERY_STATUSES = ("sent", "failed", "skipped")


class NotificationLog(Base):
    """Immutable audit trail for every notification dispatch attempt.

    Intentionally does NOT inherit TimestampMixin — there is no updated_at
    because this table is append-only. Rows must never be updated or deleted
    in application code (a DB-level trigger will enforce this in M3).

    event_type meanings:
    - open_notify:  a notification was dispatched because an index became open
    - close_reset:  an index closed; no message sent, but state reset is logged
                    (mirrors notified_this_session.discard() in watcher.py:129)

    course_* columns are denormalized snapshots of the enricher data at the
    time of notification — they must not be updated retroactively.
    """

    __tablename__ = "notification_log"
    __table_args__ = (
        CheckConstraint(
            f"event_type IN {EVENT_TYPES}",
            name="chk_notification_log_event_type",
        ),
        CheckConstraint(
            f"delivery_status IN {DELIVERY_STATUSES}",
            name="chk_notification_log_delivery_status",
        ),
        Index("idx_notification_log_user_id", "user_id"),
        Index("idx_notification_log_created_at", "created_at"),
        Index("idx_notification_log_index_semester", "index_number", "semester_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    watched_index_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("watched_indexes.id"),
        nullable=False,
    )
    # Denormalized for fast querying without joins
    index_number: Mapped[int] = mapped_column(Integer, nullable=False)
    semester_code: Mapped[str] = mapped_column(String, nullable=False)
    channel_type: Mapped[str] = mapped_column(String, nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    delivery_status: Mapped[str] = mapped_column(String, nullable=False)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    # Snapshot of course enricher data at notification time (may be None if enricher
    # had not yet loaded — preserves legacy graceful-degradation behaviour)
    course_subject: Mapped[str | None] = mapped_column(String, nullable=True)
    course_number: Mapped[str | None] = mapped_column(String, nullable=True)
    course_title: Mapped[str | None] = mapped_column(String, nullable=True)
    webreg_url: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("NOW()"),
        nullable=False,
    )

    watched_index: Mapped[WatchedIndex] = relationship(
        "WatchedIndex", back_populates="notification_logs"
    )
