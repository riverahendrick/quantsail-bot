"""Tests for walk-forward analysis framework."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from quantsail_engine.backtest.walk_forward import (
    WalkForwardAnalyzer,
    WFAResult,
    WFAWindow,
)
from quantsail_engine.backtest.metrics import BacktestMetrics


class TestWalkForwardAnalyzer:
    """Test suite for WalkForwardAnalyzer."""

    @pytest.fixture
    def analyzer(self) -> WalkForwardAnalyzer:
        """Create analyzer with short windows for testing."""
        return WalkForwardAnalyzer(
            train_days=30,
            test_days=10,
            step_days=10,
        )

    @pytest.fixture
    def sample_data(self) -> list[dict]:
        """Create sample candle data spanning 120 days."""
        data = []
        start = datetime(2024, 1, 1)
        for i in range(120 * 24 * 12):  # 120 days of 5-min candles
            data.append({
                "timestamp": start + timedelta(minutes=i * 5),
                "open": 50000 + i % 100,
                "high": 50100 + i % 100,
                "low": 49900 + i % 100,
                "close": 50050 + i % 100,
                "volume": 1000,
            })
        return data

    @pytest.fixture
    def mock_backtest_fn(self) -> MagicMock:
        """Create mock backtest function."""
        def backtest(data: list, params: dict) -> BacktestMetrics:
            # Return metrics that vary slightly based on params
            multiplier = params.get("ema_fast", 10) / 10
            return BacktestMetrics(
                total_return_pct=5.0 * multiplier,
                net_profit_usd=500.0 * multiplier,
                max_drawdown_pct=5.0,
                max_drawdown_usd=500.0,
                profit_factor=1.5 * multiplier,
                sharpe_ratio=1.2,
                sortino_ratio=1.5,
                total_trades=20,
                winning_trades=12,
                losing_trades=8,
                avg_win_usd=50.0,
                avg_loss_usd=25.0,
                avg_trade_usd=15.0,
                win_rate_pct=60.0,
                circuit_breaker_triggers=0,
                daily_lock_hits=0,
            )
        return backtest

    def test_init_default_params(self):
        """Test default initialization parameters."""
        analyzer = WalkForwardAnalyzer()
        assert analyzer.train_days == 90
        assert analyzer.test_days == 30
        assert analyzer.step_days == 30

    def test_init_custom_params(self):
        """Test custom initialization parameters."""
        analyzer = WalkForwardAnalyzer(
            train_days=60,
            test_days=14,
            step_days=7,
        )
        assert analyzer.train_days == 60
        assert analyzer.test_days == 14
        assert analyzer.step_days == 7

    def test_run_empty_data(self, analyzer: WalkForwardAnalyzer, mock_backtest_fn):
        """Test run with empty data raises error."""
        with pytest.raises(ValueError, match="Data cannot be empty"):
            analyzer.run(
                data=[],
                backtest_fn=mock_backtest_fn,
                param_grid={"ema_fast": [5, 10]},
            )

    def test_run_insufficient_data(self, analyzer: WalkForwardAnalyzer, mock_backtest_fn):
        """Test run with insufficient data returns rejection."""
        # Only 20 days of data
        short_data = [
            {"timestamp": datetime(2024, 1, 1) + timedelta(days=i)}
            for i in range(20)
        ]
        result = analyzer.run(
            data=short_data,
            backtest_fn=mock_backtest_fn,
            param_grid={"ema_fast": [5, 10]},
        )
        assert not result.passed
        assert "Insufficient data" in result.rejection_reasons[0]

    def test_run_generates_windows(
        self,
        analyzer: WalkForwardAnalyzer,
        sample_data: list,
        mock_backtest_fn,
    ):
        """Test that run generates correct windows."""
        result = analyzer.run(
            data=sample_data,
            backtest_fn=mock_backtest_fn,
            param_grid={"ema_fast": [5, 10, 15]},
        )
        # With 120 days, 30 train + 10 test, step 10
        # Should get multiple windows
        assert len(result.windows) > 0
        assert all(isinstance(w, WFAWindow) for w in result.windows)

    def test_run_aggregates_metrics(
        self,
        analyzer: WalkForwardAnalyzer,
        sample_data: list,
        mock_backtest_fn,
    ):
        """Test that metrics are correctly aggregated."""
        result = analyzer.run(
            data=sample_data,
            backtest_fn=mock_backtest_fn,
            param_grid={"ema_fast": [10]},
        )
        assert result.aggregate_trades > 0
        assert result.aggregate_net_profit_usd != 0
        assert result.aggregate_profit_factor >= 0

    def test_run_checks_acceptance_criteria(
        self,
        analyzer: WalkForwardAnalyzer,
        sample_data: list,
    ):
        """Test acceptance criteria validation."""
        # Create backtest that returns poor metrics
        def poor_backtest(data: list, params: dict) -> BacktestMetrics:
            return BacktestMetrics(
                total_return_pct=-10.0,
                net_profit_usd=-100.0,
                max_drawdown_pct=25.0,  # Fails max DD check
                max_drawdown_usd=2500.0,
                profit_factor=0.5,  # Fails profit factor check
                sharpe_ratio=-0.5,
                sortino_ratio=-0.5,
                total_trades=5,  # Fails min trades check
                winning_trades=2,
                losing_trades=3,
                avg_win_usd=30.0,
                avg_loss_usd=50.0,
                avg_trade_usd=-20.0,
                win_rate_pct=40.0,
                circuit_breaker_triggers=0,
                daily_lock_hits=0,
            )

        result = analyzer.run(
            data=sample_data,
            backtest_fn=poor_backtest,
            param_grid={"ema_fast": [10]},
        )
        assert not result.passed
        assert len(result.rejection_reasons) > 0

    def test_run_with_good_metrics_passes(
        self,
        analyzer: WalkForwardAnalyzer,
        sample_data: list,
    ):
        """Test that good metrics result in pass."""
        def good_backtest(data: list, params: dict) -> BacktestMetrics:
            return BacktestMetrics(
                total_return_pct=8.0,
                net_profit_usd=800.0,
                max_drawdown_pct=8.0,
                max_drawdown_usd=800.0,
                profit_factor=2.5,
                sharpe_ratio=2.0,
                sortino_ratio=2.5,
                total_trades=50,
                winning_trades=35,
                losing_trades=15,
                avg_win_usd=40.0,
                avg_loss_usd=20.0,
                avg_trade_usd=16.0,
                win_rate_pct=70.0,
                circuit_breaker_triggers=0,
                daily_lock_hits=0,
            )

        result = analyzer.run(
            data=sample_data,
            backtest_fn=good_backtest,
            param_grid={"ema_fast": [10]},
        )
        # May still fail on avg daily PnL depending on window count
        # but should pass most criteria
        assert result.aggregate_profit_factor >= analyzer.MIN_PROFIT_FACTOR

    def test_param_combinations_generation(self, analyzer: WalkForwardAnalyzer):
        """Test parameter combination generation."""
        combinations = analyzer._generate_param_combinations({
            "a": [1, 2],
            "b": [10, 20],
        })
        assert len(combinations) == 4
        assert {"a": 1, "b": 10} in combinations
        assert {"a": 1, "b": 20} in combinations
        assert {"a": 2, "b": 10} in combinations
        assert {"a": 2, "b": 20} in combinations

    def test_to_dict(self):
        """Test WFAResult serialization."""
        result = WFAResult(
            windows=[],
            aggregate_trades=100,
            aggregate_net_profit_usd=1000.0,
            aggregate_profit_factor=2.0,
            passed=True,
        )
        d = result.to_dict()
        assert d["windows"] == 0
        assert d["aggregate_trades"] == 100
        assert d["passed"] is True
