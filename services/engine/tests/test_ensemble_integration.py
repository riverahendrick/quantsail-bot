"""Integration tests for Ensemble Signal Provider."""

from sqlalchemy.orm import Session

from quantsail_engine.config.models import BotConfig, TrendStrategyConfig, EnsembleConfig, StrategiesConfig
from quantsail_engine.core.trading_loop import TradingLoop
from quantsail_engine.execution.dry_run_executor import DryRunExecutor
from quantsail_engine.market_data.stub_provider import StubMarketDataProvider
from quantsail_engine.signals.ensemble_provider import EnsembleSignalProvider
from quantsail_engine.models.candle import Candle, Orderbook
from datetime import datetime, timedelta

def make_trending_candles(start_price: float, count: int) -> list[Candle]:
    candles = []
    price = start_price
    for i in range(count):
        price += 100  # Strong uptrend
        candles.append(Candle(
            timestamp=datetime.now() + timedelta(minutes=i*5),
            open=price,
            high=price+50,
            low=price-50,
            close=price+40,
            volume=1000
        ))
    return candles

def test_ensemble_integration_events(in_memory_db: Session) -> None:
    """Verify ensemble emits correct events."""
    config = BotConfig()
    # Configure ensemble to be easy to trigger
    config.strategies = StrategiesConfig(
        ensemble=EnsembleConfig(min_agreement=1, confidence_threshold=0.1)
    )
    
    # We need candles that trigger at least one strategy
    # Trend strategy needs EMA fast > EMA slow + ADX > 25
    # 60 candles of uptrend should do it
    candles = make_trending_candles(50000.0, 60)
    
    market_data = StubMarketDataProvider(base_price=50000.0)
    # Patch get_candles to return our trending candles
    market_data.get_candles = lambda s, t, l: candles # type: ignore
    
    signals = EnsembleSignalProvider(config)
    executor = DryRunExecutor()

    loop = TradingLoop(config, in_memory_db, market_data, signals, executor)
    loop.tick()

    # Verify events
    from quantsail_engine.persistence.stub_models import Event
    events = in_memory_db.query(Event).all()
    
    # Expect: market.tick, signal.generated (x3), ensemble.decision
    types = [e.type for e in events]
    assert "market.tick" in types
    assert "signal.generated" in types
    assert "ensemble.decision" in types
    
    # Check ensemble decision payload
    ensemble_event = next(e for e in events if e.type == "ensemble.decision")
    assert "votes" in ensemble_event.payload
    assert "total_strategies" in ensemble_event.payload
    assert ensemble_event.payload["total_strategies"] == 3
