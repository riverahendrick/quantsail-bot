from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import sqlalchemy as sa

from app.db.events_repo import append_event, query_events
from app.db.models import Trade


def _insert_trade(engine: sa.Engine) -> UUID:
    """Insert a trade row to satisfy event foreign keys."""
    trade_id = uuid4()
    payload = {
        "id": trade_id,
        "symbol": "BTC/USDT",
        "side": "LONG",
        "status": "OPEN",
        "mode": "DRY_RUN",
        "opened_at": datetime(2026, 1, 27, tzinfo=timezone.utc),
        "entry_price": Decimal("100.0"),
        "entry_qty": Decimal("0.1"),
        "entry_notional_usd": Decimal("10.0"),
        "stop_price": Decimal("90.0"),
        "take_profit_price": Decimal("120.0"),
    }
    with engine.begin() as conn:
        conn.execute(sa.insert(Trade).values(**payload))
    return trade_id


def test_append_event_assigns_seq(migrated_engine: sa.Engine) -> None:
    """Append events and ensure seq ordering."""
    trade_id = _insert_trade(migrated_engine)
    first = append_event(
        migrated_engine,
        event_type="system.started",
        payload={"step": 1},
        level="INFO",
        public_safe=False,
        ts=datetime(2026, 1, 27, tzinfo=timezone.utc),
    )
    second = append_event(
        migrated_engine,
        event_type="trade.opened",
        payload={"step": 2},
        level="INFO",
        public_safe=True,
        ts=datetime(2026, 1, 27, tzinfo=timezone.utc),
        trade_id=trade_id,
    )

    assert int(second["seq"]) > int(first["seq"])

    events = query_events(migrated_engine, cursor=int(first["seq"]))
    assert len(events) == 1
    assert events[0]["id"] == second["id"]


def test_query_events_filters(migrated_engine: sa.Engine) -> None:
    """Filter events by type, level, symbol, and public_safe."""
    append_event(
        migrated_engine,
        event_type="system.started",
        payload={"ok": True},
        level="INFO",
        public_safe=False,
        symbol="BTC/USDT",
    )
    append_event(
        migrated_engine,
        event_type="trade.opened",
        payload={"ok": True},
        level="WARN",
        public_safe=True,
        symbol="ETH/USDT",
    )

    events = query_events(
        migrated_engine,
        event_types=["trade.opened"],
        level="WARN",
        symbol="ETH/USDT",
        public_safe=True,
    )

    assert len(events) == 1
    assert events[0]["type"] == "trade.opened"
