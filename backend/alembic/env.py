import asyncio
import logging
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

# Import Base and ALL models so metadata is fully populated for autogenerate.
# If a model is not imported here, alembic revision --autogenerate will miss it.
from app.db.base import Base
import app.models  # noqa: F401 — side-effect import registers all models on Base.metadata
from app.core.config import settings

logger = logging.getLogger("alembic.env")

# Alembic Config object — gives access to values in alembic.ini
alembic_config = context.config

# Inject DATABASE_URL from app settings so the secret never lives in alembic.ini
alembic_config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if alembic_config.config_file_name is not None:
    fileConfig(alembic_config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no live DB connection, emit SQL to stdout)."""
    url = alembic_config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations using an async engine.

    NullPool is MANDATORY here — Alembic manages its own connection lifecycle
    outside any asyncio event loop. Using a regular connection pool across
    event loop boundaries causes errors and potential connection leaks.
    """
    connectable = async_engine_from_config(
        alembic_config.get_section(alembic_config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
