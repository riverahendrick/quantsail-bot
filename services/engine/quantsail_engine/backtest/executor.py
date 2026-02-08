"""Backtest execution engine with configurable slippage and fees."""

import uuid
from datetime import datetime, timezone
from typing import Any

from quantsail_engine.backtest.time_manager import TimeManager
from quantsail_engine.execution.executor import ExecutionEngine
from quantsail_engine.models.candle import Candle
from quantsail_engine.models.trade_plan import TradePlan


class VirtualWallet:
    """Virtual wallet for tracking balance during backtesting.

    Tracks both cash (USD) and asset holdings to calculate
    true equity throughout the backtest.

    Example:
        >>> wallet = VirtualWallet(initial_cash_usd=10000.0)
        >>> wallet.deposit_asset("BTC", 0.5, 50000.0)
        >>> print(wallet.get_equity(51000.0))  # Current BTC price
    """

    def __init__(self, initial_cash_usd: float = 10000.0):
        """Initialize virtual wallet.

        Args:
            initial_cash_usd: Starting cash balance in USD
        """
        self.cash_usd = initial_cash_usd
        self.initial_cash_usd = initial_cash_usd
        self.assets: dict[str, float] = {}  # symbol -> quantity
        self.trade_history: list[dict[str, Any]] = []

    def get_asset_quantity(self, symbol: str) -> float:
        """Get quantity of asset held.

        Args:
            symbol: Asset symbol (e.g., "BTC")

        Returns:
            Quantity held
        """
        base_symbol = symbol.split("/")[0] if "/" in symbol else symbol
        return self.assets.get(base_symbol, 0.0)

    def get_equity(self, current_price: float, symbol: str = "BTC/USDT") -> float:
        """Calculate total equity in USD.

        Args:
            current_price: Current market price of the asset
            symbol: Trading pair for asset valuation

        Returns:
            Total equity (cash + asset value)
        """
        base_symbol = symbol.split("/")[0] if "/" in symbol else symbol
        asset_value = self.assets.get(base_symbol, 0.0) * current_price
        return self.cash_usd + asset_value

    def can_afford(self, quantity: float, price: float) -> bool:
        """Check if wallet has enough cash for a buy order.

        Args:
            quantity: Quantity to buy
            price: Price per unit

        Returns:
            True if affordable
        """
        cost = quantity * price
        return self.cash_usd >= cost

    def execute_buy(
        self,
        symbol: str,
        quantity: float,
        price: float,
        fee_usd: float,
        slippage_usd: float,
        timestamp: datetime,
    ) -> dict[str, Any]:
        """Execute a buy order.

        Args:
            symbol: Trading pair (e.g., "BTC/USDT")
            quantity: Quantity to buy
            price: Fill price
            fee_usd: Fee paid in USD
            slippage_usd: Slippage cost in USD
            timestamp: Execution timestamp

        Returns:
            Trade record

        Raises:
            ValueError: If insufficient funds
        """
        base_symbol = symbol.split("/")[0] if "/" in symbol else symbol
        total_cost = quantity * price + fee_usd + slippage_usd

        if self.cash_usd < total_cost:
            raise ValueError(
                f"Insufficient funds: ${self.cash_usd:.2f} < ${total_cost:.2f}"
            )

        self.cash_usd -= total_cost
        self.assets[base_symbol] = self.assets.get(base_symbol, 0.0) + quantity

        trade_record = {
            "symbol": symbol,
            "side": "BUY",
            "quantity": quantity,
            "price": price,
            "fee_usd": fee_usd,
            "slippage_usd": slippage_usd,
            "total_cost": total_cost,
            "timestamp": timestamp,
            "cash_after": self.cash_usd,
            "asset_after": self.assets[base_symbol],
        }
        self.trade_history.append(trade_record)

        return trade_record

    def execute_sell(
        self,
        symbol: str,
        quantity: float,
        price: float,
        fee_usd: float,
        slippage_usd: float,
        timestamp: datetime,
    ) -> dict[str, Any]:
        """Execute a sell order.

        Args:
            symbol: Trading pair (e.g., "BTC/USDT")
            quantity: Quantity to sell
            price: Fill price
            fee_usd: Fee paid in USD
            slippage_usd: Slippage cost in USD
            timestamp: Execution timestamp

        Returns:
            Trade record

        Raises:
            ValueError: If insufficient assets
        """
        base_symbol = symbol.split("/")[0] if "/" in symbol else symbol
        current_qty = self.assets.get(base_symbol, 0.0)

        if current_qty < quantity:
            raise ValueError(
                f"Insufficient {base_symbol}: {current_qty} < {quantity}"
            )

        proceeds = quantity * price - fee_usd - slippage_usd
        self.cash_usd += proceeds
        self.assets[base_symbol] = current_qty - quantity

        # Clean up zero balances
        if self.assets[base_symbol] == 0:
            del self.assets[base_symbol]

        trade_record = {
            "symbol": symbol,
            "side": "SELL",
            "quantity": quantity,
            "price": price,
            "fee_usd": fee_usd,
            "slippage_usd": slippage_usd,
            "proceeds": proceeds,
            "timestamp": timestamp,
            "cash_after": self.cash_usd,
            "asset_after": self.assets.get(base_symbol, 0.0),
        }
        self.trade_history.append(trade_record)

        return trade_record


class BacktestExecutor(ExecutionEngine):
    """Execution engine for backtesting with realistic fill simulation.

    Simulates order execution with configurable slippage and fees.
    Maintains a virtual wallet to track true equity.

    Example:
        >>> time_mgr = TimeManager()
        >>> executor = BacktestExecutor(
        ...     time_manager=time_mgr,
        ...     slippage_pct=0.05,  # 0.05% slippage
        ...     fee_pct=0.1,        # 0.1% trading fee
        ...     initial_cash_usd=10000.0
        ... )
    """

    def __init__(
        self,
        time_manager: TimeManager,
        slippage_pct: float = 0.05,  # 0.05% default slippage
        fee_pct: float = 0.1,        # 0.1% default fee
        initial_cash_usd: float = 10000.0,
    ):
        """Initialize backtest executor.

        Args:
            time_manager: Time manager for simulated timestamps
            slippage_pct: Slippage percentage (e.g., 0.05 for 0.05%)
            fee_pct: Trading fee percentage (e.g., 0.1 for 0.1%)
            initial_cash_usd: Starting cash balance
        """
        self.time_manager = time_manager
        self.slippage_pct = slippage_pct
        self.fee_pct = fee_pct
        self.wallet = VirtualWallet(initial_cash_usd)
        self._open_trades: dict[str, dict[str, Any]] = {}

    def _get_current_candle(self) -> Candle | None:
        """Get current candle from time manager context.

        In a real implementation, this would come from market data.
        For now, we use the last known close price for fills.
        """
        # This is set externally before execute_entry is called
        return getattr(self, '_current_candle', None)

    def set_current_candle(self, candle: Candle) -> None:
        """Set the current candle for price reference.

        This should be called before each tick to ensure
        fills use the correct price.

        Args:
            candle: Current OHLCV candle
        """
        self._current_candle = candle

    def _apply_slippage(self, price: float, side: str) -> float:
        """Apply slippage to fill price.

        For buys: price goes up (worse fill)
        For sells: price goes down (worse fill)

        Args:
            price: Expected fill price
            side: Order side ("BUY" or "SELL")

        Returns:
            Adjusted fill price with slippage
        """
        slippage_factor = self.slippage_pct / 100.0
        if side == "BUY":
            return price * (1 + slippage_factor)
        else:  # SELL
            return price * (1 - slippage_factor)

    def _calculate_fee(self, notional_value: float) -> float:
        """Calculate trading fee.

        Args:
            notional_value: Trade notional value

        Returns:
            Fee amount in same currency
        """
        return notional_value * (self.fee_pct / 100.0)

    def execute_entry(self, plan: TradePlan) -> dict[str, Any] | None:
        """Execute entry order with simulated fill.

        Args:
            plan: Trade plan to execute

        Returns:
            Dictionary with trade and orders data, or None if failed
        """
        now = self.time_manager.now()

        # Get current price (from candle if available, else plan)
        candle = self._get_current_candle()
        base_price = candle.close if candle else plan.entry_price

        # Apply slippage to entry
        fill_price = self._apply_slippage(base_price, plan.side)
        notional = fill_price * plan.quantity
        fee = self._calculate_fee(notional)
        slippage_cost = notional * (self.slippage_pct / 100.0)

        try:
            # Execute through wallet
            self.wallet.execute_buy(
                symbol=plan.symbol,
                quantity=plan.quantity,
                price=fill_price,
                fee_usd=fee,
                slippage_usd=slippage_cost,
                timestamp=now,
            )
        except ValueError as e:
            print(f"   ❌ Entry failed: {e}")
            return None

        trade_id = str(uuid.uuid4())

        # Create trade record
        trade = {
            "id": trade_id,
            "symbol": plan.symbol,
            "mode": "BACKTEST",
            "status": "OPEN",
            "side": plan.side,
            "entry_price": fill_price,
            "quantity": plan.quantity,
            "opened_at": now,
            "stop_price": plan.stop_loss_price,
            "take_profit_price": plan.take_profit_price,
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
            "filled_price": fill_price,
            "filled_qty": plan.quantity,
            "created_at": now,
            "filled_at": now,
            "fee_usd": fee,
            "slippage_usd": slippage_cost,
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

        # Store open trade
        self._open_trades[trade_id] = {
            "trade": trade,
            "sl_price": plan.stop_loss_price,
            "tp_price": plan.take_profit_price,
            "sl_order": sl_order,
            "tp_order": tp_order,
            "entry_price": fill_price,  # Store actual fill for PnL calc
        }

        return {
            "trade": trade,
            "orders": [entry_order, sl_order, tp_order],
        }

    def check_exits(self, trade_id: str, current_price: float) -> dict[str, Any] | None:
        """Check if SL or TP is hit and simulate exit.

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
        entry_price = trade_data["entry_price"]

        exit_reason = None
        exit_price_trigger = None

        # Check SL/TP for long positions (BUY side)
        if trade["side"] == "BUY":
            if current_price <= sl_price:
                exit_reason = "STOP_LOSS"
                exit_price_trigger = sl_price
            elif current_price >= tp_price:
                exit_reason = "TAKE_PROFIT"
                exit_price_trigger = tp_price

        if exit_reason is None or exit_price_trigger is None:
            return None

        # Simulate exit fill with slippage
        exit_side = "SELL" if trade["side"] == "BUY" else "BUY"
        fill_price = self._apply_slippage(exit_price_trigger, exit_side)

        now = self.time_manager.now()
        notional = fill_price * trade["quantity"]
        fee = self._calculate_fee(notional)
        slippage_cost = notional * (self.slippage_pct / 100.0)

        try:
            # Execute through wallet
            self.wallet.execute_sell(
                symbol=trade["symbol"],
                quantity=trade["quantity"],
                price=fill_price,
                fee_usd=fee,
                slippage_usd=slippage_cost,
                timestamp=now,
            )
        except ValueError as e:
            print(f"   ❌ Exit failed: {e}")
            return None

        # Calculate PnL
        gross_pnl = (fill_price - entry_price) * trade["quantity"]
        total_costs = fee + slippage_cost + self._calculate_fee(entry_price * trade["quantity"])
        net_pnl = gross_pnl - total_costs
        pnl_pct = (net_pnl / (entry_price * trade["quantity"])) * 100.0 if entry_price > 0 else 0.0

        # Update trade
        trade["status"] = "CLOSED"
        trade["closed_at"] = now
        trade["exit_price"] = fill_price
        trade["realized_pnl_usd"] = net_pnl
        trade["pnl_pct"] = pnl_pct

        # Create exit order
        exit_order = {
            "id": str(uuid.uuid4()),
            "trade_id": trade_id,
            "symbol": trade["symbol"],
            "side": exit_side,
            "order_type": exit_reason,
            "status": "FILLED",
            "quantity": trade["quantity"],
            "price": exit_price_trigger,
            "filled_price": fill_price,
            "filled_qty": trade["quantity"],
            "created_at": now,
            "filled_at": now,
            "fee_usd": fee,
            "slippage_usd": slippage_cost,
            "pnl_usd": net_pnl,
        }

        # Update SL/TP order statuses
        if exit_reason == "STOP_LOSS":
            trade_data["sl_order"]["status"] = "FILLED"
            trade_data["sl_order"]["filled_price"] = fill_price
            trade_data["sl_order"]["filled_qty"] = trade["quantity"]
            trade_data["sl_order"]["filled_at"] = now
            trade_data["tp_order"]["status"] = "CANCELLED"
        else:  # TAKE_PROFIT
            trade_data["tp_order"]["status"] = "FILLED"
            trade_data["tp_order"]["filled_price"] = fill_price
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

    def get_wallet(self) -> VirtualWallet:
        """Get the virtual wallet for equity tracking.

        Returns:
            Virtual wallet instance
        """
        return self.wallet

    def get_open_trades(self) -> dict[str, dict[str, Any]]:
        """Get all currently open trades.

        Returns:
            Dictionary of open trades by trade_id
        """
        return self._open_trades.copy()
