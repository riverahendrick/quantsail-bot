from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import cast

from fastapi import APIRouter, Depends, Query
from fastapi.encoders import jsonable_encoder

from app.db.engine import get_engine
from app.db.queries import latest_equity_snapshot, list_events, list_trades
from app.public.rate_limit import enforce_rate_limit
from app.public.sanitize import sanitize_event, sanitize_summary, sanitize_trade

router = APIRouter(prefix="/public/v1", dependencies=[Depends(enforce_rate_limit)])


def _default_limit() -> int:
    """Return the default list limit for public endpoints."""
    return int(os.environ.get("PUBLIC_LIST_LIMIT_DEFAULT", "100"))


@router.get("/summary")
def summary() -> dict[str, object]:
    """Return the latest sanitized equity snapshot."""
    try:
        snapshot = latest_equity_snapshot(get_engine())
        return cast(dict[str, object], jsonable_encoder(sanitize_summary(snapshot)))
    except Exception as e:
        # Fallback to development mode when database is not available
        if "DATABASE_URL is required" in str(e):
            return {
                "equity_usd": 10000.0,
                "realized_pnl_today_usd": 150.50,
                "unrealized_pnl_usd": 25.25,
                "total_trades": 42,
                "win_rate_30d": 0.65,
                "profit_factor_30d": 1.8,
                "max_drawdown_usd": -500.0,
                "sharpe_ratio_30d": 1.2,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        raise


@router.get("/trades")
def trades(limit: int | None = Query(None, ge=1, le=500)) -> list[dict[str, object]]:
    """Return sanitized public trades."""
    limit_value = _default_limit() if limit is None else limit
    try:
        data = list_trades(get_engine(), limit=limit_value)
        return cast(
            list[dict[str, object]],
            jsonable_encoder([sanitize_trade(item) for item in data]),
        )
    except Exception as e:
        # Fallback to development mode when database is not available
        if "DATABASE_URL is required" in str(e):
            return [
                {
                    "id": "trade_1",
                    "symbol": "BTC/USDT",
                    "side": "buy",
                    "quantity": 0.001,
                    "price": 43500.0,
                    "executed_at": datetime.now(timezone.utc).isoformat(),
                    "realized_pnl_usd": 15.50,
                },
                {
                    "id": "trade_2",
                    "symbol": "BTC/USDT",
                    "side": "sell",
                    "quantity": 0.001,
                    "price": 43750.0,
                    "executed_at": datetime.now(timezone.utc).isoformat(),
                    "realized_pnl_usd": 2.50,
                },
            ]
        raise


@router.get("/events")
def events(limit: int | None = Query(None, ge=1, le=500)) -> list[dict[str, object]]:
    """Return sanitized public events."""
    limit_value = _default_limit() if limit is None else limit
    try:
        data = list_events(get_engine(), public_only=True, limit=limit_value)
        return cast(
            list[dict[str, object]],
            jsonable_encoder([sanitize_event(item) for item in data]),
        )
    except Exception as e:
        # Fallback to development mode when database is not available
        if "DATABASE_URL is required" in str(e):
            return [
                {
                    "id": "event_1",
                    "type": "trade_executed",
                    "level": "info",
                    "message": "BTC/USDT buy order executed",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                {
                    "id": "event_2",
                    "type": "strategy_update",
                    "level": "info",
                    "message": "Trend strategy parameters updated",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            ]
        raise


@router.get("/heartbeat")
def heartbeat() -> dict[str, object]:
    """Return a lightweight public heartbeat payload."""
    return {"ok": True, "ts": datetime.now(timezone.utc).isoformat()}


@router.get("/grid/performance")
def grid_performance() -> dict[str, object]:
    """Return sanitized grid trading performance for public dashboard.

    No API keys, no exact positions, no order IDs exposed.
    """
    from app.api.grid_data import get_public_grid_performance

    return cast(dict[str, object], jsonable_encoder(get_public_grid_performance()))
