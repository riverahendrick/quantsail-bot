"""Tests for DynamicSizer and TrailingStopManager."""

import math

from quantsail_engine.config.models import PositionSizingConfig, TrailingStopConfig
from quantsail_engine.risk.dynamic_sizer import DynamicSizer
from quantsail_engine.risk.trailing_stop import TrailingStopManager


# ── DynamicSizer Tests ──────────────────────────────────────────────────


class TestDynamicSizerFixed:
    """Fixed-quantity sizing method."""

    def test_returns_fixed_quantity(self) -> None:
        config = PositionSizingConfig(method="fixed", fixed_quantity=0.05, max_position_pct=100.0)
        sizer = DynamicSizer(config)
        qty = sizer.calculate(equity_usd=10000, entry_price=50000, atr_value=1000)
        assert qty == 0.05

    def test_caps_at_max_position(self) -> None:
        config = PositionSizingConfig(method="fixed", fixed_quantity=1.0, max_position_pct=1.0)
        sizer = DynamicSizer(config)
        # max_position = 10000 * 1% = 100 USD => 100 / 50000 = 0.002
        qty = sizer.calculate(equity_usd=10000, entry_price=50000, atr_value=1000)
        assert qty == 0.002

    def test_zero_entry_price_returns_zero(self) -> None:
        config = PositionSizingConfig(method="fixed")
        sizer = DynamicSizer(config)
        assert sizer.calculate(equity_usd=10000, entry_price=0, atr_value=100) == 0.0

    def test_negative_entry_price_returns_zero(self) -> None:
        config = PositionSizingConfig(method="fixed")
        sizer = DynamicSizer(config)
        assert sizer.calculate(equity_usd=10000, entry_price=-100, atr_value=100) == 0.0


class TestDynamicSizerRiskPct:
    """Risk-percentage sizing method."""

    def test_basic_risk_pct_sizing(self) -> None:
        config = PositionSizingConfig(method="risk_pct", risk_pct=1.0, max_position_pct=100.0)
        sizer = DynamicSizer(config)
        # risk_usd = 10000 * 1% = 100
        # sl_distance = 500
        # quantity = 100 / 500 = 0.2
        qty = sizer.calculate(equity_usd=10000, entry_price=50000, atr_value=500, sl_distance=500)
        assert qty == 0.2

    def test_uses_atr_when_no_sl_distance(self) -> None:
        config = PositionSizingConfig(method="risk_pct", risk_pct=2.0, max_position_pct=100.0)
        sizer = DynamicSizer(config)
        # risk_usd = 5000 * 2% = 100
        # sl_distance = None => uses ATR * 2 = 1000 * 2 = 2000
        # quantity = 100 / 2000 = 0.05
        qty = sizer.calculate(equity_usd=5000, entry_price=50000, atr_value=1000)
        assert qty == 0.05

    def test_zero_atr_and_no_sl_falls_back_to_fixed(self) -> None:
        config = PositionSizingConfig(method="risk_pct", fixed_quantity=0.01)
        sizer = DynamicSizer(config)
        qty = sizer.calculate(equity_usd=5000, entry_price=50000, atr_value=0.0)
        assert qty == 0.01

    def test_capped_by_max_position(self) -> None:
        config = PositionSizingConfig(method="risk_pct", risk_pct=10.0, max_position_pct=5.0)
        sizer = DynamicSizer(config)
        # risk_usd = 10000 * 10% = 1000
        # sl_distance = 100 => qty = 10.0 (huge)
        # max = 10000 * 5% / 50000 = 0.01
        qty = sizer.calculate(equity_usd=10000, entry_price=50000, atr_value=100, sl_distance=100)
        assert qty == 0.01


class TestDynamicSizerKelly:
    """Kelly criterion sizing method."""

    def test_basic_kelly_sizing(self) -> None:
        config = PositionSizingConfig(method="kelly", kelly_fraction=0.25, max_position_pct=100.0)
        sizer = DynamicSizer(config)
        # p=0.6, b=2.0
        # kelly_f = (0.6*2 - 0.4)/2 = (1.2-0.4)/2 = 0.4
        # position_usd = 10000 * 0.4 * 0.25 = 1000
        # qty = 1000 / 50000 = 0.02
        qty = sizer.calculate(
            equity_usd=10000, entry_price=50000, atr_value=500,
            win_rate=0.6, avg_win_loss_ratio=2.0
        )
        assert math.isclose(qty, 0.02, rel_tol=1e-9)

    def test_defaults_when_no_win_rate(self) -> None:
        config = PositionSizingConfig(method="kelly", kelly_fraction=0.25, max_position_pct=100.0)
        sizer = DynamicSizer(config)
        # Defaults: p=0.5, b=1.5
        # kelly_f = (0.5*1.5 - 0.5)/1.5 = (0.75-0.5)/1.5 = 0.1667
        # position_usd = 10000 * 0.1667 * 0.25 = 416.67
        # qty = 416.67 / 50000 = 0.00833
        qty = sizer.calculate(equity_usd=10000, entry_price=50000, atr_value=500)
        assert math.isclose(qty, 416.6667 / 50000, rel_tol=1e-3)

    def test_negative_kelly_falls_back_to_fixed(self) -> None:
        config = PositionSizingConfig(method="kelly", fixed_quantity=0.01)
        sizer = DynamicSizer(config)
        # p=0.2, b=1.0 => kelly_f = (0.2 - 0.8)/1.0 = -0.6 (negative, don't bet)
        qty = sizer.calculate(
            equity_usd=10000, entry_price=50000, atr_value=500,
            win_rate=0.2, avg_win_loss_ratio=1.0
        )
        assert qty == 0.01


# ── TrailingStopManager Tests ───────────────────────────────────────────


class TestTrailingStopPct:
    """Percentage-based trailing stop."""

    def test_basic_trailing(self) -> None:
        config = TrailingStopConfig(enabled=True, method="pct", trail_pct=2.0, activation_pct=0.0)
        mgr = TrailingStopManager(config)
        mgr.init_position("t1", entry_price=100.0, initial_stop=95.0)

        # Price goes to 110 => trail = 110 * 0.98 = 107.8
        stop = mgr.update("t1", current_price=110.0)
        assert stop == 107.8

    def test_ratchets_up_not_down(self) -> None:
        config = TrailingStopConfig(enabled=True, method="pct", trail_pct=2.0, activation_pct=0.0)
        mgr = TrailingStopManager(config)
        mgr.init_position("t1", entry_price=100.0, initial_stop=95.0)

        mgr.update("t1", current_price=110.0)  # stop = 107.8
        stop = mgr.update("t1", current_price=105.0)  # price dropped but stop stays
        assert stop == 107.8  # Didn't go down

    def test_activation_threshold(self) -> None:
        config = TrailingStopConfig(enabled=True, method="pct", trail_pct=2.0, activation_pct=5.0)
        mgr = TrailingStopManager(config)
        mgr.init_position("t1", entry_price=100.0, initial_stop=90.0)

        # Price at 103 => 3% profit, below 5% activation
        stop = mgr.update("t1", current_price=103.0)
        assert stop == 90.0  # Still initial stop

        # Price at 106 => 6% profit, above 5% activation
        stop = mgr.update("t1", current_price=106.0)
        assert stop == 106.0 * 0.98  # Now trailing


class TestTrailingStopATR:
    """ATR-based trailing stop."""

    def test_basic_atr_trailing(self) -> None:
        config = TrailingStopConfig(
            enabled=True, method="atr", atr_multiplier=2.0, activation_pct=0.0
        )
        mgr = TrailingStopManager(config)
        mgr.init_position("t1", entry_price=100.0, initial_stop=95.0)

        # ATR=5, multiplier=2 => trail = 110 - 10 = 100
        stop = mgr.update("t1", current_price=110.0, atr_value=5.0)
        assert stop == 100.0

    def test_zero_atr_keeps_current_stop(self) -> None:
        config = TrailingStopConfig(
            enabled=True, method="atr", atr_multiplier=2.0, activation_pct=0.0
        )
        mgr = TrailingStopManager(config)
        mgr.init_position("t1", entry_price=100.0, initial_stop=95.0)

        stop = mgr.update("t1", current_price=110.0, atr_value=0.0)
        assert stop == 95.0  # No ATR, can't calculate


class TestTrailingStopShouldExit:
    """Exit signal detection."""

    def test_exit_when_price_hits_stop(self) -> None:
        config = TrailingStopConfig(enabled=True, method="pct", trail_pct=5.0, activation_pct=0.0)
        mgr = TrailingStopManager(config)
        mgr.init_position("t1", entry_price=100.0, initial_stop=90.0)

        mgr.update("t1", current_price=110.0)  # stop = 104.5
        assert mgr.should_exit("t1", current_price=104.5)  # At stop
        assert mgr.should_exit("t1", current_price=103.0)  # Below stop

    def test_no_exit_above_stop(self) -> None:
        config = TrailingStopConfig(enabled=True, method="pct", trail_pct=5.0, activation_pct=0.0)
        mgr = TrailingStopManager(config)
        mgr.init_position("t1", entry_price=100.0, initial_stop=90.0)

        mgr.update("t1", current_price=110.0)
        assert not mgr.should_exit("t1", current_price=106.0)

    def test_disabled_trailing_never_exits(self) -> None:
        config = TrailingStopConfig(enabled=False, method="pct", trail_pct=5.0)
        mgr = TrailingStopManager(config)
        mgr.init_position("t1", entry_price=100.0, initial_stop=90.0)
        assert not mgr.should_exit("t1", current_price=50.0)  # Even way below


class TestTrailingStopManagement:
    """Position management methods."""

    def test_remove_position(self) -> None:
        config = TrailingStopConfig(enabled=True, method="pct", trail_pct=2.0, activation_pct=0.0)
        mgr = TrailingStopManager(config)
        mgr.init_position("t1", entry_price=100.0, initial_stop=90.0)
        mgr.remove_position("t1")
        assert mgr.get_stop_level("t1") is None

    def test_get_stop_level_unknown(self) -> None:
        config = TrailingStopConfig(enabled=True, method="pct", trail_pct=2.0)
        mgr = TrailingStopManager(config)
        assert mgr.get_stop_level("unknown") is None

    def test_multiple_positions(self) -> None:
        config = TrailingStopConfig(enabled=True, method="pct", trail_pct=2.0, activation_pct=0.0)
        mgr = TrailingStopManager(config)
        mgr.init_position("t1", entry_price=100.0, initial_stop=90.0)
        mgr.init_position("t2", entry_price=200.0, initial_stop=180.0)

        mgr.update("t1", current_price=110.0)  # t1 stop = 107.8
        mgr.update("t2", current_price=220.0)  # t2 stop = 215.6

        assert mgr.get_stop_level("t1") == 107.8
        assert mgr.get_stop_level("t2") == 215.6
