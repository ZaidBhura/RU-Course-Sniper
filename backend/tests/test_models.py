"""Tests for SQLAlchemy model round-trips and constraint semantics."""

import json
import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decrypt_credential, encrypt_credential
from app.models.notification_channel import NotificationChannel
from app.models.tenant import Tenant
from app.models.user import User
from app.models.watched_index import WatchedIndex


# ─────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────

async def make_tenant(db: AsyncSession, slug: str = "test-tenant") -> Tenant:
    tenant = Tenant(slug=slug, display_name="Test Tenant")
    db.add(tenant)
    await db.flush()
    return tenant


async def make_user(db: AsyncSession, tenant: Tenant, email: str = "user@example.com") -> User:
    user = User(
        tenant_id=tenant.id,
        email=email,
        hashed_password="$argon2id$placeholder",
    )
    db.add(user)
    await db.flush()
    return user


# ─────────────────────────────────────────────────────
# Tenant
# ─────────────────────────────────────────────────────

async def test_tenant_id_is_uuid(db: AsyncSession) -> None:
    tenant = await make_tenant(db)
    assert isinstance(tenant.id, uuid.UUID), "tenant.id must be UUID, not integer"


async def test_tenant_university_code_defaults_to_ru(db: AsyncSession) -> None:
    tenant = await make_tenant(db)
    assert tenant.university_code == "RU"


async def test_tenant_slug_must_be_unique(db: AsyncSession) -> None:
    await make_tenant(db, slug="unique-slug")
    with pytest.raises(IntegrityError):
        await make_tenant(db, slug="unique-slug")


# ─────────────────────────────────────────────────────
# User
# ─────────────────────────────────────────────────────

async def test_user_id_is_uuid(db: AsyncSession) -> None:
    tenant = await make_tenant(db)
    user = await make_user(db, tenant)
    assert isinstance(user.id, uuid.UUID)


async def test_user_email_unique_per_tenant(db: AsyncSession) -> None:
    tenant = await make_tenant(db, slug="t1")
    await make_user(db, tenant, email="dup@example.com")
    with pytest.raises(IntegrityError, match="uq_users_tenant_email"):
        await make_user(db, tenant, email="dup@example.com")


async def test_same_email_allowed_across_tenants(db: AsyncSession) -> None:
    t1 = await make_tenant(db, slug="ta")
    t2 = await make_tenant(db, slug="tb")
    u1 = await make_user(db, t1, email="shared@example.com")
    u2 = await make_user(db, t2, email="shared@example.com")
    assert u1.id != u2.id


# ─────────────────────────────────────────────────────
# WatchedIndex
# ─────────────────────────────────────────────────────

async def test_watched_index_round_trip(db: AsyncSession) -> None:
    """Exact field values from legacy/models.py WatchedIndex must survive DB round-trip."""
    tenant = await make_tenant(db, slug="wi-tenant")
    user = await make_user(db, tenant)

    wi = WatchedIndex(
        tenant_id=tenant.id,
        user_id=user.id,
        index_number=11643,
        label="Preferred section",
        semester_code="12026",
    )
    db.add(wi)
    await db.flush()

    assert wi.index_number == 11643
    assert wi.label == "Preferred section"
    assert wi.semester_code == "12026"
    assert wi.is_active is True
    assert isinstance(wi.id, uuid.UUID)


async def test_watched_index_label_can_be_none(db: AsyncSession) -> None:
    tenant = await make_tenant(db, slug="wi-null-label")
    user = await make_user(db, tenant)
    wi = WatchedIndex(
        tenant_id=tenant.id, user_id=user.id, index_number=99999, semester_code="12026"
    )
    db.add(wi)
    await db.flush()
    assert wi.label is None


async def test_watched_index_unique_constraint(db: AsyncSession) -> None:
    """Same user + index + semester must raise IntegrityError."""
    tenant = await make_tenant(db, slug="wi-dup")
    user = await make_user(db, tenant)

    def _wi():
        return WatchedIndex(
            tenant_id=tenant.id, user_id=user.id,
            index_number=12345, semester_code="12026"
        )

    db.add(_wi())
    await db.flush()
    with pytest.raises(IntegrityError, match="uq_watched_indexes_user_index_semester"):
        db.add(_wi())
        await db.flush()


async def test_watched_index_zero_rejected(db: AsyncSession) -> None:
    """index_number=0 violates the check constraint (1 ≤ index ≤ 99999)."""
    tenant = await make_tenant(db, slug="wi-zero")
    user = await make_user(db, tenant)
    db.add(WatchedIndex(
        tenant_id=tenant.id, user_id=user.id,
        index_number=0, semester_code="12026"
    ))
    with pytest.raises(IntegrityError, match="chk_watched_indexes_index_number_range"):
        await db.flush()


async def test_watched_index_int_strips_leading_zeros(db: AsyncSession) -> None:
    """Confirm that int('00053') == 53, matching legacy soc_client.py:93 behaviour."""
    assert int("00053") == 53, "SOC API string index must parse to integer without leading zeros"


# ─────────────────────────────────────────────────────
# NotificationChannel — credential encryption
# ─────────────────────────────────────────────────────

async def test_notification_channel_credential_round_trip(db: AsyncSession) -> None:
    """Fernet-encrypted credential_blob survives write → read without data loss."""
    tenant = await make_tenant(db, slug="nc-tenant")
    user = await make_user(db, tenant)

    webhook_url = "https://discord.com/api/webhooks/123456/abcdef"
    plaintext = json.dumps({"webhook_url": webhook_url})
    blob = encrypt_credential(plaintext)

    channel = NotificationChannel(
        tenant_id=tenant.id,
        user_id=user.id,
        channel_type="discord",
        credential_blob=blob,
    )
    db.add(channel)
    await db.flush()

    # Decrypt and assert round-trip
    recovered = json.loads(decrypt_credential(channel.credential_blob))
    assert recovered["webhook_url"] == webhook_url


async def test_notification_channel_unique_per_user_type(db: AsyncSession) -> None:
    tenant = await make_tenant(db, slug="nc-dup")
    user = await make_user(db, tenant)
    blob = encrypt_credential('{"webhook_url": "https://discord.com/api/webhooks/x/y"}')

    db.add(NotificationChannel(
        tenant_id=tenant.id, user_id=user.id, channel_type="discord", credential_blob=blob
    ))
    await db.flush()

    with pytest.raises(IntegrityError, match="uq_notification_channels_user_type"):
        db.add(NotificationChannel(
            tenant_id=tenant.id, user_id=user.id, channel_type="discord", credential_blob=blob
        ))
        await db.flush()


# ─────────────────────────────────────────────────────
# Security: FERNET_KEY must not appear in Settings repr
# ─────────────────────────────────────────────────────

def test_fernet_key_not_in_settings_repr() -> None:
    from app.core.config import settings

    settings_repr = repr(settings)
    assert settings.FERNET_KEY not in settings_repr, (
        "FERNET_KEY must not appear in repr(settings) — add Field(repr=False)"
    )


def test_database_url_not_in_settings_repr() -> None:
    from app.core.config import settings

    settings_repr = repr(settings)
    assert settings.DATABASE_URL not in settings_repr, (
        "DATABASE_URL (may contain password) must not appear in repr(settings)"
    )
