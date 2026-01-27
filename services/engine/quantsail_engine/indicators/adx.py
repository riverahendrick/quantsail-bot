"""Average Directional Index (ADX) indicator."""

from quantsail_engine.models.candle import Candle


def calculate_adx(candles: list[Candle], period: int = 14) -> list[float]:
    """
    Calculate Average Directional Index (ADX).

    Args:
        candles: List of candles.
        period: Smoothing period.

    Returns:
        List of ADX values.
    """
    length = len(candles)
    adx_values = [0.0] * length
    
    if length < 2 * period:
        return adx_values

    tr_list = []
    plus_dm_list = []
    minus_dm_list = []

    # Calculate TR, +DM, -DM
    # First candle has no previous data
    tr_list.append(0.0)
    plus_dm_list.append(0.0)
    minus_dm_list.append(0.0)

    for i in range(1, length):
        high = candles[i].high
        low = candles[i].low
        prev_high = candles[i - 1].high
        prev_low = candles[i - 1].low
        prev_close = candles[i - 1].close

        # TR
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        tr_list.append(tr)

        # Directional Movement
        up_move = high - prev_high
        down_move = prev_low - low

        plus_dm_list.append(up_move if up_move > down_move and up_move > 0 else 0.0)
        minus_dm_list.append(down_move if down_move > up_move and down_move > 0 else 0.0)

    # Smooth TR, +DM, -DM (Wilder's smoothing)
    # First value is sum
    smooth_tr = [0.0] * length
    smooth_plus_dm = [0.0] * length
    smooth_minus_dm = [0.0] * length

    # Initial sums at index 'period' (using indices 1 to period)
    # Note: TR/DM lists align with candles index.
    smooth_tr[period] = sum(tr_list[1 : period + 1])
    smooth_plus_dm[period] = sum(plus_dm_list[1 : period + 1])
    smooth_minus_dm[period] = sum(minus_dm_list[1 : period + 1])

    for i in range(period + 1, length):
        smooth_tr[i] = smooth_tr[i - 1] - (smooth_tr[i - 1] / period) + tr_list[i]
        smooth_plus_dm[i] = (
            smooth_plus_dm[i - 1] - (smooth_plus_dm[i - 1] / period) + plus_dm_list[i]
        )
        smooth_minus_dm[i] = (
            smooth_minus_dm[i - 1] - (smooth_minus_dm[i - 1] / period) + minus_dm_list[i]
        )

    # Calculate DX
    dx_list = [0.0] * length
    for i in range(period, length):
        tr_val = smooth_tr[i]
        if tr_val == 0:
            dx_list[i] = 0.0
            continue

        plus_di = (smooth_plus_dm[i] / tr_val) * 100
        minus_di = (smooth_minus_dm[i] / tr_val) * 100
        
        sum_di = plus_di + minus_di
        if sum_di == 0:
            dx_list[i] = 0.0
        else:
            dx_list[i] = (abs(plus_di - minus_di) / sum_di) * 100

    # Calculate ADX (Smoothed DX)
    # First ADX is average of DX over period
    # Index for first ADX is period + period - 1 roughly.
    first_adx_idx = 2 * period - 1
    if length > first_adx_idx:
        adx_values[first_adx_idx] = sum(dx_list[period : 2 * period]) / period

        for i in range(first_adx_idx + 1, length):
            adx_values[i] = (
                (adx_values[i - 1] * (period - 1)) + dx_list[i]
            ) / period

    return adx_values
