from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.notification_channel import NotificationChannel
    from app.models.tenant import Tenant
    from app.models.watched_index import WatchedIndex


class User(Base, TimestampMixin):
    """A user belongs to exactly one tenant.

    Emails are unique per-tenant (not globally), allowing the same email address
    to exist across different tenants.

    hashed_password will be populated with an argon2 hash in M3.
    """

    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),)

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
    email: Mapped[str] = mapped_column(String, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("TRUE")
    )
    is_superuser: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("FALSE")
    )

    tenant: Mapped[Tenant] = relationship("Tenant", back_populates="users")
    watched_indexes: Mapped[list[WatchedIndex]] = relationship(
        "WatchedIndex", back_populates="user", passive_deletes=True
    )
    notification_channels: Mapped[list[NotificationChannel]] = relationship(
        "NotificationChannel", back_populates="user", passive_deletes=True
    )
