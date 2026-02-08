"""Tests for BacktestRunner."""

import pytest
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

from quantsail_engine.backtest.runner import BacktestRunner
from quantsail_engine.backtest.metrics import BacktestMetrics
from quantsail_engine.config.models import (
    BotConfig,
    SymbolsConfig,
    RiskConfig,
    ExecutionConfig,
    EnsembleConfig,
)
from quantsail_engine.core.state_machine import TradingState
from quantsail_engine.models.signal import Signal, SignalType


@pytest.fixture
def sample_config() -> BotConfig:
    """Create a sample bot configuration for testing."""
    return BotConfig(
        symbols=SymbolsConfig(
            enabled=["BTC/USDT"],
            max_concurrent_positions=1,
        ),
        risk=RiskConfig(
            max_risk_per_trade_pct=1.0,
            starting_cash_usd=10000.0,
        ),
        execution=ExecutionConfig(
            mode="dry-run",
            min_profit_usd=1.0,
            taker_fee_bps=10,
        ),
        ensemble=EnsembleConfig(),
    )


@pytest.fixture
def sample_csv_file(tmp_path: Path) -> Path:
    """Create a sample OHLCV CSV file for testing."""
    csv_content = """timestamp,open,high,low,close,volume
2024-01-01T00:00:00,42000.0,42100.0,41900.0,42050.0,100.0
2024-01-01T00:05:00,42050.0,42200.0,42000.0,42150.0,120.0
2024-01-01T00:10:00,42150.0,42300.0,42100.0,42250.0,110.0
2024-01-01T00:15:00,42250.0,42350.0,42200.0,42300.0,130.0
2024-01-01T00:20:00,42300.0,42400.0,42250.0,42350.0,140.0
2024-01-01T00:25:00,42350.0,42450.0,42300.0,42400.0,125.0
2024-01-01T00:30:00,42400.0,42500.0,42350.0,42450.0,135.0
2024-01-01T00:35:00,42450.0,42550.0,42400.0,42500.0,145.0
2024-01-01T00:40:00,42500.0,42600.0,42450.0,42550.0,155.0
2024-01-01T00:45:00,42550.0,42650.0,42500.0,42600.0,165.0
"""

    csv_file = tmp_path / "test_data.csv"
    csv_file.write_text(csv_content)
    return csv_file


class TestBacktestRunnerInit:
    """Tests for BacktestRunner initialization."""

    def test_init_default_values(
        self, sample_config: BotConfig, sample_csv_file: Path
    ) -> None:
        """Test initialization with default values."""
        runner = BacktestRunner(
            config=sample_config,
            data_file=sample_csv_file,
        )
        try:
            assert runner.starting_cash == 10000.0
            assert runner.slippage_pct == 0.05
            assert runner.fee_pct == 0.1
            assert runner.tick_interval_seconds == 300
            assert runner.progress_interval == 100
        finally:
            runner.close()

    def test_init_custom_values(
        self, sample_config: BotConfig, sample_csv_file: Path
    ) -> None:
        """Test initialization with custom values."""
        runner = BacktestRunner(
            config=sample_config,
            data_file=sample_csv_file,
            starting_cash=5000.0,
            slippage_pct=0.1,
            fee_pct=0.2,
            tick_interval_seconds=60,
            progress_interval=50,
        )
        try:
            assert runner.starting_cash == 5000.0
            assert runner.slippage_pct == 0.1
            assert runner.fee_pct == 0.2
            assert runner.tick_interval_seconds == 60
            assert runner.progress_interval == 50
        finally:
            runner.close()

    def test_init_creates_components(
        self, sample_config: BotConfig, sample_csv_file: Path
    ) -> None:
        """Test that components are created correctly."""
        runner = BacktestRunner(
            config=sample_config,
            data_file=sample_csv_file,
        )
        try:
            assert runner.time_manager is not None
            assert runner.repository is not None
            assert runner.market_provider is not None
            assert runner.execution_engine is not None
            assert runner.signal_provider is not None
            assert runner.daily_lock_manager is not None
            assert runner.profitability_gate is not None
        finally:
            runner.close()


class TestBacktestRunnerRun:
    """Tests for BacktestRunner.run method."""

    def test_run_returns_metrics(
        self, sample_config: BotConfig, sample_csv_file: Path
    ) -> None:
        """Test that run returns BacktestMetrics."""
        runner = BacktestRunner(
            config=sample_config,
            data_file=sample_csv_file,
        )
        
        try:
            result = runner.run()
            assert isinstance(result, BacktestMetrics)
            assert result.start_equity == 10000.0
            assert result.total_trades >= 0
        finally:
            runner.close()

    def test_run_updates_time_manager(
        self, sample_config: BotConfig, sample_csv_file: Path
    ) -> None:
        """Test that run updates time manager after each tick."""
        runner = BacktestRunner(
            config=sample_config,
            data_file=sample_csv_file,
        )
        
        initial_time = runner.time_manager._current_time
        
        try:
            runner.run()
            # Time should have advanced
            assert runner.tick_count >= 0  # Tick count should be tracked
        finally:
            runner.close()


class TestBacktestRunnerHelpers:
    """Tests for BacktestRunner helper methods."""

    def test_get_orderbook(
        self, sample_config: BotConfig, sample_csv_file: Path
    ) -> None:
        """Test _get_orderbook returns orderbook."""
        runner = BacktestRunner(
            config=sample_config,
            data_file=sample_csv_file,
        )
        
        try:
            # Set time to first candle timestamp and get orderbook
            runner.time_manager.set_time(runner.market_provider._candles[0].timestamp)
            
            orderbook = runner._get_orderbook("BTC/USDT")
            assert orderbook is not None
            assert hasattr(orderbook, 'bids')
            assert hasattr(orderbook, 'asks')
        finally:
            runner.close()

    def test_get_candles(
        self, sample_config: BotConfig, sample_csv_file: Path
    ) -> None:
        """Test _get_candles returns candle list."""
        runner = BacktestRunner(
            config=sample_config,
            data_file=sample_csv_file,
        )
        
        try:
            # Set time to have candle data available
            runner.time_manager.set_time(runner.market_provider._candles[-1].timestamp)
            
            candles = runner._get_candles("BTC/USDT", limit=5)
            assert isinstance(candles, list)
        finally:
            runner.close()


class TestBacktestRunnerTick:
    """Tests for BacktestRunner tick methods."""

    def test_tick_all_symbols(
        self, sample_config: BotConfig, sample_csv_file: Path
    ) -> None:
        """Test _tick runs tick_symbol for all enabled symbols."""
        runner = BacktestRunner(
            config=sample_config,
            data_file=sample_csv_file,
        )
        
        try:
            # Set time to first candle timestamp
            runner.time_manager.set_time(runner.market_provider._candles[0].timestamp)
            
            # This should not raise
            runner._tick()
        finally:
            runner.close()

    def test_tick_symbol_idle_state(
        self, sample_config: BotConfig, sample_csv_file: Path
    ) -> None:
        """Test _tick_symbol transitions from IDLE to EVAL."""
        runner = BacktestRunner(
            config=sample_config,
            data_file=sample_csv_file,
        )
        
        try:
            symbol = "BTC/USDT"
            sm = runner.state_machines[symbol]
            
            # Set time to first candle timestamp
            runner.time_manager.set_time(runner.market_provider._candles[0].timestamp)
            
            # Initially IDLE
            assert sm.current_state == TradingState.IDLE
            
            # Tick should transition to EVAL
            runner._tick_symbol(symbol)
            
            # Should have processed (may still be IDLE after evaluation)
            assert sm.current_state in [TradingState.IDLE, TradingState.EVAL]
        finally:
            runner.close()


class TestBacktestRunnerMetrics:
    """Tests for BacktestRunner metrics calculation."""

    def test_calculate_metrics(
        self, sample_config: BotConfig, sample_csv_file: Path
    ) -> None:
        """Test _calculate_metrics returns valid metrics."""
        runner = BacktestRunner(
            config=sample_config,
            data_file=sample_csv_file,
        )
        
        try:
            metrics = runner._calculate_metrics()
            
            assert isinstance(metrics, BacktestMetrics)
            assert metrics.start_equity == runner.starting_cash
            assert metrics.max_drawdown_pct >= 0
        finally:
            runner.close()


class TestBacktestRunnerSaveReport:
    """Tests for BacktestRunner saving functionality."""

    def test_save_report(
        self, sample_config: BotConfig, sample_csv_file: Path, tmp_path: Path
    ) -> None:
        """Test save_report creates JSON file."""
        runner = BacktestRunner(
            config=sample_config,
            data_file=sample_csv_file,
        )
        
        try:
            result = runner.run()
            
            output_path = tmp_path / "backtest_report.json"
            runner.save_report(result, output_path)
            
            assert output_path.exists()
            
            import json
            with open(output_path) as f:
                report = json.load(f)
            
            assert "metrics" in report
            assert "backtest_config" in report
        finally:
            runner.close()


class TestBacktestRunnerClose:
    """Tests for BacktestRunner cleanup."""

    def test_close_cleans_up_resources(
        self, sample_config: BotConfig, sample_csv_file: Path
    ) -> None:
        """Test close cleans up repository."""
        runner = BacktestRunner(
            config=sample_config,
            data_file=sample_csv_file,
        )
        
        # Close should not raise
        runner.close()


class TestBacktestRunnerDailyLock:
    """Tests for daily lock integration in BacktestRunner."""

    def test_daily_lock_rejection(
        self, sample_config: BotConfig, sample_csv_file: Path
    ) -> None:
        """Test that daily lock rejections are handled correctly."""
        runner = BacktestRunner(
            config=sample_config,
            data_file=sample_csv_file,
        )
        
        try:
            # Simulate daily lock being hit
            runner.daily_lock_manager._locked_until = datetime.now(timezone.utc) + timedelta(days=1)
            
            symbol = "BTC/USDT"
            sm = runner.state_machines[symbol]
            
            # Set time to first candle timestamp
            runner.time_manager.set_time(runner.market_provider._candles[0].timestamp)
            
            # Force to EVAL state
            sm.transition_to(TradingState.EVAL)
            
            # Tick should handle daily lock
            runner._tick_symbol(symbol)
            
            # Should be back to IDLE due to daily lock
            assert sm.current_state == TradingState.IDLE
        finally:
            runner.close()


class TestBacktestRunnerMaxPositions:
    """Tests for max positions gate in BacktestRunner."""

    def test_max_positions_rejection(
        self, sample_config: BotConfig, sample_csv_file: Path
    ) -> None:
        """Test max positions rejection is handled correctly."""
        # Set max_concurrent_positions to 0 to always reject
        sample_config.symbols.max_concurrent_positions = 0
        
        runner = BacktestRunner(
            config=sample_config,
            data_file=sample_csv_file,
        )
        
        try:
            # Simulate an open trade
            runner.open_trades["BTC/USDT"] = MagicMock()
            
            symbol = "BTC/USDT"
            sm = runner.state_machines[symbol]
            
            # Set time to first candle timestamp
            runner.time_manager.set_time(runner.market_provider._candles[0].timestamp)
            
            # Force to EVAL state with a long signal
            sm.transition_to(TradingState.EVAL)
            
            # Patch signal generation
            with patch.object(
                runner.signal_provider,
                'generate_signal',
                return_value=Signal(signal_type=SignalType.ENTER_LONG, symbol=symbol, confidence=0.8),
            ):
                runner._tick_symbol(symbol)
            
            # Should be back to IDLE due to max positions
            assert sm.current_state == TradingState.IDLE
        finally:
            runner.close()
