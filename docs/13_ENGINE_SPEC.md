# Quantsail — Engine Specification v1 (State machine + interfaces)

## 1) Hard guarantees
- Never place live orders unless ARM LIVE is enabled (later milestone)
- Never enter a trade if profitability gate fails
- Never block exits (SL/TP) due to entry pauses/breakers/news/daily lock
- Every decision emits an event (see taxonomy)

## 2) Per-symbol loop (MVP)
For each enabled symbol, repeat:
1) Fetch candles + orderbook snapshot
2) Compute indicators for required timeframes
3) Run strategies → strategy outputs
4) Ensemble decision
5) Apply gates/breakers/daily lock
6) If allowed, create entry plan and exits
7) Dry‑run: simulate fills (deterministic)
8) Persist trade/order/events; update equity snapshot

## 3) State machine
IDLE → EVAL → ENTRY_PENDING → IN_POSITION → EXIT_PENDING → IDLE  
Overlay: PAUSED_ENTRIES (entries blocked; exits allowed)

## 4) Interfaces
### MarketDataProvider
- get_candles(symbol, timeframe, limit) → candles
- get_orderbook(symbol, depth_levels) → bids/asks

### ExchangeAdapter (spot)
- get_balances()
- place_order(symbol, side, type, qty, price?)  (live later)
- cancel_order(order_id)                        (live later)
- get_open_orders(symbol)                       (live later)

### Storage
- save_event(event)
- save_trade(trade)
- save_order(order)
- save_equity_snapshot(snapshot)

## 5) Profitability gate math
expected_net_profit_usd =
  expected_gross_profit_usd
  − fee_est_usd
  − slippage_est_usd
  − spread_cost_est_usd

Reject if expected_net_profit_usd < execution.min_profit_usd
