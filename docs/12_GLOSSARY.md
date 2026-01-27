# Quantsail — Glossary (Plain English)

This glossary explains key trading and engineering terms used in the docs.

## Trading terms

### Spot trading
Buying and selling the actual asset (e.g., BTC) with no leverage. MVP scope.

### Symbol / Pair
A tradable market like BTC/USDT.

### Candle / Candlestick
Price summary for a timeframe (open/high/low/close + volume).

### Timeframe
Candle window size (1m, 5m, 15m, 1h, 4h).

### Entry / Exit
Entry opens a position; exit closes it.

### Take profit (TP)
Price where bot sells to lock profit.

### Stop loss (SL)
Price where bot sells to limit loss.

### Slippage
Difference between expected price and actual fill price.
Worse when liquidity is low or volatility is high.

### Spread
Difference between best bid and best ask.

### Fees (maker/taker)
Exchange charges trading fees; must be included in profitability.

### Realized vs Unrealized PnL
Realized: closed trades. Unrealized: open positions.

### Drawdown
Drop from a recent equity peak.

### Win rate
Percent of trades that win. Not sufficient alone.

### Profit factor
Total profits / total losses. >1 is good.

### Circuit breaker
Safety pause when market/exchange conditions are dangerous.

### Daily target lock / Floor
Protect profits after reaching daily target (STOP or OVERDRIVE).

## Engineering terms

### API
Backend endpoints the dashboard calls.

### RBAC
Role-based permissions.

### Idempotency
Safe retries without duplicated actions.

### Reconciliation
Sync internal state with exchange on restart.

### E2E test
Runs the system like a user to verify full flow.
