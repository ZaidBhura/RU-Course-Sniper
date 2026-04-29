from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from sqlalchemy import text

from app.db.session import engine
from app.routers import health


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: verify DB connectivity on startup, dispose pool on shutdown."""
    async with engine.begin() as conn:
        # Fail fast if DATABASE_URL is wrong — surfaces misconfiguration at startup
        # rather than on the first real request.
        await conn.execute(text("SELECT 1"))
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="RU Course Sniper API",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    app.include_router(health.router, prefix="/api")
    return app


app = create_app()
