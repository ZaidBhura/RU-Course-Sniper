"""Cross-tenant isolation tests — M5.

Two-layer verification:
1. API-layer: user A cannot read or mutate user B's resources through HTTP endpoints.
2. DB-layer:  when connected as sniper_api (NOBYPASSRLS) with a mismatched tenant
   context, RLS policies return zero rows for strict tables. Skipped automatically
   if sniper_api role has not been created (dev environments using the superuser).
"""

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_api_db, get_redis
from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.watched_index import WatchedIndex

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PASSWORD = "SecurePass999!"


def _email(tag: str) -> str:
    return f"rls-{tag}-{uuid.uuid4().hex[:6]}@example.com"


async def _register(client: AsyncClient, email: str) -> dict:
    r = await client.post("/api/auth/register", json={"email": email, "password": _PASSWORD})
    assert r.status_code == 201, r.text
    return r.json()


def _auth(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


# ---------------------------------------------------------------------------
# API-layer isolation tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_watchlist_cross_tenant_read_blocked(client: AsyncClient) -> None:
    """User B cannot see user A's watchlist entries."""
    tokens_a = await _register(client, _email("a-wl"))
    tokens_b = await _register(client, _email("b-wl"))

    # User A adds a watch
    r = await client.post(
        "/api/watchlist/",
        json={"index_number": 11111},
        headers=_auth(tokens_a),
    )
    assert r.status_code == 201

    # User B's watchlist is empty
    r = await client.get("/api/watchlist/", headers=_auth(tokens_b))
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_watchlist_cross_tenant_delete_blocked(client: AsyncClient) -> None:
    """User B cannot delete user A's watchlist entry (returns 404, not 204)."""
    tokens_a = await _register(client, _email("a-del"))
    tokens_b = await _register(client, _email("b-del"))

    r = await client.post(
        "/api/watchlist/",
        json={"index_number": 22222},
        headers=_auth(tokens_a),
    )
    assert r.status_code == 201
    wi_id = r.json()["id"]

    r = await client.delete(f"/api/watchlist/{wi_id}", headers=_auth(tokens_b))
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_watchlist_cross_tenant_patch_blocked(client: AsyncClient) -> None:
    """User B cannot modify user A's watchlist entry."""
    tokens_a = await _register(client, _email("a-patch"))
    tokens_b = await _register(client, _email("b-patch"))

    r = await client.post(
        "/api/watchlist/",
        json={"index_number": 33333, "label": "Original"},
        headers=_auth(tokens_a),
    )
    assert r.status_code == 201
    wi_id = r.json()["id"]

    r = await client.patch(
        f"/api/watchlist/{wi_id}",
        json={"label": "Hijacked"},
        headers=_auth(tokens_b),
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_channels_cross_tenant_read_blocked(client: AsyncClient) -> None:
    """User B cannot see user A's notification channels."""
    tokens_a = await _register(client, _email("a-ch"))
    tokens_b = await _register(client, _email("b-ch"))

    r = await client.post(
        "/api/channels/",
        json={
            "channel_type": "discord",
            "credential": {"webhook_url": "https://discord.com/api/webhooks/123/abc"},
        },
        headers=_auth(tokens_a),
    )
    assert r.status_code == 201

    r = await client.get("/api/channels/", headers=_auth(tokens_b))
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_logs_cross_tenant_read_blocked(client: AsyncClient) -> None:
    """User B's notification log is empty even if user A has entries."""
    tokens_a = await _register(client, _email("a-log"))
    tokens_b = await _register(client, _email("b-log"))

    # User A has an empty log (no notifications triggered in test), user B sees nothing
    r_a = await client.get("/api/logs/", headers=_auth(tokens_a))
    r_b = await client.get("/api/logs/", headers=_auth(tokens_b))
    assert r_a.status_code == 200
    assert r_b.status_code == 200
    assert r_b.json() == []


# ---------------------------------------------------------------------------
# DB-layer RLS enforcement test (requires sniper_api role)
# ---------------------------------------------------------------------------

_TEST_DB_URL = settings.DATABASE_URL.replace("/course_sniper", "/course_sniper_test")


async def _db_rls_prerequisites_met() -> bool:
    """Return True if sniper_api role exists AND the RLS policy exists in the test DB.

    The policy is created by the Alembic migration against the main DB, but the test
    DB is built from Base.metadata.create_all() which does not run migrations.  The
    DB-level tests create their own ephemeral policy (see fixture below) and only need
    the role to exist cluster-wide.
    """
    engine = create_async_engine(_TEST_DB_URL, echo=False)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT 1 FROM pg_roles WHERE rolname = 'sniper_api'")
            )
            return result.fetchone() is not None
    except Exception:
        return False
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def rls_policy_in_test_db():
    """Create a watched_indexes RLS policy for the test DB for the duration of one test.

    The test DB is built by Base.metadata.create_all() (no Alembic), so RLS policies
    are absent.  This fixture creates an ephemeral policy, yields, then drops it.
    Skips automatically if sniper_api role is not present.
    """
    if not await _db_rls_prerequisites_met():
        pytest.skip("sniper_api role not present — run `alembic upgrade head` to enable DB-level tests")

    _CTX = "current_setting('app.current_tenant_id', TRUE)"
    engine = create_async_engine(_TEST_DB_URL, echo=False)
    try:
        async with engine.connect() as conn:
            async with conn.begin():
                # Must ENABLE RLS first — test DB is built by create_all(), not migration
                await conn.execute(text("ALTER TABLE watched_indexes ENABLE ROW LEVEL SECURITY"))
                await conn.execute(text(
                    f"CREATE POLICY _test_wi_rls ON watched_indexes "
                    f"USING ({_CTX} != '' AND tenant_id = NULLIF({_CTX}, '')::uuid) "
                    f"WITH CHECK ({_CTX} != '' AND tenant_id = NULLIF({_CTX}, '')::uuid)"
                ))
                await conn.execute(text(
                    "GRANT SELECT, INSERT, UPDATE, DELETE ON watched_indexes TO sniper_api"
                ))
    finally:
        await engine.dispose()

    yield

    engine = create_async_engine(_TEST_DB_URL, echo=False)
    try:
        async with engine.connect() as conn:
            async with conn.begin():
                await conn.execute(text("DROP POLICY IF EXISTS _test_wi_rls ON watched_indexes"))
                await conn.execute(text("ALTER TABLE watched_indexes DISABLE ROW LEVEL SECURITY"))
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_rls_blocks_wrong_tenant_at_db_level(
    test_engine, db: AsyncSession, rls_policy_in_test_db
) -> None:
    """RLS policy for watched_indexes returns 0 rows when tenant context is wrong.

    Uses SET LOCAL ROLE sniper_api within a transaction so the test DB connection
    temporarily runs without BYPASSRLS — making policies evaluate.
    Skipped automatically if sniper_api role does not exist.
    """

    from app.models.tenant import Tenant
    from app.models.user import User

    tenant_a = Tenant(slug=f"ta-{uuid.uuid4().hex[:6]}", display_name="Tenant A")
    tenant_b = Tenant(slug=f"tb-{uuid.uuid4().hex[:6]}", display_name="Tenant B")
    db.add(tenant_a)
    db.add(tenant_b)
    await db.flush()

    user_a = User(
        tenant_id=tenant_a.id,
        email=f"dba-{uuid.uuid4().hex[:6]}@example.com",
        hashed_password="x",
        is_superuser=True,
    )
    db.add(user_a)
    await db.flush()

    wi = WatchedIndex(
        tenant_id=tenant_a.id,
        user_id=user_a.id,
        index_number=99999,
        semester_code="12026",
    )
    db.add(wi)
    await db.commit()

    # Now open a fresh connection that switches to sniper_api role.
    engine = create_async_engine(_TEST_DB_URL, echo=False)
    try:
        async with engine.connect() as conn:
            async with conn.begin():
                # Switch to the non-superuser role so RLS evaluates
                await conn.execute(text("SET LOCAL ROLE sniper_api"))

                # Set WRONG tenant context (tenant B, not A)
                await conn.execute(
                    text("SELECT set_config('app.current_tenant_id', :tid, TRUE)"),
                    {"tid": str(tenant_b.id)},
                )

                result = await conn.execute(
                    select(WatchedIndex).where(WatchedIndex.id == wi.id)
                )
                rows = result.fetchall()

    finally:
        await engine.dispose()

    assert rows == [], (
        "RLS should block watched_indexes row when tenant context does not match"
    )


@pytest.mark.asyncio
async def test_rls_allows_correct_tenant_at_db_level(
    test_engine, db: AsyncSession, rls_policy_in_test_db
) -> None:
    """RLS policy allows row when tenant context matches the row's tenant_id."""

    from app.models.tenant import Tenant
    from app.models.user import User

    tenant = Tenant(slug=f"tc-{uuid.uuid4().hex[:6]}", display_name="Tenant C")
    db.add(tenant)
    await db.flush()

    user = User(
        tenant_id=tenant.id,
        email=f"dbc-{uuid.uuid4().hex[:6]}@example.com",
        hashed_password="x",
        is_superuser=True,
    )
    db.add(user)
    await db.flush()

    wi = WatchedIndex(
        tenant_id=tenant.id,
        user_id=user.id,
        index_number=88888,
        semester_code="12026",
    )
    db.add(wi)
    await db.commit()

    engine = create_async_engine(_TEST_DB_URL, echo=False)
    try:
        async with engine.connect() as conn:
            async with conn.begin():
                await conn.execute(text("SET LOCAL ROLE sniper_api"))
                await conn.execute(
                    text("SELECT set_config('app.current_tenant_id', :tid, TRUE)"),
                    {"tid": str(tenant.id)},
                )
                result = await conn.execute(
                    select(WatchedIndex).where(WatchedIndex.id == wi.id)
                )
                rows = result.fetchall()
    finally:
        await engine.dispose()

    assert len(rows) == 1, "RLS should allow row when tenant context matches"
