from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

_echo = settings.ENVIRONMENT == "development"

# Admin pool — superuser, bypasses RLS. Used only by auth routes (login/register/refresh)
# that must query users by email before any tenant identity is established.
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_timeout=30,
    pool_pre_ping=True,
    echo=_echo,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# API pool — uses sniper_api role (NOBYPASSRLS) in production, falls back to admin pool in dev.
# All authenticated routes use this pool so RLS policies are evaluated.
_api_url = settings.API_DATABASE_URL or settings.DATABASE_URL
_api_engine = create_async_engine(
    _api_url,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_timeout=30,
    pool_pre_ping=True,
    echo=_echo,
)

_ApiSessionLocal = async_sessionmaker(
    bind=_api_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Admin session — superuser pool. Use only for auth routes."""
    async with AsyncSessionLocal() as session:
        yield session


async def get_api_db() -> AsyncGenerator[AsyncSession, None]:
    """API session — sniper_api pool in production, admin pool in dev.

    get_current_user sets SET LOCAL app.current_tenant_id on this session.
    FastAPI caches this dependency per request, so the session (and its RLS
    context) is shared between the auth dependency and the route handler.
    """
    async with _ApiSessionLocal() as session:
        yield session
