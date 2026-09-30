"""Alembic environment for the advisor schema.

Keeps its own version table inside the `advisor` schema so this migration
history never collides with the sniper backend's history in the same database.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import text

import advisor.models  # noqa: F401  (registers tables on Base.metadata)
from advisor.db import SCHEMA, Base, make_engine

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def include_name(name, type_, parent_names):
    if type_ == "schema":
        return name == SCHEMA
    return True


def run_migrations_offline() -> None:
    raise SystemExit("Offline mode is not supported; set ADVISOR_DATABASE_URL and run online.")


def run_migrations_online() -> None:
    engine = make_engine(config.attributes.get("database_url"))
    with engine.connect() as connection:
        connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"'))
        connection.commit()
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table="alembic_version",
            version_table_schema=SCHEMA,
            include_schemas=True,
            include_name=include_name,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
