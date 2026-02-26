from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session
from unittest.mock import MagicMock

from quantsail_engine.config.models import BotConfig, ExecutionConfig, RegimeConfig, StrategiesConfig
from quantsail_engine.core.trading_loop import TradingLoop
from quantsail_engine.execution.executor import ExecutionEngine
from quantsail_engine.market_data.stub_provider import StubMarketDataProvider
from quantsail_engine.models.signal import Signal, SignalType
from quantsail_engine.models.strategy import StrategyOutput
from quantsail_engine.persistence.stub_models import Event


class FailingExecutor(ExecutionEngine):
    def execute_entry(self, plan) -> dict[str, Any] | None:  # type: ignore[override]
        return None

    def check_exits(self, trade_id: str, current_price: float) -> dict[str, Any] | None:
        return None


def test_trading_loop_emits_execution_failed(in_memory_db: Session) -> None:
    """Test that execution.failed event is emitted when executor returns None."""
    config = BotConfig(
        execution=ExecutionConfig(min_profit_usd=0.0),
        strategies=StrategiesConfig(regime=RegimeConfig(enabled=False)),
    )
    market_data = StubMarketDataProvider(base_price=50000.0)
    signals = MagicMock()
    signals.generate_signal.return_value = Signal(
        signal_type=SignalType.ENTER_LONG,
        symbol="BTC/USDT",
        confidence=1.0,
        strategy_outputs=[StrategyOutput(SignalType.ENTER_LONG, 1.0, "test")],
    )

    loop = TradingLoop(
        config,
        in_memory_db,
        market_data,
        signals,
        FailingExecutor(),
    )

    loop.tick()
    assert FailingExecutor().check_exits("missing", 0.0) is None

    failed = in_memory_db.query(Event).filter(Event.type == "execution.failed").count()
    assert failed == 1
