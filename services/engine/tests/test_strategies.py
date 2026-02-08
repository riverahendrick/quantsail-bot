"Unit tests for strategies."

from unittest.mock import MagicMock, patch

from quantsail_engine.config.models import (
    BotConfig,
    BreakoutStrategyConfig,
    MeanReversionStrategyConfig,
    StrategiesConfig,
    TrendStrategyConfig,
)
from quantsail_engine.models.signal import SignalType
from quantsail_engine.strategies.breakout import BreakoutStrategy
from quantsail_engine.strategies.ensemble import EnsembleCombiner
from quantsail_engine.strategies.mean_reversion import MeanReversionStrategy
from quantsail_engine.strategies.trend import TrendStrategy
from tests.test_indicators import make_candle


def test_trend_strategy_insufficient_data() -> None:
    strat = TrendStrategy()
    config = BotConfig(strategies=StrategiesConfig(trend=TrendStrategyConfig(ema_slow=50)))
    candles = [make_candle(10, 10, 10)]
    output = strat.analyze("BTC/USDT", candles, MagicMock(), config)
    assert output.signal == SignalType.HOLD
    assert output.rationale["reason"] == "insufficient_data"


def test_trend_strategy_long_signal() -> None:
    strat = TrendStrategy()
    # Need > 50 candles.
    # Setup strong trend: Price increasing.
    candles = [make_candle(100 + i * 2, 105 + i * 2, 95 + i * 2) for i in range(60)]
    
    # ADX should be high due to trend.
    # EMA Fast (20) > EMA Slow (50) due to trend.
    config = BotConfig(strategies=StrategiesConfig(trend=TrendStrategyConfig(adx_threshold=20.0)))
    
    output = strat.analyze("BTC/USDT", candles, MagicMock(), config)
    assert output.signal == SignalType.ENTER_LONG
    assert output.confidence > 0.0
    assert output.strategy_name == "trend"


def test_mean_reversion_insufficient_data() -> None:
    strat = MeanReversionStrategy()
    config = BotConfig()
    candles = [make_candle(10, 10, 10)]
    output = strat.analyze("BTC/USDT", candles, MagicMock(), config)
    assert output.signal == SignalType.HOLD


def test_mean_reversion_long_signal() -> None:
    strat = MeanReversionStrategy()
    # Need price <= Lower BB and RSI < Oversold.
    # Create stable range for BB, then drop price sharply.
    candles = [make_candle(100, 105, 95) for _ in range(30)]
    # Drop price to 80 (should be below lower BB which is ~95-2*std)
    # std roughly 0 or small for stable range.
    # RSI will drop if we have a sharp drop.
    
    # Add drops
    for i in range(5):
        candles.append(make_candle(90 - i * 5, 90 - i * 5, 80 - i * 5))
        
    config = BotConfig(strategies=StrategiesConfig(
        mean_reversion=MeanReversionStrategyConfig(rsi_oversold=90.0)
    ))
    
    output = strat.analyze("BTC/USDT", candles, MagicMock(), config)
    assert output.signal == SignalType.ENTER_LONG
    assert output.strategy_name == "mean_reversion"

def test_mean_reversion_zero_oversold_threshold() -> None:
    # Test division by zero protection or confidence logic when threshold is 0
    strat = MeanReversionStrategy()
    candles = [make_candle(100, 100, 100) for _ in range(30)]
    # Mock indicators to force signal
    with patch("quantsail_engine.strategies.mean_reversion.calculate_bollinger_bands") as mock_bb, \
         patch("quantsail_engine.strategies.mean_reversion.calculate_rsi") as mock_rsi:
        
        # Lower BB > Price -> Price <= Lower BB
        mock_bb.return_value.lower = [110.0] * 30
        mock_bb.return_value.upper = [120.0] * 30
        # RSI < Threshold (0). Need RSI -1? No, RSI is 0-100.
        # If threshold is 0, RSI needs to be < 0? Impossible.
        # Wait, if RSI < 0 is impossible, signal won't trigger.
        # But maybe we set current_rsi to -1 just to test logic (though physically impossible)
        mock_rsi.return_value = [-1.0] * 30
        
        config = BotConfig(strategies=StrategiesConfig(
            mean_reversion=MeanReversionStrategyConfig(rsi_oversold=0.0)
        ))
        
        output = strat.analyze("BTC/USDT", candles, MagicMock(), config)
        assert output.signal == SignalType.ENTER_LONG
        assert output.confidence == 1.0


def test_breakout_insufficient_data() -> None:
    strat = BreakoutStrategy()
    config = BotConfig()
    candles = [make_candle(10, 10, 10)]
    output = strat.analyze("BTC/USDT", candles, MagicMock(), config)
    assert output.signal == SignalType.HOLD


def test_breakout_long_signal() -> None:
    strat = BreakoutStrategy()
    # Donchian High of prev period.
    # 20 periods of High=100.
    candles = [make_candle(90, 100, 80) for _ in range(25)]
    # Breakout candle: High=110, Close=105.
    
    candles.append(make_candle(105, 110, 100))
    
    config = BotConfig(strategies=StrategiesConfig(
        breakout=BreakoutStrategyConfig(atr_filter_mult=0.001)
    ))
    
    output = strat.analyze("BTC/USDT", candles, MagicMock(), config)
    assert output.signal == SignalType.ENTER_LONG
    assert output.strategy_name == "breakout"

def test_breakout_zero_atr() -> None:
    strat = BreakoutStrategy()
    candles = [make_candle(100, 100, 100) for _ in range(30)]
    
    # Mock indicators to force signal with ATR=0
    with patch("quantsail_engine.strategies.breakout.calculate_donchian_channels") as mock_dc, \
         patch("quantsail_engine.strategies.breakout.calculate_atr") as mock_atr:
        
        # Donchian high (prev) = 90. Current price (from candles) = 100.
        mock_dc.return_value.high = [90.0] * 30
        # ATR = 0.
        mock_atr.return_value = [0.0] * 30
        
        config = BotConfig(strategies=StrategiesConfig(
            breakout=BreakoutStrategyConfig(atr_filter_mult=0.001)
        ))
        
        output = strat.analyze("BTC/USDT", candles, MagicMock(), config)
        assert output.signal == SignalType.ENTER_LONG
        assert output.confidence == 0.5

def test_ensemble_combiner_exception_handling() -> None:
    # Test that one strategy failing doesn't crash ensemble
    combiner = EnsembleCombiner()
    
    # Mock a strategy that raises
    mock_strategy = MagicMock()
    mock_strategy.analyze.side_effect = Exception("Boom")
    combiner.strategies.append(mock_strategy)
    
    candles = [make_candle(10, 10, 10)]
    config = BotConfig()
    
    signal = combiner.analyze("BTC/USDT", candles, MagicMock(), config)
    
    # Should run others (HOLD on insufficient data) and catch exception
    # Outputs should include the exception rationale
    assert len(signal.strategy_outputs) == 5  # 4 real + 1 mock
    error_outputs = [o for o in signal.strategy_outputs if "error" in o.rationale]
    assert len(error_outputs) == 1
    assert error_outputs[0].rationale["error"] == "Boom"
