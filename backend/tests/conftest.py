"""pytest fixtures for the RU Course Sniper backend test suite.

Strategy:
- A session-scoped engine creates/drops all tables once per test run against a
  dedicated test database (course_sniper_test).
- A function-scoped `db` fixture yields a session that is rolled back after each
  test, giving every test a clean slate without recreating the schema.
- A function-scoped `client` fixture overrides the `get_db` dependency so
  FastAPI routes use the same rolled-back session as the test.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app

# Use a separate DB for tests to avoid clobbering dev data
TEST_DATABASE_URL = settings.DATABASE_URL.replace("/course_sniper", "/course_sniper_test")


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create test DB schema once per session, drop on teardown."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db(test_engine) -> AsyncSession:
    """Yield a session that is always rolled back after the test.

    This means every test starts with a clean DB state without needing to
    re-create or truncate tables.
    """
    session_factory = async_sessionmaker(
        test_engine, expire_on_commit=False, autoflush=False
    )
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncClient:
    """AsyncClient with get_db overridden to use the test session."""
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
