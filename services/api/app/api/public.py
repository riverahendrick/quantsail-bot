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
    snapshot = latest_equity_snapshot(get_engine())
    return cast(dict[str, object], jsonable_encoder(sanitize_summary(snapshot)))


@router.get("/trades")
def trades(limit: int | None = Query(None, ge=1, le=500)) -> list[dict[str, object]]:
    """Return sanitized public trades."""
    limit_value = _default_limit() if limit is None else limit
    data = list_trades(get_engine(), limit=limit_value)
    return cast(
        list[dict[str, object]],
        jsonable_encoder([sanitize_trade(item) for item in data]),
    )


@router.get("/events")
def events(limit: int | None = Query(None, ge=1, le=500)) -> list[dict[str, object]]:
    """Return sanitized public events."""
    limit_value = _default_limit() if limit is None else limit
    data = list_events(get_engine(), public_only=True, limit=limit_value)
    return cast(
        list[dict[str, object]],
        jsonable_encoder([sanitize_event(item) for item in data]),
    )


@router.get("/heartbeat")
def heartbeat() -> dict[str, object]:
    """Return a lightweight public heartbeat payload."""
    return {"ok": True, "ts": datetime.now(timezone.utc).isoformat()}
