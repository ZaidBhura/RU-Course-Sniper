"""Integration tests for /api/watchlist endpoints."""

import uuid

import pytest
from httpx import AsyncClient


def _unique_email(tag: str = "") -> str:
    suffix = uuid.uuid4().hex[:8]
    return f"wl-{tag or suffix}@example.com"


async def _auth_headers(client: AsyncClient, email: str | None = None) -> dict:
    email = email or _unique_email()
    r = await client.post("/api/auth/register", json={"email": email, "password": "securepass123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.mark.asyncio
async def test_list_empty(client: AsyncClient):
    headers = await _auth_headers(client)
    r = await client.get("/api/watchlist/", headers=headers)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_create_watched_index(client: AsyncClient):
    headers = await _auth_headers(client)
    r = await client.post(
        "/api/watchlist/",
        json={"index_number": 12345, "label": "Intro CS", "semester_code": "12026"},
        headers=headers,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["index_number"] == 12345
    assert data["label"] == "Intro CS"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_create_duplicate_rejected(client: AsyncClient):
    headers = await _auth_headers(client)
    payload = {"index_number": 11111, "semester_code": "12026"}
    await client.post("/api/watchlist/", json=payload, headers=headers)
    r = await client.post("/api/watchlist/", json=payload, headers=headers)
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_create_invalid_index_number(client: AsyncClient):
    headers = await _auth_headers(client)
    r = await client.post(
        "/api/watchlist/", json={"index_number": 0, "semester_code": "12026"}, headers=headers
    )
    assert r.status_code == 422

    r2 = await client.post(
        "/api/watchlist/", json={"index_number": 100000, "semester_code": "12026"}, headers=headers
    )
    assert r2.status_code == 422


@pytest.mark.asyncio
async def test_create_invalid_semester_code(client: AsyncClient):
    headers = await _auth_headers(client)
    r = await client.post(
        "/api/watchlist/",
        json={"index_number": 12345, "semester_code": "abc"},
        headers=headers,
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_patch_label(client: AsyncClient):
    headers = await _auth_headers(client)
    create = await client.post(
        "/api/watchlist/", json={"index_number": 55555, "semester_code": "12026"}, headers=headers
    )
    wi_id = create.json()["id"]

    r = await client.patch(f"/api/watchlist/{wi_id}", json={"label": "Updated"}, headers=headers)
    assert r.status_code == 200
    assert r.json()["label"] == "Updated"


@pytest.mark.asyncio
async def test_patch_is_active(client: AsyncClient):
    headers = await _auth_headers(client)
    create = await client.post(
        "/api/watchlist/", json={"index_number": 44444, "semester_code": "12026"}, headers=headers
    )
    wi_id = create.json()["id"]

    r = await client.patch(
        f"/api/watchlist/{wi_id}", json={"is_active": False}, headers=headers
    )
    assert r.status_code == 200
    assert r.json()["is_active"] is False


@pytest.mark.asyncio
async def test_delete_soft_deletes(client: AsyncClient):
    headers = await _auth_headers(client)
    create = await client.post(
        "/api/watchlist/", json={"index_number": 33333, "semester_code": "12026"}, headers=headers
    )
    wi_id = create.json()["id"]

    r = await client.delete(f"/api/watchlist/{wi_id}", headers=headers)
    assert r.status_code == 204

    # Soft-deleted items are hidden from the list (is_active=False filtered out).
    list_r = await client.get("/api/watchlist/", headers=headers)
    items = list_r.json()
    match = next((i for i in items if i["id"] == wi_id), None)
    assert match is None


@pytest.mark.asyncio
async def test_delete_not_found(client: AsyncClient):
    headers = await _auth_headers(client)
    r = await client.delete(f"/api/watchlist/{uuid.uuid4()}", headers=headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_tenant_isolation(client: AsyncClient):
    """User A cannot see or modify user B's watchlist items."""
    headers_a = await _auth_headers(client, _unique_email("iso-a"))
    headers_b = await _auth_headers(client, _unique_email("iso-b"))

    create = await client.post(
        "/api/watchlist/",
        json={"index_number": 22222, "semester_code": "12026"},
        headers=headers_a,
    )
    wi_id = create.json()["id"]

    list_r = await client.get("/api/watchlist/", headers=headers_b)
    assert all(i["id"] != wi_id for i in list_r.json())

    patch_r = await client.patch(
        f"/api/watchlist/{wi_id}", json={"label": "hack"}, headers=headers_b
    )
    assert patch_r.status_code == 404

    del_r = await client.delete(f"/api/watchlist/{wi_id}", headers=headers_b)
    assert del_r.status_code == 404


@pytest.mark.asyncio
async def test_unauthenticated_rejected(client: AsyncClient):
    r = await client.get("/api/watchlist/")
    assert r.status_code == 401
