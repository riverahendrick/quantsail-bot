# Quantsail — Validation & Go-Live Gates v7

## 0) Rules
Follow all validation and go-live requirements documented in this file.

## 1) Backtesting
- multi-regime testing
- net PnL after fees
- drawdown + stability metrics

## 2) Walk-forward
- rolling windows
- reject in-sample-only strategies

## 3) Paper trading
- 2–4 weeks dry-run with real data
- calibrate slippage estimates

## 4) Live rollout
- smallest size first
- few symbols
- expand slowly only after stable results

## 5) Technical Gates (Prompt 12)
- [x] **ARM LIVE Gate**: Two-step authentication required for live mode start.
- [x] **Idempotency**: Client-side order IDs (`QS-{trade_id}-{seq}`) prevent duplicate fills on network retries.
- [x] **Reconciliation**: Engine performs exchange vs DB state sync on every restart to detect orphaned orders.
- [x] **Sanitization**: All execution details (exchange order IDs, exact sizes) sanitized for public views.
