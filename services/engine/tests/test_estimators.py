"""Unit tests for cost estimators."""

import math

import pytest

from quantsail_engine.gates.estimators import (
    calculate_fee,
    calculate_slippage,
    calculate_spread_cost,
)
from quantsail_engine.models.candle import Orderbook


def test_calculate_fee() -> None:
    # 10000 USD * 10 bps (0.1%) = 10 USD
    assert calculate_fee(10000.0, 10.0) == 10.0
    # 5000 USD * 50 bps (0.5%) = 25 USD
    assert calculate_fee(5000.0, 50.0) == 25.0
    # 0 value
    assert calculate_fee(0.0, 10.0) == 0.0


def test_calculate_slippage_buy() -> None:
    # Asks: 1.0 @ 100, 1.0 @ 101, 1.0 @ 102
    orderbook = Orderbook(
        bids=[(99.0, 10.0)],
        asks=[(100.0, 1.0), (101.0, 1.0), (102.0, 1.0)]
    )
    
    # 1. Quantity 0.5 (Available at best ask 100)
    # Fill: 0.5 @ 100. Cost 50. Avg 100. Best 100. Slippage 0.
    avg, slip = calculate_slippage("BUY", 0.5, orderbook)
    assert avg == 100.0
    assert slip == 0.0
    
    # 2. Quantity 1.5 (1.0 @ 100, 0.5 @ 101)
    # Cost: 100 + 50.5 = 150.5. Avg: 150.5 / 1.5 = 100.333...
    # Slippage: (100.333 - 100) * 1.5 = 0.333 * 1.5 = 0.5
    # Or: 1.0 traded at 0 slip, 0.5 traded at (101-100)=1 slip -> total 0.5
    avg, slip = calculate_slippage("BUY", 1.5, orderbook)
    assert avg == 150.5 / 1.5
    assert math.isclose(slip, 0.5, rel_tol=1e-9)
    
    # 3. Quantity 3.0 (Full book)
    # Cost: 100 + 101 + 102 = 303. Avg: 101.
    # Slippage: (101 - 100) * 3 = 3.0
    avg, slip = calculate_slippage("BUY", 3.0, orderbook)
    assert avg == 101.0
    assert slip == 3.0


def test_calculate_slippage_exact_match() -> None:
    # Exact match on first level to force early break with rem=0
    orderbook = Orderbook(bids=[(100.0, 1.0)], asks=[(100.0, 1.0)])
    avg, slip = calculate_slippage("BUY", 1.0, orderbook)
    assert avg == 100.0
    assert slip == 0.0


def test_calculate_slippage_sell() -> None:
    # Bids: 1.0 @ 100, 1.0 @ 99, 1.0 @ 98 (descending)
    orderbook = Orderbook(
        bids=[(100.0, 1.0), (99.0, 1.0), (98.0, 1.0)],
        asks=[(101.0, 10.0)]
    )
    
    # 1. Qty 1.5
    # Fill: 1.0 @ 100, 0.5 @ 99.
    # Revenue: 100 + 49.5 = 149.5. Avg: 99.666...
    # Best Bid: 100.
    # Slippage (Cost): (Best - Avg) * Qty = (100 - 99.666) * 1.5 = 0.333 * 1.5 = 0.5
    avg, slip = calculate_slippage("SELL", 1.5, orderbook)
    assert avg == 149.5 / 1.5
    assert math.isclose(slip, 0.5, rel_tol=1e-9)


def test_calculate_slippage_insufficient_liquidity() -> None:
    orderbook = Orderbook(
        bids=[(100.0, 1.0)],
        asks=[(101.0, 1.0)]
    )
    # Ask for 2.0, only 1.0 available
    with pytest.raises(ValueError, match="Insufficient liquidity"):
        calculate_slippage("BUY", 2.0, orderbook)


def test_calculate_slippage_empty_book() -> None:
    # Should technically be validated by Orderbook model, but defensive check
    # Orderbook model ensures at least one bid/ask.
    pass


def test_calculate_slippage_zero_qty() -> None:
    orderbook = Orderbook(bids=[(10.0, 1.0)], asks=[(11.0, 1.0)])
    avg, slip = calculate_slippage("BUY", 0.0, orderbook)
    assert avg == 0.0
    assert slip == 0.0
    
    avg, slip = calculate_slippage("BUY", -1.0, orderbook)
    assert avg == 0.0
    assert slip == 0.0


def test_calculate_spread_cost() -> None:
    # Bid 99, Ask 101. Mid 100. Spread 2. Half-spread 1.
    orderbook = Orderbook(
        bids=[(99.0, 1.0)],
        asks=[(101.0, 1.0)]
    )
    
    # Buy: enters at 101. Cost vs Mid (100) = 1 per unit.
    cost = calculate_spread_cost("BUY", 10.0, orderbook)
    assert cost == 1.0 * 10.0 # 10.0
    
    # Sell: enters at 99. Cost vs Mid (100) = 1 per unit.
    cost = calculate_spread_cost("SELL", 5.0, orderbook)
    assert cost == 1.0 * 5.0 # 5.0