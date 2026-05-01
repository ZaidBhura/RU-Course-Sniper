"""Tests for GET /api/health endpoint."""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch


async def test_health_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["db"] == "reachable"


async def test_health_returns_500_when_db_unreachable() -> None:
    """Health check returns 500 when the DB is unreachable."""
    from app.main import create_app
    from app.db.session import get_db
    from sqlalchemy.exc import OperationalError

    async def broken_db():
        mock = AsyncMock()
        mock.execute.side_effect = OperationalError("connection refused", None, None)
        yield mock

    app = create_app()
    app.dependency_overrides[get_db] = broken_db

    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/health")
    assert response.status_code == 500
