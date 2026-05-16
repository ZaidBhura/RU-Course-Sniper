"""pytest fixtures for the RU Course Sniper backend test suite.

Strategy:
- Schema is created/dropped once per session via a SYNC engine (psycopg2) to avoid
  asyncpg event-loop-scope issues when the schema fixture is session-scoped.
- Each test gets a fresh ASYNC engine (asyncpg) so its connection pool is tied to the
  correct function-scoped event loop — eliminates "future attached to different loop".
- Each HTTP request through `client` gets its own managed session (real commits).
  Tests use unique email addresses for isolation.
- The `db` fixture yields a rolled-back session for direct ORM tests.
"""

import pytest
import pytest_asyncio
from fakeredis import aioredis as fake_aioredis
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_redis
from app.core.config import settings
from app.db.base import Base
from app.db.session import get_api_db, get_db
from app.main import create_app

# If DATABASE_URL already points at a *_test database (e.g. in CI), use it
# as-is.  In local dev it points at the main 'course_sniper' database, so we
# derive a separate 'course_sniper_test' URL to avoid touching dev data.
_raw_url = settings.DATABASE_URL
TEST_DATABASE_URL = (
    _raw_url
    if _raw_url.rsplit("/", 1)[-1].endswith("_test")
    else _raw_url.replace("/course_sniper", "/course_sniper_test")
)
SYNC_TEST_DATABASE_URL = TEST_DATABASE_URL.replace("+asyncpg", "+psycopg2")


@pytest.fixture(scope="session")
def create_test_schema():
    """Create schema once per session using a sync engine; drop on teardown."""
    engine = create_engine(SYNC_TEST_DATABASE_URL, echo=False)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest_asyncio.fixture
async def test_engine(create_test_schema):
    """Per-test async engine — tied to the test function's event loop."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db(test_engine) -> AsyncSession:
    """Yield a session that is rolled back after the test (for ORM-level tests)."""
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False, autoflush=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture(autouse=True)
def reset_rate_limits():
    """Clear slowapi in-memory counters before each test to prevent cross-test interference."""
    from app.core.rate_limit import limiter as _limiter
    _limiter._storage.reset()
    yield


@pytest.fixture
def fake_redis():
    """In-memory async Redis compatible with redis.asyncio."""
    return fake_aioredis.FakeRedis(decode_responses=True)


@pytest_asyncio.fixture
async def client(test_engine, fake_redis) -> AsyncClient:
    """AsyncClient where each HTTP request gets its own managed session.

    Tests must use unique email addresses since commits are real and
    data persists within the test session.
    """
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False, autoflush=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_api_db] = override_get_db
    app.dependency_overrides[get_redis] = lambda: fake_redis
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
