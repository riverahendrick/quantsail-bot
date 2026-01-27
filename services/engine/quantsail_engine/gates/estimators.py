"""Cost estimators for fee, slippage, and spread."""

from quantsail_engine.models.candle import Orderbook


def calculate_fee(
    notional_usd: float, rate_bps: float
) -> float:
    """
    Calculate trading fee in USD.

    Args:
        notional_usd: Notional value of the trade (Price * Qty).
        rate_bps: Fee rate in basis points (1 bps = 0.01%).

    Returns:
        Fee amount in USD.
    """
    return notional_usd * (rate_bps / 10000.0)


def calculate_slippage(
    side: str, quantity: float, orderbook: Orderbook
) -> tuple[float, float]:
    """
    Estimate average fill price and total slippage cost.

    Args:
        side: "BUY" or "SELL".
        quantity: Desired quantity to trade.
        orderbook: Current orderbook snapshot.

    Returns:
        Tuple of (average_fill_price, total_slippage_usd).
        Raises ValueError if insufficient liquidity.
    """
    if quantity <= 0:
        return 0.0, 0.0

    levels = orderbook.asks if side == "BUY" else orderbook.bids
    
    remaining_qty = quantity
    total_cost = 0.0
    
    for price, qty in levels:
        fill_qty = min(remaining_qty, qty)
        total_cost += fill_qty * price
        remaining_qty -= fill_qty
        if remaining_qty <= 0:
            break
            
    if remaining_qty > 0:
        raise ValueError(f"Insufficient liquidity for quantity {quantity}")
        
    avg_fill_price = total_cost / quantity
    best_price = levels[0][0]
    
    if side == "BUY":
        slippage_cost = (avg_fill_price - best_price) * quantity
    else:
        slippage_cost = (best_price - avg_fill_price) * quantity
        
    return avg_fill_price, slippage_cost


def calculate_spread_cost(
    side: str, quantity: float, orderbook: Orderbook
) -> float:
    """
    Estimate spread cost relative to mid-price.

    Entering at market (Best Ask for Buy) incurs half-spread cost vs fair value (Mid).
    
    Args:
        side: "BUY" or "SELL".
        quantity: Trade quantity.
        orderbook: Current orderbook.

    Returns:
        Spread cost in USD.
    """
    if side == "BUY":
        cost_per_unit = orderbook.best_ask - orderbook.mid_price
    else:
        cost_per_unit = orderbook.mid_price - orderbook.best_bid
        
    return cost_per_unit * quantity
