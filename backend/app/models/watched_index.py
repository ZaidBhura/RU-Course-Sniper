from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.notification_log import NotificationLog
    from app.models.user import User


class WatchedIndex(Base, TimestampMixin):
    """A course section index being monitored for availability.

    Preserves original field semantics from legacy/models.py:
    - index_number: int (5-digit Rutgers section ID, stored as INTEGER not TEXT)
      The SOC API returns "00053" as a string; int("00053") == 53 strips leading
      zeros. Unique constraint is correct only with INTEGER storage.
    - label: optional human-readable name (e.g. "Preferred section")
    - semester_code: verbatim string e.g. "12026" (term 1 = Spring, year 2026)
    """

    __tablename__ = "watched_indexes"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "index_number",
            "semester_code",
            name="uq_watched_indexes_user_index_semester",
        ),
        CheckConstraint(
            "index_number BETWEEN 1 AND 99999",
            name="chk_watched_indexes_index_number_range",
        ),
        # Partial index: only active watched indexes; used by polling task in M2
        Index(
            "idx_watched_indexes_active",
            "index_number",
            "semester_code",
            postgresql_where=text("is_active = TRUE"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    index_number: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str | None] = mapped_column(String, nullable=True)
    semester_code: Mapped[str] = mapped_column(
        String, nullable=False, default="12026", server_default="12026"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("TRUE")
    )

    user: Mapped[User] = relationship("User", back_populates="watched_indexes")
    notification_logs: Mapped[list[NotificationLog]] = relationship(
        "NotificationLog", back_populates="watched_index"
    )
