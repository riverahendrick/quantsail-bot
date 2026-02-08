"""Tests for Monte Carlo stress testing framework."""

import pytest
from unittest.mock import MagicMock

from quantsail_engine.backtest.monte_carlo import (
    MonteCarloSimulator,
    MonteCarloResult,
    MonteCarloRun,
)
from quantsail_engine.backtest.metrics import BacktestMetrics


def create_test_metrics(
    profit_factor: float = 1.5,
    total_return_pct: float = 5.0,
    net_profit_usd: float = 500.0,
    max_drawdown_pct: float = 5.0,
) -> BacktestMetrics:
    """Helper to create test metrics."""
    return BacktestMetrics(
        total_return_pct=total_return_pct,
        net_profit_usd=net_profit_usd,
        max_drawdown_pct=max_drawdown_pct,
        max_drawdown_usd=max_drawdown_pct * 100,  # Approximate
        profit_factor=profit_factor,
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


class TestMonteCarloSimulator:
    """Test suite for MonteCarloSimulator."""

    @pytest.fixture
    def simulator(self) -> MonteCarloSimulator:
        """Create simulator with fixed seed for reproducibility."""
        return MonteCarloSimulator(seed=42)

    @pytest.fixture
    def sample_trades(self) -> list[dict]:
        """Create sample trades for shuffle testing."""
        return [
            {"id": i, "pnl_usd": 10 if i % 3 != 0 else -5, "symbol": "BTC"}
            for i in range(100)
        ]

    @pytest.fixture
    def sample_data(self) -> list[dict]:
        """Create sample candle data."""
        return [
            {"timestamp": 1704067200000 + i * 300000, "close": 50000 + i}
            for i in range(1000)
        ]

    def test_init_with_seed(self):
        """Test initialization with seed."""
        sim = MonteCarloSimulator(seed=123)
        assert sim.seed == 123

    def test_init_without_seed(self):
        """Test initialization without seed."""
        sim = MonteCarloSimulator()
        assert sim.seed is None

    # Trade Shuffle Tests
    def test_trade_shuffle_empty_trades(self, simulator: MonteCarloSimulator):
        """Test trade shuffle with empty trades."""
        result = simulator.run_trade_shuffle(
            trades=[],
            calculate_metrics=lambda t: create_test_metrics(),
            num_simulations=10,
        )
        assert not result.passed
        assert "No trades" in result.rejection_reasons[0]

    def test_trade_shuffle_runs_simulations(
        self,
        simulator: MonteCarloSimulator,
        sample_trades: list,
    ):
        """Test that trade shuffle runs correct number of simulations."""
        calc_metrics = MagicMock(return_value=create_test_metrics())
        
        result = simulator.run_trade_shuffle(
            trades=sample_trades,
            calculate_metrics=calc_metrics,
            num_simulations=100,
        )
        
        assert result.num_simulations == 100
        assert len(result.runs) == 100
        assert calc_metrics.call_count == 100

    def test_trade_shuffle_shuffles_trades(
        self,
        simulator: MonteCarloSimulator,
        sample_trades: list,
    ):
        """Test that trades are actually shuffled."""
        received_orders = []
        
        def track_order(trades: list) -> BacktestMetrics:
            received_orders.append([t["id"] for t in trades[:5]])
            return create_test_metrics()
        
        simulator.run_trade_shuffle(
            trades=sample_trades,
            calculate_metrics=track_order,
            num_simulations=5,
        )
        
        # Orders should be different across runs
        unique_orders = set(tuple(o) for o in received_orders)
        assert len(unique_orders) > 1

    def test_trade_shuffle_passes_with_good_metrics(
        self,
        simulator: MonteCarloSimulator,
        sample_trades: list,
    ):
        """Test pass with consistently good metrics."""
        result = simulator.run_trade_shuffle(
            trades=sample_trades,
            calculate_metrics=lambda t: create_test_metrics(profit_factor=2.0),
            num_simulations=50,
        )
        assert result.passed
        assert len(result.rejection_reasons) == 0

    def test_trade_shuffle_fails_with_poor_metrics(
        self,
        simulator: MonteCarloSimulator,
        sample_trades: list,
    ):
        """Test fail with poor metrics."""
        result = simulator.run_trade_shuffle(
            trades=sample_trades,
            calculate_metrics=lambda t: create_test_metrics(profit_factor=0.8),
            num_simulations=50,
        )
        assert not result.passed
        assert any("5th percentile PF" in r for r in result.rejection_reasons)

    # Param Jitter Tests
    def test_param_jitter_runs_simulations(
        self,
        simulator: MonteCarloSimulator,
        sample_data: list,
    ):
        """Test param jitter runs correct number of simulations."""
        backtest_fn = MagicMock(return_value=create_test_metrics())
        
        result = simulator.run_param_jitter(
            data=sample_data,
            backtest_fn=backtest_fn,
            base_params={"ema_fast": 10, "ema_slow": 30},
            jitter_params=["ema_fast", "ema_slow"],
            num_simulations=50,
        )
        
        assert result.num_simulations == 50
        # +1 for baseline
        assert backtest_fn.call_count == 51

    def test_param_jitter_applies_noise(
        self,
        simulator: MonteCarloSimulator,
        sample_data: list,
    ):
        """Test that params are actually jittered."""
        received_params = []
        
        def track_params(data: list, params: dict) -> BacktestMetrics:
            received_params.append(params.get("ema_fast"))
            return create_test_metrics()
        
        simulator.run_param_jitter(
            data=sample_data,
            backtest_fn=track_params,
            base_params={"ema_fast": 10},
            jitter_params=["ema_fast"],
            num_simulations=20,
        )
        
        # Should have variation (not all 10)
        unique_values = set(received_params)
        assert len(unique_values) > 1

    def test_param_jitter_detects_sensitivity(
        self,
        simulator: MonteCarloSimulator,
        sample_data: list,
    ):
        """Test detection of parameter sensitivity."""
        call_count = [0]
        
        def sensitive_backtest(data: list, params: dict) -> BacktestMetrics:
            call_count[0] += 1
            # Baseline returns good PF
            if call_count[0] == 1:
                return create_test_metrics(profit_factor=3.0)
            # Jittered returns much worse PF (>25% drop)
            return create_test_metrics(profit_factor=1.0)
        
        result = simulator.run_param_jitter(
            data=sample_data,
            backtest_fn=sensitive_backtest,
            base_params={"ema_fast": 10},
            jitter_params=["ema_fast"],
            num_simulations=20,
        )
        
        assert not result.passed
        assert any("PF dropped" in r for r in result.rejection_reasons)

    # Cost Jitter Tests
    def test_cost_jitter_runs_simulations(
        self,
        simulator: MonteCarloSimulator,
        sample_data: list,
    ):
        """Test cost jitter runs correct number of simulations."""
        backtest_fn = MagicMock(return_value=create_test_metrics())
        
        result = simulator.run_cost_jitter(
            data=sample_data,
            backtest_fn=backtest_fn,
            base_params={},
            base_fee_pct=0.1,
            base_slippage_pct=0.05,
            num_simulations=50,
        )
        
        assert result.num_simulations == 50
        assert backtest_fn.call_count == 50

    def test_cost_jitter_varies_costs(
        self,
        simulator: MonteCarloSimulator,
        sample_data: list,
    ):
        """Test that costs are varied."""
        received_fees = []
        received_slippage = []
        
        def track_costs(data: list, params: dict) -> BacktestMetrics:
            received_fees.append(params.get("fee_pct"))
            received_slippage.append(params.get("slippage_pct"))
            return create_test_metrics()
        
        simulator.run_cost_jitter(
            data=sample_data,
            backtest_fn=track_costs,
            base_params={},
            base_fee_pct=0.1,
            base_slippage_pct=0.05,
            num_simulations=20,
        )
        
        # Should have variation
        assert len(set(received_fees)) > 1
        assert len(set(received_slippage)) > 1

    def test_cost_jitter_detects_thin_edge(
        self,
        simulator: MonteCarloSimulator,
        sample_data: list,
    ):
        """Test detection of thin edge with cost sensitivity."""
        def thin_edge_backtest(data: list, params: dict) -> BacktestMetrics:
            # Higher costs result in losses
            fee = params.get("fee_pct", 0.1)
            if fee > 0.11:  # Just a bit above base
                return create_test_metrics(net_profit_usd=-100)
            return create_test_metrics(net_profit_usd=100)
        
        result = simulator.run_cost_jitter(
            data=sample_data,
            backtest_fn=thin_edge_backtest,
            base_params={},
            base_fee_pct=0.1,
            base_slippage_pct=0.05,
            num_simulations=100,
        )
        
        # Should have high negative rate
        assert not result.passed or result.rejection_reasons

    # Statistics Tests
    def test_statistics_calculation(self, simulator: MonteCarloSimulator):
        """Test statistics are correctly calculated."""
        result = MonteCarloResult(test_type="test", num_simulations=100)
        
        profit_factors = [1.0 + i * 0.02 for i in range(100)]  # 1.0 to 2.98
        returns = [i * 0.1 for i in range(100)]  # 0 to 9.9
        drawdowns = [i * 0.05 for i in range(100)]  # 0 to 4.95
        
        result = simulator._calculate_statistics(result, profit_factors, returns, drawdowns)
        
        assert result.mean_profit_factor == pytest.approx(1.99, abs=0.01)
        assert result.mean_return_pct == pytest.approx(4.95, abs=0.1)
        assert result.percentile_5_profit_factor < result.mean_profit_factor
        assert result.percentile_95_profit_factor > result.mean_profit_factor

    # Run All Tests
    def test_run_all(
        self,
        simulator: MonteCarloSimulator,
        sample_trades: list,
        sample_data: list,
    ):
        """Test run_all executes all three tests."""
        backtest_fn = MagicMock(return_value=create_test_metrics())
        calc_fn = MagicMock(return_value=create_test_metrics())
        
        results = simulator.run_all(
            trades=sample_trades,
            data=sample_data,
            backtest_fn=backtest_fn,
            calc_metrics_fn=calc_fn,
            base_params={"ema_fast": 10},
            jitter_params=["ema_fast"],
        )
        
        assert "trade_shuffle" in results
        assert "param_jitter" in results
        assert "cost_jitter" in results
        assert all(isinstance(r, MonteCarloResult) for r in results.values())

    def test_result_to_dict(self):
        """Test MonteCarloResult serialization."""
        result = MonteCarloResult(
            test_type="trade_shuffle",
            num_simulations=1000,
            mean_profit_factor=1.8,
            passed=True,
        )
        d = result.to_dict()
        
        assert d["test_type"] == "trade_shuffle"
        assert d["num_simulations"] == 1000
        assert d["mean_profit_factor"] == 1.8
        assert d["passed"] is True
