"""Engine repository for database persistence operations."""

from datetime import datetime, timezone
from typing import Any

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
