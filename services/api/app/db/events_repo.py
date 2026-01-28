from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import sqlalchemy as sa

from app.db.models import Event


def append_event(
    engine: sa.Engine,
    *,
    event_type: str,
    payload: dict[str, Any],
    level: str,
    public_safe: bool,
    symbol: str | None = None,
    trade_id: UUID | None = None,
    ts: datetime | None = None,
) -> dict[str, Any]:
    """Append an event row and return the inserted record."""
    event_ts = ts or datetime.now(timezone.utc)
    values = {
        "ts": event_ts,
        "level": level,
        "type": event_type,
        "symbol": symbol,
        "trade_id": trade_id,
        "payload": payload,
        "public_safe": public_safe,
    }
    query = sa.insert(Event).values(**values).returning(Event.__table__)
    with engine.begin() as conn:
        result = conn.execute(query).mappings().first()
    assert result is not None
    return dict(result)


def query_events(
    engine: sa.Engine,
    *,
    limit: int = 100,
    cursor: int | None = None,
    event_types: list[str] | None = None,
    level: str | None = None,
    symbol: str | None = None,
    public_safe: bool | None = None,
) -> list[dict[str, Any]]:
    """Query events ordered by seq ascending with optional filters."""
    query = sa.select(Event.__table__)
    if cursor is not None:
        query = query.where(Event.seq > cursor)
    if event_types:
        query = query.where(Event.type.in_(event_types))
    if level:
        query = query.where(Event.level == level)
    if symbol:
        query = query.where(Event.symbol == symbol)
    if public_safe is not None:
        query = query.where(Event.public_safe.is_(public_safe))
    query = query.order_by(Event.seq.asc()).limit(limit)
    with engine.connect() as conn:
        return [dict(row) for row in conn.execute(query).mappings().all()]
