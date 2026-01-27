"""Dry-run execution engine with deterministic simulated fills."""

import uuid
from datetime import datetime, timezone
from typing import Any

from quantsail_engine.models.trade_plan import TradePlan

from .executor import ExecutionEngine


class DryRunExecutor(ExecutionEngine):
    """Dry-run executor that simulates fills deterministically."""

    def __init__(self) -> None:
        """Initialize dry-run executor."""
        self._open_trades: dict[str, dict[str, Any]] = {}

    def execute_entry(self, plan: TradePlan) -> dict[str, Any]:
        """
        Simulate entry execution.

        Creates:
        - 1 Trade record (mode: DRY_RUN, status: OPEN)
        - 1 Entry order (status: SIMULATED, FILLED)
        - 1 SL order (status: SIMULATED, PENDING)
        - 1 TP order (status: SIMULATED, PENDING)

        Args:
            plan: Trade plan to execute

        Returns:
            Dictionary with trade and orders data
        """
        now = datetime.now(timezone.utc)
        trade_id = str(uuid.uuid4())

        # Create trade
        trade = {
            "id": trade_id,
            "symbol": plan.symbol,
            "mode": "DRY_RUN",
            "status": "OPEN",
            "side": plan.side,
            "entry_price": plan.entry_price,
            "quantity": plan.quantity,
            "opened_at": now,
            "closed_at": None,
            "exit_price": None,
            "pnl_usd": None,
            "pnl_pct": None,
        }

        # Create entry order
        entry_order = {
            "id": str(uuid.uuid4()),
            "trade_id": trade_id,
            "symbol": plan.symbol,
            "side": plan.side,
            "order_type": "MARKET",
            "status": "FILLED",
            "quantity": plan.quantity,
            "price": plan.entry_price,
            "filled_price": plan.entry_price,
            "filled_qty": plan.quantity,
            "created_at": now,
            "filled_at": now,
        }

        # Create SL order
        sl_order = {
            "id": str(uuid.uuid4()),
            "trade_id": trade_id,
            "symbol": plan.symbol,
            "side": "SELL" if plan.side == "BUY" else "BUY",
            "order_type": "STOP_LOSS",
            "status": "PENDING",
            "quantity": plan.quantity,
            "price": plan.stop_loss_price,
            "filled_price": None,
            "filled_qty": None,
            "created_at": now,
            "filled_at": None,
        }

        # Create TP order
        tp_order = {
            "id": str(uuid.uuid4()),
            "trade_id": trade_id,
            "symbol": plan.symbol,
            "side": "SELL" if plan.side == "BUY" else "BUY",
            "order_type": "TAKE_PROFIT",
            "status": "PENDING",
            "quantity": plan.quantity,
            "price": plan.take_profit_price,
            "filled_price": None,
            "filled_qty": None,
            "created_at": now,
            "filled_at": None,
        }

        # Store open trade for exit checking
        self._open_trades[trade_id] = {
            "trade": trade,
            "sl_price": plan.stop_loss_price,
            "tp_price": plan.take_profit_price,
            "sl_order": sl_order,
            "tp_order": tp_order,
        }

        return {
            "trade": trade,
            "orders": [entry_order, sl_order, tp_order],
        }

    def check_exits(self, trade_id: str, current_price: float) -> dict[str, Any] | None:
        """
        Check if SL or TP is hit.

        For long positions:
        - SL hit if current_price <= sl_price
        - TP hit if current_price >= tp_price

        Args:
            trade_id: ID of the open trade
            current_price: Current market price

        Returns:
            Dictionary with exit data if exit triggered, None otherwise
        """
        if trade_id not in self._open_trades:
            return None

        trade_data = self._open_trades[trade_id]
        trade = trade_data["trade"]
        sl_price = trade_data["sl_price"]
        tp_price = trade_data["tp_price"]

        exit_reason = None
        exit_price = None

        # Check SL/TP for long positions (BUY side)
        if trade["side"] == "BUY":
            if current_price <= sl_price:
                exit_reason = "STOP_LOSS"
                exit_price = sl_price
            elif current_price >= tp_price:
                exit_reason = "TAKE_PROFIT"
                exit_price = tp_price

        if exit_reason is None:
            return None

        # Calculate PnL
        now = datetime.now(timezone.utc)
        pnl_usd = (exit_price - trade["entry_price"]) * trade["quantity"]
        pnl_pct = (pnl_usd / (trade["entry_price"] * trade["quantity"])) * 100.0

        # Update trade
        trade["status"] = "CLOSED"
        trade["closed_at"] = now
        trade["exit_price"] = exit_price
        trade["pnl_usd"] = pnl_usd
        trade["pnl_pct"] = pnl_pct

        # Create exit order
        exit_order = {
            "id": str(uuid.uuid4()),
            "trade_id": trade_id,
            "symbol": trade["symbol"],
            "side": "SELL" if trade["side"] == "BUY" else "BUY",
            "order_type": exit_reason,
            "status": "FILLED",
            "quantity": trade["quantity"],
            "price": exit_price,
            "filled_price": exit_price,
            "filled_qty": trade["quantity"],
            "created_at": now,
            "filled_at": now,
        }

        # Update SL/TP order statuses
        if exit_reason == "STOP_LOSS":
            trade_data["sl_order"]["status"] = "FILLED"
            trade_data["sl_order"]["filled_price"] = exit_price
            trade_data["sl_order"]["filled_qty"] = trade["quantity"]
            trade_data["sl_order"]["filled_at"] = now
            trade_data["tp_order"]["status"] = "CANCELLED"
        else:  # TAKE_PROFIT
            trade_data["tp_order"]["status"] = "FILLED"
            trade_data["tp_order"]["filled_price"] = exit_price
            trade_data["tp_order"]["filled_qty"] = trade["quantity"]
            trade_data["tp_order"]["filled_at"] = now
            trade_data["sl_order"]["status"] = "CANCELLED"

        # Remove from open trades
        del self._open_trades[trade_id]

        return {
            "trade": trade,
            "exit_order": exit_order,
            "exit_reason": exit_reason,
        }
