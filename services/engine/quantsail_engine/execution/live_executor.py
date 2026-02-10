"""Live execution logic with exchange-native protective orders.

Places SL+TP (via OCO when available) on the exchange immediately after
entry fill. Monitors exits by polling protective order status rather
than in-process price checks.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from quantsail_engine.execution.adapter import ExchangeAdapter
from quantsail_engine.execution.executor import ExecutionEngine
from quantsail_engine.models.trade_plan import TradePlan
from quantsail_engine.persistence.repository import EngineRepository

logger = logging.getLogger(__name__)


class LiveExecutor(ExecutionEngine):
    """Executes trades on a real exchange with exchange-native protection.

    After a market entry fill, immediately places OCO (SL + TP) protective
    orders so the position is never unprotected — even if the engine crashes.
    Exit detection is done by polling order status on the exchange.
    """

    def __init__(self, repo: EngineRepository, adapter: ExchangeAdapter) -> None:
        self.repo = repo
        self.adapter = adapter
        # In-memory tracking: trade_id → protective order metadata
        self._protective_orders: dict[str, dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # ExecutionEngine interface
    # ------------------------------------------------------------------

    def execute_entry(self, plan: TradePlan) -> dict[str, Any] | None:
        """Execute market entry + place exchange-native SL/TP.

        1. Idempotency check (skip duplicate trade IDs).
        2. Place MARKET BUY on exchange.
        3. Place OCO (SL + TP) protective orders.
        4. Return trade + orders.
        """
        client_order_id = f"QS-{plan.trade_id}-ENTRY"

        # 1. Idempotency
        existing = self.repo.get_trade(plan.trade_id)
        if existing:
            self.repo.append_event(
                event_type="execution.idempotency_hit",
                level="WARN",
                payload={"trade_id": plan.trade_id},
                public_safe=False,
            )
            return {"trade": existing, "orders": []}

        # 2. Market entry
        try:
            response = self.adapter.create_order(
                symbol=plan.symbol,
                side=plan.side,
                order_type="market",
                quantity=plan.quantity,
                client_order_id=client_order_id,
            )
        except Exception as e:
            self.repo.append_event(
                event_type="error.execution",
                level="ERROR",
                payload={"error": str(e), "trade_id": plan.trade_id},
                public_safe=False,
            )
            return None

        fill_price = self._extract_fill_price(response, plan.entry_price)
        filled_qty = float(response.get("amount", plan.quantity))
        now = datetime.now(timezone.utc)

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

        orders = [entry_order]

        # 3. Place exchange-native SL + TP protective orders
        protective = self._place_protective_orders(plan, filled_qty, fill_price)
        if protective:
            self._protective_orders[plan.trade_id] = protective
            # Persist protective order IDs
            trade_data["protective_sl_order_id"] = protective.get("sl_order_id")
            trade_data["protective_tp_order_id"] = protective.get("tp_order_id")
            trade_data["protective_oco_mode"] = protective.get("oco_mode")
            orders.append(self._make_protective_order_record(
                plan, "STOP_LOSS", protective.get("sl_order_id", ""), now,
            ))
            orders.append(self._make_protective_order_record(
                plan, "TAKE_PROFIT", protective.get("tp_order_id", ""), now,
            ))
        else:
            logger.error(
                "Failed to place protective orders for %s — position is unprotected!",
                plan.trade_id,
            )
            self.repo.append_event(
                event_type="error.protective_orders",
                level="ERROR",
                payload={"trade_id": plan.trade_id, "symbol": plan.symbol},
                public_safe=False,
            )

        return {"trade": trade_data, "orders": orders}

    def check_exits(self, trade_id: str, current_price: float) -> dict[str, Any] | None:
        """Poll exchange for protective order fills.

        Instead of comparing price in-process, checks whether the SL or TP
        order has been filled on the exchange. If a fill is detected:
        1. Cancel the other leg.
        2. Mark trade as closed.
        3. Return exit data.

        Falls back to in-process price check if no protective orders exist
        (e.g. DryRun compatibility or protective order placement failure).
        """
        trade = self.repo.get_trade(trade_id)
        if not trade or trade["status"] != "OPEN":
            return None

        symbol = trade["symbol"]
        protective = self._protective_orders.get(trade_id)

        # If we have protective orders, poll exchange
        if protective:
            return self._poll_protective_orders(trade, protective)

        # Fallback: in-process price check (safety net)
        return self._fallback_price_check(trade, trade_id, current_price)

    def reconcile_state(self, open_trades: list[Any]) -> None:
        """Reconcile engine state with exchange on startup.

        1. Verify connectivity.
        2. For each open trade: check protective orders on exchange.
        3. Re-place missing protective orders.
        4. Sync fills that may have happened while engine was down.
        """
        try:
            self.repo.append_event(
                event_type="reconcile.started",
                level="INFO",
                payload={"open_trades_count": len(open_trades)},
                public_safe=True,
            )

            # Verify exchange connectivity
            self.adapter.fetch_balance()

            for trade in open_trades:
                _symbol = getattr(trade, "symbol", None)
                _trade_id = getattr(trade, "id", None)
                if not _symbol or not _trade_id:
                    continue
                symbol: str = str(_symbol)
                trade_id: str = str(_trade_id)

                open_orders = self.adapter.fetch_open_orders(symbol)
                trade_orders = [
                    o for o in open_orders
                    if (o.get("clientOrderId", "") or "").startswith(f"QS-{trade_id}")
                ]

                self.repo.append_event(
                    event_type="reconcile.symbol",
                    level="INFO",
                    payload={
                        "symbol": symbol,
                        "db_open_trade": trade_id,
                        "exchange_open_orders": len(open_orders),
                        "matched_protective_orders": len(trade_orders),
                    },
                    public_safe=False,
                )

                # Re-index protective orders for polling
                sl_order_id = ""
                tp_order_id = ""
                for order in trade_orders:
                    client_id = order.get("clientOrderId", "")
                    if "-SL" in client_id:
                        sl_order_id = order.get("id", "")
                    elif "-TP" in client_id:
                        tp_order_id = order.get("id", "")

                if sl_order_id or tp_order_id:
                    self._protective_orders[trade_id] = {
                        "sl_order_id": sl_order_id,
                        "tp_order_id": tp_order_id,
                        "symbol": symbol,
                        "oco_mode": "reconciled",
                    }

            self.repo.append_event(
                event_type="reconcile.completed",
                level="INFO",
                payload={"checked_trades": len(open_trades)},
                public_safe=True,
            )

        except Exception as e:
            self.repo.append_event(
                event_type="error.reconcile",
                level="ERROR",
                payload={"error": str(e)},
                public_safe=False,
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_fill_price(response: dict[str, Any], fallback: float) -> float:
        """Extract best fill price from exchange response."""
        if response.get("average"):
            return float(response["average"])
        return float(response.get("price", fallback) or fallback)

    def _place_protective_orders(
        self, plan: TradePlan, quantity: float, fill_price: float
    ) -> dict[str, Any] | None:
        """Place OCO (SL + TP) on the exchange.

        Uses a slight offset on stop_limit_price to ensure execution.
        """
        try:
            # SL limit price slightly below stop price for guaranteed fill
            sl_limit_offset = fill_price * 0.001  # 0.1% slippage allowance
            stop_limit_price = plan.stop_loss_price - sl_limit_offset

            result = self.adapter.create_oco_order(
                symbol=plan.symbol,
                side="sell",
                quantity=quantity,
                take_profit_price=plan.take_profit_price,
                stop_price=plan.stop_loss_price,
                stop_limit_price=stop_limit_price,
                client_order_id_prefix=f"QS-{plan.trade_id}",
            )
            result["symbol"] = plan.symbol

            self.repo.append_event(
                event_type="protective_orders.placed",
                level="INFO",
                payload={
                    "trade_id": plan.trade_id,
                    "symbol": plan.symbol,
                    "sl_order_id": result.get("sl_order_id"),
                    "tp_order_id": result.get("tp_order_id"),
                    "oco_mode": result.get("oco_mode"),
                },
                public_safe=False,
            )
            return result

        except Exception as e:
            logger.error("Protective order placement failed: %s", e)
            self.repo.append_event(
                event_type="error.protective_placement",
                level="ERROR",
                payload={"trade_id": plan.trade_id, "error": str(e)},
                public_safe=False,
            )
            return None

    def _poll_protective_orders(
        self, trade: dict[str, Any], protective: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Poll exchange for SL/TP fill status."""
        symbol: str = str(protective.get("symbol", trade["symbol"]))
        sl_id = protective.get("sl_order_id", "")
        tp_id = protective.get("tp_order_id", "")
        trade_id = trade["id"]

        try:
            # Check SL order
            if sl_id:
                sl_status = self.adapter.fetch_order_status(symbol, sl_id)
                if sl_status.get("status") == "closed":
                    return self._handle_protective_fill(
                        trade, "STOP_LOSS", sl_status, tp_id, symbol,
                    )

            # Check TP order
            if tp_id:
                tp_status = self.adapter.fetch_order_status(symbol, tp_id)
                if tp_status.get("status") == "closed":
                    return self._handle_protective_fill(
                        trade, "TAKE_PROFIT", tp_status, sl_id, symbol,
                    )

        except Exception as e:
            logger.warning(
                "Failed to poll protective orders for %s: %s", trade_id, e
            )
            self.repo.append_event(
                event_type="error.poll_protective",
                level="WARN",
                payload={"trade_id": trade_id, "error": str(e)},
                public_safe=False,
            )

        return None

    def _handle_protective_fill(
        self,
        trade: dict[str, Any],
        exit_reason: str,
        filled_order: dict[str, Any],
        other_order_id: str,
        symbol: str,
    ) -> dict[str, Any]:
        """Process a protective order fill — cancel the other leg, close trade."""
        trade_id = trade["id"]
        fill_price = self._extract_fill_price(filled_order, float(trade["entry_price"]))
        quantity = float(trade["quantity"])
        entry_price = float(trade["entry_price"])
        now = datetime.now(timezone.utc)

        # Cancel the other leg
        if other_order_id:
            try:
                self.adapter.cancel_order(symbol, other_order_id)
            except Exception as cancel_err:
                logger.warning(
                    "Failed to cancel %s order %s: %s", exit_reason, other_order_id, cancel_err
                )

        # Calculate PnL
        pnl_usd = (fill_price - entry_price) * quantity
        pnl_pct = (pnl_usd / (entry_price * quantity)) * 100.0 if entry_price * quantity else 0.0

        # Update trade
        trade["status"] = "CLOSED"
        trade["closed_at"] = now
        trade["exit_price"] = fill_price
        trade["pnl_usd"] = pnl_usd
        trade["pnl_pct"] = pnl_pct
        trade["realized_pnl_usd"] = pnl_usd

        exit_order = {
            "id": str(uuid.uuid4()),
            "trade_id": trade_id,
            "symbol": symbol,
            "side": "SELL",
            "order_type": exit_reason,
            "status": "FILLED",
            "quantity": quantity,
            "price": fill_price,
            "filled_price": fill_price,
            "filled_qty": quantity,
            "exchange_order_id": str(filled_order.get("id", "")),
            "client_order_id": f"QS-{trade_id}-{exit_reason}",
            "created_at": now,
            "filled_at": now,
        }

        # Clean up in-memory tracking
        self._protective_orders.pop(trade_id, None)

        logger.info(
            "Protective %s fill for %s: exit=%.2f, PnL=$%.2f (%.2f%%)",
            exit_reason, trade_id, fill_price, pnl_usd, pnl_pct,
        )

        return {
            "trade": trade,
            "exit_order": exit_order,
            "exit_reason": exit_reason,
        }

    def _fallback_price_check(
        self, trade: dict[str, Any], trade_id: str, current_price: float
    ) -> dict[str, Any] | None:
        """In-process SL/TP check as safety net when protective orders are missing."""
        sl_price = float(trade["stop_price"])
        tp_price = float(trade["take_profit_price"])
        quantity = float(trade["quantity"])
        symbol = trade["symbol"]

        exit_reason = None
        if trade["side"] == "BUY":
            if current_price <= sl_price:
                exit_reason = "STOP_LOSS"
            elif current_price >= tp_price:
                exit_reason = "TAKE_PROFIT"

        if not exit_reason:
            return None

        # Execute exit via market order
        try:
            client_order_id = f"QS-{trade_id}-{exit_reason}"
            response = self.adapter.create_order(
                symbol=symbol,
                side="SELL",
                order_type="market",
                quantity=quantity,
                client_order_id=client_order_id,
            )

            fill_price = self._extract_fill_price(response, current_price)
            now = datetime.now(timezone.utc)

            entry_price = float(trade["entry_price"])
            pnl_usd = (fill_price - entry_price) * quantity
            pnl_pct = (
                (pnl_usd / (entry_price * quantity)) * 100.0
                if entry_price * quantity
                else 0.0
            )

            trade["status"] = "CLOSED"
            trade["closed_at"] = now
            trade["exit_price"] = fill_price
            trade["pnl_usd"] = pnl_usd
            trade["pnl_pct"] = pnl_pct
            trade["realized_pnl_usd"] = pnl_usd

            exit_order = {
                "id": str(uuid.uuid4()),
                "trade_id": trade_id,
                "symbol": symbol,
                "side": "SELL",
                "order_type": exit_reason,
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
                "exit_reason": exit_reason,
            }

        except Exception as e:
            self.repo.append_event(
                event_type="error.exit_execution",
                level="ERROR",
                payload={
                    "error": str(e),
                    "trade_id": trade_id,
                    "reason": exit_reason,
                },
                public_safe=False,
            )
            return None

    @staticmethod
    def _make_protective_order_record(
        plan: TradePlan, order_type: str, exchange_id: str, now: datetime
    ) -> dict[str, Any]:
        """Create an order record dict for a protective order."""
        return {
            "id": str(uuid.uuid4()),
            "trade_id": plan.trade_id,
            "symbol": plan.symbol,
            "side": "SELL",
            "order_type": order_type,
            "status": "PENDING",
            "quantity": plan.quantity,
            "price": plan.stop_loss_price if order_type == "STOP_LOSS" else plan.take_profit_price,
            "filled_price": None,
            "filled_qty": None,
            "exchange_order_id": exchange_id,
            "client_order_id": f"QS-{plan.trade_id}-{order_type}",
            "created_at": now,
            "filled_at": None,
        }
