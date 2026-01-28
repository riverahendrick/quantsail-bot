import os
import sys
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.config import Config

from alembic import command

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))


def _alembic_config() -> Config:
    """Return the Alembic config for the API project."""
    return Config(PROJECT_ROOT / "alembic.ini")


def _get_database_url() -> str:
    """Load the database URL using the app helper."""
    from app.db.engine import get_database_url

    return get_database_url()


@pytest.fixture(scope="session")
def database_url() -> str:
    """Return the DATABASE_URL for integration tests."""
    return _get_database_url()


@pytest.fixture(scope="session")
def migrated_engine(database_url: str) -> sa.Engine:
    """Apply migrations and return a SQLAlchemy engine."""
    os.environ["DATABASE_URL"] = database_url
    command.upgrade(_alembic_config(), "head")
    return sa.create_engine(database_url, future=True)


@pytest.fixture(autouse=True)
def _truncate_tables(request: pytest.FixtureRequest) -> None:
    """Reset all tables before tests that use migrated_engine."""
    if "migrated_engine" not in request.fixturenames:
        return

    engine: sa.Engine = request.getfixturevalue("migrated_engine")
    tables = [
        "events",
        "orders",
        "trades",
        "equity_snapshots",
        "bot_config_versions",
        "exchange_keys",
        "users",
    ]
    with engine.begin() as conn:
        conn.execute(sa.text(f"TRUNCATE {', '.join(tables)} RESTART IDENTITY CASCADE"))
