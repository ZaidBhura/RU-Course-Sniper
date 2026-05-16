from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from app.core.config import settings
from app.core.logging import configure_logging
from app.core.rate_limit import limiter
from app.db.session import engine
from app.middleware.request_logging import RequestLoggingMiddleware
from app.routers import admin, auth, channels, health, logs, watchlist

configure_logging()

if settings.SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        send_default_pii=False,
        traces_sample_rate=0.1 if settings.ENVIRONMENT == "production" else 0.0,
        integrations=[FastApiIntegration(), SqlalchemyIntegration()],
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
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

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # RequestLoggingMiddleware must wrap before CORS so request_id is set first.
    app.add_middleware(RequestLoggingMiddleware)

    allowed_origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix="/api")
    app.include_router(auth.router, prefix="/api")
    app.include_router(watchlist.router, prefix="/api")
    app.include_router(channels.router, prefix="/api")
    app.include_router(logs.router, prefix="/api")
    app.include_router(admin.router, prefix="/api")

    return app


app = create_app()
