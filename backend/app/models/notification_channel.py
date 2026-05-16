from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    LargeBinary,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User

CHANNEL_TYPES = ("discord", "pushover")


class NotificationChannel(Base, TimestampMixin):
    """A user's configured notification destination.

    credential_blob stores Fernet-encrypted JSON. The ORM never handles
    plaintext — encryption/decryption is done in app/core/security.py at
    the service layer before write and after read.

    Encrypted JSON schemas:
      discord:  {"webhook_url": "https://discord.com/api/webhooks/..."}
      pushover: {"token": "...", "user_key": "..."}

    One row per channel type per user (enforced by unique constraint).
    """

    __tablename__ = "notification_channels"
    __table_args__ = (
        UniqueConstraint("user_id", "channel_type", name="uq_notification_channels_user_type"),
        CheckConstraint(
            f"channel_type IN {CHANNEL_TYPES}",
            name="chk_notification_channels_type",
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
    channel_type: Mapped[str] = mapped_column(String, nullable=False)
    # BYTEA column — always Fernet-encrypted before insert, never stored plaintext
    credential_blob: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("TRUE")
    )

    user: Mapped[User] = relationship("User", back_populates="notification_channels")
