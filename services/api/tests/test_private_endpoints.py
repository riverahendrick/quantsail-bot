from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient

from app.db.models import EquitySnapshot, Event, Trade, User
from app.db.queries import list_equity_snapshots
from app.main import app
from app.public.rate_limit import reset_rate_limiter


def _authorized_client(
    engine: sa.Engine, monkeypatch: pytest.MonkeyPatch, role: str = "OWNER"
) -> TestClient:
    """Return a TestClient authorized with the given role."""
    reset_rate_limiter()
    email = f"{role.lower()}@example.com"
    with engine.begin() as conn:
        conn.execute(sa.insert(User).values(id=uuid.uuid4(), email=email, role=role))

    def _verify(_: str) -> dict[str, str]:
        """Return a fixed decoded token payload."""
        return {"uid": "firebase-uid", "email": email}

    monkeypatch.setattr("app.auth.dependencies.verify_firebase_token", _verify)
    return TestClient(app, headers={"Authorization": "Bearer token"})


def _insert_trade(engine: sa.Engine) -> None:
    """Insert a trade row for private endpoint tests."""
    with engine.begin() as conn:
        conn.execute(
            sa.insert(Trade).values(
                id=uuid.uuid4(),
                symbol="BTC/USDT",
                side="LONG",
                status="OPEN",
                mode="DRY_RUN",
                opened_at=datetime(2026, 1, 27, tzinfo=timezone.utc),
                entry_price=Decimal("100.00"),
                entry_qty=Decimal("0.10"),
                entry_notional_usd=Decimal("10.00"),
                stop_price=Decimal("90.00"),
                take_profit_price=Decimal("120.00"),
                trailing_enabled=False,
            )
        )


def _insert_event(engine: sa.Engine) -> None:
    """Insert an event row for private endpoint tests."""
    with engine.begin() as conn:
        conn.execute(
            sa.insert(Event).values(
                id=uuid.uuid4(),
                ts=datetime(2026, 1, 27, tzinfo=timezone.utc),
                level="INFO",
                type="trade.opened",
                symbol="BTC/USDT",
                payload={"message": "opened"},
                public_safe=False,
            )
        )


def _insert_snapshot(engine: sa.Engine) -> None:
    """Insert an equity snapshot row for private endpoint tests."""
    with engine.begin() as conn:
        conn.execute(
            sa.insert(EquitySnapshot).values(
                id=uuid.uuid4(),
                ts=datetime(2026, 1, 27, tzinfo=timezone.utc),
                equity_usd=Decimal("1100"),
                cash_usd=Decimal("900"),
                unrealized_pnl_usd=Decimal("200"),
                realized_pnl_today_usd=Decimal("50"),
                open_positions=1,
            )
        )


def test_private_db_health(migrated_engine: sa.Engine, monkeypatch: pytest.MonkeyPatch) -> None:
    """Return ok when the DB connection is healthy."""
    client = _authorized_client(migrated_engine, monkeypatch)

    response = client.get("/v1/health/db")

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_private_status_returns_env(
    migrated_engine: sa.Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Return the configured BOT_STATUS value."""
    monkeypatch.setenv("BOT_STATUS", "running")
    client = _authorized_client(migrated_engine, monkeypatch)

    response = client.get("/v1/status")

    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_private_trades_returns_rows(
    migrated_engine: sa.Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Return trades with full fields."""
    _insert_trade(migrated_engine)
    client = _authorized_client(migrated_engine, monkeypatch)

    response = client.get("/v1/trades")

    assert response.status_code == 200
    trades = response.json()
    assert len(trades) == 1
    assert trades[0]["symbol"] == "BTC/USDT"
    assert "id" in trades[0]


def test_private_events_returns_rows(
    migrated_engine: sa.Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Return events with full fields."""
    _insert_event(migrated_engine)
    client = _authorized_client(migrated_engine, monkeypatch)

    response = client.get("/v1/events")

    assert response.status_code == 200
    events = response.json()
    assert len(events) == 1
    assert events[0]["type"] == "trade.opened"


def test_private_equity_returns_rows(
    migrated_engine: sa.Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Return equity snapshots with full fields."""
    _insert_snapshot(migrated_engine)
    client = _authorized_client(migrated_engine, monkeypatch)

    response = client.get("/v1/equity")

    assert response.status_code == 200
    snapshots = response.json()
    assert len(snapshots) == 1
    assert snapshots[0]["equity_usd"] == 1100


def test_list_equity_snapshots_limit(migrated_engine: sa.Engine) -> None:
    """Respect the list limit for equity snapshots."""
    _insert_snapshot(migrated_engine)
    _insert_snapshot(migrated_engine)

    snapshots = list_equity_snapshots(migrated_engine, limit=1)

    assert len(snapshots) == 1
