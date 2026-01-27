"""Integration tests for Profitability Gate within TradingLoop."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from sqlalchemy.orm import Session

from quantsail_engine.config.models import (
    BotConfig,
    EnsembleConfig,
    ExecutionConfig,
    StrategiesConfig,
)
from quantsail_engine.core.state_machine import TradingState
from quantsail_engine.core.trading_loop import TradingLoop
from quantsail_engine.execution.dry_run_executor import DryRunExecutor
from quantsail_engine.market_data.stub_provider import StubMarketDataProvider
from quantsail_engine.models.candle import Candle, Orderbook
from quantsail_engine.signals.ensemble_provider import EnsembleSignalProvider


def test_integration_profitability_gate_rejects(in_memory_db: Session) -> None:
    # Set high min profit to force rejection
    config = BotConfig(
        execution=ExecutionConfig(min_profit_usd=1000.0, taker_fee_bps=10.0),
        strategies=StrategiesConfig(
            ensemble=EnsembleConfig(min_agreement=0, confidence_threshold=0.0)
        )
    )
    
    # Mock market data to trigger signal
    market_data = StubMarketDataProvider(base_price=50000.0)
    # Ensure signal generated (using empty strategy logic or mock)
    # Ensemble with min_agreement 0 and confidence 0 triggers if any strategy returns anything valid
    # But strategies check for data length.
    # Let's mock signals provider to force ENTER_LONG
    
    signals = MagicMock(spec=EnsembleSignalProvider)
    from quantsail_engine.models.signal import Signal, SignalType
    from quantsail_engine.models.strategy import StrategyOutput
    
    signals.generate_signal.return_value = Signal(
        signal_type=SignalType.ENTER_LONG,
        symbol="BTC/USDT",
        confidence=1.0,
        strategy_outputs=[StrategyOutput(SignalType.ENTER_LONG, 1.0, "mock")]
    )
    
    executor = DryRunExecutor()
    loop = TradingLoop(config, in_memory_db, market_data, signals, executor)
    
    loop.tick()
    
    # Verify rejection event
    from quantsail_engine.persistence.stub_models import Event, Trade
    events = in_memory_db.query(Event).filter(Event.type == "gate.profitability.rejected").all()
    assert len(events) == 1
    assert events[0].payload["net_profit_usd"] < 1000.0
    
    # Verify no trade opened
    trades = in_memory_db.query(Trade).all()
    assert len(trades) == 0


def test_integration_liquidity_rejection(in_memory_db: Session) -> None:
    config = BotConfig()
    
    # Mock signal
    signals = MagicMock(spec=EnsembleSignalProvider)
    from quantsail_engine.models.signal import Signal, SignalType
    from quantsail_engine.models.strategy import StrategyOutput
    signals.generate_signal.return_value = Signal(
        signal_type=SignalType.ENTER_LONG,
        symbol="BTC/USDT",
        confidence=1.0,
        strategy_outputs=[StrategyOutput(SignalType.ENTER_LONG, 1.0, "mock")]
    )
    
    # Mock market data with insufficient liquidity
    market_data = MagicMock(spec=StubMarketDataProvider)
    market_data.get_candles.return_value = []
    # Asks present but quantity 0.0001 < required 0.01
    market_data.get_orderbook.return_value = Orderbook(
        bids=[(100.0, 1.0)], 
        asks=[(101.0, 0.0001)]
    )
    
    executor = DryRunExecutor()
    loop = TradingLoop(config, in_memory_db, market_data, signals, executor)
    
    loop.tick()
    
    # Verify liquidity rejection event
    from quantsail_engine.persistence.stub_models import Event
    events = in_memory_db.query(Event).filter(Event.type == "gate.liquidity.rejected").all()
    assert len(events) == 1
    
    # Verify no trade
    from quantsail_engine.persistence.stub_models import Trade
    trades = in_memory_db.query(Trade).all()
    assert len(trades) == 0


def test_integration_max_positions_rejection(in_memory_db: Session) -> None:
    # Max positions = 1. We need to fill it first.
    from quantsail_engine.config.models import SymbolsConfig
    config = BotConfig(
        symbols=SymbolsConfig(enabled=["BTC/USDT"], max_concurrent_positions=1)
    )
    
    signals = MagicMock(spec=EnsembleSignalProvider)
    from quantsail_engine.models.signal import Signal, SignalType
    from quantsail_engine.models.strategy import StrategyOutput
    signals.generate_signal.return_value = Signal(
        signal_type=SignalType.ENTER_LONG,
        symbol="BTC/USDT",
        confidence=1.0,
        strategy_outputs=[StrategyOutput(SignalType.ENTER_LONG, 1.0, "mock")]
    )
    
    market_data = StubMarketDataProvider(base_price=50000.0)
    executor = DryRunExecutor()
    loop = TradingLoop(config, in_memory_db, market_data, signals, executor)
    
    # Artificially fill the slot
    loop.open_trades["BTC/USDT"] = "trade-existing"
    
    loop.tick()
    
    # Verify max positions rejection event
    from quantsail_engine.persistence.stub_models import Event
    events = in_memory_db.query(Event).filter(Event.type == "gate.max_positions.rejected").all()
    assert len(events) == 1


def test_integration_entry_execution_failure_recovery(in_memory_db: Session) -> None:
    # Simulate a failure during re-calculation of slippage in ENTRY_PENDING state
    # This covers the try/except block in ENTRY_PENDING
    config = BotConfig(execution=ExecutionConfig(min_profit_usd=0.0))
    
    # Mock signal to get us to ENTRY_PENDING
    signals = MagicMock(spec=EnsembleSignalProvider)
    from quantsail_engine.models.signal import Signal, SignalType
    from quantsail_engine.models.strategy import StrategyOutput
    signals.generate_signal.return_value = Signal(
        signal_type=SignalType.ENTER_LONG,
        symbol="BTC/USDT",
        confidence=1.0,
        strategy_outputs=[StrategyOutput(SignalType.ENTER_LONG, 1.0, "mock")]
    )
    
    market_data = MagicMock(spec=StubMarketDataProvider)
    # First call (EVAL): valid orderbook
    # Second call (ENTRY_PENDING): invalid orderbook (insufficient liquidity)
    valid_ob = Orderbook(bids=[(99.0, 10.0)], asks=[(100.0, 10.0)])
    invalid_ob = Orderbook(bids=[(99.0, 10.0)], asks=[(100.0, 0.000001)]) 
    
    market_data.get_orderbook.side_effect = [valid_ob, invalid_ob]
    market_data.get_candles.return_value = []
    
    executor = DryRunExecutor()
    loop = TradingLoop(config, in_memory_db, market_data, signals, executor)
    
    # Tick 1: EVAL (Passes) -> ENTRY_PENDING (Fails) -> IDLE
    loop.tick()
    
    # Verify we are back to IDLE
    from quantsail_engine.core.state_machine import TradingState
    assert loop.state_machines["BTC/USDT"].current_state == TradingState.IDLE
    
    # Verify no trade created
    from quantsail_engine.persistence.stub_models import Trade
    trades = in_memory_db.query(Trade).all()
    assert len(trades) == 0
    
    # Verify failure happened in ENTRY_PENDING (Silent reset) vs EVAL (Event emitted)
    from quantsail_engine.persistence.stub_models import Event
    events = in_memory_db.query(Event).filter(Event.type == "gate.liquidity.rejected").all()
    assert len(events) == 0


def test_gate_breaker_rejects_entry(in_memory_db: Session) -> None:
    """Test that active circuit breaker rejects entry with event."""
    config = BotConfig()
    market_data = StubMarketDataProvider(base_price=50000.0)
    signals = MagicMock(spec=EnsembleSignalProvider)

    from quantsail_engine.models.signal import Signal, SignalType
    from quantsail_engine.models.strategy import StrategyOutput

    signals.generate_signal.return_value = Signal(
        signal_type=SignalType.ENTER_LONG,
        symbol="BTC/USDT",
        confidence=1.0,
        strategy_outputs=[StrategyOutput(SignalType.ENTER_LONG, 1.0, "mock")]
    )

    executor = DryRunExecutor()
    loop = TradingLoop(config, in_memory_db, market_data, signals, executor)

    # Manually trigger a breaker before tick
    loop.breaker_manager.trigger_breaker("volatility", "Test spike", 30, {"atr": 2.0})

    # Execute tick
    loop.tick()

    # Verify back to IDLE
    assert loop.state_machines["BTC/USDT"].current_state == TradingState.IDLE

    # Verify gate.breaker.rejected event emitted
    from quantsail_engine.persistence.stub_models import Event
    events = in_memory_db.query(Event).filter(Event.type == "gate.breaker.rejected").all()
    assert len(events) == 1
    assert events[0].level == "WARN"
    assert events[0].public_safe == "true"


def test_gate_volatility_breaker_triggers(in_memory_db: Session) -> None:
    """Test volatility breaker triggers during trade planning."""
    config = BotConfig()
    signals = MagicMock(spec=EnsembleSignalProvider)

    from quantsail_engine.models.signal import Signal, SignalType
    from quantsail_engine.models.strategy import StrategyOutput

    signals.generate_signal.return_value = Signal(
        signal_type=SignalType.ENTER_LONG,
        symbol="BTC/USDT",
        confidence=1.0,
        strategy_outputs=[StrategyOutput(SignalType.ENTER_LONG, 1.0, "mock")]
    )

    # Create high volatility market data
    market_data = MagicMock()
    high_vol_candles = [
        Candle(datetime.now(timezone.utc), 100.0, 200.0, 50.0, 150.0, 1000.0),  # Range = 150
    ]
    market_data.get_candles.return_value = high_vol_candles
    market_data.get_orderbook.return_value = Orderbook(
        bids=[(99.9, 10.0)],
        asks=[(100.1, 10.0)],
    )

    executor = DryRunExecutor()
    loop = TradingLoop(config, in_memory_db, market_data, signals, executor)

    # Mock ATR to make volatility spike trigger
    with patch("quantsail_engine.core.trading_loop.calculate_atr") as mock_atr:
        mock_atr.return_value = [10.0]  # ATR = 10, threshold = 30, range = 150 > 30

        loop.tick()

    # Verify breaker was triggered
    assert "volatility" in loop.breaker_manager.active_breakers

    # Verify back to IDLE
    assert loop.state_machines["BTC/USDT"].current_state == TradingState.IDLE


def test_gate_spread_breaker_triggers(in_memory_db: Session) -> None:
    """Test spread breaker triggers during trade planning."""
    config = BotConfig()
    signals = MagicMock(spec=EnsembleSignalProvider)

    from quantsail_engine.models.signal import Signal, SignalType
    from quantsail_engine.models.strategy import StrategyOutput

    signals.generate_signal.return_value = Signal(
        signal_type=SignalType.ENTER_LONG,
        symbol="BTC/USDT",
        confidence=1.0,
        strategy_outputs=[StrategyOutput(SignalType.ENTER_LONG, 1.0, "mock")]
    )

    # Create wide spread orderbook
    market_data = MagicMock()
    market_data.get_candles.return_value = [
        Candle(datetime.now(timezone.utc), 100.0, 101.0, 99.0, 100.5, 1000.0),
    ]
    wide_spread_ob = Orderbook(
        bids=[(95.0, 10.0)],
        asks=[(105.0, 10.0)],
    )  # Mid = 100, spread = 10, spread_bps = 1000 > 50
    market_data.get_orderbook.return_value = wide_spread_ob

    executor = DryRunExecutor()
    loop = TradingLoop(config, in_memory_db, market_data, signals, executor)

    with patch("quantsail_engine.core.trading_loop.calculate_atr") as mock_atr:
        mock_atr.return_value = [2.0]  # Normal ATR

        loop.tick()

    # Verify breaker was triggered
    assert "spread_slippage" in loop.breaker_manager.active_breakers

    # Verify back to IDLE
    assert loop.state_machines["BTC/USDT"].current_state == TradingState.IDLE


def test_gate_consecutive_losses_breaker_triggers(in_memory_db: Session) -> None:
    """Test consecutive losses breaker triggers during trade planning."""
    config = BotConfig()
    signals = MagicMock(spec=EnsembleSignalProvider)

    from quantsail_engine.models.signal import Signal, SignalType
    from quantsail_engine.models.strategy import StrategyOutput

    signals.generate_signal.return_value = Signal(
        signal_type=SignalType.ENTER_LONG,
        symbol="BTC/USDT",
        confidence=1.0,
        strategy_outputs=[StrategyOutput(SignalType.ENTER_LONG, 1.0, "mock")]
    )

    # Use mock market data with normal volatility and spread
    market_data = MagicMock()
    market_data.get_candles.return_value = [
        Candle(datetime.now(timezone.utc), 100.0, 101.0, 99.0, 100.5, 1000.0),
    ]
    market_data.get_orderbook.return_value = Orderbook(
        bids=[(99.9, 10.0)],
        asks=[(100.1, 10.0)],
    )

    executor = DryRunExecutor()
    loop = TradingLoop(config, in_memory_db, market_data, signals, executor)

    # Add 3 consecutive losing trades
    from quantsail_engine.persistence.stub_models import Trade
    for i in range(3):
        trade = Trade(
            id=f"trade{i}",
            symbol="BTC/USDT",
            mode="DRY_RUN",
            status="CLOSED",
            side="LONG",
            entry_price=100.0,
            quantity=0.01,
            opened_at=datetime.now(timezone.utc),
            closed_at=datetime.now(timezone.utc),
            exit_price=98.0,
            pnl_usd=-2.0,
            pnl_pct=-2.0,
        )
        in_memory_db.add(trade)
    in_memory_db.commit()

    with patch("quantsail_engine.core.trading_loop.calculate_atr") as mock_atr:
        mock_atr.return_value = [2.0]  # Normal ATR

        loop.tick()

    # Verify breaker was triggered
    assert "consecutive_losses" in loop.breaker_manager.active_breakers

    # Verify back to IDLE
    assert loop.state_machines["BTC/USDT"].current_state == TradingState.IDLE


def test_entry_pending_slippage_error_resets(in_memory_db: Session) -> None:
    """Test ENTRY_PENDING state resets on slippage calculation error."""
    config = BotConfig()
    market_data = StubMarketDataProvider(base_price=50000.0)
    signals = MagicMock(spec=EnsembleSignalProvider)

    from quantsail_engine.models.signal import Signal, SignalType
    from quantsail_engine.models.strategy import StrategyOutput

    signals.generate_signal.return_value = Signal(
        signal_type=SignalType.ENTER_LONG,
        symbol="BTC/USDT",
        confidence=1.0,
        strategy_outputs=[StrategyOutput(SignalType.ENTER_LONG, 1.0, "mock")]
    )

    executor = DryRunExecutor()
    loop = TradingLoop(config, in_memory_db, market_data, signals, executor)

    # Force state to ENTRY_PENDING
    loop.state_machines["BTC/USDT"].transition_to(TradingState.EVAL)
    loop.state_machines["BTC/USDT"].transition_to(TradingState.ENTRY_PENDING)

    # Mock calculate_slippage to raise ValueError during ENTRY_PENDING
    with patch("quantsail_engine.core.trading_loop.calculate_slippage") as mock_slip:
        mock_slip.side_effect = ValueError("Insufficient liquidity")

        loop._tick_symbol("BTC/USDT")

    # Verify state reset to IDLE
    assert loop.state_machines["BTC/USDT"].current_state == TradingState.IDLE
