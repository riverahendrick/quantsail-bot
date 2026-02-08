"""Tests for backtest metrics calculator."""

from datetime import datetime, timezone

import pytest

from quantsail_engine.backtest.metrics import BacktestMetrics, MetricsCalculator


class TestMetricsCalculator:
    """Test suite for MetricsCalculator."""

    @pytest.fixture
    def calculator(self) -> MetricsCalculator:
        """Create a metrics calculator fixture."""
        return MetricsCalculator(starting_equity=10000.0)

    def test_empty_calculator(self, calculator: MetricsCalculator) -> None:
        """Test calculator with no data."""
        metrics = calculator.calculate()

        assert metrics.total_return_pct == 0.0
        assert metrics.net_profit_usd == 0.0
        assert metrics.total_trades == 0
        assert metrics.max_drawdown_pct == 0.0

    def test_single_winning_trade(self, calculator: MetricsCalculator) -> None:
        """Test metrics with one winning trade."""
        calculator.add_trade({
            "status": "CLOSED",
            "realized_pnl_usd": 150.0,
        })

        # Add equity points
        calculator.add_equity_point(datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc), 10000.0)
        calculator.add_equity_point(datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc), 10150.0)

        metrics = calculator.calculate()

        assert metrics.total_trades == 1
        assert metrics.winning_trades == 1
        assert metrics.losing_trades == 0
        assert metrics.win_rate_pct == 100.0
        assert metrics.total_return_pct == 1.5
        assert metrics.net_profit_usd == 150.0

    def test_single_losing_trade(self, calculator: MetricsCalculator) -> None:
        """Test metrics with one losing trade."""
        calculator.add_trade({
            "status": "CLOSED",
            "realized_pnl_usd": -100.0,
        })

        calculator.add_equity_point(datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc), 10000.0)
        calculator.add_equity_point(datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc), 9900.0)

        metrics = calculator.calculate()

        assert metrics.total_trades == 1
        assert metrics.winning_trades == 0
        assert metrics.losing_trades == 1
        assert metrics.win_rate_pct == 0.0
        assert metrics.total_return_pct == -1.0
        assert metrics.net_profit_usd == -100.0

    def test_mixed_trades(self, calculator: MetricsCalculator) -> None:
        """Test metrics with mix of winning and losing trades."""
        # 3 wins, 2 losses
        trades = [
            {"status": "CLOSED", "realized_pnl_usd": 100.0},
            {"status": "CLOSED", "realized_pnl_usd": -50.0},
            {"status": "CLOSED", "realized_pnl_usd": 200.0},
            {"status": "CLOSED", "realized_pnl_usd": -30.0},
            {"status": "CLOSED", "realized_pnl_usd": 150.0},
        ]

        for trade in trades:
            calculator.add_trade(trade)

        calculator.add_equity_point(datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc), 10000.0)
        calculator.add_equity_point(datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc), 10370.0)

        metrics = calculator.calculate()

        assert metrics.total_trades == 5
        assert metrics.winning_trades == 3
        assert metrics.losing_trades == 2
        assert metrics.win_rate_pct == 60.0
        assert metrics.net_profit_usd == 370.0

    def test_profit_factor(self, calculator: MetricsCalculator) -> None:
        """Test profit factor calculation."""
        # Gross profit: 100 + 200 = 300
        # Gross loss: 50
        # Profit factor: 300 / 50 = 6.0
        trades = [
            {"status": "CLOSED", "realized_pnl_usd": 100.0},
            {"status": "CLOSED", "realized_pnl_usd": -50.0},
            {"status": "CLOSED", "realized_pnl_usd": 200.0},
        ]

        for trade in trades:
            calculator.add_trade(trade)

        calculator.add_equity_point(datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc), 10000.0)
        calculator.add_equity_point(datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc), 10250.0)

        metrics = calculator.calculate()

        assert metrics.profit_factor == 6.0

    def test_profit_factor_no_losses(self, calculator: MetricsCalculator) -> None:
        """Test profit factor when no losing trades."""
        trades = [
            {"status": "CLOSED", "realized_pnl_usd": 100.0},
            {"status": "CLOSED", "realized_pnl_usd": 200.0},
        ]

        for trade in trades:
            calculator.add_trade(trade)

        calculator.add_equity_point(datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc), 10000.0)
        calculator.add_equity_point(datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc), 10300.0)

        metrics = calculator.calculate()

        # When no losses, profit factor equals gross profit
        assert metrics.profit_factor == 300.0

    def test_max_drawdown(self, calculator: MetricsCalculator) -> None:
        """Test maximum drawdown calculation."""
        # Equity curve: 10000 → 10500 → 10200 → 10800 → 10300
        # Peak: 10500, Trough: 10200, Drawdown: (10500-10200)/10500 = 2.86%
        # Peak: 10800, Trough: 10300, Drawdown: (10800-10300)/10800 = 4.63%
        # Max drawdown should be 4.63%

        equity_points = [
            (datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc), 10000.0),
            (datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc), 10500.0),
            (datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc), 10200.0),
            (datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc), 10800.0),
            (datetime(2024, 1, 1, 14, 0, tzinfo=timezone.utc), 10300.0),
        ]

        for ts, equity in equity_points:
            calculator.add_equity_point(ts, equity)

        # Add a trade so we have something
        calculator.add_trade({"status": "CLOSED", "realized_pnl_usd": 300.0})

        metrics = calculator.calculate()

        assert metrics.max_drawdown_pct == pytest.approx(4.63, abs=0.01)
        assert metrics.max_drawdown_usd == pytest.approx(500.0, abs=1.0)

    def test_average_trade_metrics(self, calculator: MetricsCalculator) -> None:
        """Test average win/loss calculations."""
        trades = [
            {"status": "CLOSED", "realized_pnl_usd": 100.0},
            {"status": "CLOSED", "realized_pnl_usd": 200.0},
            {"status": "CLOSED", "realized_pnl_usd": -50.0},
            {"status": "CLOSED", "realized_pnl_usd": -30.0},
        ]

        for trade in trades:
            calculator.add_trade(trade)

        calculator.add_equity_point(datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc), 10000.0)
        calculator.add_equity_point(datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc), 10220.0)

        metrics = calculator.calculate()

        assert metrics.avg_win_usd == 150.0  # (100 + 200) / 2
        assert metrics.avg_loss_usd == -40.0  # (-50 + -30) / 2
        assert metrics.avg_trade_usd == 55.0  # (100 + 200 - 50 - 30) / 4

    def test_safety_stats(self, calculator: MetricsCalculator) -> None:
        """Test safety mechanism stats."""
        calculator.set_safety_stats(
            breaker_triggers=5,
            daily_lock_hits=3,
        )

        calculator.add_equity_point(datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc), 10000.0)
        calculator.add_equity_point(datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc), 10000.0)

        metrics = calculator.calculate()

        assert metrics.circuit_breaker_triggers == 5
        assert metrics.daily_lock_hits == 3

    def test_metrics_to_dict(self, calculator: MetricsCalculator) -> None:
        """Test converting metrics to dictionary."""
        calculator.add_trade({"status": "CLOSED", "realized_pnl_usd": 100.0})
        calculator.add_equity_point(datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc), 10000.0)
        calculator.add_equity_point(datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc), 10100.0)

        metrics = calculator.calculate()
        data = metrics.to_dict()

        assert isinstance(data, dict)
        assert "total_return_pct" in data
        assert "net_profit_usd" in data
        assert "total_trades" in data
        assert data["total_trades"] == 1

    def test_metrics_to_json(self, calculator: MetricsCalculator) -> None:
        """Test converting metrics to JSON."""
        calculator.add_trade({"status": "CLOSED", "realized_pnl_usd": 100.0})
        calculator.add_equity_point(datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc), 10000.0)
        calculator.add_equity_point(datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc), 10100.0)

        metrics = calculator.calculate()
        json_str = metrics.to_json()

        assert isinstance(json_str, str)
        assert '"total_return_pct"' in json_str
        assert '"total_trades"' in json_str


class TestMetricsEdgeCases:
    """Test edge cases for metrics calculation."""

    def test_no_equity_curve(self) -> None:
        """Test calculator with trades but no equity curve."""
        calculator = MetricsCalculator(starting_equity=10000.0)
        calculator.add_trade({"status": "CLOSED", "realized_pnl_usd": 100.0})

        metrics = calculator.calculate()

        # Should still calculate trade stats
        assert metrics.total_trades == 1
        # But returns will be 0 due to no equity data
        assert metrics.total_return_pct == 0.0

    def test_single_equity_point(self) -> None:
        """Test calculator with single equity point."""
        calculator = MetricsCalculator(starting_equity=10000.0)
        calculator.add_equity_point(datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc), 10500.0)

        metrics = calculator.calculate()

        # Can't calculate meaningful metrics with single point
        assert metrics.sharpe_ratio == 0.0

    def test_all_losing_trades(self) -> None:
        """Test calculator with only losing trades."""
        calculator = MetricsCalculator(starting_equity=10000.0)

        trades = [
            {"status": "CLOSED", "realized_pnl_usd": -100.0},
            {"status": "CLOSED", "realized_pnl_usd": -50.0},
        ]

        for trade in trades:
            calculator.add_trade(trade)

        calculator.add_equity_point(datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc), 10000.0)
        calculator.add_equity_point(datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc), 9850.0)

        metrics = calculator.calculate()

        assert metrics.winning_trades == 0
        assert metrics.win_rate_pct == 0.0
        assert metrics.profit_factor == 0.0  # No profit, only losses
