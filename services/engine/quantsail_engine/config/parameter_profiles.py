"""Preset parameter profiles for different risk appetites.

Each profile provides a complete set of configuration overrides that can be
applied on top of the default BotConfig to tune the bot for conservative,
moderate, or aggressive trading.
"""

from __future__ import annotations

from typing import Any

_PROFILES: dict[str, dict[str, Any]] = {
    "conservative": {
        "position_sizing": {
            "method": "risk_pct",
            "risk_pct": 0.5,
            "max_position_pct": 15.0,
            "kelly_fraction": 0.15,
            "fixed_quantity": 0.001,
        },
        "stop_loss": {
            "method": "atr",
            "atr_multiplier": 2.5,
            "atr_period": 14,
            "fixed_pct": 2.5,
        },
        "take_profit": {
            "method": "risk_reward",
            "risk_reward_ratio": 2.0,
            "fixed_pct": 6.0,
            "atr_multiplier": 4.5,
        },
        "trailing_stop": {
            "enabled": True,
            "method": "atr",
            "trail_pct": 1.5,
            "atr_multiplier": 2.5,
            "activation_pct": 0.75,
        },
        "strategies": {
            "ensemble": {
                "mode": "weighted",
                "min_agreement": 2,
                "confidence_threshold": 0.5,
                "weighted_threshold": 0.30,
                "weight_trend": 0.30,
                "weight_mean_reversion": 0.25,
                "weight_breakout": 0.20,
                "weight_vwap": 0.25,
            },
            "trend": {
                "ema_fast": 20,
                "ema_slow": 50,
                "adx_threshold": 28.0,
            },
            "mean_reversion": {
                "bb_period": 20,
                "bb_std_dev": 2.0,
                "rsi_period": 14,
                "rsi_oversold": 30.0,
            },
            "breakout": {
                "atr_filter_mult": 1.0,
            },
            "vwap_reversion": {
                "deviation_entry_pct": 1.5,
                "rsi_oversold": 35.0,
            },
        },
        "portfolio": {
            "max_daily_trades": 5,
            "max_daily_loss_usd": 10.0,
            "max_portfolio_exposure_pct": 20.0,
        },
        "daily": {
            "target_usd": 30.0,
        },
        "risk": {
            "max_risk_per_trade_pct": 0.15,
        },
    },
    "moderate": {
        "position_sizing": {
            "method": "risk_pct",
            "risk_pct": 1.0,
            "max_position_pct": 25.0,
            "kelly_fraction": 0.25,
            "fixed_quantity": 0.001,
        },
        "stop_loss": {
            "method": "atr",
            "atr_multiplier": 2.0,
            "atr_period": 14,
            "fixed_pct": 1.5,
        },
        "take_profit": {
            "method": "risk_reward",
            "risk_reward_ratio": 2.0,
            "fixed_pct": 3.5,
            "atr_multiplier": 3.0,
        },
        "trailing_stop": {
            "enabled": True,
            "method": "atr",
            "trail_pct": 1.0,
            "atr_multiplier": 2.0,
            "activation_pct": 0.5,
        },
        "strategies": {
            "ensemble": {
                "mode": "weighted",
                "min_agreement": 2,
                "confidence_threshold": 0.4,
                "weighted_threshold": 0.35,
                "weight_trend": 0.30,
                "weight_mean_reversion": 0.25,
                "weight_breakout": 0.20,
                "weight_vwap": 0.25,
            },
            "trend": {
                "ema_fast": 20,
                "ema_slow": 50,
                "adx_threshold": 25.0,
            },
            "mean_reversion": {
                "bb_period": 20,
                "bb_std_dev": 2.0,
                "rsi_period": 14,
                "rsi_oversold": 35.0,
            },
            "breakout": {
                "atr_filter_mult": 0.75,
            },
            "vwap_reversion": {
                "deviation_entry_pct": 1.0,
                "rsi_oversold": 38.0,
            },
        },
        "portfolio": {
            "max_daily_trades": 10,
            "max_daily_loss_usd": 20.0,
            "max_portfolio_exposure_pct": 30.0,
        },
        "daily": {
            "target_usd": 50.0,
        },
        "risk": {
            "max_risk_per_trade_pct": 0.25,
        },
    },
    "aggressive": {
        "position_sizing": {
            "method": "kelly",
            "risk_pct": 2.0,
            "max_position_pct": 40.0,
            "kelly_fraction": 0.35,
            "fixed_quantity": 0.001,
        },
        "stop_loss": {
            "method": "atr",
            "atr_multiplier": 2.5,
            "atr_period": 14,
            "fixed_pct": 2.0,
        },
        "take_profit": {
            "method": "risk_reward",
            "risk_reward_ratio": 2.0,
            "fixed_pct": 4.0,
            "atr_multiplier": 3.5,
        },
        "trailing_stop": {
            "enabled": True,
            "method": "atr",
            "trail_pct": 0.75,
            "atr_multiplier": 1.5,
            "activation_pct": 0.3,
        },
        "strategies": {
            "ensemble": {
                "mode": "weighted",
                "min_agreement": 2,
                "confidence_threshold": 0.3,
                "weighted_threshold": 0.25,
                "weight_trend": 0.35,
                "weight_mean_reversion": 0.25,
                "weight_breakout": 0.20,
                "weight_vwap": 0.20,
            },
            "trend": {
                "ema_fast": 12,
                "ema_slow": 50,
                "adx_threshold": 20.0,
            },
            "mean_reversion": {
                "bb_period": 20,
                "bb_std_dev": 2.0,
                "rsi_period": 14,
                "rsi_oversold": 40.0,
            },
            "breakout": {
                "atr_filter_mult": 0.5,
            },
            "vwap_reversion": {
                "deviation_entry_pct": 0.75,
                "rsi_oversold": 42.0,
            },
        },
        "portfolio": {
            "max_daily_trades": 20,
            "max_daily_loss_usd": 50.0,
            "max_portfolio_exposure_pct": 45.0,
        },
        "daily": {
            "target_usd": 100.0,
        },
        "risk": {
            "max_risk_per_trade_pct": 0.50,
        },
    },
    "aggressive_1h": {
        "position_sizing": {
            "method": "kelly",
            "risk_pct": 2.0,
            "max_position_pct": 40.0,   # Required: forces single-trade focus
            "kelly_fraction": 0.35,
            "fixed_quantity": 0.001,
        },
        "stop_loss": {
            "method": "atr",
            "atr_multiplier": 2.0,
            "atr_period": 14,
            "fixed_pct": 2.0,
        },
        "take_profit": {
            "method": "risk_reward",
            "risk_reward_ratio": 3.0,
            "fixed_pct": 6.0,
            "atr_multiplier": 4.0,
        },
        "trailing_stop": {
            "enabled": True,
            "method": "atr",
            "trail_pct": 1.0,
            "atr_multiplier": 2.0,
            "activation_pct": 1.5,
        },
        "strategies": {
            "ensemble": {
                "mode": "weighted",
                "min_agreement": 2,
                "confidence_threshold": 0.40,
                "weighted_threshold": 0.25,
                "weight_trend": 0.40,
                "weight_mean_reversion": 0.20,
                "weight_breakout": 0.20,
                "weight_vwap": 0.20,
            },
            "trend": {
                "ema_fast": 12,
                "ema_slow": 50,
                "adx_threshold": 25.0,
            },
            "mean_reversion": {
                "bb_period": 20,
                "bb_std_dev": 2.0,
                "rsi_period": 14,
                "rsi_oversold": 35.0,
            },
            "breakout": {
                "atr_filter_mult": 0.5,
            },
            "vwap_reversion": {
                "deviation_entry_pct": 0.75,
                "rsi_oversold": 40.0,
            },
        },
        "portfolio": {
            "max_daily_trades": 10,
            "max_daily_loss_usd": 50.0,
            "max_portfolio_exposure_pct": 45.0,
        },
        "daily": {
            "target_usd": 100.0,
        },
        "risk": {
            "max_risk_per_trade_pct": 0.50,
        },
    },
    # Optimized for consistent daily profit: $1-2/day with $1K-5K account.
    # Based on 1-year backtest analysis:
    #   - BTC excluded (29.4% WR, consistently unprofitable)
    #   - Wider SL (2.5x ATR) to avoid premature stop-outs
    #   - Lower R:R (2.0) to increase win rate
    #   - Higher confidence threshold (0.45) to filter weak signals
    #   - Trend strategy weighted highest (0.50) based on best signal quality
    #   - Mean reversion RSI lowered to 30 for higher-quality oversold entries
    "daily_target": {
        "position_sizing": {
            "method": "risk_pct",
            "risk_pct": 1.5,
            "max_position_pct": 30.0,
            "kelly_fraction": 0.25,
            "fixed_quantity": 0.001,
        },
        "stop_loss": {
            "method": "atr",
            "atr_multiplier": 2.5,   # Wider SL to let trades breathe
            "atr_period": 14,
            "fixed_pct": 2.5,
        },
        "take_profit": {
            "method": "risk_reward",
            "risk_reward_ratio": 2.0,  # Lower R:R = higher win rate
            "fixed_pct": 5.0,
            "atr_multiplier": 4.0,
        },
        "trailing_stop": {
            "enabled": True,
            "method": "atr",
            "trail_pct": 1.0,
            "atr_multiplier": 2.0,
            "activation_pct": 1.0,    # Activate trailing after 1% profit
        },
        "strategies": {
            "ensemble": {
                "mode": "weighted",
                "min_agreement": 2,
                "confidence_threshold": 0.40,  # Match aggressive_1h (0.45 = zero trades)
                "weighted_threshold": 0.25,    # Match aggressive_1h (0.30 = zero trades)
                "weight_trend": 0.50,          # Trend is best signal source
                "weight_mean_reversion": 0.20,
                "weight_breakout": 0.10,       # Breakout weakest on crypto
                "weight_vwap": 0.20,
            },
            "trend": {
                "ema_fast": 12,
                "ema_slow": 50,
                "adx_threshold": 20.0,  # Lower threshold = capture more trends
            },
            "mean_reversion": {
                "bb_period": 20,
                "bb_std_dev": 2.0,
                "rsi_period": 14,
                "rsi_oversold": 30.0,  # Stricter = higher quality entries
            },
            "breakout": {
                "atr_filter_mult": 0.75,
            },
            "vwap_reversion": {
                "deviation_entry_pct": 1.0,
                "rsi_oversold": 35.0,
            },
        },
        "portfolio": {
            "max_daily_trades": 8,
            "max_daily_loss_usd": 30.0,
            "max_portfolio_exposure_pct": 35.0,
        },
        "daily": {
            "target_usd": 50.0,  # Display target; actual goal is $1-2/day
        },
        "risk": {
            "max_risk_per_trade_pct": 0.30,
        },
    },
    # 5-minute candle aggressive profile.
    # Faster EMAs for short timeframe, same concentrated position sizing.
    "aggressive_5m": {
        "position_sizing": {
            "method": "kelly",
            "risk_pct": 2.0,
            "max_position_pct": 40.0,   # Same as 1h: single-trade focus
            "kelly_fraction": 0.35,
            "fixed_quantity": 0.001,
        },
        "stop_loss": {
            "method": "atr",
            "atr_multiplier": 2.0,
            "atr_period": 10,           # Shorter ATR for 5m candles
            "fixed_pct": 1.5,
        },
        "take_profit": {
            "method": "risk_reward",
            "risk_reward_ratio": 3.0,
            "fixed_pct": 4.0,
            "atr_multiplier": 4.0,
        },
        "trailing_stop": {
            "enabled": True,
            "method": "atr",
            "trail_pct": 0.5,
            "atr_multiplier": 1.5,
            "activation_pct": 1.0,
        },
        "strategies": {
            "ensemble": {
                "mode": "weighted",
                "min_agreement": 2,
                "confidence_threshold": 0.40,
                "weighted_threshold": 0.25,
                "weight_trend": 0.40,
                "weight_mean_reversion": 0.20,
                "weight_breakout": 0.20,
                "weight_vwap": 0.20,
            },
            "trend": {
                "ema_fast": 8,          # Faster for 5m
                "ema_slow": 21,         # Faster for 5m
                "adx_threshold": 25.0,
            },
            "mean_reversion": {
                "bb_period": 20,
                "bb_std_dev": 2.0,
                "rsi_period": 14,
                "rsi_oversold": 35.0,
            },
            "breakout": {
                "atr_filter_mult": 0.5,
            },
            "vwap_reversion": {
                "deviation_entry_pct": 0.5,   # Tighter for 5m
                "rsi_oversold": 40.0,
            },
        },
        "portfolio": {
            "max_daily_trades": 20,     # More trades on 5m
            "max_daily_loss_usd": 50.0,
            "max_portfolio_exposure_pct": 45.0,
        },
        "daily": {
            "target_usd": 100.0,
        },
        "risk": {
            "max_risk_per_trade_pct": 0.50,
        },
    },
    # ═══════════════════════════════════════════════════════════════════
    # PRODUCTION ROUTING — Per-coin optimal strategy from 1-year backtest
    # ═══════════════════════════════════════════════════════════════════
    # Based on 90-backtest analysis (5 configs × 18 coins × 8,760 candles).
    # Each coin routes to its best-performing strategy via per_coin_overrides.
    # Expected: $2.42/day ($884/year) from $5K account.
    #
    # TREND_ONLY coins: XRP, AVAX, NEAR, APT, ATOM, POL, SUI
    # ENSEMBLE coins: ETH, SOL
    # MEAN_REV coin: DOGE
    # VWAP coin: BNB
    "production_routing": {
        "position_sizing": {
            "method": "kelly",
            "risk_pct": 2.0,
            "max_position_pct": 40.0,
            "kelly_fraction": 0.35,
            "fixed_quantity": 0.001,
        },
        "stop_loss": {
            "method": "atr",
            "atr_multiplier": 2.0,
            "atr_period": 14,
            "fixed_pct": 2.0,
        },
        "take_profit": {
            "method": "risk_reward",
            "risk_reward_ratio": 3.0,
            "fixed_pct": 6.0,
            "atr_multiplier": 4.0,
        },
        "trailing_stop": {
            "enabled": True,
            "method": "atr",
            "trail_pct": 1.0,
            "atr_multiplier": 2.0,
            "activation_pct": 1.5,
        },
        "strategies": {
            "ensemble": {
                "mode": "weighted",
                "min_agreement": 1,
                "confidence_threshold": 0.30,
                "weighted_threshold": 0.15,
                # Global weights (default for coins without overrides)
                "weight_trend": 0.40,
                "weight_mean_reversion": 0.20,
                "weight_breakout": 0.20,
                "weight_vwap": 0.20,
                # Per-coin optimal routing from 1-year backtest
                "per_coin_overrides": {
                    # ── TREND_ONLY ─────────────────────────────
                    "XRP": {
                        "weight_trend": 1.0,
                        "weight_mean_reversion": 0.0,
                        "weight_breakout": 0.0,
                        "weight_vwap": 0.0,
                    },
                    "AVAX": {
                        "weight_trend": 1.0,
                        "weight_mean_reversion": 0.0,
                        "weight_breakout": 0.0,
                        "weight_vwap": 0.0,
                    },
                    "NEAR": {
                        "weight_trend": 1.0,
                        "weight_mean_reversion": 0.0,
                        "weight_breakout": 0.0,
                        "weight_vwap": 0.0,
                    },
                    "APT": {
                        "weight_trend": 1.0,
                        "weight_mean_reversion": 0.0,
                        "weight_breakout": 0.0,
                        "weight_vwap": 0.0,
                    },
                    "ATOM": {
                        "weight_trend": 1.0,
                        "weight_mean_reversion": 0.0,
                        "weight_breakout": 0.0,
                        "weight_vwap": 0.0,
                    },
                    "POL": {
                        "weight_trend": 1.0,
                        "weight_mean_reversion": 0.0,
                        "weight_breakout": 0.0,
                        "weight_vwap": 0.0,
                    },
                    "SUI": {
                        "weight_trend": 1.0,
                        "weight_mean_reversion": 0.0,
                        "weight_breakout": 0.0,
                        "weight_vwap": 0.0,
                    },
                    # ── ENSEMBLE (balanced) ────────────────────
                    "ETH": {
                        "weight_trend": 0.40,
                        "weight_mean_reversion": 0.20,
                        "weight_breakout": 0.20,
                        "weight_vwap": 0.20,
                    },
                    "SOL": {
                        "weight_trend": 0.40,
                        "weight_mean_reversion": 0.20,
                        "weight_breakout": 0.20,
                        "weight_vwap": 0.20,
                    },
                    # ── MEAN REVERSION ─────────────────────────
                    "DOGE": {
                        "weight_trend": 0.0,
                        "weight_mean_reversion": 1.0,
                        "weight_breakout": 0.0,
                        "weight_vwap": 0.0,
                    },
                    # ── VWAP ───────────────────────────────────
                    "BNB": {
                        "weight_trend": 0.0,
                        "weight_mean_reversion": 0.0,
                        "weight_breakout": 0.0,
                        "weight_vwap": 1.0,
                    },
                },
            },
            "trend": {
                "ema_fast": 12,
                "ema_slow": 50,
                "adx_threshold": 25.0,
            },
            "mean_reversion": {
                "bb_period": 20,
                "bb_std_dev": 2.0,
                "rsi_period": 14,
                "rsi_oversold": 35.0,
            },
            "breakout": {
                "atr_filter_mult": 0.5,
            },
            "vwap_reversion": {
                "deviation_entry_pct": 0.75,
                "rsi_oversold": 40.0,
            },
        },
        "portfolio": {
            "max_daily_trades": 15,
            "max_daily_loss_usd": 50.0,
            "max_portfolio_exposure_pct": 45.0,
        },
        "daily": {
            "target_usd": 100.0,
        },
        "risk": {
            "max_risk_per_trade_pct": 0.50,
        },
    },
}

AVAILABLE_PROFILES = list(_PROFILES.keys())


def get_profile(name: str) -> dict[str, Any]:
    """Return configuration overrides for a named profile.

    Args:
        name: Profile name (conservative, moderate, aggressive).

    Returns:
        Dictionary of config overrides to apply.

    Raises:
        ValueError: If profile name is not recognized.
    """
    if name not in _PROFILES:
        raise ValueError(
            f"Unknown profile '{name}'. Available: {AVAILABLE_PROFILES}"
        )
    # Return a deep copy to prevent mutation
    import copy

    return copy.deepcopy(_PROFILES[name])


def list_profiles() -> list[str]:
    """Return list of available profile names."""
    return list(AVAILABLE_PROFILES)


def apply_profile(config_dict: dict[str, Any], profile: str) -> dict[str, Any]:
    """Apply a profile's overrides to an existing config dictionary.

    Performs a deep merge: profile values override matching keys in the
    config, while non-overridden keys are preserved.

    Args:
        config_dict: Base configuration dictionary (e.g. from BotConfig.model_dump()).
        profile: Profile name to apply.

    Returns:
        New dictionary with profile overrides merged in.
    """
    import copy

    overrides = get_profile(profile)
    result = copy.deepcopy(config_dict)
    _deep_merge(result, overrides)
    return result


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> None:
    """Recursively merge override dict into base dict (in-place)."""
    for key, value in override.items():
        if (
            key in base
            and isinstance(base[key], dict)
            and isinstance(value, dict)
        ):
            _deep_merge(base[key], value)
        else:
            base[key] = value
