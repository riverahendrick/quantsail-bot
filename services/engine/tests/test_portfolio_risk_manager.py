"""Comprehensive tests for PortfolioRiskManager.

Tests all portfolio-level risk constraints:
- Max concurrent positions
- Max correlated positions  
- Max daily trades
- Daily loss limit (hard stop)
- Total portfolio exposure
- Daily counter reset
"""

from datetime import datetime, date, timedelta, timezone
from unittest.mock import patch

import pytest

from quantsail_engine.config.models import (
    PortfolioConfig,
    RiskConfig,
    SymbolsConfig,
)
# Import directly from module to avoid import chain through __init__.py
from quantsail_engine.core.portfolio_risk_manager import PortfolioRiskManager


@pytest.fixture
def default_symbols_config() -> SymbolsConfig:
    """Default symbols configuration with 2 max concurrent."""
    return SymbolsConfig(
        enabled=["BTC/USDT", "ETH/USDT", "ADA/USDT"],
        max_concurrent_positions=2,
    )


@pytest.fixture
def default_portfolio_config() -> PortfolioConfig:
    """Default portfolio config for testing."""
    return PortfolioConfig(
        max_correlated_positions=1,
        max_daily_trades=5,
        max_daily_loss_usd=50.0,
        max_portfolio_exposure_pct=30.0,
    )


@pytest.fixture
def default_risk_config() -> RiskConfig:
    """Default risk config with $1000 starting cash."""
    return RiskConfig(
        starting_cash_usd=1000.0,
        max_risk_per_trade_pct=1.0,
    )


@pytest.fixture
def manager(
    default_symbols_config: SymbolsConfig,
    default_portfolio_config: PortfolioConfig,
    default_risk_config: RiskConfig,
) -> PortfolioRiskManager:
    """Create fresh manager for each test."""
    return PortfolioRiskManager(
        default_symbols_config,
        default_portfolio_config,
        default_risk_config,
    )


class TestMaxConcurrentPositions:
    """Tests for max_concurrent_positions gate."""
    
    def test_allows_first_position(self, manager: PortfolioRiskManager) -> None:
        """Should allow opening first position when none exist."""
        allowed, reason = manager.can_open_position("BTC/USDT", 100.0)
        assert allowed is True
        assert reason == "OK"
    
    def test_allows_up_to_max(self, manager: PortfolioRiskManager) -> None:
        """Should allow positions up to max_concurrent limit."""
        manager.add_position("BTC/USDT", 100.0)
        allowed, reason = manager.can_open_position("ETH/USDT", 100.0)
        assert allowed is True
        assert reason == "OK"
    
    def test_blocks_beyond_max(self, manager: PortfolioRiskManager) -> None:
        """Should block when max_concurrent_positions reached."""
        manager.add_position("BTC/USDT", 100.0)
        manager.add_position("ETH/USDT", 100.0)
        
        allowed, reason = manager.can_open_position("ADA/USDT", 100.0)
        assert allowed is False
        assert "Max concurrent positions (2) reached" in reason
    
    def test_allows_after_close(self, manager: PortfolioRiskManager) -> None:
        """Should allow new position after closing one."""
        manager.add_position("BTC/USDT", 100.0)
        manager.add_position("ETH/USDT", 100.0)
        
        manager.close_position("BTC/USDT", pnl=5.0)
        
        allowed, reason = manager.can_open_position("ADA/USDT", 100.0)
        assert allowed is True


class TestMaxCorrelatedPositions:
    """Tests for max_correlated_positions gate."""
    
    def test_blocks_correlated_symbol(self, manager: PortfolioRiskManager) -> None:
        """Should block second position in same base currency."""
        manager.add_position("BTC/USDT", 100.0)
        
        # BTC/EUR is correlated to BTC/USDT (same base)
        allowed, reason = manager.can_open_position("BTC/EUR", 100.0)
        assert allowed is False
        assert "Max correlated positions (1) reached" in reason
    
    def test_allows_uncorrelated_symbol(self, manager: PortfolioRiskManager) -> None:
        """Should allow position in different base currency."""
        manager.add_position("BTC/USDT", 100.0)
        
        # ETH is not correlated to BTC
        allowed, reason = manager.can_open_position("ETH/USDT", 100.0)
        assert allowed is True
    
    def test_stablecoins_not_correlated(self, manager: PortfolioRiskManager) -> None:
        """Stablecoins should not be considered correlated to each other."""
        manager.add_position("USDT/USD", 100.0)
        
        allowed, reason = manager.can_open_position("USDC/USD", 100.0)
        # Stablecoins are explicitly not correlated
        assert allowed is True


class TestMaxDailyTrades:
    """Tests for max_daily_trades gate."""
    
    def test_blocks_after_max_trades(self, manager: PortfolioRiskManager) -> None:
        """Should block new entries after max_daily_trades reached."""
        # Use up all 5 daily trades
        for i in range(5):
            manager.add_position(f"SYM{i}/USDT", 10.0)
            manager.close_position(f"SYM{i}/USDT", pnl=1.0)
        
        allowed, reason = manager.can_open_position("NEW/USDT", 10.0)
        assert allowed is False
        assert "Max daily trades (5) reached" in reason
    
    def test_allows_within_limit(self, manager: PortfolioRiskManager) -> None:
        """Should allow trades within daily limit."""
        manager.add_position("BTC/USDT", 100.0)
        manager.close_position("BTC/USDT", pnl=1.0)
        
        allowed, reason = manager.can_open_position("ETH/USDT", 100.0)
        assert allowed is True


class TestDailyLossLimit:
    """Tests for max_daily_loss_usd HARD STOP gate."""
    
    def test_blocks_after_loss_limit_hit(self, manager: PortfolioRiskManager) -> None:
        """Should block ALL new entries after daily loss limit breached."""
        # Take a big loss that exceeds limit
        manager.add_position("BTC/USDT", 100.0)
        manager.close_position("BTC/USDT", pnl=-55.0)  # Exceeds $50 limit
        
        allowed, reason = manager.can_open_position("ETH/USDT", 50.0)
        assert allowed is False
        assert "Daily loss limit hit" in reason
        assert "-55.00" in reason
    
    def test_allows_after_small_loss(self, manager: PortfolioRiskManager) -> None:
        """Should allow entries if loss below limit."""
        manager.add_position("BTC/USDT", 100.0)
        manager.close_position("BTC/USDT", pnl=-20.0)  # Below $50 limit
        
        allowed, reason = manager.can_open_position("ETH/USDT", 50.0)
        assert allowed is True
    
    def test_exactly_at_limit_still_blocked(self, manager: PortfolioRiskManager) -> None:
        """Loss exactly at limit should still block (<=)."""
        manager.add_position("BTC/USDT", 100.0)
        manager.close_position("BTC/USDT", pnl=-50.0)  # Exactly at limit
        
        allowed, reason = manager.can_open_position("ETH/USDT", 50.0)
        assert allowed is False


class TestPortfolioExposure:
    """Tests for max_portfolio_exposure_pct gate."""
    
    def test_blocks_over_exposure_limit(self, manager: PortfolioRiskManager) -> None:
        """Should block when total exposure exceeds limit (30% of $1000 = $300)."""
        manager.add_position("BTC/USDT", 200.0)  # 20%
        
        # Adding $150 would make it 35% - over limit
        allowed, reason = manager.can_open_position("ETH/USDT", 150.0)
        assert allowed is False
        assert "Portfolio exposure limit" in reason
    
    def test_allows_within_exposure_limit(self, manager: PortfolioRiskManager) -> None:
        """Should allow if total exposure stays under limit."""
        manager.add_position("BTC/USDT", 100.0)  # 10%
        
        # Adding $100 would be 20% - still under 30%
        allowed, reason = manager.can_open_position("ETH/USDT", 100.0)
        assert allowed is True
    
    def test_exposure_adjusts_with_equity(self, manager: PortfolioRiskManager) -> None:
        """Exposure limit should be based on current equity (starting + pnl)."""
        # Take a profit
        manager.add_position("BTC/USDT", 100.0)
        manager.close_position("BTC/USDT", pnl=100.0)  # Now equity = $1100
        
        # 30% of $1100 = $330 max exposure
        # Should allow $300 position
        allowed, reason = manager.can_open_position("ETH/USDT", 300.0)
        assert allowed is True


class TestDailyReset:
    """Tests for daily counter reset logic."""
    
    def test_resets_on_new_day(self, manager: PortfolioRiskManager) -> None:
        """Should reset counters when date changes."""
        # Use up daily trades
        for i in range(5):
            manager.add_position(f"SYM{i}/USDT", 10.0)
            manager.close_position(f"SYM{i}/USDT", pnl=1.0)
        
        # Mock next day
        tomorrow = datetime.now(timezone.utc).date() + timedelta(days=1)
        with patch.object(manager, "_last_reset", tomorrow - timedelta(days=2)):
            with patch("quantsail_engine.core.portfolio_risk_manager.datetime") as mock_dt:
                mock_dt.now.return_value = datetime(tomorrow.year, tomorrow.month, tomorrow.day, tzinfo=timezone.utc)
                
                # This triggers reset
                was_reset = manager.reset_daily_counters()
                assert was_reset is True
                assert manager.daily_trades_count == 0
                assert manager.daily_realized_pnl == 0.0
    
    def test_no_reset_same_day(self, manager: PortfolioRiskManager) -> None:
        """Should not reset if still same day."""
        manager.daily_trades_count = 3
        manager.daily_realized_pnl = 25.0
        
        was_reset = manager.reset_daily_counters()
        assert was_reset is False
        assert manager.daily_trades_count == 3
        assert manager.daily_realized_pnl == 25.0


class TestPositionManagement:
    """Tests for add_position and close_position."""
    
    def test_add_position_increments_count(self, manager: PortfolioRiskManager) -> None:
        """Adding position should increment daily trades count."""
        assert manager.daily_trades_count == 0
        manager.add_position("BTC/USDT", 100.0)
        assert manager.daily_trades_count == 1
    
    def test_add_position_tracks_notional(self, manager: PortfolioRiskManager) -> None:
        """Should track notional value of positions."""
        manager.add_position("BTC/USDT", 150.0)
        assert manager.open_positions["BTC/USDT"]["notional"] == 150.0
    
    def test_close_position_updates_pnl(self, manager: PortfolioRiskManager) -> None:
        """Closing position should update daily PnL."""
        manager.add_position("BTC/USDT", 100.0)
        manager.close_position("BTC/USDT", pnl=15.0)
        assert manager.daily_realized_pnl == 15.0
    
    def test_close_nonexistent_returns_false(self, manager: PortfolioRiskManager) -> None:
        """Closing non-existent position should return False."""
        result = manager.close_position("FAKE/USDT", pnl=10.0)
        assert result is False
    
    def test_close_removes_from_open(self, manager: PortfolioRiskManager) -> None:
        """Closing should remove position from open_positions."""
        manager.add_position("BTC/USDT", 100.0)
        manager.close_position("BTC/USDT", pnl=5.0)
        assert "BTC/USDT" not in manager.open_positions


class TestStatusSummary:
    """Tests for get_status_summary."""
    
    def test_summary_contains_all_fields(self, manager: PortfolioRiskManager) -> None:
        """Status summary should have all required fields."""
        manager.add_position("BTC/USDT", 100.0)
        
        status = manager.get_status_summary()
        
        assert "open_positions" in status
        assert "max_concurrent" in status
        assert "daily_trades" in status
        assert "max_daily_trades" in status
        assert "daily_pnl_usd" in status
        assert "daily_loss_limit_usd" in status
        assert "total_exposure_usd" in status
        assert "equity_usd" in status
        assert "exposure_pct" in status
        assert "max_exposure_pct" in status
    
    def test_summary_values_accurate(self, manager: PortfolioRiskManager) -> None:
        """Summary values should reflect current state."""
        manager.add_position("BTC/USDT", 100.0)
        manager.add_position("ETH/USDT", 50.0)
        
        status = manager.get_status_summary()
        
        assert status["open_positions"] == 2
        assert status["daily_trades"] == 2
        assert status["total_exposure_usd"] == 150.0
        assert status["exposure_pct"] == 15.0  # 150/1000 = 15%


class TestEquityProperty:
    """Tests for equity calculation."""
    
    def test_equity_equals_starting_cash_initially(
        self, manager: PortfolioRiskManager
    ) -> None:
        """Equity should equal starting cash before any trades."""
        assert manager.equity == 1000.0
    
    def test_equity_adjusts_with_pnl(self, manager: PortfolioRiskManager) -> None:
        """Equity should adjust based on realized P&L."""
        manager.add_position("BTC/USDT", 100.0)
        manager.close_position("BTC/USDT", pnl=50.0)
        
        assert manager.equity == 1050.0
    
    def test_equity_decreases_on_loss(self, manager: PortfolioRiskManager) -> None:
        """Equity should decrease on losses."""
        manager.add_position("BTC/USDT", 100.0)
        manager.close_position("BTC/USDT", pnl=-30.0)
        
        assert manager.equity == 970.0
