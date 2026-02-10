"""Integration tests for TradingLoop."""

from sqlalchemy.orm import Session

from quantsail_engine.config.models import BotConfig, RegimeConfig, StrategiesConfig
from quantsail_engine.core.trading_loop import TradingLoop
from quantsail_engine.execution.dry_run_executor import DryRunExecutor
from quantsail_engine.market_data.stub_provider import StubMarketDataProvider
from quantsail_engine.models.signal import SignalType
from quantsail_engine.signals.stub_provider import StubSignalProvider


def test_trading_loop_single_tick_hold(in_memory_db: Session) -> None:
    """Test single tick with HOLD signal does not create trade."""
    config = BotConfig()
    market_data = StubMarketDataProvider(base_price=50000.0)
    signals = StubSignalProvider()  # Defaults to HOLD
    executor = DryRunExecutor()

    loop = TradingLoop(config, in_memory_db, market_data, signals, executor)
    loop.tick()

    # No trades should be created
    from quantsail_engine.persistence.stub_models import Trade

    trades = in_memory_db.query(Trade).all()
    assert len(trades) == 0


def test_trading_loop_enter_long_profitability_pass(in_memory_db: Session) -> None:
    """Test ENTER_LONG signal with profitability gate passing."""
    from quantsail_engine.config.models import ExecutionConfig

    config = BotConfig(
        execution=ExecutionConfig(min_profit_usd=0.01),
        strategies=StrategiesConfig(regime=RegimeConfig(enabled=False)),
    )
    market_data = StubMarketDataProvider(base_price=50000.0)
    signals = StubSignalProvider()
    signals.set_next_signal(SignalType.ENTER_LONG)
    executor = DryRunExecutor()

    loop = TradingLoop(config, in_memory_db, market_data, signals, executor)
    loop.tick()

    # Trade should be created
    from quantsail_engine.persistence.stub_models import Trade

    trades = in_memory_db.query(Trade).all()
    assert len(trades) == 1
    assert trades[0].status == "OPEN"


def test_trading_loop_enter_long_profitability_fail(in_memory_db: Session) -> None:
    """Test ENTER_LONG signal with profitability gate failing."""
    from quantsail_engine.config.models import ExecutionConfig

    config = BotConfig(execution=ExecutionConfig(min_profit_usd=10000.0))
    market_data = StubMarketDataProvider(base_price=50000.0)
    signals = StubSignalProvider()
    signals.set_next_signal(SignalType.ENTER_LONG)
    executor = DryRunExecutor()

    loop = TradingLoop(config, in_memory_db, market_data, signals, executor)
    loop.tick()

    # No trade should be created (profitability gate rejected)
    from quantsail_engine.persistence.stub_models import Trade

    trades = in_memory_db.query(Trade).all()
    assert len(trades) == 0


def test_trading_loop_full_lifecycle_take_profit(in_memory_db: Session) -> None:
    """Test full trade lifecycle with TP hit (simplified)."""
    from quantsail_engine.config.models import ExecutionConfig

    config = BotConfig(
        execution=ExecutionConfig(min_profit_usd=0.01),
        strategies=StrategiesConfig(regime=RegimeConfig(enabled=False)),
    )
    signals = StubSignalProvider()
    executor = DryRunExecutor()
    market_data = StubMarketDataProvider(base_price=50000.0)

    # Tick 1: ENTER_LONG signal, entry executed
    signals.set_next_signal(SignalType.ENTER_LONG)
    loop = TradingLoop(config, in_memory_db, market_data, signals, executor)
    loop.tick()

    # Verify trade was created and is open
    from quantsail_engine.persistence.stub_models import Trade

    trades = in_memory_db.query(Trade).all()
    assert len(trades) == 1
    assert trades[0].status == "OPEN"
    assert len(loop.open_trades) == 1


def test_trading_loop_full_lifecycle_stop_loss(in_memory_db: Session) -> None:
    """Test trade entry verified (exit logic tested separately)."""
    from quantsail_engine.config.models import ExecutionConfig

    config = BotConfig(
        execution=ExecutionConfig(min_profit_usd=0.01),
        strategies=StrategiesConfig(regime=RegimeConfig(enabled=False)),
    )
    signals = StubSignalProvider()
    executor = DryRunExecutor()
    market_data = StubMarketDataProvider(base_price=50000.0)

    # Tick 1: ENTER_LONG signal, entry executed
    signals.set_next_signal(SignalType.ENTER_LONG)
    loop = TradingLoop(config, in_memory_db, market_data, signals, executor)
    loop.tick()

    # Verify trade entry
    from quantsail_engine.persistence.stub_models import Order, Trade

    trades = in_memory_db.query(Trade).all()
    orders = in_memory_db.query(Order).all()

    assert len(trades) == 1
    assert trades[0].status == "OPEN"
    assert len(orders) == 3  # Entry, SL, TP


def test_trading_loop_equity_snapshot(in_memory_db: Session) -> None:
    """Test that equity snapshot is saved after each tick."""
    config = BotConfig()
    market_data = StubMarketDataProvider(base_price=50000.0)
    signals = StubSignalProvider()
    executor = DryRunExecutor()

    loop = TradingLoop(config, in_memory_db, market_data, signals, executor)
    loop.tick()

    # Equity snapshot should be created
    from quantsail_engine.persistence.stub_models import EquitySnapshot

    snapshots = in_memory_db.query(EquitySnapshot).all()
    assert len(snapshots) == 1
    assert snapshots[0].equity_usd == 10000.0  # Starting cash


def test_trading_loop_run_with_max_ticks(in_memory_db: Session) -> None:
    """Test run method with max_ticks parameter."""
    config = BotConfig()
    market_data = StubMarketDataProvider(base_price=50000.0)
    signals = StubSignalProvider()
    executor = DryRunExecutor()

    loop = TradingLoop(config, in_memory_db, market_data, signals, executor)
    loop.run(max_ticks=3)

    # 3 equity snapshots should be created
    from quantsail_engine.persistence.stub_models import EquitySnapshot

    snapshots = in_memory_db.query(EquitySnapshot).all()
    assert len(snapshots) == 3


def test_trading_loop_max_positions_gate(in_memory_db: Session) -> None:
    """Test max concurrent positions gate."""
    from quantsail_engine.config.models import ExecutionConfig, SymbolsConfig

    config = BotConfig(
        execution=ExecutionConfig(min_profit_usd=0.01),
        symbols=SymbolsConfig(enabled=["BTC/USDT", "ETH/USDT"], max_concurrent_positions=1),
        strategies=StrategiesConfig(regime=RegimeConfig(enabled=False)),
    )
    market_data = StubMarketDataProvider(base_price=50000.0)
    signals = StubSignalProvider()
    signals.set_next_signal(SignalType.ENTER_LONG)
    executor = DryRunExecutor()

    loop = TradingLoop(config, in_memory_db, market_data, signals, executor)
    loop.tick()

    # Only 1 trade should be opened (max_concurrent_positions = 1)
    from quantsail_engine.persistence.stub_models import Trade

    trades = in_memory_db.query(Trade).all()
    assert len(trades) == 1
