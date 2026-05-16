from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        # Never expose secrets in repr() / model_dump() without explicit request
    )

    # Database — async driver for FastAPI (postgresql+asyncpg://)
    DATABASE_URL: str = Field(repr=False)
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    # Sync driver for Celery workers (postgresql+psycopg2://)
    SYNC_DATABASE_URL: str = Field(repr=False)

    # M5: least-privilege role URLs (optional — falls back to DATABASE_URL /
    # SYNC_DATABASE_URL in dev). In prod, point at sniper_api / sniper_worker.
    API_DATABASE_URL: str | None = Field(default=None, repr=False)
    WORKER_DATABASE_URL: str | None = Field(default=None, repr=False)

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Polling
    POLL_INTERVAL_SECONDS: int = 10
    ENRICH_INTERVAL_SECONDS: int = 600
    POLL_LOCK_TTL_SECONDS: int = 15
    SEMESTER_CODE: str = "92026"

    # Secrets — repr=False prevents accidental logging via str(settings)
    SECRET_KEY: str = Field(repr=False)
    # Generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"  # noqa: E501
    FERNET_KEY: str = Field(repr=False)

    # Auth
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    # Comma-separated list of allowed CORS origins
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    # Application
    ENVIRONMENT: str = "development"  # "development" | "staging" | "production"
    LOG_LEVEL: str = "INFO"
    SENTRY_DSN: str | None = None


settings = Settings()
