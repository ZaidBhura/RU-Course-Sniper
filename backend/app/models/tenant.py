from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class Tenant(Base, TimestampMixin):
    """A tenant represents an isolated workspace (e.g. one Rutgers student or team).

    university_code is a forward-compat column for the M7 multi-university adapter
    pattern. All M1 tenants default to 'RU'.
    """

    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    university_code: Mapped[str] = mapped_column(
        String, nullable=False, default="RU", server_default="RU"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("TRUE")
    )

    users: Mapped[list[User]] = relationship("User", back_populates="tenant", passive_deletes=True)
