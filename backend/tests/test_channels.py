"""Integration tests for /api/channels endpoints."""

import uuid

import pytest
from httpx import AsyncClient


def _unique_email(tag: str = "") -> str:
    suffix = uuid.uuid4().hex[:8]
    return f"ch-{tag or suffix}@example.com"


async def _auth_headers(client: AsyncClient, email: str | None = None) -> dict:
    email = email or _unique_email()
    r = await client.post("/api/auth/register", json={"email": email, "password": "securepass123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.mark.asyncio
async def test_list_empty(client: AsyncClient):
    headers = await _auth_headers(client)
    r = await client.get("/api/channels/", headers=headers)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_create_discord_channel(client: AsyncClient):
    headers = await _auth_headers(client)
    r = await client.post(
        "/api/channels/",
        json={
            "channel_type": "discord",
            "credential": {"webhook_url": "https://discord.com/api/webhooks/123/abc"},
        },
        headers=headers,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["channel_type"] == "discord"
    assert data["is_active"] is True
    assert "credential_blob" not in data
    assert "webhook_url" not in data


@pytest.mark.asyncio
async def test_create_pushover_channel(client: AsyncClient):
    headers = await _auth_headers(client)
    r = await client.post(
        "/api/channels/",
        json={"channel_type": "pushover", "credential": {"token": "tok123", "user_key": "uk456"}},
        headers=headers,
    )
    assert r.status_code == 201
    assert r.json()["channel_type"] == "pushover"


@pytest.mark.asyncio
async def test_create_discord_missing_webhook(client: AsyncClient):
    headers = await _auth_headers(client)
    r = await client.post(
        "/api/channels/",
        json={"channel_type": "discord", "credential": {}},
        headers=headers,
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_pushover_missing_fields(client: AsyncClient):
    headers = await _auth_headers(client)
    r = await client.post(
        "/api/channels/",
        json={"channel_type": "pushover", "credential": {"token": "tok"}},
        headers=headers,
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_invalid_channel_type(client: AsyncClient):
    headers = await _auth_headers(client)
    r = await client.post(
        "/api/channels/",
        json={"channel_type": "slack", "credential": {}},
        headers=headers,
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_duplicate_channel_type_rejected(client: AsyncClient):
    headers = await _auth_headers(client)
    payload = {
        "channel_type": "discord",
        "credential": {"webhook_url": "https://discord.com/api/webhooks/1/x"},
    }
    await client.post("/api/channels/", json=payload, headers=headers)
    r = await client.post("/api/channels/", json=payload, headers=headers)
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_delete_channel(client: AsyncClient):
    headers = await _auth_headers(client)
    create = await client.post(
        "/api/channels/",
        json={
            "channel_type": "discord",
            "credential": {"webhook_url": "https://discord.com/api/webhooks/2/y"},
        },
        headers=headers,
    )
    ch_id = create.json()["id"]

    r = await client.delete(f"/api/channels/{ch_id}", headers=headers)
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_delete_not_found(client: AsyncClient):
    headers = await _auth_headers(client)
    r = await client.delete(f"/api/channels/{uuid.uuid4()}", headers=headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_create_discord_invalid_webhook_url(client: AsyncClient):
    headers = await _auth_headers(client)
    r = await client.post(
        "/api/channels/",
        json={
            "channel_type": "discord",
            "credential": {"webhook_url": "https://evil.com/steal"},
        },
        headers=headers,
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_credential_not_exposed_in_list(client: AsyncClient):
    headers = await _auth_headers(client)
    await client.post(
        "/api/channels/",
        json={
            "channel_type": "discord",
            "credential": {"webhook_url": "https://discord.com/api/webhooks/3/z"},
        },
        headers=headers,
    )
    r = await client.get("/api/channels/", headers=headers)
    for item in r.json():
        assert "webhook_url" not in item
        assert "credential_blob" not in item
        assert "credential" not in item
