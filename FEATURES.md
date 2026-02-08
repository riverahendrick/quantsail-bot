# FEATURES - Quantsail Feature Registry

_Last updated: 2026-02-07_

## User Features
- [x] Dashboard i18n (EN/ES) with locale switch
- [x] Public overview page at /public/overview
- [x] Public trades and transparency pages

## Admin Features
- [x] Operator dashboard (private)
- [x] Admin RBAC and configuration controls
- [x] User management (owner-only)

## Developer Features
- [x] Lint/typecheck/test guardrails (dashboard + services)
- [x] Database migrations via Alembic

## Backend Features
- [x] API health endpoint (/v1/health)
- [x] Private API auth (Firebase JWT) + RBAC enforcement
- [x] Public API endpoints with sanitization + rate limiting
- [x] Private WS event stream with cursor resume + redaction
- [x] Engine placeholder entrypoint
- [x] Postgres schema + migrations applied
- [x] API DB health check (/v1/health/db)

## Engine — Strategies & Signals
- [x] Trend strategy (EMA crossover + ADX filter)
- [x] Mean Reversion strategy (Bollinger Bands + RSI)
- [x] Breakout strategy (Donchian Channels + ATR filter)
- [x] VWAP Mean Reversion strategy (deviation + volume + OBV confirmation)
- [x] Ensemble combiner (configurable agreement + confidence thresholds)

## Engine — Indicators
- [x] EMA, SMA, RSI, Bollinger Bands, ATR, Donchian Channels, ADX
- [x] VWAP (Volume Weighted Average Price)
- [x] MACD (Moving Average Convergence Divergence)
- [x] OBV (On-Balance Volume)

## Engine — Risk Management
- [x] Dynamic position sizing (ATR-based with risk-per-trade limits)
- [x] Configurable stop-loss (ATR-multiplier based)
- [x] Configurable take-profit (reward-to-risk ratio based)
- [x] Trailing stop-loss (ATR-based with activation threshold)
- [x] Profitability gate (fee + slippage + spread estimation)
- [x] Circuit breakers (volatility, spread, consecutive losses, exchange)
- [x] Daily target lock (STOP + OVERDRIVE modes)
- [x] News pause integration

## Engine — Execution
- [x] Dry-run executor (paper trading)
- [x] Live executor (Binance via ccxt)
- [x] State machine (IDLE→EVAL→ENTRY→IN_POSITION→EXIT)

