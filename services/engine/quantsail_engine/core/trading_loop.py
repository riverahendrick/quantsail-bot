"""Main trading loop coordinating per-symbol state machines.

Delegates to EntryPipeline and ExitPipeline for the heavy lifting.
"""

import logging
import signal
import uuid
from typing import Any
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from quantsail_engine.breakers.manager import BreakerManager
from quantsail_engine.config.models import BotConfig
from quantsail_engine.core.entry_pipeline import EntryPipeline
from quantsail_engine.core.exit_pipeline import ExitPipeline
from quantsail_engine.core.state_machine import StateMachine, TradingState
from quantsail_engine.execution.executor import ExecutionEngine
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
from quantsail_engine.market_data.provider import MarketDataProvider
from quantsail_engine.models.trade_plan import TradePlan
from quantsail_engine.persistence.repository import EngineRepository
from quantsail_engine.risk.dynamic_sizer import DynamicSizer
from quantsail_engine.risk.trailing_stop import TrailingStopManager
from quantsail_engine.signals.provider import SignalProvider

# Control plane is optional so existing usage doesn't break
try:
    from quantsail_engine.cache.control import ControlPlane, BotState
    _HAS_CONTROL_PLANE = True
except ImportError:
    _HAS_CONTROL_PLANE = False

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
        control_plane: Any | None = None,
    ):
        """
        Initialize trading loop.

        Args:
            config: Bot configuration
            session: Database session
            market_data_provider: Market data provider
            signal_provider: Signal provider
            execution_engine: Execution engine
            control_plane: Optional control plane for lifecycle state checks
        """
        self.config = config
        self.repo = EngineRepository(session)
        self.market_data_provider = market_data_provider
        self.signal_provider = signal_provider
        self.execution_engine = execution_engine
        self.control_plane = control_plane

        # Initialize sub-components shared by pipelines
        self.breaker_manager = BreakerManager(config=config.breakers, repo=self.repo)
        self.daily_lock_manager = DailyLockManager(config=config.daily, repo=self.repo)
        self.dynamic_sizer = DynamicSizer(config.position_sizing)
        self.trailing_stop_manager = TrailingStopManager(config.trailing_stop)
        self.regime_filter = RegimeFilter(config.strategies.regime)
        self.profitability_gate = ProfitabilityGate(
            min_profit_usd=config.execution.min_profit_usd
        )
        self.cooldown_gate = CooldownGate(config.cooldown)
        self.daily_symbol_limit = DailySymbolLossLimit(config.daily_symbol_limit)
        self.streak_sizer = StreakSizer(config.streak_sizer)

        # Build pipelines
        self.entry_pipeline = EntryPipeline(
            config=config,
            repo=self.repo,
            market_data_provider=market_data_provider,
            signal_provider=signal_provider,
            breaker_manager=self.breaker_manager,
            daily_lock_manager=self.daily_lock_manager,
            dynamic_sizer=self.dynamic_sizer,
            regime_filter=self.regime_filter,
            profitability_gate=self.profitability_gate,
            cooldown_gate=self.cooldown_gate,
            daily_symbol_limit=self.daily_symbol_limit,
            streak_sizer=self.streak_sizer,
        )
        self.exit_pipeline = ExitPipeline(
            config=config,
            repo=self.repo,
            market_data_provider=market_data_provider,
            execution_engine=execution_engine,
            trailing_stop_manager=self.trailing_stop_manager,
            cooldown_gate=self.cooldown_gate,
            daily_symbol_limit=self.daily_symbol_limit,
            streak_sizer=self.streak_sizer,
        )

        # Per-symbol state machines and tracking
        self.state_machines: dict[str, StateMachine] = {}
        self.open_trades: dict[str, str] = {}  # symbol -> trade_id
        self.trade_plans: dict[str, TradePlan] = {}  # symbol -> active trade plan

        for symbol in config.symbols.enabled:
            self.state_machines[symbol] = StateMachine(symbol)

        # Shutdown flag
        self._shutdown_requested = False

    def tick(self) -> None:
        """Execute one tick of the trading loop for all symbols."""
        logger.info("📊 Tick started")

        # Control plane gate
        if self.control_plane is not None:
            self.control_plane.heartbeat()
            state = self.control_plane.get_state()
            entries_allowed = self.control_plane.is_entries_allowed()
            exits_allowed = self.control_plane.is_exits_allowed()
            logger.info("Control plane: state=%s, entries=%s, exits=%s", state, entries_allowed, exits_allowed)

            if not exits_allowed:
                # STOPPED state: no entries, no exit processing
                logger.info("Bot is STOPPED — skipping tick entirely")
                return
        else:
            entries_allowed = True
            exits_allowed = True

        for symbol in self.config.symbols.enabled:
            logger.info(f"  Symbol: {symbol}")
            self._tick_symbol(symbol, entries_allowed=entries_allowed)

        # Update equity snapshot after all symbols processed
        equity = self.repo.calculate_equity(self.config.risk.starting_cash_usd)
        self.repo.save_equity_snapshot(equity)
        logger.info(f"  Equity: ${equity:.2f}")

    def _tick_symbol(self, symbol: str, *, entries_allowed: bool = True) -> None:
        """Execute one tick for a specific symbol.

        State machine flow:
        IDLE → EVAL → (signal check) → ENTRY_PENDING → IN_POSITION → EXIT_PENDING → IDLE

        Args:
            symbol: Trading symbol
            entries_allowed: Whether new entries should be evaluated
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

        # EVAL: Delegate to EntryPipeline
        if sm.current_state == TradingState.EVAL:
            plan = self.entry_pipeline.evaluate(
                symbol=symbol,
                num_open_positions=len(self.open_trades),
            )
            if plan is not None:
                self.trade_plans[symbol] = plan
                sm.transition_to(TradingState.ENTRY_PENDING)
            else:
                sm.transition_to(TradingState.IDLE)
                return

        # ENTRY_PENDING: Execute entry
        if sm.current_state == TradingState.ENTRY_PENDING:
            plan = self.trade_plans.get(symbol)
            if not plan:
                # Fallback: re-evaluate if plan was lost
                plan = self.entry_pipeline.evaluate(
                    symbol=symbol,
                    num_open_positions=len(self.open_trades),
                )
                if not plan:
                    sm.reset()
                    return

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

            # Initialize trailing stop for this position
            if self.config.trailing_stop.enabled:
                self.trailing_stop_manager.init_position(
                    trade_id=trade["id"],
                    entry_price=plan.entry_price,
                    initial_stop=plan.stop_loss_price,
                )

            sm.transition_to(TradingState.IN_POSITION)

        # IN_POSITION: Delegate to ExitPipeline
        if sm.current_state == TradingState.IN_POSITION:
            trade_id = self.open_trades.get(symbol)
            if not trade_id:
                sm.reset()
                return

            # Check trailing stop
            if self.exit_pipeline.check_trailing_stop(symbol, trade_id):
                sm.transition_to(TradingState.EXIT_PENDING)
                return

            # Check SL/TP
            if self.exit_pipeline.check_exit(symbol, trade_id):
                sm.transition_to(TradingState.EXIT_PENDING)

        # EXIT_PENDING: Finalize exit via ExitPipeline
        if sm.current_state == TradingState.EXIT_PENDING:
            trade_id = self.open_trades.get(symbol)
            if not trade_id:
                sm.reset()
                return

            exit_result = self.exit_pipeline.finalize_exit(symbol, trade_id)
            if exit_result.should_exit:
                # Clean up tracking
                trade_id_to_clean = self.open_trades.pop(symbol)
                self.trade_plans.pop(symbol, None)
                self.trailing_stop_manager.remove_position(trade_id_to_clean)
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
