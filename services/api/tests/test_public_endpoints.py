from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
import redis
import sqlalchemy as sa
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.db.models import EquitySnapshot, Event, Trade
from app.main import app
from app.public.rate_limit import get_client_ip, reset_rate_limiter


def _configure_rate_limit(
    monkeypatch: pytest.MonkeyPatch,
    limit: int,
    redis_url: str | None,
    window_seconds: int = 60,
) -> None:
    """Configure rate limit settings for a test run."""
    monkeypatch.setenv("PUBLIC_RATE_LIMIT_PER_MIN", str(limit))
    monkeypatch.setenv("PUBLIC_RATE_LIMIT_WINDOW_SECONDS", str(window_seconds))
    if redis_url:
        monkeypatch.setenv("REDIS_URL", redis_url)
    else:
        monkeypatch.delenv("REDIS_URL", raising=False)
    reset_rate_limiter()


def _flush_redis(redis_url: str) -> None:
    """Clear Redis state for rate limit tests."""
    client = redis.Redis.from_url(redis_url)
    client.flushdb()


def _insert_trade(engine: sa.Engine) -> None:
    """Insert a sample trade row."""
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


def _insert_events(engine: sa.Engine) -> None:
    """Insert public and private events."""
    with engine.begin() as conn:
        conn.execute(
            sa.insert(Event).values(
                id=uuid.uuid4(),
                ts=datetime(2026, 1, 27, tzinfo=timezone.utc),
                level="INFO",
                type="trade.opened",
                symbol="BTC/USDT",
                payload={
                    "message": "opened",
                    "exchange_order_id": "secret",
                    "idempotency_key": "secret",
                    "ciphertext": "secret",
                    "nonce": "secret",
                    "api_key": "secret",
                    "secret": "secret",
                    "key_hint": "secret",
                },
                public_safe=True,
            )
        )
        conn.execute(
            sa.insert(Event).values(
                id=uuid.uuid4(),
                ts=datetime(2026, 1, 27, tzinfo=timezone.utc),
                level="INFO",
                type="trade.note",
                symbol="BTC/USDT",
                payload=["list", "payload"],
                public_safe=True,
            )
        )
        conn.execute(
            sa.insert(Event).values(
                id=uuid.uuid4(),
                ts=datetime(2026, 1, 27, tzinfo=timezone.utc),
                level="WARN",
                type="trade.rejected",
                symbol="BTC/USDT",
                payload={"message": "blocked"},
                public_safe=False,
            )
        )


def _insert_snapshots(engine: sa.Engine) -> None:
    """Insert two equity snapshots for summary tests."""
    with engine.begin() as conn:
        conn.execute(
            sa.insert(EquitySnapshot).values(
                id=uuid.uuid4(),
                ts=datetime(2026, 1, 26, tzinfo=timezone.utc),
                equity_usd=Decimal("1000"),
                cash_usd=Decimal("1000"),
                unrealized_pnl_usd=Decimal("0"),
                realized_pnl_today_usd=Decimal("0"),
                open_positions=0,
            )
        )
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


def test_public_events_are_sanitized(
    migrated_engine: sa.Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Return only public_safe events with sanitized payloads."""
    _configure_rate_limit(monkeypatch, limit=1000, redis_url=None)
    _insert_events(migrated_engine)

    client = TestClient(app)
    response = client.get("/public/v1/events")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    by_type = {item["type"]: item for item in data}
    event = by_type["trade.opened"]

    assert event["type"] == "trade.opened"
    assert event["payload"].get("message") == "opened"
    for forbidden in [
        "exchange_order_id",
        "idempotency_key",
        "ciphertext",
        "nonce",
        "api_key",
        "secret",
    ]:
        assert forbidden not in event["payload"]
    assert "id" not in event
    assert "trade_id" not in event
    assert by_type["trade.note"]["payload"] == {}


def test_public_trades_are_sanitized(
    migrated_engine: sa.Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Return sanitized trades without internal fields."""
    _configure_rate_limit(monkeypatch, limit=1000, redis_url=None)
    _insert_trade(migrated_engine)

    client = TestClient(app)
    response = client.get("/public/v1/trades")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    trade = data[0]

    allowed_keys = {
        "symbol",
        "side",
        "status",
        "mode",
        "opened_at",
        "closed_at",
        "entry_price",
        "exit_price",
        "realized_pnl_usd",
    }
    assert set(trade.keys()) == allowed_keys


def test_public_summary_returns_latest_snapshot(
    migrated_engine: sa.Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Return the most recent equity snapshot."""
    _configure_rate_limit(monkeypatch, limit=1000, redis_url=None)
    _insert_snapshots(migrated_engine)

    client = TestClient(app)
    response = client.get("/public/v1/summary")

    assert response.status_code == 200
    summary = response.json()
    assert summary["equity_usd"] == 1100
    assert summary["open_positions"] == 1


def test_public_summary_empty(
    migrated_engine: sa.Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Return null fields when no snapshots exist."""
    _configure_rate_limit(monkeypatch, limit=1000, redis_url=None)
    client = TestClient(app)

    response = client.get("/public/v1/summary")

    assert response.status_code == 200
    assert response.json() == {
        "ts": None,
        "equity_usd": None,
        "cash_usd": None,
        "unrealized_pnl_usd": None,
        "realized_pnl_today_usd": None,
        "open_positions": None,
    }


def test_public_rate_limit_in_memory(monkeypatch: pytest.MonkeyPatch) -> None:
    """Enforce in-memory rate limiting."""
    _configure_rate_limit(monkeypatch, limit=2, redis_url=None)
    client = TestClient(app)
    headers = {"X-Forwarded-For": "203.0.113.5"}

    assert client.get("/public/v1/heartbeat", headers=headers).status_code == 200
    assert client.get("/public/v1/heartbeat", headers=headers).status_code == 200
    response = client.get("/public/v1/heartbeat", headers=headers)

    assert response.status_code == 429
    assert response.json()["detail"]["code"] == "RATE_LIMITED"


def test_public_rate_limit_window_resets(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset counts when the rate limit window is cleared."""
    _configure_rate_limit(monkeypatch, limit=1, redis_url=None, window_seconds=0)
    client = TestClient(app)
    headers = {"X-Forwarded-For": "203.0.113.6"}

    assert client.get("/public/v1/heartbeat", headers=headers).status_code == 200
    assert client.get("/public/v1/heartbeat", headers=headers).status_code == 200


def test_public_rate_limit_redis(monkeypatch: pytest.MonkeyPatch) -> None:
    """Enforce Redis-backed rate limiting."""
    redis_url = "redis://localhost:6380/0"
    _configure_rate_limit(monkeypatch, limit=2, redis_url=redis_url)
    _flush_redis(redis_url)
    client = TestClient(app)

    assert client.get("/public/v1/heartbeat").status_code == 200
    assert client.get("/public/v1/heartbeat").status_code == 200
    response = client.get("/public/v1/heartbeat")

    assert response.status_code == 429
    assert response.json()["detail"]["code"] == "RATE_LIMITED"


def test_get_client_ip_unknown() -> None:
    """Fallback to unknown when client info is missing."""
    request = Request({"type": "http", "headers": []})
    assert get_client_ip(request) == "unknown"
