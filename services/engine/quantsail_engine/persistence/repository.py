"""Engine repository for database persistence operations."""

from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

# Try to import from API service, fall back to stub models
try:
    from app.db.models import EquitySnapshot, Event, Order, Trade  # type: ignore[import-not-found]
except ModuleNotFoundError:
    from quantsail_engine.persistence.stub_models import (
        EquitySnapshot,
        Event,
        Order,
        Trade,
    )


class EngineRepository:
    """Repository wrapping database operations for the engine."""

    def __init__(self, session: Session):
        """
        Initialize repository with database session.

        Args:
            session: SQLAlchemy session
        """
        self.session = session

    def save_trade(self, trade_data: dict[str, Any]) -> str:
        """
        Save a new trade to the database.

        Args:
            trade_data: Trade data dictionary

        Returns:
            Trade ID
        """
        trade = Trade(
            id=trade_data["id"],
            symbol=trade_data["symbol"],
            mode=trade_data["mode"],
            status=trade_data["status"],
            side=trade_data["side"],
            entry_price=trade_data["entry_price"],
            quantity=trade_data["quantity"],
            opened_at=trade_data["opened_at"],
            stop_price=trade_data["stop_price"],
            take_profit_price=trade_data["take_profit_price"],
            trailing_enabled=trade_data.get("trailing_enabled", False),
            trailing_offset=trade_data.get("trailing_offset"),
            closed_at=trade_data.get("closed_at"),
            exit_price=trade_data.get("exit_price"),
            pnl_usd=trade_data.get("pnl_usd"),
            pnl_pct=trade_data.get("pnl_pct"),
        )
        self.session.add(trade)
        self.session.commit()
        trade_id: str = trade.id
        return trade_id

    def update_trade(self, trade_data: dict[str, Any]) -> None:
        """
        Update an existing trade.

        Args:
            trade_data: Trade data dictionary with id
        """
        trade = self.session.query(Trade).filter(Trade.id == trade_data["id"]).first()
        if trade:
            trade.status = trade_data["status"]
            trade.closed_at = trade_data.get("closed_at")
            trade.exit_price = trade_data.get("exit_price")
            trade.pnl_usd = trade_data.get("pnl_usd")
            trade.pnl_pct = trade_data.get("pnl_pct")
            self.session.commit()

    def get_trade(self, trade_id: str) -> dict[str, Any] | None:
        """
        Get trade by ID.

        Args:
            trade_id: Trade ID

        Returns:
            Trade data dictionary or None
        """
        trade = self.session.query(Trade).filter(Trade.id == trade_id).first()
        if not trade:
            return None

        return {
            "id": trade.id,
            "symbol": trade.symbol,
            "mode": trade.mode,
            "status": trade.status,
            "side": trade.side,
            "entry_price": trade.entry_price,
            "quantity": trade.quantity,
            "opened_at": trade.opened_at,
            "stop_price": trade.stop_price,
            "take_profit_price": trade.take_profit_price,
            "trailing_enabled": trade.trailing_enabled,
            "trailing_offset": trade.trailing_offset,
            "closed_at": trade.closed_at,
            "exit_price": trade.exit_price,
            "pnl_usd": trade.pnl_usd,
            "pnl_pct": trade.pnl_pct,
        }

    def save_order(self, order_data: dict[str, Any]) -> str:
        """
        Save a new order to the database.

        Args:
            order_data: Order data dictionary

        Returns:
            Order ID
        """
        order = Order(
            id=order_data["id"],
            trade_id=order_data["trade_id"],
            symbol=order_data["symbol"],
            side=order_data["side"],
            order_type=order_data["order_type"],
            status=order_data["status"],
            quantity=order_data["quantity"],
            price=order_data.get("price"),
            filled_price=order_data.get("filled_price"),
            filled_qty=order_data.get("filled_qty"),
            created_at=order_data["created_at"],
            filled_at=order_data.get("filled_at"),
        )
        self.session.add(order)
        self.session.commit()
        order_id: str = order.id
        return order_id

    def append_event(
        self,
        event_type: str,
        level: str,
        payload: dict[str, Any],
        public_safe: bool = False,
    ) -> int:
        """
        Append an event to the events table.

        Args:
            event_type: Event type (e.g., "market.tick", "trade.opened")
            level: Log level (INFO, WARN, ERROR)
            payload: Event payload as dictionary
            public_safe: Whether event is safe for public dashboard

        Returns:
            Event sequence number
        """
        event = Event(
            type=event_type,
            level=level,
            payload=payload,
            public_safe="true" if public_safe else "false",
            timestamp=datetime.now(timezone.utc),
        )
        self.session.add(event)
        self.session.commit()
        seq: int = event.seq
        return seq

    def calculate_equity(self, starting_cash_usd: float) -> float:
        """
        Calculate current equity based on closed trades.

        Equity = starting_cash + sum(pnl_usd for closed trades)

        Args:
            starting_cash_usd: Starting cash in USD

        Returns:
            Current equity in USD
        """
        closed_trades = (
            self.session.query(Trade).filter(Trade.status == "CLOSED").all()
        )
        total_pnl = sum(trade.pnl_usd or 0.0 for trade in closed_trades)
        return starting_cash_usd + total_pnl

    def save_equity_snapshot(self, equity_usd: float) -> None:
        """
        Save an equity snapshot.

        Args:
            equity_usd: Current equity in USD
        """
        snapshot = EquitySnapshot(
            equity_usd=equity_usd,
            timestamp=datetime.now(timezone.utc),
        )
        self.session.add(snapshot)
        self.session.commit()

    def get_recent_closed_trades(self, limit: int) -> list[dict[str, Any]]:
        """
        Get recent closed trades ordered by closed_at DESC.

        Args:
            limit: Maximum number of trades to return

        Returns:
            List of trade dictionaries with id, symbol, pnl_usd, pnl_pct, closed_at
        """
        trades = (
            self.session.query(Trade)
            .filter(Trade.status == "CLOSED")
            .order_by(Trade.closed_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": trade.id,
                "symbol": trade.symbol,
                "pnl_usd": trade.pnl_usd,
                "pnl_pct": trade.pnl_pct,
                "closed_at": trade.closed_at,
            }
            for trade in trades
        ]

    def get_today_realized_pnl(self, timezone_str: str = "UTC") -> float:
        """
        Calculate realized PnL for the current day in the specified timezone.

        Args:
            timezone_str: Timezone string (e.g., "UTC", "America/New_York")

        Returns:
            Sum of pnl_usd for trades closed today
        """
        tz = ZoneInfo(timezone_str)
        now = datetime.now(tz)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Convert start_of_day to UTC for DB query if DB stores in UTC (it does)
        start_of_day_utc = start_of_day.astimezone(timezone.utc)

        closed_trades = (
            self.session.query(Trade)
            .filter(
                Trade.status == "CLOSED",
                Trade.closed_at >= start_of_day_utc
            )
            .all()
        )
        return sum(trade.pnl_usd or 0.0 for trade in closed_trades)

    def get_today_closed_trades(self, timezone_str: str = "UTC") -> list[Trade]:
        """
        Get all trades closed today in the specified timezone, ordered by closed_at.

        Args:
            timezone_str: Timezone string

        Returns:
            List of Trade objects
        """
        tz = ZoneInfo(timezone_str)
        now = datetime.now(tz)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start_of_day_utc = start_of_day.astimezone(timezone.utc)

        return (
            self.session.query(Trade)
            .filter(
                Trade.status == "CLOSED",
                Trade.closed_at >= start_of_day_utc
            )
            .order_by(Trade.closed_at.asc())
            .all()
        )
