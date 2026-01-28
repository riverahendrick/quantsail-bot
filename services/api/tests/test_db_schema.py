from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import cast

import pytest
import sqlalchemy as sa
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from alembic import command
from app.db.engine import get_database_url
from app.db.models import BotConfigVersion, ExchangeKey, User
from app.main import app


def _alembic_config() -> Config:
    """Build an Alembic Config pointing at the local alembic.ini."""
    project_root = Path(__file__).resolve().parents[1]
    return Config(project_root / "alembic.ini")


def _require_database_url() -> str:
    """Return DATABASE_URL or raise when missing."""
    value = os.environ.get("DATABASE_URL")
    if not value:
        raise RuntimeError("DATABASE_URL must be set for integration tests.")
    return value


def test_database_url_requires_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail fast when DATABASE_URL is missing."""
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        get_database_url()


def test_require_database_url_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure DATABASE_URL helper fails fast without configuration."""
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        _require_database_url()


def test_require_database_url_present(monkeypatch: pytest.MonkeyPatch) -> None:
    """Return DATABASE_URL when configured."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://example")

    assert _require_database_url() == "postgresql://example"


def test_alembic_requires_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail alembic commands when DATABASE_URL is missing."""
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        command.upgrade(_alembic_config(), "head", sql=True)


def test_alembic_offline_upgrade_generates_sql(database_url: str) -> None:
    """Run an offline upgrade to cover alembic env/migration paths."""
    os.environ["DATABASE_URL"] = database_url
    command.upgrade(_alembic_config(), "head", sql=True)


def test_alembic_offline_downgrade_generates_sql(database_url: str) -> None:
    """Run an offline downgrade to cover migration downgrade paths."""
    os.environ["DATABASE_URL"] = database_url
    command.downgrade(_alembic_config(), "head:base", sql=True)


def test_schema_tables_and_columns_exist(migrated_engine: sa.Engine) -> None:
    """Ensure required tables and columns exist with correct types."""
    expected = cast(
        dict[str, dict[str, dict[str, object]]],
        {
            "users": {
                "id": {"udt_name": "uuid", "is_nullable": "NO"},
                "email": {"udt_name": "text", "is_nullable": "NO"},
                "role": {"udt_name": "text", "is_nullable": "NO"},
                "created_at": {"udt_name": "timestamptz", "is_nullable": "NO"},
        },
        "exchange_keys": {
            "id": {"udt_name": "uuid", "is_nullable": "NO"},
            "exchange": {"udt_name": "text", "is_nullable": "NO"},
            "label": {"udt_name": "text", "is_nullable": "YES"},
            "ciphertext": {"udt_name": "bytea", "is_nullable": "NO"},
            "nonce": {"udt_name": "bytea", "is_nullable": "NO"},
            "key_version": {"udt_name": "int4", "is_nullable": "NO"},
            "created_by": {"udt_name": "uuid", "is_nullable": "YES"},
            "created_at": {"udt_name": "timestamptz", "is_nullable": "NO"},
            "is_active": {"udt_name": "bool", "is_nullable": "NO"},
            "revoked_at": {"udt_name": "timestamptz", "is_nullable": "YES"},
        },
        "bot_config_versions": {
            "id": {"udt_name": "uuid", "is_nullable": "NO"},
            "version": {"udt_name": "int4", "is_nullable": "NO"},
            "config_json": {"udt_name": "jsonb", "is_nullable": "NO"},
            "config_hash": {"udt_name": "text", "is_nullable": "NO"},
            "created_by": {"udt_name": "uuid", "is_nullable": "YES"},
            "created_at": {"udt_name": "timestamptz", "is_nullable": "NO"},
            "activated_at": {"udt_name": "timestamptz", "is_nullable": "YES"},
            "is_active": {"udt_name": "bool", "is_nullable": "NO"},
        },
        "trades": {
            "id": {"udt_name": "uuid", "is_nullable": "NO"},
            "symbol": {"udt_name": "text", "is_nullable": "NO"},
            "side": {"udt_name": "text", "is_nullable": "NO"},
            "status": {"udt_name": "text", "is_nullable": "NO"},
            "mode": {"udt_name": "text", "is_nullable": "NO"},
            "opened_at": {"udt_name": "timestamptz", "is_nullable": "NO"},
            "closed_at": {"udt_name": "timestamptz", "is_nullable": "YES"},
            "entry_price": {
                "udt_name": "numeric",
                "numeric_precision": 24,
                "numeric_scale": 10,
                "is_nullable": "NO",
            },
            "entry_qty": {
                "udt_name": "numeric",
                "numeric_precision": 24,
                "numeric_scale": 10,
                "is_nullable": "NO",
            },
            "entry_notional_usd": {
                "udt_name": "numeric",
                "numeric_precision": 24,
                "numeric_scale": 10,
                "is_nullable": "NO",
            },
            "stop_price": {
                "udt_name": "numeric",
                "numeric_precision": 24,
                "numeric_scale": 10,
                "is_nullable": "NO",
            },
            "take_profit_price": {
                "udt_name": "numeric",
                "numeric_precision": 24,
                "numeric_scale": 10,
                "is_nullable": "NO",
            },
            "trailing_enabled": {"udt_name": "bool", "is_nullable": "NO"},
            "trailing_offset": {
                "udt_name": "numeric",
                "numeric_precision": 24,
                "numeric_scale": 10,
                "is_nullable": "YES",
            },
            "exit_price": {
                "udt_name": "numeric",
                "numeric_precision": 24,
                "numeric_scale": 10,
                "is_nullable": "YES",
            },
            "realized_pnl_usd": {
                "udt_name": "numeric",
                "numeric_precision": 24,
                "numeric_scale": 10,
                "is_nullable": "YES",
            },
            "fees_paid_usd": {
                "udt_name": "numeric",
                "numeric_precision": 24,
                "numeric_scale": 10,
                "is_nullable": "YES",
            },
            "slippage_est_usd": {
                "udt_name": "numeric",
                "numeric_precision": 24,
                "numeric_scale": 10,
                "is_nullable": "YES",
            },
            "notes": {"udt_name": "jsonb", "is_nullable": "YES"},
        },
        "orders": {
            "id": {"udt_name": "uuid", "is_nullable": "NO"},
            "trade_id": {"udt_name": "uuid", "is_nullable": "NO"},
            "symbol": {"udt_name": "text", "is_nullable": "NO"},
            "side": {"udt_name": "text", "is_nullable": "NO"},
            "order_type": {"udt_name": "text", "is_nullable": "NO"},
            "qty": {
                "udt_name": "numeric",
                "numeric_precision": 24,
                "numeric_scale": 10,
                "is_nullable": "NO",
            },
            "price": {
                "udt_name": "numeric",
                "numeric_precision": 24,
                "numeric_scale": 10,
                "is_nullable": "YES",
            },
            "status": {"udt_name": "text", "is_nullable": "NO"},
            "exchange_order_id": {"udt_name": "text", "is_nullable": "YES"},
            "idempotency_key": {"udt_name": "text", "is_nullable": "YES"},
            "created_at": {"udt_name": "timestamptz", "is_nullable": "NO"},
            "updated_at": {"udt_name": "timestamptz", "is_nullable": "NO"},
        },
        "equity_snapshots": {
            "id": {"udt_name": "uuid", "is_nullable": "NO"},
            "ts": {"udt_name": "timestamptz", "is_nullable": "NO"},
            "equity_usd": {
                "udt_name": "numeric",
                "numeric_precision": 24,
                "numeric_scale": 10,
                "is_nullable": "NO",
            },
            "cash_usd": {
                "udt_name": "numeric",
                "numeric_precision": 24,
                "numeric_scale": 10,
                "is_nullable": "NO",
            },
            "unrealized_pnl_usd": {
                "udt_name": "numeric",
                "numeric_precision": 24,
                "numeric_scale": 10,
                "is_nullable": "NO",
            },
            "realized_pnl_today_usd": {
                "udt_name": "numeric",
                "numeric_precision": 24,
                "numeric_scale": 10,
                "is_nullable": "NO",
            },
            "open_positions": {"udt_name": "int4", "is_nullable": "NO"},
            "meta": {"udt_name": "jsonb", "is_nullable": "YES"},
        },
            "events": {
                "id": {"udt_name": "uuid", "is_nullable": "NO"},
                "seq": {"udt_name": "int8", "is_nullable": "NO"},
                "ts": {"udt_name": "timestamptz", "is_nullable": "NO"},
                "level": {"udt_name": "text", "is_nullable": "NO"},
                "type": {"udt_name": "text", "is_nullable": "NO"},
                "symbol": {"udt_name": "text", "is_nullable": "YES"},
                "trade_id": {"udt_name": "uuid", "is_nullable": "YES"},
                "payload": {"udt_name": "jsonb", "is_nullable": "NO"},
                "public_safe": {"udt_name": "bool", "is_nullable": "NO"},
            },
        },
    )

    query = sa.text(
        """
        SELECT table_name, column_name, udt_name, is_nullable, numeric_precision, numeric_scale
        FROM information_schema.columns
        WHERE table_schema = 'public'
        """
    )
    with migrated_engine.connect() as conn:
        rows = [dict(row) for row in conn.execute(query).mappings().all()]

    lookup: dict[tuple[str, str], dict[str, object]] = {
        (row["table_name"], row["column_name"]): row for row in rows
    }

    for table_name, columns in expected.items():
        for column_name, expectations in columns.items():
            key = (table_name, column_name)
            assert key in lookup, f"Missing column {table_name}.{column_name}"
            for attr, expected_value in expectations.items():
                actual = lookup[key].get(attr)
                assert actual == expected_value, (
                    f"{table_name}.{column_name} {attr} expected {expected_value}, got {actual}"
                )


def test_schema_indexes_exist(migrated_engine: sa.Engine) -> None:
    """Ensure required indexes (including partial/desc) exist."""
    expected: dict[str, dict[str, object]] = {
        "uq_users_email": {"unique": True},
        "uq_bot_config_versions_version": {"unique": True},
        "uq_bot_config_versions_is_active": {"unique": True, "where": "is_active"},
        "uq_exchange_keys_active": {"unique": True, "where": "is_active"},
        "ix_trades_symbol_opened_at": {"desc": "opened_at"},
        "ix_trades_status": {},
        "ix_orders_trade_id": {},
        "ix_orders_symbol_created_at": {"desc": "created_at"},
        "ix_orders_exchange_order_id": {},
        "ix_equity_snapshots_ts": {"desc": "ts"},
        "uq_events_seq": {"unique": True},
        "ix_events_ts": {"desc": "ts"},
        "ix_events_type": {},
        "ix_events_symbol": {},
        "ix_events_public_safe": {},
    }

    query = sa.text(
        """
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE schemaname = 'public'
        """
    )
    with migrated_engine.connect() as conn:
        rows = [dict(row) for row in conn.execute(query).mappings().all()]

    index_defs: dict[str, str] = {
        row["indexname"]: row["indexdef"] for row in rows if row["indexname"]
    }

    for index_name, expectations in expected.items():
        assert index_name in index_defs, f"Missing index {index_name}"
        index_def = index_defs[index_name].lower()
        if expectations.get("unique"):
            assert "unique" in index_def, f"Index {index_name} should be unique"
        if "where" in expectations:
            where_clause = cast(str, expectations["where"])
            assert where_clause in index_def, (
                f"Index {index_name} should include WHERE {where_clause}"
            )
        if "desc" in expectations:
            desc_column = cast(str, expectations["desc"])
            assert f"{desc_column} desc" in index_def, (
                f"Index {index_name} should include {desc_column} DESC"
            )

def test_schema_foreign_keys_exist(migrated_engine: sa.Engine) -> None:
    """Ensure foreign key constraints match the documented schema."""
    expected = {
        ("exchange_keys", "created_by", "users", "id"),
        ("bot_config_versions", "created_by", "users", "id"),
        ("orders", "trade_id", "trades", "id"),
        ("events", "trade_id", "trades", "id"),
    }

    query = sa.text(
        """
        SELECT
            tc.table_name,
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage ccu
            ON ccu.constraint_name = tc.constraint_name
            AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND tc.table_schema = 'public'
        """
    )

    with migrated_engine.connect() as conn:
        rows = conn.execute(query).all()

    found = {
        (row[0], row[1], row[2], row[3])
        for row in rows
        if row[0] and row[1] and row[2] and row[3]
    }

    for entry in expected:
        assert entry in found, f"Missing foreign key {entry}"


def test_exchange_keys_allows_nullable_fields(migrated_engine: sa.Engine) -> None:
    """Accept nullable fields in exchange_keys for optional metadata."""
    table = cast(sa.Table, ExchangeKey.__table__)
    payload = {
        "id": uuid.uuid4(),
        "exchange": "binance",
        "label": None,
        "ciphertext": b"ciphertext",
        "nonce": b"nonce",
        "key_version": 1,
        "created_by": None,
        "is_active": True,
        "revoked_at": None,
    }

    with migrated_engine.begin() as conn:
        conn.execute(sa.delete(table))
        conn.execute(sa.insert(table).values(**payload))
        rows = conn.execute(sa.select(table.c.id)).all()

    assert len(rows) == 1


def test_bot_config_active_unique_index_enforced(migrated_engine: sa.Engine) -> None:
    """Enforce only one active bot config version at a time."""
    table = cast(sa.Table, BotConfigVersion.__table__)

    with migrated_engine.begin() as conn:
        conn.execute(sa.delete(table))
        conn.execute(
            sa.insert(table).values(
                id=uuid.uuid4(),
                version=1,
                config_json={"k": "v"},
                config_hash="hash-1",
                is_active=True,
            )
        )

    with pytest.raises(IntegrityError):
        with migrated_engine.begin() as conn:
            conn.execute(
                sa.insert(table).values(
                    id=uuid.uuid4(),
                    version=2,
                    config_json={"k": "v2"},
                    config_hash="hash-2",
                    is_active=True,
                )
            )


def test_db_health_endpoint(
    migrated_engine: sa.Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Confirm /v1/health/db responds when Postgres is reachable."""
    email = "owner@example.com"
    with migrated_engine.begin() as conn:
        conn.execute(sa.insert(User).values(id=uuid.uuid4(), email=email, role="OWNER"))

    def _verify(_: str) -> dict[str, str]:
        """Return a fixed Firebase token payload."""
        return {"uid": "firebase-uid", "email": email}

    monkeypatch.setattr("app.auth.dependencies.verify_firebase_token", _verify)

    client = TestClient(app, headers={"Authorization": "Bearer token"})
    response = client.get("/v1/health/db")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
