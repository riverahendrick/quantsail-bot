"""Backtest runner for executing trading strategies against historical data."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from quantsail_engine.backtest.executor import BacktestExecutor
from quantsail_engine.backtest.market_provider import BacktestMarketProvider
from quantsail_engine.backtest.metrics import BacktestMetrics, MetricsCalculator
from quantsail_engine.backtest.repository import BacktestRepository
from quantsail_engine.backtest.time_manager import TimeManager
from quantsail_engine.config.models import BotConfig
from quantsail_engine.core.state_machine import StateMachine, TradingState
from quantsail_engine.execution.position_sizer import AdaptivePositionSizer, FeeModel
from quantsail_engine.gates.cooldown_gate import CooldownGate
from quantsail_engine.gates.daily_lock import DailyLockManager
from quantsail_engine.gates.daily_symbol_limit import DailySymbolLossLimit
from quantsail_engine.gates.estimators import (
    calculate_fee,
    calculate_slippage,
    calculate_spread_cost,
)
from quantsail_engine.gates.profitability import ProfitabilityGate
from quantsail_engine.gates.regime_filter import RegimeFilter
from quantsail_engine.gates.streak_sizer import StreakSizer
from quantsail_engine.indicators.atr import calculate_atr
from quantsail_engine.models.signal import SignalType
from quantsail_engine.models.trade_plan import TradePlan
from quantsail_engine.models.trade_plan import TradePlan
from quantsail_engine.signals.ensemble_provider import EnsembleSignalProvider

logger = logging.getLogger(__name__)


class BacktestRunner:
    """Main backtest runner that executes production engine code.

    This runner orchestrates the backtesting process by:
    1. Loading historical market data
    2. Iterating through time steps
    3. Running the actual TradingLoop logic
    4. Tracking performance metrics

    Example:
        >>> config = BotConfig()
        >>> runner = BacktestRunner(
        ...     config=config,
        ...     data_file="BTC_USDT_1m.csv",
        ...     starting_cash=10000.0,
        ...     slippage_pct=0.05,
        ...     fee_pct=0.1,
        ... )
        >>> results = runner.run()
        >>> print(f"Total Return: {results.total_return_pct:.2f}%")
    """

    def __init__(
        self,
        config: BotConfig,
        data_file: str | Path,
        starting_cash: float = 10000.0,
        slippage_pct: float = 0.05,
        fee_pct: float = 0.1,
        tick_interval_seconds: int = 300,  # 5 minutes
        output_db: str | None = None,
        progress_interval: int = 100,  # Print progress every N ticks
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ):
        """Initialize backtest runner.

        Args:
            config: Bot configuration
            data_file: Path to historical OHLCV data
            starting_cash: Starting cash balance
            slippage_pct: Slippage percentage
            fee_pct: Trading fee percentage
            tick_interval_seconds: Time between simulation ticks
            output_db: Optional path to save backtest database
            progress_interval: Print progress every N ticks
        """
        self.config = config
        self.data_file = Path(data_file)
        self.starting_cash = starting_cash
        self.slippage_pct = slippage_pct
        self.fee_pct = fee_pct
        self.tick_interval_seconds = tick_interval_seconds
        self.output_db = output_db
        self.progress_interval = progress_interval
        self.start_time = start_time
        self.end_time = end_time

        # Initialize components
        self.time_manager = TimeManager()
        self.repository = BacktestRepository(
            db_path=output_db or ":memory:",
            time_manager=self.time_manager,
        )
        self.market_provider = BacktestMarketProvider(
            data_file=data_file,
            time_manager=self.time_manager,
            symbol=config.symbols.enabled[0],  # Use first enabled symbol
        )
        self.execution_engine = BacktestExecutor(
            time_manager=self.time_manager,
            slippage_pct=slippage_pct,
            fee_pct=fee_pct,
            initial_cash_usd=starting_cash,
        )
        self.signal_provider = EnsembleSignalProvider(config)
        self.regime_filter = RegimeFilter(config.strategies.regime)

        # New realism gates
        self.cooldown_gate = CooldownGate(config.cooldown)
        self.daily_symbol_limit = DailySymbolLossLimit(config.daily_symbol_limit)
        self.streak_sizer = StreakSizer(config.streak_sizer)

        # Initialize trading components (same as TradingLoop)
        self.profitability_gate = ProfitabilityGate(
            min_profit_usd=config.execution.min_profit_usd
        )
        self.daily_lock_manager = DailyLockManager(
            config=config.daily,
            repo=self.repository,
        )

        # Adaptive position sizing — uses config fee rates
        self.position_sizer = AdaptivePositionSizer(
            fee_model=FeeModel(
                taker_rate_bps=config.execution.taker_fee_bps,
                maker_rate_bps=config.execution.taker_fee_bps,
                use_bnb_discount=False,  # Backtest assumes raw fees
            ),
            min_profit_floor=config.execution.min_profit_usd,
            max_risk_pct=config.risk.max_risk_per_trade_pct
            if hasattr(config, "risk")
            else 1.0,
            sizing_config=config.position_sizing,
        )

        # State machines per symbol
        self.state_machines: dict[str, StateMachine] = {}
        self.open_trades: dict[str, str] = {}  # symbol -> trade_id
        self._pending_exits: dict[str, dict] = {}  # symbol -> cached exit_result
        self._pending_plans: dict[str, TradePlan] = {}  # symbol -> cached TradePlan

        for symbol in config.symbols.enabled:
            self.state_machines[symbol] = StateMachine(symbol)

        # Statistics
        self.tick_count = 0
        self.trades_executed = 0
        self.last_known_price = 0.0

    def _get_orderbook(self, symbol: str) -> Any:
        """Get current orderbook for symbol."""
        return self.market_provider.get_orderbook(symbol, depth_levels=5)

    def _get_candles(self, symbol: str, limit: int = 100) -> list[Any]:
        """Get recent candles for symbol."""
        # Try different timeframes - backtest typically uses 1m or 5m data
        # The provider should return available data regardless of timeframe request
        try:
            return self.market_provider.get_candles(symbol, "5m", limit)
        except ValueError:
            return self.market_provider.get_candles(symbol, "1m", limit)

    def _calculate_sl_price(
        self, entry_price: float, candles: list[Any]
    ) -> float:
        """Calculate stop-loss price from config (ATR or fixed_pct).

        Args:
            entry_price: Entry price for the trade.
            candles: Recent candles for ATR calculation.

        Returns:
            Stop-loss price below entry.
        """
        sl_config = self.config.stop_loss

        if sl_config.method == "atr" and len(candles) >= sl_config.atr_period + 1:
            atr_values = calculate_atr(candles, sl_config.atr_period)
            current_atr = atr_values[-1]
            sl_price = entry_price - (current_atr * sl_config.atr_multiplier)
        else:
            # Fallback to fixed_pct
            sl_price = entry_price * (1.0 - sl_config.fixed_pct / 100.0)

        return max(sl_price, 0.01)  # Never go below $0.01

    def _calculate_tp_price(
        self, entry_price: float, sl_price: float, candles: list[Any]
    ) -> float:
        """Calculate take-profit price from config (risk_reward, ATR, or fixed_pct).

        Args:
            entry_price: Entry price for the trade.
            sl_price: Stop-loss price (needed for risk_reward method).
            candles: Recent candles for ATR calculation.

        Returns:
            Take-profit price above entry.
        """
        tp_config = self.config.take_profit

        if tp_config.method == "risk_reward":
            sl_distance = entry_price - sl_price
            tp_price = entry_price + (sl_distance * tp_config.risk_reward_ratio)
        elif tp_config.method == "atr" and len(candles) >= 15:
            atr_values = calculate_atr(candles, 14)
            current_atr = atr_values[-1]
            tp_price = entry_price + (current_atr * tp_config.atr_multiplier)
        else:
            # Fallback to fixed_pct
            tp_price = entry_price * (1.0 + tp_config.fixed_pct / 100.0)

        return tp_price

    def _tick_symbol(self, symbol: str) -> None:
        """Execute one tick for a specific symbol (reproduces TradingLoop logic)."""
        sm = self.state_machines[symbol]

        # Emit market.tick event
        self.repository.append_event(
            event_type="market.tick",
            level="INFO",
            payload={"symbol": symbol},
            public_safe=True,
        )

        # IDLE → EVAL
        if sm.current_state == TradingState.IDLE:
            sm.transition_to(TradingState.EVAL)

        # EVAL: Fetch market data and generate signal
        if sm.current_state == TradingState.EVAL:
            candles = self._get_candles(symbol, limit=100)
            orderbook = self._get_orderbook(symbol)

            # Set current candle for executor price reference
            if candles:
                self.execution_engine.set_current_candle(candles[-1])

            # 0. Check Market Regime (Gate) — with per-symbol overrides
            if not self.regime_filter.analyze(candles, symbol=symbol):
                self.repository.append_event(
                    event_type="gate.regime.rejected",
                    level="INFO",
                    payload={"symbol": symbol, "reason": "choppy_market_detected"},
                    public_safe=True,
                )
                sm.transition_to(TradingState.IDLE)
                return

            # 0b. Check stop-loss cooldown
            cooldown_ok, cooldown_reason = self.cooldown_gate.is_allowed(
                symbol, self.time_manager.now()
            )
            if not cooldown_ok:
                self.repository.append_event(
                    event_type="gate.cooldown.rejected",
                    level="INFO",
                    payload={"symbol": symbol, "reason": cooldown_reason},
                    public_safe=True,
                )
                sm.transition_to(TradingState.IDLE)
                return

            # 0c. Check daily per-symbol loss limit
            daily_ok, daily_reason = self.daily_symbol_limit.is_allowed(
                symbol, self.time_manager.now()
            )
            if not daily_ok:
                self.repository.append_event(
                    event_type="gate.daily_symbol_limit.rejected",
                    level="WARN",
                    payload={"symbol": symbol, "reason": daily_reason},
                    public_safe=True,
                )
                sm.transition_to(TradingState.IDLE)
                return

            # 1. Get Signal
            signal = self.signal_provider.generate_signal(symbol, candles, orderbook)

            # Emit per-strategy events
            for output in signal.strategy_outputs:
                self.repository.append_event(
                    event_type="signal.generated",
                    level="INFO",
                    payload={
                        "symbol": symbol,
                        "strategy": output.strategy_name,
                        "signal": output.signal,
                        "confidence": output.confidence,
                        "rationale": output.rationale,
                    },
                    public_safe=True,
                )

            # Emit ensemble decision event
            from quantsail_engine.models.signal import SignalType
            votes = sum(
                1 for o in signal.strategy_outputs if o.signal == SignalType.ENTER_LONG
            )
            self.repository.append_event(
                event_type="ensemble.decision",
                level="INFO",
                payload={
                    "symbol": symbol,
                    "signal_type": signal.signal_type,
                    "confidence": signal.confidence,
                    "votes": votes,
                    "total_strategies": len(signal.strategy_outputs),
                },
                public_safe=True,
            )

            # Check if we should enter
            if signal.signal_type == SignalType.ENTER_LONG:
                # Check daily lock
                entries_allowed, rejection_reason = self.daily_lock_manager.entries_allowed()
                if not entries_allowed:
                    self.repository.append_event(
                        event_type="gate.daily_lock.rejected",
                        level="WARN",
                        payload={"symbol": symbol, "reason": rejection_reason},
                        public_safe=True,
                    )
                    sm.transition_to(TradingState.IDLE)
                    return

                # Check position limits
                num_open_positions = len(self.open_trades)
                if num_open_positions >= self.config.symbols.max_concurrent_positions:
                    self.repository.append_event(
                        event_type="gate.max_positions.rejected",
                        level="WARN",
                        payload={
                            "symbol": symbol,
                            "open_positions": num_open_positions,
                            "max_allowed": self.config.symbols.max_concurrent_positions,
                        },
                        public_safe=False,
                    )
                    sm.transition_to(TradingState.IDLE)
                    return

                # Calculate dynamic SL/TP from config
                entry_price = orderbook.mid_price
                sl_price = self._calculate_sl_price(entry_price, candles)
                tp_price = self._calculate_tp_price(entry_price, sl_price, candles)

                # Use AdaptivePositionSizer to find optimal trade size
                equity = self.execution_engine.wallet.cash_usd
                sizing_result = self.position_sizer.find_optimal_size(
                    entry_price=entry_price,
                    target_price=tp_price,
                    stop_price=sl_price,
                    equity=equity,
                )

                if not sizing_result:
                    self.repository.append_event(
                        event_type="gate.sizing.rejected",
                        level="WARN",
                        payload={
                            "symbol": symbol,
                            "reason": "no_viable_size",
                            "entry": entry_price,
                            "sl": sl_price,
                            "tp": tp_price,
                            "equity": equity,
                        },
                        public_safe=False,
                    )
                    sm.transition_to(TradingState.IDLE)
                    return

                quantity = sizing_result.quantity

                # Apply streak sizer reduction
                streak_mult = self.streak_sizer.get_multiplier(symbol)
                if streak_mult < 1.0:
                    quantity = quantity * streak_mult
                    self.repository.append_event(
                        event_type="gate.streak_sizer.applied",
                        level="INFO",
                        payload={
                            "symbol": symbol,
                            "multiplier": streak_mult,
                            "adjusted_quantity": quantity,
                        },
                        public_safe=False,
                    )

                plan = TradePlan(
                    symbol=symbol,
                    side="BUY",
                    entry_price=entry_price,
                    quantity=quantity,
                    stop_loss_price=sl_price,
                    take_profit_price=tp_price,
                    estimated_fee_usd=sizing_result.total_fees,
                    estimated_slippage_usd=sizing_result.slippage_cost,
                    estimated_spread_cost_usd=sizing_result.spread_cost,
                    trade_id=f"trade-{self.trades_executed}",
                    timestamp=self.time_manager.now(),
                )

                # Evaluate profitability gate
                passed, breakdown = self.profitability_gate.evaluate(plan)

                if passed:
                    self.repository.append_event(
                        event_type="gate.profitability.passed",
                        level="INFO",
                        payload=breakdown,
                        public_safe=False,
                    )
                    # Cache plan for ENTRY_PENDING
                    self._pending_plans[symbol] = plan
                    sm.transition_to(TradingState.ENTRY_PENDING)
                else:
                    self.repository.append_event(
                        event_type="gate.profitability.rejected",
                        level="WARN",
                        payload=breakdown,
                        public_safe=False,
                    )
                    sm.transition_to(TradingState.IDLE)
                    return

            else:
                # No entry signal, back to IDLE
                sm.transition_to(TradingState.IDLE)
                return

        # ENTRY_PENDING: Execute entry using cached plan
        if sm.current_state == TradingState.ENTRY_PENDING:
            plan = self._pending_plans.pop(symbol, None)
            if not plan:
                # Safety fallback — should not happen
                sm.reset()
                return

            # Ensure executor has current candle for price reference
            candles = self._get_candles(symbol, limit=100)
            if candles:
                self.execution_engine.set_current_candle(candles[-1])

            result = self.execution_engine.execute_entry(plan)
            if not result:
                self.repository.append_event(
                    event_type="execution.failed",
                    level="ERROR",
                    payload={"symbol": symbol, "reason": "entry_execution_failed"},
                    public_safe=False,
                )
                sm.transition_to(TradingState.IDLE)
                return

            trade = result["trade"]
            orders = result["orders"]

            # Persist trade and orders
            self.repository.save_trade(trade)
            for order in orders:
                self.repository.save_order(order)

            # Emit events
            self.repository.append_event(
                event_type="trade.opened",
                level="INFO",
                payload={
                    "trade_id": trade["id"],
                    "symbol": symbol,
                    "entry_price": trade["entry_price"],
                    "quantity": trade["quantity"],
                },
                public_safe=True,
            )

            # Track open trade
            self.open_trades[symbol] = trade["id"]
            self.trades_executed += 1

            sm.transition_to(TradingState.IN_POSITION)

        # IN_POSITION: Check for exits
        if sm.current_state == TradingState.IN_POSITION:
            trade_id = self.open_trades.get(symbol)
            if not trade_id:
                sm.reset()
                return

            # Get current price
            orderbook = self._get_orderbook(symbol)
            current_price = orderbook.mid_price

            # Check if SL or TP hit — check_exits processes the full exit
            # (wallet sell, PnL calc, status update) and removes the trade
            # from executor._open_trades.  We cache the result so that the
            # EXIT_PENDING handler can persist it without a second call.
            exit_result = self.execution_engine.check_exits(trade_id, current_price)

            if exit_result:
                self._pending_exits[symbol] = exit_result
                sm.transition_to(TradingState.EXIT_PENDING)

        # EXIT_PENDING: Finalize exit using cached result
        if sm.current_state == TradingState.EXIT_PENDING:
            exit_result = self._pending_exits.pop(symbol, None)
            if not exit_result:
                # Safety fallback — should not happen
                sm.reset()
                return

            trade = exit_result["trade"]
            exit_order = exit_result["exit_order"]
            exit_reason = exit_result["exit_reason"]

            # Update trade in DB (status → CLOSED, PnL, exit_price)
            self.repository.update_trade(trade)

            # Save exit order
            self.repository.save_order(exit_order)

            # Record exit for realism gates
            pnl = trade.get("realized_pnl_usd", 0.0)
            exit_ts = self.time_manager.now()
            is_win = pnl is not None and pnl > 0

            self.cooldown_gate.record_exit(symbol, exit_reason, exit_ts)

            if is_win:
                self.daily_symbol_limit.record_win(symbol, exit_ts)
                self.streak_sizer.record_result(symbol, won=True)
            else:
                self.daily_symbol_limit.record_loss(symbol, exit_ts)
                self.streak_sizer.record_result(symbol, won=False)

            # Emit events
            self.repository.append_event(
                event_type="trade.closed",
                level="INFO",
                payload={
                    "trade_id": trade["id"],
                    "symbol": symbol,
                    "exit_reason": exit_reason,
                    "exit_price": trade["exit_price"],
                    "pnl_usd": pnl,
                    "pnl_pct": trade.get("pnl_pct"),
                },
                public_safe=True,
            )

            # Remove from open trades
            del self.open_trades[symbol]

            sm.transition_to(TradingState.IDLE)

    def _tick(self) -> None:
        """Execute one tick of the backtest for all symbols."""
        for symbol in self.config.symbols.enabled:
            self._tick_symbol(symbol)

        # Update equity snapshot
        wallet = self.execution_engine.get_wallet()
        try:
            orderbook = self._get_orderbook(self.config.symbols.enabled[0])
            current_price = orderbook.mid_price
            self.last_known_price = current_price
        except Exception:
            current_price = self.last_known_price

        equity = wallet.get_equity(current_price)
        self.repository.save_equity_snapshot(equity_usd=equity)

    def run(self) -> BacktestMetrics:
        """Run the backtest.

        Iterates through historical data and executes trading logic.

        Returns:
            BacktestMetrics with performance results
        """
        print("🚀 Starting Backtest")
        print(f"   Data: {self.data_file}")
        print(f"   Starting Cash: ${self.starting_cash:.2f}")
        print(f"   Slippage: {self.slippage_pct}%")
        print(f"   Fee: {self.fee_pct}%")
        print(f"   Tick Interval: {self.tick_interval_seconds}s")
        print()

        # Emit start event
        self.repository.append_event(
            event_type="system.started",
            level="INFO",
            payload={
                "mode": "backtest",
                "starting_cash": self.starting_cash,
                "slippage_pct": self.slippage_pct,
                "fee_pct": self.fee_pct,
            },
            public_safe=True,
        )

        # Iterate through historical data
        data_start, data_end = self.market_provider.get_data_range()
        print(f"📅 Data Range: {data_start} to {data_end}")
        print()

        total_ticks = 0

        for timestamp in self.market_provider.iter_timestamps(
            self.tick_interval_seconds,
            start_time=self.start_time,
            end_time=self.end_time,
        ):
            self.time_manager.set_time(timestamp)
            self._tick()
            total_ticks += 1

            # Progress indicator
            if total_ticks % self.progress_interval == 0:
                wallet = self.execution_engine.get_wallet()
                try:
                    orderbook = self._get_orderbook(self.config.symbols.enabled[0])
                    equity = wallet.get_equity(orderbook.mid_price)
                except Exception:
                    equity = wallet.cash_usd

                print(f"   Tick {total_ticks} | {timestamp.strftime('%Y-%m-%d %H:%M')} | Equity: ${equity:.2f}")

        print()
        print(f"✅ Backtest Complete: {total_ticks} ticks processed")
        print(f"   Trades Executed: {self.trades_executed}")

        # Emit end event
        self.repository.append_event(
            event_type="system.stopped",
            level="INFO",
            payload={"ticks_executed": total_ticks},
            public_safe=True,
        )

        # Calculate metrics
        return self._calculate_metrics()

    def _calculate_metrics(self) -> BacktestMetrics:
        """Calculate and return performance metrics."""
        calculator = MetricsCalculator(starting_equity=self.starting_cash)

        # Add all trades
        trades = self.repository.get_all_trades()
        for trade in trades:
            calculator.add_trade(trade)

        # Add equity curve
        equity_curve = self.repository.get_equity_curve()
        for timestamp, equity in equity_curve:
            calculator.add_equity_point(timestamp, equity)

        # Set safety stats
        calculator.set_safety_stats(
            breaker_triggers=self.repository.get_circuit_breaker_count(),
            daily_lock_hits=self.repository.get_daily_lock_count(),
        )

        return calculator.calculate()

    def save_report(self, metrics: BacktestMetrics, output_path: str | Path) -> None:
        """Save backtest report to JSON file.

        Args:
            metrics: Backtest metrics to save
            output_path: Output file path
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        report = {
            "backtest_config": {
                "data_file": str(self.data_file),
                "starting_cash": self.starting_cash,
                "slippage_pct": self.slippage_pct,
                "fee_pct": self.fee_pct,
                "tick_interval_seconds": self.tick_interval_seconds,
                "symbols": self.config.symbols.enabled,
            },
            "metrics": metrics.to_dict(),
        }

        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"📄 Report saved to: {output_path}")

    def close(self) -> None:
        """Clean up resources."""
        self.repository.close()
