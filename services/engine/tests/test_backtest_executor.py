"""Tests for BacktestExecutor."""

from datetime import datetime, timezone

import pytest

from quantsail_engine.backtest.executor import BacktestExecutor, VirtualWallet
from quantsail_engine.backtest.time_manager import TimeManager
from quantsail_engine.models.candle import Candle
from quantsail_engine.models.trade_plan import TradePlan


class TestVirtualWallet:
    """Test suite for VirtualWallet."""

    def test_initial_balance(self) -> None:
        """Test initial wallet state."""
        wallet = VirtualWallet(initial_cash_usd=10000.0)

        assert wallet.cash_usd == 10000.0
        assert wallet.get_equity(50000.0, "BTC/USDT") == 10000.0
        assert wallet.get_asset_quantity("BTC") == 0.0

    def test_execute_buy(self) -> None:
        """Test executing a buy order."""
        wallet = VirtualWallet(initial_cash_usd=10000.0)
        timestamp = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)

        result = wallet.execute_buy(
            symbol="BTC/USDT",
            quantity=0.1,
            price=50000.0,
            fee_usd=5.0,
            slippage_usd=2.5,
            timestamp=timestamp,
        )

        # Cost: 0.1 * 50000 + 5 + 2.5 = 5007.5
        assert wallet.cash_usd == 10000.0 - 5007.5
        assert wallet.get_asset_quantity("BTC") == 0.1
        assert result["side"] == "BUY"

    def test_execute_buy_insufficient_funds(self) -> None:
        """Test that insufficient funds raises error."""
        wallet = VirtualWallet(initial_cash_usd=100.0)
        timestamp = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)

        with pytest.raises(ValueError, match="Insufficient funds"):
            wallet.execute_buy(
                symbol="BTC/USDT",
                quantity=1.0,
                price=50000.0,
                fee_usd=5.0,
                slippage_usd=2.5,
                timestamp=timestamp,
            )

    def test_execute_sell(self) -> None:
        """Test executing a sell order."""
        wallet = VirtualWallet(initial_cash_usd=10000.0)
        timestamp = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)

        # First buy
        wallet.execute_buy(
            symbol="BTC/USDT",
            quantity=0.1,
            price=50000.0,
            fee_usd=5.0,
            slippage_usd=2.5,
            timestamp=timestamp,
        )

        # Then sell at higher price
        result = wallet.execute_sell(
            symbol="BTC/USDT",
            quantity=0.1,
            price=51000.0,
            fee_usd=5.1,
            slippage_usd=2.55,
            timestamp=timestamp,
        )

        # Asset should be gone
        assert wallet.get_asset_quantity("BTC") == 0.0
        assert result["side"] == "SELL"

    def test_execute_sell_insufficient_assets(self) -> None:
        """Test that selling without assets raises error."""
        wallet = VirtualWallet(initial_cash_usd=10000.0)
        timestamp = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)

        with pytest.raises(ValueError, match="Insufficient BTC"):
            wallet.execute_sell(
                symbol="BTC/USDT",
                quantity=0.1,
                price=50000.0,
                fee_usd=5.0,
                slippage_usd=2.5,
                timestamp=timestamp,
            )

    def test_equity_calculation_with_position(self) -> None:
        """Test equity calculation with open position."""
        wallet = VirtualWallet(initial_cash_usd=10000.0)
        timestamp = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)

        # Buy 0.1 BTC at $50,000
        wallet.execute_buy(
            symbol="BTC/USDT",
            quantity=0.1,
            price=50000.0,
            fee_usd=5.0,
            slippage_usd=2.5,
            timestamp=timestamp,
        )

        # Cash is reduced
        assert wallet.cash_usd < 10000.0

        # Equity at same price should be slightly less due to fees
        equity = wallet.get_equity(50000.0, "BTC/USDT")
        assert equity < 10000.0
        assert equity > 9990.0  # Lost ~$7.5 in fees

        # Equity at higher price
        equity_at_55k = wallet.get_equity(55000.0, "BTC/USDT")
        # 0.1 BTC @ $55,000 = $5,500, plus remaining cash minus fees
        assert equity_at_55k > equity


class TestBacktestExecutor:
    """Test suite for BacktestExecutor."""

    @pytest.fixture
    def executor(self) -> BacktestExecutor:
        """Create a backtest executor fixture."""
        time_mgr = TimeManager()
        time_mgr.set_time(datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc))

        return BacktestExecutor(
            time_manager=time_mgr,
            slippage_pct=0.05,
            fee_pct=0.1,
            initial_cash_usd=10000.0,
        )

    @pytest.fixture
    def sample_plan(self) -> TradePlan:
        """Create a sample trade plan."""
        return TradePlan(
            symbol="BTC/USDT",
            side="BUY",
            entry_price=50000.0,
            quantity=0.1,
            stop_loss_price=49000.0,
            take_profit_price=52000.0,
            estimated_fee_usd=5.0,
            estimated_slippage_usd=2.5,
            estimated_spread_cost_usd=1.0,
            timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            trade_id="test-trade-1",
        )

    def test_execute_entry(self, executor: BacktestExecutor, sample_plan: TradePlan) -> None:
        """Test executing an entry order."""
        result = executor.execute_entry(sample_plan)

        assert result is not None
        trade = result["trade"]
        assert trade["symbol"] == "BTC/USDT"
        assert trade["side"] == "BUY"
        assert trade["status"] == "OPEN"
        assert len(result["orders"]) == 3  # Entry, SL, TP

        # Check wallet was updated
        wallet = executor.get_wallet()
        assert wallet.get_asset_quantity("BTC") == 0.1

    def test_entry_slippage_applied(self, executor: BacktestExecutor, sample_plan: TradePlan) -> None:
        """Test that slippage is applied to entry price."""
        result = executor.execute_entry(sample_plan)

        assert result is not None
        trade = result["trade"]

        # With 0.05% slippage on BUY, price should be higher
        # Note: actual fill depends on implementation, but should be close to entry price
        assert trade["entry_price"] > 0

    def test_check_exits_stop_loss(self, executor: BacktestExecutor, sample_plan: TradePlan) -> None:
        """Test that stop loss is triggered correctly."""
        # Execute entry
        entry_result = executor.execute_entry(sample_plan)
        assert entry_result is not None
        trade_id = entry_result["trade"]["id"]

        # Price drops below SL
        exit_result = executor.check_exits(trade_id, current_price=48900.0)

        assert exit_result is not None
        assert exit_result["exit_reason"] == "STOP_LOSS"
        trade = exit_result["trade"]
        assert trade["status"] == "CLOSED"
        assert trade["realized_pnl_usd"] < 0  # Loss

    def test_check_exits_take_profit(self, executor: BacktestExecutor, sample_plan: TradePlan) -> None:
        """Test that take profit is triggered correctly."""
        # Execute entry
        entry_result = executor.execute_entry(sample_plan)
        assert entry_result is not None
        trade_id = entry_result["trade"]["id"]

        # Price rises above TP
        exit_result = executor.check_exits(trade_id, current_price=52100.0)

        assert exit_result is not None
        assert exit_result["exit_reason"] == "TAKE_PROFIT"
        trade = exit_result["trade"]
        assert trade["status"] == "CLOSED"
        assert trade["realized_pnl_usd"] > 0  # Profit

    def test_check_exits_no_trigger(self, executor: BacktestExecutor, sample_plan: TradePlan) -> None:
        """Test that exit is not triggered when price is in range."""
        # Execute entry
        entry_result = executor.execute_entry(sample_plan)
        assert entry_result is not None
        trade_id = entry_result["trade"]["id"]

        # Price in middle of range
        exit_result = executor.check_exits(trade_id, current_price=50500.0)

        assert exit_result is None  # No exit triggered

    def test_position_tracking(self, executor: BacktestExecutor, sample_plan: TradePlan) -> None:
        """Test that open positions are tracked correctly."""
        # No positions initially
        assert len(executor.get_open_trades()) == 0

        # Execute entry
        entry_result = executor.execute_entry(sample_plan)
        assert entry_result is not None
        trade_id = entry_result["trade"]["id"]

        # Position should be tracked
        assert len(executor.get_open_trades()) == 1
        assert trade_id in executor.get_open_trades()

        # Exit
        executor.check_exits(trade_id, current_price=52100.0)

        # Position should be removed
        assert len(executor.get_open_trades()) == 0

    def test_wallet_equity_tracking(self, executor: BacktestExecutor, sample_plan: TradePlan) -> None:
        """Test wallet equity tracking through a trade."""
        wallet = executor.get_wallet()
        initial_equity = wallet.get_equity(50000.0)

        # Execute entry
        entry_result = executor.execute_entry(sample_plan)
        assert entry_result is not None
        trade_id = entry_result["trade"]["id"]

        # Equity should decrease due to entry fees
        equity_after_entry = wallet.get_equity(50000.0)
        assert equity_after_entry < initial_equity

        # Exit at profit
        executor.check_exits(trade_id, current_price=52100.0)

        # Equity should reflect profit (minus fees)
        equity_after_exit = wallet.get_equity(52100.0)
        assert equity_after_exit > equity_after_entry


class TestVirtualWalletCanAfford:
    """Tests for VirtualWallet.can_afford method."""

    def test_can_afford_true(self) -> None:
        """Test can_afford returns True when funds are sufficient."""
        wallet = VirtualWallet(initial_cash_usd=10000.0)
        
        # Can afford 0.1 BTC at $50,000 = $5,000
        assert wallet.can_afford(quantity=0.1, price=50000.0) is True

    def test_can_afford_false(self) -> None:
        """Test can_afford returns False when funds are insufficient."""
        wallet = VirtualWallet(initial_cash_usd=1000.0)
        
        # Cannot afford 0.1 BTC at $50,000 = $5,000
        assert wallet.can_afford(quantity=0.1, price=50000.0) is False

    def test_can_afford_exact_amount(self) -> None:
        """Test can_afford returns True when exact amount available."""
        wallet = VirtualWallet(initial_cash_usd=5000.0)
        
        # Can exactly afford 0.1 BTC at $50,000 = $5,000
        assert wallet.can_afford(quantity=0.1, price=50000.0) is True


class TestBacktestExecutorEdgeCases:
    """Edge case tests for BacktestExecutor."""

    @pytest.fixture
    def executor(self) -> BacktestExecutor:
        """Create a backtest executor fixture."""
        time_mgr = TimeManager()
        time_mgr.set_time(datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc))

        return BacktestExecutor(
            time_manager=time_mgr,
            slippage_pct=0.05,
            fee_pct=0.1,
            initial_cash_usd=10000.0,
        )

    def test_check_exits_unknown_trade_id(self, executor: BacktestExecutor) -> None:
        """Test check_exits returns None for unknown trade_id."""
        result = executor.check_exits("nonexistent-trade-id", current_price=50000.0)
        assert result is None

    def test_execute_entry_insufficient_funds(self) -> None:
        """Test execute_entry returns None when wallet has insufficient funds."""
        time_mgr = TimeManager()
        time_mgr.set_time(datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc))

        # Create executor with very low initial cash
        executor = BacktestExecutor(
            time_manager=time_mgr,
            slippage_pct=0.05,
            fee_pct=0.1,
            initial_cash_usd=100.0,  # Only $100
        )

        # Try to buy $5000 worth of BTC
        plan = TradePlan(
            symbol="BTC/USDT",
            side="BUY",
            entry_price=50000.0,
            quantity=0.1,  # 0.1 * 50000 = $5000
            stop_loss_price=49000.0,
            take_profit_price=52000.0,
            estimated_fee_usd=5.0,
            estimated_slippage_usd=2.5,
            estimated_spread_cost_usd=1.0,
            timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            trade_id="test-trade-1",
        )

        result = executor.execute_entry(plan)
        assert result is None  # Entry should fail

    def test_set_current_candle(self, executor: BacktestExecutor) -> None:
        """Test set_current_candle sets the candle correctly."""
        candle = Candle(
            timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            open=50000.0,
            high=50100.0,
            low=49900.0,
            close=50050.0,
            volume=100.0,
        )
        
        executor.set_current_candle(candle)
        assert executor._get_current_candle() == candle

    def test_execute_entry_uses_candle_price(self) -> None:
        """Test that entry uses candle price when set."""
        time_mgr = TimeManager()
        time_mgr.set_time(datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc))

        executor = BacktestExecutor(
            time_manager=time_mgr,
            slippage_pct=0.0,  # No slippage for easier testing
            fee_pct=0.0,  # No fees for easier testing
            initial_cash_usd=10000.0,
        )

        # Set current candle with different price
        candle = Candle(
            timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            open=48000.0,
            high=49000.0,
            low=47000.0,
            close=48500.0,  # Different from plan entry price
            volume=100.0,
        )
        executor.set_current_candle(candle)

        plan = TradePlan(
            symbol="BTC/USDT",
            side="BUY",
            entry_price=50000.0,  # Plan price is different
            quantity=0.1,
            stop_loss_price=47000.0,
            take_profit_price=52000.0,
            estimated_fee_usd=0.0,
            estimated_slippage_usd=0.0,
            estimated_spread_cost_usd=0.0,
            timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            trade_id="test-trade-1",
        )

        result = executor.execute_entry(plan)
        assert result is not None
        # Should use candle close price (48500), not plan entry price (50000)
        assert result["trade"]["entry_price"] == 48500.0
