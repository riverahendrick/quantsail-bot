import logging
import signal
from typing import Any

from sqlalchemy.orm import Session

from quantsail_engine.breakers.manager import BreakerManager
from quantsail_engine.breakers.triggers import (
    check_consecutive_losses,
    check_spread_slippage_spike,
    check_volatility_spike,
)
from quantsail_engine.config.models import BotConfig
from quantsail_engine.core.state_machine import StateMachine, TradingState
from quantsail_engine.execution.executor import ExecutionEngine
from quantsail_engine.gates.daily_lock import DailyLockManager
from quantsail_engine.gates.estimators import (
    calculate_fee,
    calculate_slippage,
    calculate_spread_cost,
)
from quantsail_engine.gates.profitability import ProfitabilityGate
from quantsail_engine.indicators.atr import calculate_atr
from quantsail_engine.market_data.provider import MarketDataProvider
from quantsail_engine.models.signal import SignalType
from quantsail_engine.models.trade_plan import TradePlan
from quantsail_engine.persistence.repository import EngineRepository
from quantsail_engine.signals.provider import SignalProvider

logger = logging.getLogger(__name__)


class TradingLoop:
    """Main trading loop coordinating per-symbol state machines."""

    def __init__(
        self,
        config: BotConfig,
        session: Session,
        market_data_provider: MarketDataProvider,
        signal_provider: SignalProvider,
        execution_engine: ExecutionEngine,
    ):
        """
        Initialize trading loop.

        Args:
            config: Bot configuration
            session: Database session
            market_data_provider: Market data provider
            signal_provider: Signal provider
            execution_engine: Execution engine
        """
        self.config = config
        self.repo = EngineRepository(session)
        self.market_data_provider = market_data_provider
        self.signal_provider = signal_provider
        self.execution_engine = execution_engine

        # Initialize profitability gate
        self.profitability_gate = ProfitabilityGate(
            min_profit_usd=config.execution.min_profit_usd
        )

        # Initialize breaker manager
        self.breaker_manager = BreakerManager(
            config=config.breakers,
            repo=self.repo
        )
        
        # Initialize daily lock manager
        self.daily_lock_manager = DailyLockManager(
            config=config.daily,
            repo=self.repo
        )

        # Initialize per-symbol state machines
        self.state_machines: dict[str, StateMachine] = {}
        self.open_trades: dict[str, str] = {}  # symbol -> trade_id

        for symbol in config.symbols.enabled:
            self.state_machines[symbol] = StateMachine(symbol)

        # Shutdown flag
        self._shutdown_requested = False

    def tick(self) -> None:
        """Execute one tick of the trading loop for all symbols."""
        logger.info("📊 Tick started")
        for symbol in self.config.symbols.enabled:
            logger.info(f"  Symbol: {symbol}")
            self._tick_symbol(symbol)

        # Update equity snapshot after all symbols processed
        equity = self.repo.calculate_equity(self.config.risk.starting_cash_usd)
        self.repo.save_equity_snapshot(equity)
        logger.info(f"  Equity: ${equity:.2f}")

    def _tick_symbol(self, symbol: str) -> None:
        """
        Execute one tick for a specific symbol.

        State machine flow:
        IDLE → EVAL → (signal check) → ENTRY_PENDING → IN_POSITION → EXIT_PENDING → IDLE

        Args:
            symbol: Trading symbol
        """
        sm = self.state_machines[symbol]

        # Emit market.tick event
        self.repo.append_event(
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
            candles = self.market_data_provider.get_candles(symbol, "5m", 100)
            orderbook = self.market_data_provider.get_orderbook(symbol, 5)
            signal = self.signal_provider.generate_signal(symbol, candles, orderbook)
            logger.info(f"    State: {sm.current_state.value}, Signal: {signal.signal_type}")

            # Emit per-strategy events
            for output in signal.strategy_outputs:
                self.repo.append_event(
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
            votes = sum(
                1 for o in signal.strategy_outputs if o.signal == SignalType.ENTER_LONG
            )
            self.repo.append_event(
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
                # Check if entries allowed (fast check for active breakers and news pause)
                entries_allowed, rejection_reason = self.breaker_manager.entries_allowed()
                if not entries_allowed:
                    # Determine event type based on rejection reason
                    if rejection_reason and "news" in rejection_reason:
                        event_type = "gate.news.rejected"
                    else:
                        event_type = "gate.breaker.rejected"

                    self.repo.append_event(
                        event_type=event_type,
                        level="WARN",
                        payload={"symbol": symbol, "reason": rejection_reason},
                        public_safe=True,
                    )
                    sm.transition_to(TradingState.IDLE)
                    return
                
                # Check daily lock
                entries_allowed, rejection_reason = self.daily_lock_manager.entries_allowed()
                if not entries_allowed:
                    self.repo.append_event(
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
                    # Reject: max positions reached
                    self.repo.append_event(
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

                # Calculate Trade Plan with Real Estimators
                quantity = 0.01  # Fixed for now (Risk sizing in Prompt 08/09?)
                
                try:
                    avg_fill_price, slippage_usd = calculate_slippage(
                        "BUY", quantity, orderbook
                    )
                except ValueError as e:
                    logger.warning(f"    ❌ Slippage estimation failed: {e}")
                    self.repo.append_event(
                        event_type="gate.liquidity.rejected",
                        level="WARN",
                        payload={"symbol": symbol, "reason": str(e)},
                        public_safe=False,
                    )
                    sm.transition_to(TradingState.IDLE)
                    return

                fee_usd = calculate_fee(
                    avg_fill_price * quantity, self.config.execution.taker_fee_bps
                )
                spread_cost_usd = calculate_spread_cost("BUY", quantity, orderbook)
                
                # Entry price for plan is usually the estimated average fill price
                entry_price = avg_fill_price
                
                # Simple SL/TP logic (2% / 4% relative to entry)
                import uuid
                from datetime import datetime, timezone
                
                plan = TradePlan(
                    symbol=symbol,
                    side="BUY",
                    entry_price=entry_price,
                    quantity=quantity,
                    stop_loss_price=entry_price * 0.98,
                    take_profit_price=entry_price * 1.04,
                    estimated_fee_usd=fee_usd,
                    estimated_slippage_usd=slippage_usd,
                    estimated_spread_cost_usd=spread_cost_usd,
                    trade_id=f"trade-{uuid.uuid4()}",
                    timestamp=datetime.now(timezone.utc),
                )

                # Check individual breaker triggers AFTER plan creation
                # Calculate ATR for volatility check
                atr_values = calculate_atr(candles, period=14)

                # Check volatility spike
                should_trigger, context = check_volatility_spike(
                    self.config.breakers.volatility, symbol, candles, atr_values
                )
                if should_trigger:
                    assert context is not None  # Type narrowing
                    self.breaker_manager.trigger_breaker(
                        "volatility", "ATR spike detected",
                        self.config.breakers.volatility.pause_minutes, context
                    )
                    sm.transition_to(TradingState.IDLE)
                    return

                # Check spread/slippage spike
                should_trigger, context = check_spread_slippage_spike(
                    self.config.breakers.spread_slippage, symbol, orderbook, plan
                )
                if should_trigger:
                    assert context is not None  # Type narrowing
                    self.breaker_manager.trigger_breaker(
                        "spread_slippage", "Spread spike detected",
                        self.config.breakers.spread_slippage.pause_minutes, context
                    )
                    sm.transition_to(TradingState.IDLE)
                    return

                # Check consecutive losses
                should_trigger, context = check_consecutive_losses(
                    self.config.breakers.consecutive_losses, self.repo
                )
                if should_trigger:
                    assert context is not None  # Type narrowing
                    self.breaker_manager.trigger_breaker(
                        "consecutive_losses", "Too many consecutive losses",
                        self.config.breakers.consecutive_losses.pause_minutes, context
                    )
                    sm.transition_to(TradingState.IDLE)
                    return

                # Evaluate profitability gate
                passed, breakdown = self.profitability_gate.evaluate(plan)

                if passed:
                    net_profit = breakdown['net_profit_usd']
                    logger.info(f"    ✅ Profitability gate PASSED (net: ${net_profit:.2f})")
                    self.repo.append_event(
                        event_type="gate.profitability.passed",
                        level="INFO",
                        payload=breakdown,
                        public_safe=False,
                    )
                    sm.transition_to(TradingState.ENTRY_PENDING)
                else:
                    net_profit = breakdown['net_profit_usd']
                    logger.info(f"    ❌ Profitability gate REJECTED (net: ${net_profit:.2f})")
                    self.repo.append_event(
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

        # ENTRY_PENDING: Execute entry
        if sm.current_state == TradingState.ENTRY_PENDING:
            # Re-fetch plan (already created above)
            # In real system, pass plan via State Machine or Context
            # For now, re-calc quickly or assume it's valid.
            # To avoid drift, we should ideally carry the plan over.
            # Note: In a real system, market data changes between ticks/states.
            
            candles = self.market_data_provider.get_candles(symbol, "5m", 100)
            orderbook = self.market_data_provider.get_orderbook(symbol, 5)
            
            # ... re-calc logic ... (Simplification: using Mid for Entry in dry-run executor?)
            # DryRunExecutor in Prompt 05 used Mid Price.
            # We should pass the `plan` to `execute_entry`?
            # `execute_entry` currently takes `plan`.
            
            # Recalculate plan to pass to executor
            quantity = 0.01
            try:
                avg_fill_price, slippage_usd = calculate_slippage(
                    "BUY", quantity, orderbook
                )
            except ValueError:
                sm.reset()
                return

            fee_usd = calculate_fee(
                avg_fill_price * quantity, self.config.execution.taker_fee_bps
            )
            spread_cost_usd = calculate_spread_cost("BUY", quantity, orderbook)
            entry_price = avg_fill_price

            import uuid
            from datetime import datetime, timezone

            plan = TradePlan(
                symbol=symbol,
                side="BUY",
                entry_price=entry_price,
                quantity=quantity,
                stop_loss_price=entry_price * 0.98,
                take_profit_price=entry_price * 1.04,
                estimated_fee_usd=fee_usd,
                estimated_slippage_usd=slippage_usd,
                estimated_spread_cost_usd=spread_cost_usd,
                trade_id=f"trade-{uuid.uuid4()}",
                timestamp=datetime.now(timezone.utc),
            )

            result = self.execution_engine.execute_entry(plan)
            if not result:
                self.repo.append_event(
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
            self.repo.save_trade(trade)
            for order in orders:
                self.repo.save_order(order)

            logger.info(
                f"    🟢 Trade OPENED: {trade['id'][:8]} @ ${trade['entry_price']:.2f} "
                f"(qty: {trade['quantity']}, SL: ${plan.stop_loss_price:.2f}, "
                f"TP: ${plan.take_profit_price:.2f})"
            )

            # Emit events
            self.repo.append_event(
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

            for order in orders:
                self.repo.append_event(
                    event_type="order.placed",
                    level="INFO",
                    payload={
                        "order_id": order["id"],
                        "trade_id": trade["id"],
                        "order_type": order["order_type"],
                        "status": order["status"],
                    },
                    public_safe=False,
                )

            # Track open trade
            self.open_trades[symbol] = trade["id"]

            sm.transition_to(TradingState.IN_POSITION)

        # IN_POSITION: Check for exits
        if sm.current_state == TradingState.IN_POSITION:
            trade_id = self.open_trades.get(symbol)
            if not trade_id:
                # Should not happen, but recover
                sm.reset()
                return

            # Get current price
            orderbook = self.market_data_provider.get_orderbook(symbol, 5)
            current_price = orderbook.mid_price

            # Check if SL or TP hit
            exit_result = self.execution_engine.check_exits(trade_id, current_price)

            if exit_result:
                sm.transition_to(TradingState.EXIT_PENDING)

        # EXIT_PENDING: Finalize exit
        if sm.current_state == TradingState.EXIT_PENDING:
            trade_id = self.open_trades.get(symbol)
            if not trade_id:
                sm.reset()
                return

            # Get current price and execute exit
            orderbook = self.market_data_provider.get_orderbook(symbol, 5)
            current_price = orderbook.mid_price
            exit_result = self.execution_engine.check_exits(trade_id, current_price)

            if exit_result:
                trade = exit_result["trade"]
                exit_order = exit_result["exit_order"]
                exit_reason = exit_result["exit_reason"]

                # Update trade in DB
                self.repo.update_trade(trade)

                # Save exit order
                self.repo.save_order(exit_order)

                # Emit events
                self.repo.append_event(
                    event_type="trade.closed",
                    level="INFO",
                    payload={
                        "trade_id": trade["id"],
                        "symbol": symbol,
                        "exit_reason": exit_reason,
                        "exit_price": trade["exit_price"],
                        "pnl_usd": trade.get("realized_pnl_usd"),
                        "pnl_pct": trade.get("pnl_pct"),
                    },
                    public_safe=True,
                )

                self.repo.append_event(
                    event_type="order.filled",
                    level="INFO",
                    payload={
                        "order_id": exit_order["id"],
                        "trade_id": trade["id"],
                        "order_type": exit_order["order_type"],
                    },
                    public_safe=False,
                )

                # Remove from open trades
                del self.open_trades[symbol]

                sm.transition_to(TradingState.IDLE)

    def run(self, max_ticks: int | None = None) -> None:
        """
        Run the trading loop continuously or for a fixed number of ticks.

        Args:
            max_ticks: Maximum number of ticks to run (None = infinite)
        """
        # Emit system.started event
        self.repo.append_event(
            event_type="system.started",
            level="INFO",
            payload={"mode": self.config.execution.mode},
            public_safe=True,
        )
        
        # Reconcile state
        # In a real system we'd query DB for open trades here.
        # For now, we assume self.open_trades is empty on restart unless we load them.
        # MVP: Skip deep DB loading, just call reconcile with empty list to test hook.
        self.execution_engine.reconcile_state([])

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        tick_count = 0
        while not self._shutdown_requested:
            self.tick()
            tick_count += 1

            if max_ticks is not None and tick_count >= max_ticks:
                break

        # Emit system.stopped event
        self.repo.append_event(
            event_type="system.stopped",
            level="INFO",
            payload={"ticks_executed": tick_count},
            public_safe=True,
        )

    def _signal_handler(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals gracefully."""
        self._shutdown_requested = True
