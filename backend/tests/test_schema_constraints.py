"""Tests for database-level CHECK constraints and cascade behaviour."""

import json
import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import encrypt_credential
from app.models.index_state import IndexState
from app.models.notification_channel import NotificationChannel
from app.models.notification_log import NotificationLog
from app.models.tenant import Tenant
from app.models.user import User
from app.models.watched_index import WatchedIndex


# ─────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────

async def _make_tenant(db: AsyncSession, slug: str) -> Tenant:
    t = Tenant(slug=slug, display_name="T")
    db.add(t)
    await db.flush()
    return t


async def _make_user(db: AsyncSession, tenant: Tenant) -> User:
    u = User(tenant_id=tenant.id, email=f"{uuid.uuid4()}@x.com", hashed_password="x")
    db.add(u)
    await db.flush()
    return u


async def _make_watched_index(db: AsyncSession, tenant: Tenant, user: User) -> WatchedIndex:
    wi = WatchedIndex(
        tenant_id=tenant.id, user_id=user.id,
        index_number=11111, semester_code="12026"
    )
    db.add(wi)
    await db.flush()
    return wi


# ─────────────────────────────────────────────────────
# notification_log CHECK constraints
# ─────────────────────────────────────────────────────

async def test_notification_log_event_type_constraint(db: AsyncSession) -> None:
    """event_type must be 'open_notify' or 'close_reset'."""
    tenant = await _make_tenant(db, slug="nl-event")
    user = await _make_user(db, tenant)
    wi = await _make_watched_index(db, tenant, user)

    db.add(NotificationLog(
        tenant_id=tenant.id, user_id=user.id, watched_index_id=wi.id,
        index_number=11111, semester_code="12026",
        channel_type="discord",
        event_type="INVALID_TYPE",  # <── must be rejected
        delivery_status="sent",
    ))
    with pytest.raises(IntegrityError, match="chk_notification_log_event_type"):
        await db.flush()


async def test_notification_log_delivery_status_constraint(db: AsyncSession) -> None:
    """delivery_status must be 'sent', 'failed', or 'skipped'."""
    tenant = await _make_tenant(db, slug="nl-status")
    user = await _make_user(db, tenant)
    wi = await _make_watched_index(db, tenant, user)

    db.add(NotificationLog(
        tenant_id=tenant.id, user_id=user.id, watched_index_id=wi.id,
        index_number=11111, semester_code="12026",
        channel_type="discord",
        event_type="open_notify",
        delivery_status="INVALID_STATUS",  # <── must be rejected
    ))
    with pytest.raises(IntegrityError, match="chk_notification_log_delivery_status"):
        await db.flush()


async def test_notification_log_valid_row_inserts(db: AsyncSession) -> None:
    """A valid notification_log row must insert without error."""
    tenant = await _make_tenant(db, slug="nl-valid")
    user = await _make_user(db, tenant)
    wi = await _make_watched_index(db, tenant, user)

    log = NotificationLog(
        tenant_id=tenant.id, user_id=user.id, watched_index_id=wi.id,
        index_number=11111, semester_code="12026",
        channel_type="discord",
        event_type="open_notify",
        delivery_status="sent",
        webreg_url="https://sims.rutgers.edu/webreg/editSchedule.htm?login=cas&semesterSelection=12026&indexList=11111",
    )
    db.add(log)
    await db.flush()
    assert isinstance(log.id, uuid.UUID)
    assert log.created_at is not None


# ─────────────────────────────────────────────────────
# notification_channels CHECK constraint
# ─────────────────────────────────────────────────────

async def test_notification_channel_type_constraint(db: AsyncSession) -> None:
    """channel_type must be 'discord' or 'pushover'."""
    tenant = await _make_tenant(db, slug="nc-type")
    user = await _make_user(db, tenant)
    blob = encrypt_credential('{"webhook_url": "x"}')

    db.add(NotificationChannel(
        tenant_id=tenant.id, user_id=user.id,
        channel_type="email",  # <── must be rejected
        credential_blob=blob,
    ))
    with pytest.raises(IntegrityError, match="chk_notification_channels_type"):
        await db.flush()


# ─────────────────────────────────────────────────────
# Cascade: delete tenant removes all child rows
# ─────────────────────────────────────────────────────

async def test_cascade_delete_tenant(db: AsyncSession) -> None:
    """Deleting a tenant must cascade to users, watched_indexes, notification_channels."""
    from sqlalchemy import select

    tenant = await _make_tenant(db, slug="cascade-tenant")
    user = await _make_user(db, tenant)
    wi = await _make_watched_index(db, tenant, user)
    blob = encrypt_credential(json.dumps({"webhook_url": "https://discord.com/x"}))
    nc = NotificationChannel(
        tenant_id=tenant.id, user_id=user.id, channel_type="discord", credential_blob=blob
    )
    db.add(nc)
    await db.flush()

    tenant_id = tenant.id
    user_id = user.id
    wi_id = wi.id

    await db.delete(tenant)
    await db.flush()
    db.expire_all()  # force re-query so DB-level cascade is visible

    assert await db.get(User, user_id) is None
    assert await db.get(WatchedIndex, wi_id) is None


# ─────────────────────────────────────────────────────
# index_state — global table, no tenant_id
# ─────────────────────────────────────────────────────

async def test_index_state_unique_constraint(db: AsyncSession) -> None:
    s1 = IndexState(index_number=11643, semester_code="12026", is_open=True)
    db.add(s1)
    await db.flush()

    with pytest.raises(IntegrityError, match="uq_index_state_index_semester"):
        db.add(IndexState(index_number=11643, semester_code="12026", is_open=False))
        await db.flush()


async def test_index_state_has_no_tenant_id(db: AsyncSession) -> None:
    """index_state must NOT have a tenant_id column — it is a global table."""
    from sqlalchemy import inspect
    cols = [c.key for c in IndexState.__table__.columns]
    assert "tenant_id" not in cols, "index_state must be tenant-agnostic"
