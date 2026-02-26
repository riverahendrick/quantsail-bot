"""Entry pipeline — evaluates gates, sizes position, and creates trade plans."""

import logging
import uuid
from datetime import datetime, timezone

from quantsail_engine.breakers.manager import BreakerManager
from quantsail_engine.breakers.triggers import (
    check_consecutive_losses,
    check_spread_slippage_spike,
    check_volatility_spike,
)
from quantsail_engine.config.models import BotConfig
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
from quantsail_engine.models.signal import SignalType
from quantsail_engine.models.trade_plan import TradePlan
from quantsail_engine.persistence.repository import EngineRepository
from quantsail_engine.risk.dynamic_sizer import DynamicSizer
from quantsail_engine.signals.provider import SignalProvider

logger = logging.getLogger(__name__)


class EntryPipeline:
    """Evaluates all entry gates and produces a TradePlan if conditions are met.

    Encapsulates: regime filter, cooldown, daily symbol limit, signal generation,
    breakers, daily lock, position limits, sizing, slippage/fee estimation,
    SL/TP calculation, breaker triggers, and profitability gate.
    """

    def __init__(
        self,
        config: BotConfig,
        repo: EngineRepository,
        market_data_provider: MarketDataProvider,
        signal_provider: SignalProvider,
        breaker_manager: BreakerManager,
        daily_lock_manager: DailyLockManager,
        dynamic_sizer: DynamicSizer,
        regime_filter: RegimeFilter,
        profitability_gate: ProfitabilityGate,
        cooldown_gate: CooldownGate,
        daily_symbol_limit: DailySymbolLossLimit,
        streak_sizer: StreakSizer,
    ) -> None:
        self.config = config
        self.repo = repo
        self.market_data_provider = market_data_provider
        self.signal_provider = signal_provider
        self.breaker_manager = breaker_manager
        self.daily_lock_manager = daily_lock_manager
        self.dynamic_sizer = dynamic_sizer
        self.regime_filter = regime_filter
        self.profitability_gate = profitability_gate
        self.cooldown_gate = cooldown_gate
        self.daily_symbol_limit = daily_symbol_limit
        self.streak_sizer = streak_sizer

    def evaluate(
        self,
        symbol: str,
        num_open_positions: int,
    ) -> TradePlan | None:
        """Run all entry gates and return a TradePlan if entry is viable.

        Args:
            symbol: Trading symbol to evaluate.
            num_open_positions: Current number of open positions.

        Returns:
            A TradePlan ready for execution, or None if any gate rejected.
        """
        # Fetch market data
        candles = self.market_data_provider.get_candles(symbol, "5m", 100)
        orderbook = self.market_data_provider.get_orderbook(symbol, 5)

        # --- Gate: Market regime ---
        if not self.regime_filter.analyze(candles, symbol=symbol):
            self.repo.append_event(
                event_type="gate.regime.rejected",
                level="INFO",
                payload={"symbol": symbol, "reason": "choppy_market_detected"},
                public_safe=True,
            )
            return None

        # --- Gate: Stop-loss cooldown ---
        cooldown_ok, cooldown_reason = self.cooldown_gate.is_allowed(
            symbol, datetime.now(timezone.utc)
        )
        if not cooldown_ok:
            self.repo.append_event(
                event_type="gate.cooldown.rejected",
                level="INFO",
                payload={"symbol": symbol, "reason": cooldown_reason},
                public_safe=True,
            )
            return None

        # --- Gate: Daily per-symbol loss limit ---
        daily_ok, daily_reason = self.daily_symbol_limit.is_allowed(
            symbol, datetime.now(timezone.utc)
        )
        if not daily_ok:
            self.repo.append_event(
                event_type="gate.daily_symbol_limit.rejected",
                level="WARN",
                payload={"symbol": symbol, "reason": daily_reason},
                public_safe=True,
            )
            return None

        # --- Generate signals ---
        signal = self.signal_provider.generate_signal(symbol, candles, orderbook)
        logger.info("    Signal: %s (confidence=%.2f)", signal.signal_type, signal.confidence)

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

        # Emit ensemble decision
        votes = sum(1 for o in signal.strategy_outputs if o.signal == SignalType.ENTER_LONG)
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

        # No entry signal — reject
        if signal.signal_type != SignalType.ENTER_LONG:
            return None

        # --- Gate: Breakers (volatility/spread/news) ---
        entries_allowed, rejection_reason = self.breaker_manager.entries_allowed()
        if not entries_allowed:
            event_type = (
                "gate.news.rejected"
                if rejection_reason and "news" in rejection_reason
                else "gate.breaker.rejected"
            )
            self.repo.append_event(
                event_type=event_type,
                level="WARN",
                payload={"symbol": symbol, "reason": rejection_reason},
                public_safe=True,
            )
            return None

        # --- Gate: Daily lock ---
        entries_allowed, rejection_reason = self.daily_lock_manager.entries_allowed()
        if not entries_allowed:
            self.repo.append_event(
                event_type="gate.daily_lock.rejected",
                level="WARN",
                payload={"symbol": symbol, "reason": rejection_reason},
                public_safe=True,
            )
            return None

        # --- Gate: Max concurrent positions ---
        if num_open_positions >= self.config.symbols.max_concurrent_positions:
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
            return None

        # --- Position sizing ---
        atr_values = calculate_atr(candles, period=14)
        current_atr = atr_values[-1] if atr_values else 0.0
        equity_usd = self.repo.calculate_equity(self.config.risk.starting_cash_usd)
        entry_est = orderbook.mid_price

        quantity = self.dynamic_sizer.calculate(
            equity_usd=equity_usd,
            entry_price=entry_est,
            atr_value=current_atr,
        )

        # Apply streak sizer reduction
        streak_mult = self.streak_sizer.get_multiplier(symbol)
        if streak_mult < 1.0:
            quantity = quantity * streak_mult
            self.repo.append_event(
                event_type="gate.streak_sizer.applied",
                level="INFO",
                payload={
                    "symbol": symbol,
                    "multiplier": streak_mult,
                    "adjusted_quantity": quantity,
                },
                public_safe=False,
            )

        # --- Slippage / fee / spread estimation ---
        try:
            avg_fill_price, slippage_usd = calculate_slippage("BUY", quantity, orderbook)
        except ValueError as e:
            logger.warning("    ❌ Slippage estimation failed: %s", e)
            self.repo.append_event(
                event_type="gate.liquidity.rejected",
                level="WARN",
                payload={"symbol": symbol, "reason": str(e)},
                public_safe=False,
            )
            return None

        fee_usd = calculate_fee(
            avg_fill_price * quantity, self.config.execution.taker_fee_bps
        )
        spread_cost_usd = calculate_spread_cost("BUY", quantity, orderbook)
        entry_price = avg_fill_price

        # --- SL / TP calculation ---
        sl_config = self.config.stop_loss
        tp_config = self.config.take_profit

        if sl_config.method == "atr" and current_atr > 0:
            sl_price = entry_price - (current_atr * sl_config.atr_multiplier)
        else:
            sl_price = entry_price * (1.0 - sl_config.fixed_pct / 100.0)

        if tp_config.method == "risk_reward" and sl_price > 0:
            sl_distance = entry_price - sl_price
            tp_price = entry_price + (sl_distance * tp_config.risk_reward_ratio)
        elif tp_config.method == "atr" and current_atr > 0:
            tp_price = entry_price + (current_atr * tp_config.atr_multiplier)
        else:
            tp_price = entry_price * (1.0 + tp_config.fixed_pct / 100.0)

        plan = TradePlan(
            symbol=symbol,
            side="BUY",
            entry_price=entry_price,
            quantity=quantity,
            stop_loss_price=sl_price,
            take_profit_price=tp_price,
            estimated_fee_usd=fee_usd,
            estimated_slippage_usd=slippage_usd,
            estimated_spread_cost_usd=spread_cost_usd,
            trade_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
        )

        # --- Breaker triggers on plan ---
        should_trigger, context = check_volatility_spike(
            self.config.breakers.volatility, symbol, candles, atr_values
        )
        if should_trigger:
            assert context is not None
            self.breaker_manager.trigger_breaker(
                "volatility", "ATR spike detected",
                self.config.breakers.volatility.pause_minutes, context
            )
            return None

        should_trigger, context = check_spread_slippage_spike(
            self.config.breakers.spread_slippage, symbol, orderbook, plan
        )
        if should_trigger:
            assert context is not None
            self.breaker_manager.trigger_breaker(
                "spread_slippage", "Spread spike detected",
                self.config.breakers.spread_slippage.pause_minutes, context
            )
            return None

        should_trigger, context = check_consecutive_losses(
            self.config.breakers.consecutive_losses, self.repo
        )
        if should_trigger:
            assert context is not None
            self.breaker_manager.trigger_breaker(
                "consecutive_losses", "Too many consecutive losses",
                self.config.breakers.consecutive_losses.pause_minutes, context
            )
            return None

        # --- Gate: Profitability ---
        passed, breakdown = self.profitability_gate.evaluate(plan)
        net_profit = breakdown['net_profit_usd']

        if passed:
            logger.info("    ✅ Profitability gate PASSED (net: $%.2f)", net_profit)
            self.repo.append_event(
                event_type="gate.profitability.passed",
                level="INFO",
                payload=breakdown,
                public_safe=False,
            )
            return plan
        else:
            logger.info("    ❌ Profitability gate REJECTED (net: $%.2f)", net_profit)
            self.repo.append_event(
                event_type="gate.profitability.rejected",
                level="WARN",
                payload=breakdown,
                public_safe=False,
            )
            return None
