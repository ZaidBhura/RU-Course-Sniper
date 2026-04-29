from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class IndexState(Base, TimestampMixin):
    """Global (non-tenant) polling state cache for course section indexes.

    This table is the durable equivalent of watcher.py's in-memory
    `currently_open` set. It is NOT tenant-scoped — a given index is either
    open or closed for everyone, so the state is shared.

    Key invariants (preserved from legacy/watcher.py):
    - last_opened_at is set when is_open transitions FALSE → TRUE
    - last_closed_at is set when is_open transitions TRUE → FALSE
    - These timestamps are used in M2 to implement the re-notification guard
      (mirrors notified_this_session.discard() on close in watcher.py:129)

    In M2, Redis becomes the primary real-time deduplication layer.
    This table provides durable audit of open/close transitions.
    """

    __tablename__ = "index_state"
    __table_args__ = (
        UniqueConstraint(
            "index_number", "semester_code", name="uq_index_state_index_semester"
        ),
        # Partial index for fast lookup of currently-open indexes by the polling task
        Index(
            "idx_index_state_open",
            "index_number",
            "semester_code",
            postgresql_where=text("is_open = TRUE"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    index_number: Mapped[int] = mapped_column(Integer, nullable=False)
    semester_code: Mapped[str] = mapped_column(String, nullable=False)
    is_open: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("FALSE")
    )
    last_opened_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_polled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False
    )
