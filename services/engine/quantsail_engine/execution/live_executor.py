"""Live execution logic with idempotency."""

import uuid
from datetime import datetime, timezone
from typing import Any

from quantsail_engine.execution.adapter import ExchangeAdapter
from quantsail_engine.execution.executor import ExecutionEngine
from quantsail_engine.persistence.repository import EngineRepository
from quantsail_engine.models.trade_plan import TradePlan


class LiveExecutor(ExecutionEngine):
    """Executes trades on a real exchange via adapter."""

    def __init__(self, repo: EngineRepository, adapter: ExchangeAdapter):
        """
        Initialize LiveExecutor.

        Args:
            repo: Engine repository for persistence
            adapter: Exchange adapter
        """
        self.repo = repo
        self.adapter = adapter

    def execute_entry(self, plan: TradePlan) -> dict[str, Any] | None:
        """
        Execute entry order with idempotency.

        1. Generate deterministic client_order_id.
        2. Check if order already exists (idempotency).
        3. Create order on exchange.
        4. Persist trade.
        """
        # 1. Deterministic ID: "QS-{uuid}-ENTRY"
        client_order_id = f"QS-{plan.trade_id}-ENTRY"

        # 2. Check if trade already exists in DB with this ID
        existing = self.repo.get_trade(plan.trade_id)
        if existing:
            # Idempotency hit: Trade already recorded.
            # We assume orders are also saved if trade is saved in this atomic-like flow
            # But we need to return the expected dict structure
            # Logic below requires fetching associated orders if we wanted to be perfect
            # For now, just logging and skipping to avoid duplicate execution
            self.repo.append_event(
                event_type="execution.idempotency_hit",
                level="WARN",
                payload={"trade_id": plan.trade_id},
                public_safe=False
            )
            return {"trade": existing, "orders": []}

        # 3. Create on Exchange
        try:
            response = self.adapter.create_order(
                symbol=plan.symbol,
                side=plan.side,
                order_type="market",
                quantity=plan.quantity,
                client_order_id=client_order_id,
            )
            
            # Extract filled price/qty
            fill_price = float(response.get("price", plan.entry_price) or plan.entry_price)
            if response.get("average"):
                fill_price = float(response["average"])
            
            filled_qty = float(response.get("amount", plan.quantity))
            
            now = datetime.now(timezone.utc)
            
            # 4. Construct Data
            trade_data = {
                "id": plan.trade_id,
                "symbol": plan.symbol,
                "mode": "LIVE",
                "status": "OPEN",
                "side": plan.side,
                "entry_price": fill_price,
                "quantity": filled_qty,
                "opened_at": response.get("datetime") or now,
                "stop_price": plan.stop_loss_price,
                "take_profit_price": plan.take_profit_price,
                "trailing_enabled": False,
                "trailing_offset": None,
                "closed_at": None,
                "exit_price": None,
                "pnl_usd": None,
                "pnl_pct": None,
            }

            entry_order = {
                "id": str(uuid.uuid4()),
                "trade_id": plan.trade_id,
                "symbol": plan.symbol,
                "side": plan.side,
                "order_type": "MARKET",
                "status": "FILLED",
                "quantity": filled_qty,
                "price": fill_price,
                "filled_price": fill_price,
                "filled_qty": filled_qty,
                "exchange_order_id": str(response.get("id")),
                "client_order_id": client_order_id,
                "created_at": now,
                "filled_at": now,
            }
            
            # We don't create separate SL/TP orders on exchange yet (MVP uses check_exits loop)
            # So we only return the entry order.
            
            return {
                "trade": trade_data,
                "orders": [entry_order]
            }

        except Exception as e:
            self.repo.append_event(
                event_type="error.execution",
                level="ERROR",
                payload={"error": str(e), "trade_id": plan.trade_id},
                public_safe=False
            )
            return None

    def check_exits(self, trade_id: str, current_price: float) -> dict[str, Any] | None:
        """
        Check and execute exits for live trades.
        
        Monitors price against SL/TP stored in DB.
        If triggered, sends MARKET SELL to exchange.
        """
        trade = self.repo.get_trade(trade_id)
        if not trade:
            return None
        
        # Only check open trades
        if trade["status"] != "OPEN":
            return None

        sl_price = float(trade["stop_price"])
        tp_price = float(trade["take_profit_price"])
        quantity = float(trade["quantity"])
        symbol = trade["symbol"]
        
        exit_reason = None
        target_price = None

        # Logic for LONG positions
        if trade["side"] == "BUY":
            if current_price <= sl_price:
                exit_reason = "STOP_LOSS"
                target_price = sl_price
            elif current_price >= tp_price:
                exit_reason = "TAKE_PROFIT"
                target_price = tp_price
        
        if not exit_reason:
            return None

        # Execute Exit
        try:
            client_order_id = f"QS-{trade_id}-{exit_reason}"
            response = self.adapter.create_order(
                symbol=symbol,
                side="SELL", # Closing a LONG
                order_type="market",
                quantity=quantity,
                client_order_id=client_order_id
            )
            
            fill_price = float(response.get("price", current_price) or current_price)
            if response.get("average"):
                fill_price = float(response["average"])
                
            now = datetime.now(timezone.utc)

            # Calculate PnL
            entry_price = float(trade["entry_price"])
            pnl_usd = (fill_price - entry_price) * quantity
            pnl_pct = (pnl_usd / (entry_price * quantity)) * 100.0

            # Update trade dict
            trade["status"] = "CLOSED"
            trade["closed_at"] = now
            trade["exit_price"] = fill_price
            trade["pnl_usd"] = pnl_usd
            trade["pnl_pct"] = pnl_pct

            exit_order = {
                "id": str(uuid.uuid4()),
                "trade_id": trade_id,
                "symbol": symbol,
                "side": "SELL",
                "order_type": exit_reason, # "STOP_LOSS" or "TAKE_PROFIT" for internal tracking
                "status": "FILLED",
                "quantity": quantity,
                "price": fill_price,
                "filled_price": fill_price,
                "filled_qty": quantity,
                "exchange_order_id": str(response.get("id")),
                "client_order_id": client_order_id,
                "created_at": now,
                "filled_at": now,
            }

            return {
                "trade": trade,
                "exit_order": exit_order,
                "exit_reason": exit_reason
            }

        except Exception as e:
            self.repo.append_event(
                event_type="error.exit_execution",
                level="ERROR",
                payload={
                    "error": str(e), 
                    "trade_id": trade_id,
                    "reason": exit_reason
                },
                public_safe=False
            )
            return None

    def reconcile_state(self, open_trades: list[Any]) -> None:
        """
        Reconcile state on startup.
        
        For MVP: Just log current open orders from exchange.
        """
        try:
            # We log reconciliation start
            self.repo.append_event(
                event_type="reconcile.started",
                level="INFO",
                payload={"open_trades_count": len(open_trades)},
                public_safe=True
            )
            
            # Simple check: Ensure we can fetch balances or connectivity
            # Real reconciliation is complex (matching IDs), out of MVP scope for full auto-correction.
            # We just verify connectivity and log open orders.

            # If we had a list of symbols, we'd check them.
            # For now, just a connectivity check via balance.
            self.adapter.fetch_balance()

            for trade in open_trades:
                symbol = getattr(trade, "symbol", None)
                trade_id = getattr(trade, "id", None)
                if not symbol or not trade_id:
                    continue
                open_orders = self.adapter.fetch_open_orders(symbol)
                self.repo.append_event(
                    event_type="reconcile.symbol",
                    level="INFO",
                    payload={
                        "symbol": symbol,
                        "db_open_trade": trade_id,
                        "exchange_open_orders": len(open_orders),
                    },
                    public_safe=False
                )
            
            self.repo.append_event(
                event_type="reconcile.completed",
                level="INFO",
                payload={"checked_trades": len(open_trades)},
                public_safe=True
            )
            
        except Exception as e:
             self.repo.append_event(
                event_type="error.reconcile",
                level="ERROR",
                payload={"error": str(e)},
                public_safe=False
            )
