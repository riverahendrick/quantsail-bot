"""Engine repository for database persistence operations."""

import uuid
import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from quantsail_engine.security.encryption import DecryptedCredentials, EncryptionService

# Try to import from API service, fall back to stub models
try:
    from app.db.models import EquitySnapshot, Event, ExchangeKey, Order, Trade  # type: ignore[import-not-found]
except ModuleNotFoundError:  # pragma: no cover
    from quantsail_engine.persistence.stub_models import (
        EquitySnapshot,
        Event,
        ExchangeKey,
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
            id=uuid.UUID(str(trade_data["id"])),
            symbol=trade_data["symbol"],
            mode=trade_data["mode"],
            status=trade_data["status"],
            side=trade_data["side"],
            entry_price=trade_data["entry_price"],
            entry_qty=trade_data["quantity"],
            entry_notional_usd=trade_data["entry_price"] * trade_data["quantity"],
            opened_at=trade_data["opened_at"],
            stop_price=trade_data.get("stop_price"),
            take_profit_price=trade_data.get("take_profit_price"),
            trailing_enabled=trade_data.get("trailing_enabled", False),
            trailing_offset=trade_data.get("trailing_offset"),
            closed_at=trade_data.get("closed_at"),
            exit_price=trade_data.get("exit_price"),
            realized_pnl_usd=trade_data.get("realized_pnl_usd"),
            # fees_paid_usd=trade_data.get("fees_paid_usd"),
            # slippage_est_usd=trade_data.get("slippage_est_usd"),
            # notes=trade_data.get("notes"),
        )
        self.session.add(trade)
        self.session.commit()
        trade_id: str = str(trade.id)
        return trade_id

    def update_trade(self, trade_data: dict[str, Any]) -> None:
        """
        Update an existing trade.

        Args:
            trade_data: Trade data dictionary with id
        """
        trade_id = uuid.UUID(str(trade_data["id"]))
        trade = self.session.query(Trade).filter(Trade.id == trade_id).first()
        if trade:
            trade.status = trade_data["status"]
            trade.closed_at = trade_data.get("closed_at")
            trade.exit_price = trade_data.get("exit_price")
            trade.realized_pnl_usd = trade_data.get("realized_pnl_usd")
            # trade.fees_paid_usd = trade_data.get("fees_paid_usd")
            # trade.slippage_est_usd = trade_data.get("slippage_est_usd")
            self.session.commit()

    def get_trade(self, trade_id: str) -> dict[str, Any] | None:
        """
        Get trade by ID.

        Args:
            trade_id: Trade ID

        Returns:
            Trade data dictionary or None
        """
        try:
            t_id = uuid.UUID(str(trade_id))
        except ValueError:
            return None

        trade = self.session.query(Trade).filter(Trade.id == t_id).first()
        if not trade:
            return None

        return {
            "id": str(trade.id),
            "symbol": trade.symbol,
            "mode": trade.mode,
            "status": trade.status,
            "side": trade.side,
            "entry_price": float(trade.entry_price),
            "quantity": float(trade.entry_qty),
            "opened_at": trade.opened_at,
            "stop_price": float(trade.stop_price) if trade.stop_price is not None else None,
            "take_profit_price": float(trade.take_profit_price) if trade.take_profit_price is not None else None,
            "trailing_enabled": trade.trailing_enabled,
            "trailing_offset": float(trade.trailing_offset) if trade.trailing_offset is not None else None,
            "closed_at": trade.closed_at,
            "exit_price": float(trade.exit_price) if trade.exit_price is not None else None,
            "realized_pnl_usd": float(trade.realized_pnl_usd) if trade.realized_pnl_usd is not None else None,
            "pnl_pct": 0.0, # Placeholder
        }

    def save_order(self, order_data: dict[str, Any]) -> str:
        """Save order to database."""
        order = Order(
            id=uuid.UUID(str(order_data["id"])),
            trade_id=uuid.UUID(str(order_data["trade_id"])),
            symbol=order_data["symbol"],
            side=order_data["side"],
            order_type=order_data["order_type"],
            status=order_data["status"],
            qty=order_data["quantity"],
            price=order_data.get("price"),
            filled_price=order_data.get("filled_price"),
            filled_qty=order_data.get("filled_qty"),
            filled_at=order_data.get("filled_at"),
            created_at=order_data["created_at"],
        )
        self.session.add(order)
        self.session.commit()
        order_id: str = str(order.id)
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
        def _json_serial(obj: Any) -> Any:
            if isinstance(obj, Decimal):
                return float(obj)
            if isinstance(obj, datetime):
                return obj.isoformat()
            return str(obj)

        # Ensure payload is JSON serializable
        safe_payload = json.loads(json.dumps(payload, default=_json_serial))

        # Handle SQLite sequence generation manually (no Identity support)
        event_kwargs = {
            "type": event_type,
            "level": level,
            "payload": safe_payload,
            "public_safe": public_safe,
            "ts": datetime.now(timezone.utc),
        }

        if self.session.bind.dialect.name == "sqlite":
            import sqlalchemy as sa
            max_seq = self.session.query(sa.func.max(Event.seq)).scalar() or 0
            event_kwargs["seq"] = max_seq + 1

        event = Event(**event_kwargs)
        self.session.add(event)
        self.session.commit()
        self.session.refresh(event)
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
        """
        Save an equity snapshot.

        Args:
            equity_usd: Current equity in USD
            cash_usd: Current cash balance
            unrealized_pnl_usd: Current unrealized PnL
            realized_pnl_today_usd: PnL realized today
            open_positions: Count of open positions
        """
        snapshot = EquitySnapshot(
            equity_usd=equity_usd,
            cash_usd=cash_usd,
            unrealized_pnl_usd=unrealized_pnl_usd,
            realized_pnl_today_usd=realized_pnl_today_usd,
            open_positions=open_positions,
            ts=datetime.now(timezone.utc),
        )
        self.session.add(snapshot)
        self.session.commit()

    def get_active_exchange_credentials(
        self, exchange: str, encryption: EncryptionService
    ) -> DecryptedCredentials | None:
        """Return active exchange credentials for the given exchange."""
        row = (
            self.session.query(ExchangeKey)
            .filter(
                ExchangeKey.exchange == exchange,
                ExchangeKey.revoked_at.is_(None),
                ExchangeKey.is_active.is_(True),
            )
            .first()
        )
        if not row:
            return None
        return encryption.decrypt(row.ciphertext, row.nonce)

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
                "id": str(trade.id),
                "symbol": trade.symbol,
                "realized_pnl_usd": float(trade.realized_pnl_usd) if trade.realized_pnl_usd is not None else 0.0,
                "pnl_pct": 0.0, # Placeholder
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
        return sum(float(trade.realized_pnl_usd or 0.0) for trade in closed_trades)

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