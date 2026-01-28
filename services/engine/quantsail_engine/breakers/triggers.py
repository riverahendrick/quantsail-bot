"""Trigger detection functions for circuit breakers."""

from typing import Any

from quantsail_engine.config.models import (
    ConsecutiveLossesBreakerConfig,
    ExchangeInstabilityBreakerConfig,
    SpreadSlippageBreakerConfig,
    VolatilityBreakerConfig,
)
from quantsail_engine.models.candle import Candle, Orderbook
from quantsail_engine.persistence.repository import EngineRepository


def check_volatility_spike(
    config: VolatilityBreakerConfig,
    symbol: str,
    candles: list[Candle],
    atr_values: list[float],
) -> tuple[bool, dict[str, float] | None]:
    """
    Check if current candle range exceeds ATR multiple threshold.

    Args:
        config: Volatility breaker configuration
        symbol: Trading symbol
        candles: Recent candles (last candle is most recent)
        atr_values: ATR values aligned with candles

    Returns:
        Tuple of (should_trigger, context_dict)
    """
    if not config.enabled:
        return False, None

    if not candles or not atr_values:
        return False, None

    current_candle = candles[-1]
    current_atr = atr_values[-1]

    if current_atr == 0:
        return False, None

    candle_range = current_candle.high - current_candle.low
    threshold = config.atr_multiple_pause * current_atr

    if candle_range > threshold:
        context = {
            "candle_range": candle_range,
            "atr": current_atr,
            "atr_multiple": candle_range / current_atr,
            "threshold": threshold,
        }
        return True, context

    return False, None


def check_spread_slippage_spike(
    config: SpreadSlippageBreakerConfig,
    symbol: str,
    orderbook: Orderbook,
    plan: Any,
) -> tuple[bool, dict[str, float] | None]:
    """
    Check if current spread exceeds basis points threshold.

    Args:
        config: Spread/slippage breaker configuration
        symbol: Trading symbol
        orderbook: Current orderbook
        plan: Trade plan with entry price

    Returns:
        Tuple of (should_trigger, context_dict)
    """
    if not config.enabled:
        return False, None

    mid_price = orderbook.mid_price
    if mid_price == 0:
        return False, None

    spread = orderbook.best_ask - orderbook.best_bid
    spread_bps = (spread / mid_price) * 10000

    if spread_bps > config.max_spread_bps:
        context = {
            "spread_bps": spread_bps,
            "max_spread_bps": config.max_spread_bps,
            "best_bid": orderbook.best_bid,
            "best_ask": orderbook.best_ask,
            "mid_price": mid_price,
        }
        return True, context

    return False, None


def check_consecutive_losses(
    config: ConsecutiveLossesBreakerConfig,
    repo: EngineRepository,
) -> tuple[bool, dict[str, Any] | None]:
    """
    Check if consecutive losing trades exceed threshold.

    Args:
        config: Consecutive losses breaker configuration
        repo: Engine repository for querying trades

    Returns:
        Tuple of (should_trigger, context_dict)
    """
    if not config.enabled:
        return False, None

    # Query recent closed trades
    recent_trades = repo.get_recent_closed_trades(limit=config.max_losses + 5)

        if not recent_trades:
            return False, None

        # Count consecutive losses from most recent backwards
        consecutive_losses = 0
        losing_trade_ids = []

        for trade in recent_trades:
            # Check realized_pnl_usd
            pnl = trade.get("realized_pnl_usd")
            if pnl is not None and pnl < 0:
                consecutive_losses += 1
                losing_trade_ids.append(trade["id"])
            else:
                # Streak broken by a winner or breakeven
                break


    if consecutive_losses >= config.max_losses:
        context = {
            "consecutive_losses": consecutive_losses,
            "max_losses": config.max_losses,
            "losing_trade_ids": losing_trade_ids[:config.max_losses],
        }
        return True, context

    return False, None


def check_exchange_instability(
    config: ExchangeInstabilityBreakerConfig,
) -> tuple[bool, dict[str, int] | None]:
    """
    Check for exchange instability (stub for MVP).

    Args:
        config: Exchange instability breaker configuration

    Returns:
        Tuple of (should_trigger, context_dict) - Always False in MVP
    """
    # Stub for MVP - no live exchange connection yet
    return False, None
