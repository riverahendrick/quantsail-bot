from __future__ import annotations

from typing import Any

import sqlalchemy as sa

from app.db.models import EquitySnapshot, Event, Trade, User


def get_user_role_by_email(engine: sa.Engine, email: str) -> str | None:
    """Return the role for the given user email, if present."""
    query = sa.select(User.role).where(User.email == email)
    with engine.connect() as conn:
        return conn.execute(query).scalar_one_or_none()


def get_user_info_by_email(engine: sa.Engine, email: str) -> tuple[str, str] | None:
    """Return (user_id, role) for the given user email, if present."""
    query = sa.select(User.id, User.role).where(User.email == email)
    with engine.connect() as conn:
        row = conn.execute(query).fetchone()
        if row:
            return str(row.id), row.role
        return None


def list_trades(engine: sa.Engine, limit: int | None = None) -> list[dict[str, Any]]:
    """Return trades ordered by opened_at descending."""
    query = sa.select(Trade.__table__).order_by(sa.desc(Trade.opened_at))
    if limit is not None:
        query = query.limit(limit)
    with engine.connect() as conn:
        return [dict(row) for row in conn.execute(query).mappings().all()]


def list_events(
    engine: sa.Engine, public_only: bool, limit: int | None = None
) -> list[dict[str, Any]]:
    """Return events ordered by ts descending, optionally filtered for public_safe."""
    query = sa.select(Event.__table__)
    if public_only:
        query = query.where(Event.public_safe.is_(True))
    query = query.order_by(sa.desc(Event.ts))
    if limit is not None:
        query = query.limit(limit)
    with engine.connect() as conn:
        return [dict(row) for row in conn.execute(query).mappings().all()]


def list_equity_snapshots(engine: sa.Engine, limit: int | None = None) -> list[dict[str, Any]]:
    """Return equity snapshots ordered by ts descending."""
    query = sa.select(EquitySnapshot.__table__).order_by(sa.desc(EquitySnapshot.ts))
    if limit is not None:
        query = query.limit(limit)
    with engine.connect() as conn:
        return [dict(row) for row in conn.execute(query).mappings().all()]


def latest_equity_snapshot(engine: sa.Engine) -> dict[str, Any] | None:
    """Return the most recent equity snapshot, if any."""
    query = sa.select(EquitySnapshot.__table__).order_by(sa.desc(EquitySnapshot.ts)).limit(1)
    with engine.connect() as conn:
        result = conn.execute(query).mappings().first()
    return dict(result) if result else None
