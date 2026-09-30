"""Settings come from the environment only. No secrets in code."""

from __future__ import annotations

import os


class ConfigError(RuntimeError):
    pass


def database_url() -> str:
    url = os.environ.get("ADVISOR_DATABASE_URL", "").strip()
    if not url:
        raise ConfigError(
            "ADVISOR_DATABASE_URL is not set, e.g. "
            "postgresql+psycopg://advisor:<password>@localhost:5433/advisor"
        )
    return url
