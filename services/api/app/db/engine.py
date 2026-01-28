from __future__ import annotations

import os
from functools import lru_cache

import sqlalchemy as sa


def get_database_url() -> str:
    """Return the Postgres connection URL from the environment."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required to connect to Postgres.")
    return database_url


@lru_cache(maxsize=1)
def get_engine() -> sa.Engine:
    """Create and cache a SQLAlchemy engine for the configured Postgres URL."""
    return sa.create_engine(get_database_url(), future=True)
