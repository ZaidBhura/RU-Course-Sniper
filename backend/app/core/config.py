from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        # Never expose secrets in repr() / model_dump() without explicit request
    )

    # Database — must use postgresql+asyncpg:// driver prefix
    DATABASE_URL: str = Field(repr=False)
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Secrets — repr=False prevents accidental logging via str(settings)
    SECRET_KEY: str = Field(repr=False)
    FERNET_KEY: str = Field(repr=False)  # Generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

    # Auth
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Application
    ENVIRONMENT: str = "development"  # "development" | "staging" | "production"
    LOG_LEVEL: str = "INFO"
    SENTRY_DSN: str | None = None


settings = Settings()
