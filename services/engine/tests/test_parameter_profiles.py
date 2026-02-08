"""Tests for parameter profiles module."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from quantsail_engine.config.models import BotConfig, TrendStrategyConfig
from quantsail_engine.config.parameter_profiles import (
    AVAILABLE_PROFILES,
    apply_profile,
    get_profile,
    list_profiles,
)


class TestListProfiles:
    """Tests for list_profiles."""

    def test_returns_three_profiles(self) -> None:
        profiles = list_profiles()
        assert len(profiles) == 3
        assert "conservative" in profiles
        assert "moderate" in profiles
        assert "aggressive" in profiles

    def test_matches_constant(self) -> None:
        assert list_profiles() == AVAILABLE_PROFILES


class TestGetProfile:
    """Tests for get_profile."""

    def test_conservative_profile(self) -> None:
        profile = get_profile("conservative")
        assert profile["position_sizing"]["risk_pct"] == 0.5
        assert profile["stop_loss"]["atr_multiplier"] == 2.5
        assert profile["take_profit"]["risk_reward_ratio"] == 2.0
        assert profile["portfolio"]["max_daily_trades"] == 5

    def test_moderate_profile(self) -> None:
        profile = get_profile("moderate")
        assert profile["position_sizing"]["risk_pct"] == 1.0
        assert profile["stop_loss"]["atr_multiplier"] == 2.0
        assert profile["strategies"]["ensemble"]["mode"] == "weighted"

    def test_aggressive_profile(self) -> None:
        profile = get_profile("aggressive")
        assert profile["position_sizing"]["method"] == "kelly"
        assert profile["stop_loss"]["atr_multiplier"] == 2.5
        assert profile["portfolio"]["max_daily_trades"] == 20

    def test_unknown_profile_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown profile 'nonexistent'"):
            get_profile("nonexistent")

    def test_returns_deep_copy(self) -> None:
        """Ensure mutations don't affect the source."""
        p1 = get_profile("conservative")
        p1["position_sizing"]["risk_pct"] = 999.0
        p2 = get_profile("conservative")
        assert p2["position_sizing"]["risk_pct"] == 0.5


class TestApplyProfile:
    """Tests for apply_profile."""

    def test_apply_conservative(self) -> None:
        base = BotConfig().model_dump()
        result = apply_profile(base, "conservative")
        assert result["position_sizing"]["risk_pct"] == 0.5
        assert result["stop_loss"]["atr_multiplier"] == 2.5

    def test_apply_aggressive(self) -> None:
        base = BotConfig().model_dump()
        result = apply_profile(base, "aggressive")
        assert result["position_sizing"]["method"] == "kelly"
        assert result["trailing_stop"]["activation_pct"] == 0.3

    def test_preserves_non_overridden_fields(self) -> None:
        """Non-overridden fields should remain at their original values."""
        base = BotConfig().model_dump()
        base["execution"]["mode"] = "live"
        result = apply_profile(base, "moderate")
        # execution.mode is not overridden by any profile
        assert result["execution"]["mode"] == "live"
        # But profile-touched fields change
        assert result["position_sizing"]["risk_pct"] == 1.0

    def test_apply_unknown_raises(self) -> None:
        base = BotConfig().model_dump()
        with pytest.raises(ValueError, match="Unknown profile"):
            apply_profile(base, "invalid")

    def test_applied_config_validates(self) -> None:
        """Ensure profile overrides produce a valid BotConfig."""
        for profile_name in list_profiles():
            base = BotConfig().model_dump()
            result = apply_profile(base, profile_name)
            # Should successfully create a BotConfig
            config = BotConfig(**result)
            assert config is not None


class TestCrossParameterValidation:
    """Tests for cross-parameter validators in models."""

    def test_ema_fast_lt_slow_valid(self) -> None:
        cfg = TrendStrategyConfig(ema_fast=12, ema_slow=50)
        assert cfg.ema_fast == 12
        assert cfg.ema_slow == 50

    def test_ema_fast_eq_slow_raises(self) -> None:
        with pytest.raises(ValidationError, match="ema_fast.*must be less than ema_slow"):
            TrendStrategyConfig(ema_fast=50, ema_slow=50)

    def test_ema_fast_gt_slow_raises(self) -> None:
        with pytest.raises(ValidationError, match="ema_fast.*must be less than ema_slow"):
            TrendStrategyConfig(ema_fast=100, ema_slow=50)

    def test_risk_coherence_valid(self) -> None:
        """Default config should pass validation."""
        config = BotConfig()
        assert config is not None

    def test_risk_exceeds_exposure_raises(self) -> None:
        """Risk per trade greater than max exposure should fail."""
        with pytest.raises(ValidationError, match="max_risk_per_trade_pct.*cannot exceed"):
            BotConfig(
                risk={"max_risk_per_trade_pct": 50.0},
                portfolio={"max_portfolio_exposure_pct": 10.0},
            )

    def test_daily_loss_too_high_raises(self) -> None:
        """Daily loss limit exceeding 2x daily target should fail."""
        with pytest.raises(ValidationError, match="max_daily_loss_usd.*should not exceed"):
            BotConfig(
                portfolio={"max_daily_loss_usd": 200.0},
                daily={"target_usd": 50.0},
            )

    def test_profile_field_accepts_valid_values(self) -> None:
        for profile in ["conservative", "moderate", "aggressive", "custom"]:
            cfg = BotConfig(profile=profile)
            assert cfg.profile == profile

    def test_profile_field_rejects_invalid(self) -> None:
        with pytest.raises(ValidationError):
            BotConfig(profile="invalid_profile")
