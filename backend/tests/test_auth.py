"""Integration tests for /api/auth endpoints."""

import uuid

import pytest
from httpx import AsyncClient


def _unique_email(tag: str = "") -> str:
    suffix = uuid.uuid4().hex[:8]
    return f"user-{tag or suffix}@example.com"


async def _register(client: AsyncClient, email: str | None = None, password: str = "securepass123"):
    return await client.post(
        "/api/auth/register",
        json={"email": email or _unique_email(), "password": password},
    )


async def _login(client: AsyncClient, email: str, password: str = "securepass123"):
    return await client.post("/api/auth/login", json={"email": email, "password": password})


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    r = await _register(client)
    assert r.status_code == 201
    data = r.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    email = _unique_email("dup")
    await _register(client, email=email)
    r = await _register(client, email=email)
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_register_password_too_short(client: AsyncClient):
    r = await client.post(
        "/api/auth/register",
        json={"email": _unique_email("short"), "password": "short"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_register_invalid_email(client: AsyncClient):
    r = await client.post(
        "/api/auth/register",
        json={"email": "not-an-email", "password": "securepass123"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    email = _unique_email("login")
    await _register(client, email=email)
    r = await _login(client, email)
    assert r.status_code == 200
    assert "access_token" in r.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    email = _unique_email("wrongpw")
    await _register(client, email=email)
    r = await client.post("/api/auth/login", json={"email": email, "password": "wrongpassword"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email(client: AsyncClient):
    r = await _login(client, "nobody-xyz@example.com")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_me_success(client: AsyncClient):
    email = _unique_email("me")
    reg = await _register(client, email=email)
    token = reg.json()["access_token"]
    r = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == email
    assert data["is_superuser"] is True
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_me_no_token(client: AsyncClient):
    r = await client.get("/api/auth/me")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_me_invalid_token(client: AsyncClient):
    r = await client.get("/api/auth/me", headers={"Authorization": "Bearer invalidtoken"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_refresh_success(client: AsyncClient):
    reg = await _register(client)
    refresh = reg.json()["refresh_token"]
    r = await client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert r.status_code == 200
    assert "access_token" in r.json()
    # Refresh token is rotated
    assert r.json()["refresh_token"] != refresh


@pytest.mark.asyncio
async def test_refresh_invalid_token(client: AsyncClient):
    r = await client.post("/api/auth/refresh", json={"refresh_token": "fake-token"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_rotation(client: AsyncClient):
    """After using a refresh token, the old one must be invalid."""
    reg = await _register(client)
    old_refresh = reg.json()["refresh_token"]
    r = await client.post("/api/auth/refresh", json={"refresh_token": old_refresh})
    assert r.status_code == 200

    r2 = await client.post("/api/auth/refresh", json={"refresh_token": old_refresh})
    assert r2.status_code == 401


@pytest.mark.asyncio
async def test_logout_invalidates_refresh_token(client: AsyncClient):
    reg = await _register(client)
    refresh = reg.json()["refresh_token"]

    r = await client.post("/api/auth/logout", json={"refresh_token": refresh})
    assert r.status_code == 204

    r2 = await client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert r2.status_code == 401
