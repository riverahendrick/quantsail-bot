"""Tests for AdaptivePositionSizer."""

import pytest

from quantsail_engine.execution.position_sizer import (
    AdaptivePositionSizer,
    FeeModel,
    PositionSizeResult,
)


class TestFeeModel:
    """Test suite for FeeModel."""

    def test_default_rates(self):
        """Test default fee rates."""
        model = FeeModel()
        assert model.maker_rate_bps == 10.0
        assert model.taker_rate_bps == 10.0
        assert model.use_bnb_discount is True

    def test_bnb_discount(self):
        """Test BNB discount reduces fees by 25%."""
        model = FeeModel(use_bnb_discount=True)
        assert model.effective_maker_bps == 7.5  # 10 * 0.75
        assert model.effective_taker_bps == 7.5

    def test_no_bnb_discount(self):
        """Test fees without BNB discount."""
        model = FeeModel(use_bnb_discount=False)
        assert model.effective_maker_bps == 10.0
        assert model.effective_taker_bps == 10.0

    def test_calculate_fee_taker(self):
        """Test taker fee calculation."""
        model = FeeModel(use_bnb_discount=False)
        # $1000 * 0.10% = $1.00
        assert model.calculate_fee(1000.0) == 1.0

    def test_calculate_fee_maker(self):
        """Test maker fee calculation."""
        model = FeeModel(use_bnb_discount=False)
        assert model.calculate_fee(1000.0, is_maker=True) == 1.0

    def test_calculate_fee_with_bnb(self):
        """Test fee calculation with BNB discount."""
        model = FeeModel(use_bnb_discount=True)
        # $1000 * 0.075% = $0.75
        assert model.calculate_fee(1000.0) == 0.75

    def test_calculate_spread_cost(self):
        """Test spread cost calculation."""
        model = FeeModel(spread_bps=2.0)
        # $1000 * 0.02% = $0.20
        assert model.calculate_spread_cost(1000.0) == 0.20

    def test_calculate_slippage(self):
        """Test slippage calculation."""
        model = FeeModel(slippage_bps=3.0)
        # $1000 * 0.03% = $0.30
        assert model.calculate_slippage(1000.0) == 0.30


class TestPositionSizeResult:
    """Test suite for PositionSizeResult."""

    def test_total_costs(self):
        """Test total costs property."""
        result = PositionSizeResult(
            notional=100.0,
            quantity=0.002,
            gross_profit=2.0,
            total_fees=0.15,
            spread_cost=0.02,
            slippage_cost=0.03,
            net_profit=1.80,
            min_profit=0.15,
            risk_amount=1.0,
            risk_pct=0.1,
        )
        assert result.total_costs == pytest.approx(0.20, rel=0.01)

    def test_is_profitable_true(self):
        """Test is_profitable when net > min."""
        result = PositionSizeResult(
            notional=100.0,
            quantity=0.002,
            gross_profit=2.0,
            total_fees=0.15,
            spread_cost=0.02,
            slippage_cost=0.03,
            net_profit=1.80,
            min_profit=0.15,
            risk_amount=1.0,
            risk_pct=0.1,
        )
        assert result.is_profitable is True

    def test_is_profitable_false(self):
        """Test is_profitable when net < min."""
        result = PositionSizeResult(
            notional=100.0,
            quantity=0.002,
            gross_profit=0.10,
            total_fees=0.15,
            spread_cost=0.02,
            slippage_cost=0.03,
            net_profit=-0.10,
            min_profit=0.15,
            risk_amount=1.0,
            risk_pct=0.1,
        )
        assert result.is_profitable is False


class TestAdaptivePositionSizer:
    """Test suite for AdaptivePositionSizer."""

    @pytest.fixture
    def sizer(self) -> AdaptivePositionSizer:
        """Create sizer with default settings."""
        return AdaptivePositionSizer()

    @pytest.fixture
    def custom_sizer(self) -> AdaptivePositionSizer:
        """Create sizer with custom settings."""
        return AdaptivePositionSizer(
            fee_model=FeeModel(use_bnb_discount=True),
            test_notionals=(50.0, 100.0, 200.0),
            min_profit_floor=0.10,
            min_profit_rate=0.001,
            max_risk_pct=2.0,
        )

    def test_default_notionals(self, sizer):
        """Test default notional values."""
        assert sizer.test_notionals == (25.0, 50.0, 100.0, 200.0, 500.0, 1000.0)

    def test_calculate_min_profit_floor(self, sizer):
        """Test min profit uses floor for small trades."""
        # $25 * 0.12% = $0.03, but floor is $0.15
        assert sizer.calculate_min_profit(25.0) == 0.15

    def test_calculate_min_profit_rate(self, sizer):
        """Test min profit uses rate for large trades."""
        # $500 * 0.12% = $0.60 > $0.15 floor
        assert sizer.calculate_min_profit(500.0) == 0.60

    def test_calculate_trade_metrics_long(self, sizer):
        """Test trade metrics for long position."""
        result = sizer.calculate_trade_metrics(
            notional=100.0,
            entry_price=50000.0,
            target_price=51000.0,  # 2% up
            stop_price=49500.0,    # 1% down
            equity=10000.0,
        )
        
        assert result.notional == 100.0
        assert result.quantity == 100.0 / 50000.0
        
        # Gross profit: $100 * (51000-50000)/50000 = $2.00
        assert result.gross_profit == pytest.approx(2.0, rel=0.01)
        
        # Risk: $100 * (50000-49500)/50000 = $1.00
        assert result.risk_amount == pytest.approx(1.0, rel=0.01)
        assert result.risk_pct == pytest.approx(0.01, rel=0.01)  # 1% of $10k

    def test_calculate_trade_metrics_short(self, sizer):
        """Test trade metrics for short position."""
        result = sizer.calculate_trade_metrics(
            notional=100.0,
            entry_price=50000.0,
            target_price=49000.0,  # 2% down (target for short)
            stop_price=50500.0,    # 1% up (stop for short)
            equity=10000.0,
        )
        
        # Same absolute profit regardless of direction
        assert result.gross_profit == pytest.approx(2.0, rel=0.01)
        assert result.risk_amount == pytest.approx(1.0, rel=0.01)

    def test_find_optimal_size_success(self, sizer):
        """Test finding optimal size with profitable trade."""
        result = sizer.find_optimal_size(
            entry_price=50000.0,
            target_price=51500.0,  # 3% target
            stop_price=49500.0,    # 1% stop
            equity=10000.0,
        )
        
        assert result is not None
        # Should find smallest size that's profitable
        assert result.notional in sizer.test_notionals
        assert result.is_profitable

    def test_find_optimal_size_smallest(self, sizer):
        """Test that we get the smallest viable size."""
        # With 5% target, even $25 should be profitable
        result = sizer.find_optimal_size(
            entry_price=100.0,
            target_price=105.0,  # 5% target
            stop_price=99.0,     # 1% stop
            equity=10000.0,
        )
        
        assert result is not None
        # Should return smallest size that works
        assert result.notional == 25.0

    def test_find_optimal_size_skips_unprofitable(self):
        """Test skipping sizes that aren't profitable enough."""
        # Create sizer with high min profit requirement
        sizer = AdaptivePositionSizer(
            min_profit_floor=1.0,  # Need $1 profit
            test_notionals=(25.0, 50.0, 100.0),
        )
        
        # 0.5% target might not be enough for small sizes
        result = sizer.find_optimal_size(
            entry_price=100.0,
            target_price=100.5,  # 0.5% target
            stop_price=99.5,     # 0.5% stop
            equity=10000.0,
        )
        
        if result is not None:
            # If a size works, it must meet min profit
            assert result.net_profit >= 1.0

    def test_find_optimal_size_respects_risk(self, sizer):
        """Test that risk limit is respected."""
        # With tiny equity, larger sizes exceed risk limit
        result = sizer.find_optimal_size(
            entry_price=100.0,
            target_price=110.0,  # 10% target
            stop_price=90.0,     # 10% stop = high risk
            equity=100.0,        # Only $100 equity
            max_risk_pct=1.0,
        )
        
        # High risk trades should be limited or rejected
        if result is not None:
            assert result.risk_pct <= 1.0

    def test_find_optimal_size_no_viable(self, sizer):
        """Test when no viable size exists."""
        result = sizer.find_optimal_size(
            entry_price=100.0,
            target_price=100.01,  # Tiny 0.01% target
            stop_price=99.0,      # 1% stop
            equity=10000.0,
        )
        
        # Profit won't exceed costs
        assert result is None

    def test_find_all_viable_sizes(self, sizer):
        """Test finding all viable sizes."""
        results = sizer.find_all_viable_sizes(
            entry_price=100.0,
            target_price=105.0,  # 5% target
            stop_price=99.0,     # 1% stop
            equity=100000.0,     # Large equity, low risk
        )
        
        # With good setup, multiple sizes should work
        assert len(results) > 0
        for result in results:
            assert result.is_profitable
            assert result.risk_pct <= sizer.max_risk_pct

    def test_find_all_viable_sizes_empty(self, sizer):
        """Test finding all viable sizes when none exist."""
        results = sizer.find_all_viable_sizes(
            entry_price=100.0,
            target_price=100.01,  # Tiny target
            stop_price=99.0,
            equity=10000.0,
        )
        
        assert results == []

    def test_custom_fee_model(self):
        """Test with custom fee model."""
        model = FeeModel(
            maker_rate_bps=5.0,  # 0.05% fee
            taker_rate_bps=5.0,
            use_bnb_discount=False,
            spread_bps=1.0,
            slippage_bps=1.0,
        )
        sizer = AdaptivePositionSizer(fee_model=model)
        
        result = sizer.find_optimal_size(
            entry_price=100.0,
            target_price=101.0,  # 1% target
            stop_price=99.5,
            equity=10000.0,
        )
        
        # Lower fees should allow smaller profitable trades
        assert result is not None

    def test_custom_notionals(self):
        """Test with custom notional list."""
        sizer = AdaptivePositionSizer(
            test_notionals=(10.0, 20.0, 30.0),
        )
        
        result = sizer.find_optimal_size(
            entry_price=100.0,
            target_price=110.0,  # 10% target
            stop_price=99.0,
            equity=10000.0,
        )
        
        assert result is not None
        assert result.notional in (10.0, 20.0, 30.0)

    def test_override_max_risk(self, sizer):
        """Test overriding max risk in find_optimal_size."""
        # Small equity + default 1% max risk = small sizes only
        result_default = sizer.find_optimal_size(
            entry_price=100.0,
            target_price=110.0,
            stop_price=95.0,  # 5% stop = high risk
            equity=500.0,
        )
        
        # Allow higher risk
        result_higher = sizer.find_optimal_size(
            entry_price=100.0,
            target_price=110.0,
            stop_price=95.0,
            equity=500.0,
            max_risk_pct=10.0,  # Allow up to 10% risk
        )
        
        # Higher risk allowance may find a viable size
        if result_default and result_higher:
            assert result_higher.notional >= result_default.notional
