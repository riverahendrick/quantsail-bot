"""Backtest repository with SQLite storage for trade history."""

import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from quantsail_engine.backtest.time_manager import TimeManager
from quantsail_engine.persistence.repository import EngineRepository
from quantsail_engine.persistence.stub_models import (
    Base,
    EquitySnapshot,
    Event,
    Order,
    Trade,
)


class BacktestRepository(EngineRepository):
    """Repository for backtesting with isolated SQLite storage.

    Uses an in-memory or file-based SQLite database to store
    backtest data separately from the production/dev database.

    Example:
        >>> repo = BacktestRepository(":memory:")  # In-memory
        >>> # or
        >>> repo = BacktestRepository("./backtests/run_123.db")  # File-based
        >>> trade_id = repo.save_trade({...})
    """

    def __init__(
        self,
        db_path: str = ":memory:",
        time_manager: TimeManager | None = None,
    ):
        """Initialize backtest repository.

        Args:
            db_path: SQLite database path (default: in-memory)
            time_manager: Optional time manager for simulated timestamps
        """
        # Create engine and tables
        self.db_path = db_path
        self.time_manager = time_manager
        self._engine = create_engine(f"sqlite:///{db_path}", echo=False)
        Base.metadata.create_all(self._engine)

        # Create session
        SessionLocal = sessionmaker(bind=self._engine)
        self.session = SessionLocal()

        # Statistics tracking
        self._circuit_breaker_triggers = 0
        self._daily_lock_hits = 0
        self._events_emitted: list[dict[str, Any]] = []

    def _now(self) -> datetime:
        """Get current timestamp (simulated or real)."""
        if self.time_manager:
            try:
                return self.time_manager.now()
            except RuntimeError:
                # Time not set yet, use real time
                return datetime.now(timezone.utc)
        return datetime.now(timezone.utc)

    def append_event(
        self,
        event_type: str,
        level: str,
        payload: dict[str, Any],
        public_safe: bool = False,
    ) -> int:
        """Append an event to the events table.

        Also tracks safety statistics for reporting.

        Args:
            event_type: Event type
            level: Log level
            payload: Event payload
            public_safe: Whether safe for public display

        Returns:
            Event sequence number
        """
        # Track safety events
        if event_type == "breaker.triggered":
            self._circuit_breaker_triggers += 1
        elif event_type in ("daily_lock.engaged", "daily_lock.entries_paused"):
            self._daily_lock_hits += 1

        # Store event for analysis
        event_record = {
            "type": event_type,
            "level": level,
            "payload": payload,
            "timestamp": self._now().isoformat(),
        }
        self._events_emitted.append(event_record)

        safe_payload = self._make_json_safe(payload)

        # Handle SQLite sequence generation manually (no Identity support)
        event_kwargs = {
            "type": event_type,
            "level": level,
            "payload": safe_payload,
            "public_safe": public_safe,
            "ts": self._now(),
        }

        if self.session.bind.dialect.name == "sqlite":
            import sqlalchemy as sa
            max_seq = self.session.query(sa.func.max(Event.seq)).scalar() or 0
            event_kwargs["seq"] = max_seq + 1

        event = Event(**event_kwargs)
        self.session.add(event)
        self.session.commit()
        self.session.refresh(event)
        return int(event.seq)

    def _make_json_safe(self, obj: Any) -> Any:
        """Recursively convert object to JSON-safe primitives."""
        if isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        if isinstance(obj, dict):
            return {str(k): self._make_json_safe(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple, set)):
            return [self._make_json_safe(x) for x in obj]
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, "model_dump"):  # Pydantic v2
            return self._make_json_safe(obj.model_dump())
        if hasattr(obj, "dict"):  # Pydantic v1
            return self._make_json_safe(obj.dict())
        # Fallback to string representation for unknown objects
        return str(obj)

    def calculate_equity(self, starting_cash_usd: float) -> float:
        """Calculate current equity based on closed trades.

        Args:
            starting_cash_usd: Starting cash in USD

        Returns:
            Current equity
        """
        closed_trades = (
            self.session.query(Trade).filter(Trade.status == "CLOSED").all()
        )
        total_pnl = sum(float(trade.realized_pnl_usd or 0.0) for trade in closed_trades)
        return starting_cash_usd + total_pnl

    def save_equity_snapshot(
        self,
        equity_usd: float,
        cash_usd: float = 0.0,
        unrealized_pnl_usd: float = 0.0,
        realized_pnl_today_usd: float = 0.0,
        open_positions: int = 0,
    ) -> None:
        """Save an equity snapshot.

        Args:
            equity_usd: Current equity
            cash_usd: Cash balance
            unrealized_pnl_usd: Unrealized PnL
            realized_pnl_today_usd: Today's realized PnL
            open_positions: Number of open positions
        """
        snapshot = EquitySnapshot(
            equity_usd=equity_usd,
            cash_usd=cash_usd,
            unrealized_pnl_usd=unrealized_pnl_usd,
            realized_pnl_today_usd=realized_pnl_today_usd,
            open_positions=open_positions,
            ts=self._now(),
        )
        self.session.add(snapshot)
        self.session.commit()

    def get_today_realized_pnl(self, timezone_str: str = "UTC") -> float:
        """Calculate realized PnL for the current day.

        Uses the time manager's current time if available.

        Args:
            timezone_str: Timezone string

        Returns:
            Sum of PnL for trades closed "today" in backtest time
        """
        from zoneinfo import ZoneInfo

        if self.time_manager:
            now = self.time_manager.now()
        else:
            now = datetime.now(timezone.utc)

        tz = ZoneInfo(timezone_str)
        now_local = now.astimezone(tz)
        start_of_day = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        start_of_day_utc = start_of_day.astimezone(timezone.utc)

        closed_trades = (
            self.session.query(Trade)
            .filter(
                Trade.status == "CLOSED",
                Trade.closed_at >= start_of_day_utc,
            )
            .all()
        )
        return sum(float(trade.realized_pnl_usd or 0.0) for trade in closed_trades)

    def get_today_closed_trades(self, timezone_str: str = "UTC") -> list[Trade]:
        """Get trades closed today in the simulated time.

        Args:
            timezone_str: Timezone string

        Returns:
            List of Trade objects
        """
        from zoneinfo import ZoneInfo

        if self.time_manager:
            now = self.time_manager.now()
        else:
            now = datetime.now(timezone.utc)

        tz = ZoneInfo(timezone_str)
        now_local = now.astimezone(tz)
        start_of_day = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        start_of_day_utc = start_of_day.astimezone(timezone.utc)

        return (
            self.session.query(Trade)
            .filter(
                Trade.status == "CLOSED",
                Trade.closed_at >= start_of_day_utc,
            )
            .order_by(Trade.closed_at.asc())
            .all()
        )

    def get_equity_curve(self) -> list[tuple[datetime, float]]:
        """Get the equity curve over time.

        Returns:
            List of (timestamp, equity) tuples
        """
        snapshots = (
            self.session.query(EquitySnapshot)
            .order_by(EquitySnapshot.ts.asc())
            .all()
        )
        result: list[tuple[datetime, float]] = []
        for snap in snapshots:
            if snap.ts is not None and snap.equity_usd is not None:
                ts: datetime = snap.ts  # type: ignore[assignment]
                eq: float = float(snap.equity_usd)
                result.append((ts, eq))
        return result

    def get_all_trades(self) -> list[dict[str, Any]]:
        """Get all trades for analysis.

        Returns:
            List of trade dictionaries
        """
        trades = self.session.query(Trade).order_by(Trade.opened_at.asc()).all()
        return [
            {
                "id": str(trade.id),
                "symbol": trade.symbol,
                "status": trade.status,
                "side": trade.side,
                "entry_price": float(trade.entry_price),
                "quantity": float(trade.entry_qty),
                "opened_at": trade.opened_at,
                "closed_at": trade.closed_at,
                "exit_price": float(trade.exit_price) if trade.exit_price is not None else None,
                "realized_pnl_usd": float(trade.realized_pnl_usd) if trade.realized_pnl_usd is not None else None,
            }
            for trade in trades
        ]

    def get_circuit_breaker_count(self) -> int:
        """Get number of circuit breaker triggers.

        Returns:
            Count of breaker triggers
        """
        return self._circuit_breaker_triggers

    def get_daily_lock_count(self) -> int:
        """Get number of daily lock hits.

        Returns:
            Count of daily lock engagements
        """
        return self._daily_lock_hits

    def get_events(self, event_type: str | None = None) -> list[dict[str, Any]]:
        """Get events, optionally filtered by type.

        Args:
            event_type: Optional event type filter

        Returns:
            List of event dictionaries
        """
        query = self.session.query(Event)
        if event_type:
            query = query.filter(Event.type == event_type)
        events = query.order_by(Event.ts.asc()).all()
        return [
            {
                "type": e.type,
                "level": e.level,
                "payload": e.payload,
                "timestamp": e.ts.isoformat(),
            }
            for e in events
        ]

    def close(self) -> None:
        """Close database session."""
        self.session.close()
