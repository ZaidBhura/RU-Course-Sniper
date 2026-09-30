"""Database tests run against ADVISOR_TEST_DATABASE_URL and are skipped without it.

The URL must point at a throwaway database: the fixture drops and recreates
the `advisor` schema.
"""

import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from advisor.db import SCHEMA, make_engine

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="session")
def db_url():
    url = os.environ.get("ADVISOR_TEST_DATABASE_URL")
    if not url:
        pytest.skip("ADVISOR_TEST_DATABASE_URL not set")
    return url


@pytest.fixture(scope="session")
def alembic_cfg(db_url):
    cfg = Config(os.path.join(ROOT, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(ROOT, "alembic"))
    cfg.attributes["database_url"] = db_url
    return cfg


@pytest.fixture(scope="session")
def migrated_engine(db_url, alembic_cfg):
    engine = make_engine(db_url)
    with engine.begin() as conn:
        conn.execute(text(f'DROP SCHEMA IF EXISTS "{SCHEMA}" CASCADE'))
    command.upgrade(alembic_cfg, "head")
    yield engine
    engine.dispose()
