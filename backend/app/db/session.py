from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,  # must start with postgresql+asyncpg://
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_timeout=30,
    pool_pre_ping=True,
    # SECURITY: echo=True logs full SQL including WHERE clause values.
    # Never enable in production — only in local development.
    echo=settings.ENVIRONMENT == "development",
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # MANDATORY with async: avoids MissingGreenlet on lazy load
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a database session per request.

    The session is rolled back automatically on exception and closed on exit.
    Application-level tenant_id filtering is enforced at the query layer (M1).
    PostgreSQL RLS will enforce it at the database layer in M5.
    """
    async with AsyncSessionLocal() as session:
        yield session
