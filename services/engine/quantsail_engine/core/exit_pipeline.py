"""Exit pipeline — checks trailing stops, SL/TP, and finalizes trade exits."""

import logging
from datetime import datetime, timezone

from quantsail_engine.config.models import BotConfig
from quantsail_engine.execution.executor import ExecutionEngine
from quantsail_engine.gates.cooldown_gate import CooldownGate
from quantsail_engine.gates.daily_symbol_limit import DailySymbolLossLimit
from quantsail_engine.gates.streak_sizer import StreakSizer
from quantsail_engine.indicators.atr import calculate_atr
from quantsail_engine.market_data.provider import MarketDataProvider
from quantsail_engine.persistence.repository import EngineRepository
from quantsail_engine.risk.trailing_stop import TrailingStopManager

logger = logging.getLogger(__name__)


class ExitResult:
    """Result of exit pipeline evaluation."""

    __slots__ = ("should_exit", "trade", "exit_order", "exit_reason")

    def __init__(
        self,
        should_exit: bool,
        trade: dict | None = None,
        exit_order: dict | None = None,
        exit_reason: str | None = None,
    ) -> None:
        self.should_exit = should_exit
        self.trade = trade
        self.exit_order = exit_order
        self.exit_reason = exit_reason


class ExitPipeline:
    """Checks trailing stops, SL/TP fills, and finalizes trade exits.

    Encapsulates: trailing stop updates, exit detection, DB persistence,
    gate recording (cooldown, daily symbol limit, streak sizer), and
    event emission for closed trades.
    """

    def __init__(
        self,
        config: BotConfig,
        repo: EngineRepository,
        market_data_provider: MarketDataProvider,
        execution_engine: ExecutionEngine,
        trailing_stop_manager: TrailingStopManager,
        cooldown_gate: CooldownGate,
        daily_symbol_limit: DailySymbolLossLimit,
        streak_sizer: StreakSizer,
    ) -> None:
        self.config = config
        self.repo = repo
        self.market_data_provider = market_data_provider
        self.execution_engine = execution_engine
        self.trailing_stop_manager = trailing_stop_manager
        self.cooldown_gate = cooldown_gate
        self.daily_symbol_limit = daily_symbol_limit
        self.streak_sizer = streak_sizer

    def check_trailing_stop(self, symbol: str, trade_id: str) -> bool:
        """Check if the trailing stop has been hit.

        Args:
            symbol: Trading pair symbol.
            trade_id: ID of the active trade.

        Returns:
            True if trailing stop was triggered and state should move to EXIT_PENDING.
        """
        if not self.config.trailing_stop.enabled:
            return False

        orderbook = self.market_data_provider.get_orderbook(symbol, 5)
        current_price = orderbook.mid_price

        candles = self.market_data_provider.get_candles(symbol, "5m", 100)
        atr_values = calculate_atr(candles, period=self.config.trailing_stop.atr_period)
        current_atr = atr_values[-1] if atr_values else 0.0

        new_stop = self.trailing_stop_manager.update(
            trade_id=trade_id,
            current_price=current_price,
            atr_value=current_atr,
        )

        if new_stop is not None and current_price <= new_stop:
            logger.info(
                "    🛑 Trailing stop hit for %s (stop: $%.2f, price: $%.2f)",
                symbol, new_stop, current_price,
            )
            self.repo.append_event(
                event_type="trailing_stop.triggered",
                level="INFO",
                payload={
                    "symbol": symbol,
                    "trade_id": trade_id,
                    "stop_level": new_stop,
                    "current_price": current_price,
                },
                public_safe=True,
            )
            return True

        return False

    def check_exit(self, symbol: str, trade_id: str) -> bool:
        """Check if SL or TP was hit (traditional check).

        Returns:
            True if an exit condition was detected.
        """
        orderbook = self.market_data_provider.get_orderbook(symbol, 5)
        current_price = orderbook.mid_price
        exit_result = self.execution_engine.check_exits(trade_id, current_price)
        return exit_result is not None

    def finalize_exit(self, symbol: str, trade_id: str) -> ExitResult:
        """Execute the exit: persist trade close, record gates, emit events.

        Args:
            symbol: Trading pair symbol.
            trade_id: ID of the trade to close.

        Returns:
            ExitResult with trade, exit_order, and exit_reason if exit happened.
        """
        orderbook = self.market_data_provider.get_orderbook(symbol, 5)
        current_price = orderbook.mid_price
        exit_result = self.execution_engine.check_exits(trade_id, current_price)

        if not exit_result:
            return ExitResult(should_exit=False)

        trade = exit_result["trade"]
        exit_order = exit_result["exit_order"]
        exit_reason = exit_result["exit_reason"]

        # Persist to database
        self.repo.update_trade(trade)
        self.repo.save_order(exit_order)

        # Record exit for realism gates
        pnl = trade.get("realized_pnl_usd", 0.0)
        exit_ts = datetime.now(timezone.utc)
        is_win = pnl is not None and pnl > 0

        self.cooldown_gate.record_exit(symbol, exit_reason, exit_ts)

        if is_win:
            self.daily_symbol_limit.record_win(symbol, exit_ts)
            self.streak_sizer.record_result(symbol, won=True)
        else:
            self.daily_symbol_limit.record_loss(symbol, exit_ts)
            self.streak_sizer.record_result(symbol, won=False)

        # Emit events
        self.repo.append_event(
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

        return ExitResult(
            should_exit=True,
            trade=trade,
            exit_order=exit_order,
            exit_reason=exit_reason,
        )
