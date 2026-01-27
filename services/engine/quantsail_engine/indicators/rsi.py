"""Relative Strength Index (RSI) indicator."""

def calculate_rsi(values: list[float], period: int = 14) -> list[float]:
    """
    Calculate Relative Strength Index (RSI).

    Args:
        values: List of closing prices.
        period: RSI period (default 14).

    Returns:
        List of RSI values. 0.0 for initial insufficient data points.
    """
    if not values or len(values) < period + 1:
        return [0.0] * len(values)

    rsi_values = [0.0] * len(values)
    
    gains = []
    losses = []

    # Calculate initial changes
    for i in range(1, len(values)):
        change = values[i] - values[i - 1]
        if change > 0:
            gains.append(change)
            losses.append(0.0)
        else:
            gains.append(0.0)
            losses.append(abs(change))

    # First Average Gain/Loss (SMA)
    # Note: We need 'period' changes, which means period+1 data points
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    if avg_loss == 0:
        rsi_values[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi_values[period] = 100.0 - (100.0 / (1.0 + rs))

    # Smoothed calculation for subsequent values
    for i in range(period + 1, len(values)):
        # gains/losses list is 0-indexed relative to values 1-indexed.
        # gains[i-1] corresponds to change at values[i]
        current_gain = gains[i - 1]
        current_loss = losses[i - 1]

        avg_gain = ((avg_gain * (period - 1)) + current_gain) / period
        avg_loss = ((avg_loss * (period - 1)) + current_loss) / period

        if avg_loss == 0:
            rsi_values[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi_values[i] = 100.0 - (100.0 / (1.0 + rs))

    return rsi_values
