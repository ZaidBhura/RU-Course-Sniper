"""Integration tests for /api/admin endpoints."""

import uuid

import pytest
from httpx import AsyncClient


def _unique_email(tag: str = "") -> str:
    suffix = uuid.uuid4().hex[:8]
    return f"adm-{tag or suffix}@example.com"


async def _register(client: AsyncClient, email: str | None = None, password: str = "securepass123") -> dict:
    email = email or _unique_email()
    r = await client.post("/api/auth/register", json={"email": email, "password": password})
    assert r.status_code == 201
    return r.json()


async def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_admin_requires_auth(client: AsyncClient):
    r = await client.get("/api/admin/users")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_admin_list_users_as_superuser(client: AsyncClient):
    """Register creates a superuser — they can access admin routes."""
    tokens = await _register(client)
    h = await _headers(tokens["access_token"])

    r = await client.get("/api/admin/users", headers=h)
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert len(r.json()) >= 1


@pytest.mark.asyncio
async def test_admin_list_users_scoped_to_tenant(client: AsyncClient):
    """Admin only sees users within their own tenant."""
    email_a = _unique_email("scope-a")
    email_b = _unique_email("scope-b")
    tokens_a = await _register(client, email=email_a)
    await _register(client, email=email_b)

    ha = await _headers(tokens_a["access_token"])
    users = (await client.get("/api/admin/users", headers=ha)).json()
    user_emails = [u["email"] for u in users]

    assert email_a in user_emails
    assert email_b not in user_emails


@pytest.mark.asyncio
async def test_admin_update_user_is_active(client: AsyncClient):
    tokens = await _register(client)
    ha = await _headers(tokens["access_token"])

    users = (await client.get("/api/admin/users", headers=ha)).json()
    user_id = users[0]["id"]

    r = await client.patch(f"/api/admin/users/{user_id}", json={"is_active": False}, headers=ha)
    assert r.status_code == 200
    assert r.json()["is_active"] is False


@pytest.mark.asyncio
async def test_admin_cannot_modify_other_tenant_user(client: AsyncClient):
    tokens_a = await _register(client)
    tokens_b = await _register(client)
    ha = await _headers(tokens_a["access_token"])

    me_b = (
        await client.get("/api/auth/me", headers=await _headers(tokens_b["access_token"]))
    ).json()
    b_user_id = me_b["id"]

    r = await client.patch(
        f"/api/admin/users/{b_user_id}", json={"is_active": False}, headers=ha
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_admin_list_watchlists(client: AsyncClient):
    tokens = await _register(client)
    h = await _headers(tokens["access_token"])

    await client.post(
        "/api/watchlist/", json={"index_number": 77777, "semester_code": "12026"}, headers=h
    )

    r = await client.get("/api/admin/watchlists", headers=h)
    assert r.status_code == 200
    assert any(i["index_number"] == 77777 for i in r.json())


@pytest.mark.asyncio
async def test_admin_list_logs_returns_list(client: AsyncClient):
    tokens = await _register(client)
    h = await _headers(tokens["access_token"])

    r = await client.get("/api/admin/logs", headers=h)
    assert r.status_code == 200
    assert isinstance(r.json(), list)
