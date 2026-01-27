# Quantsail — System Overview (Non-Technical)

## What we are building
Quantsail is an automated **crypto spot** trading system with two dashboards:

1) **Private Operator Dashboard**
   - Start/stop bot
   - Configure strategies and risk
   - Monitor trades, positions, events, and profit/loss

2) **Public Transparency Dashboard**
   - Shows performance and what the bot is doing in a safe, sanitized way
   - Never shows API keys, secrets, or identity-linked details

The system runs on:
- **VPS (server):** trading engine + backend API + database (Postgres + Redis)
- **Vercel:** dashboard UI only (no secrets)

## The decision pipeline (simple)
For each enabled symbol (example BTC/USDT), the bot:
1) Reads market data (candles + order book)
2) Computes indicators across multiple timeframes
3) Runs multiple strategies and checks if enough agree
4) Applies safety filters (risk limits, circuit breakers, fee/slippage profitability)
5) If allowed, opens a position and sets exits (TP + SL)
6) Records everything (trades + events) and streams updates to dashboards

## Why “fee + slippage aware” matters
A trade may appear profitable but becomes unprofitable after:
- exchange fees (maker/taker)
- slippage (fill price worse than expected)
- spread (difference between best bid/ask)

Quantsail estimates costs before entry and rejects trades with insufficient net edge.

## Reality check
No system can guarantee profitable days. This project is designed to:
- avoid low-quality trades,
- stop trading in dangerous conditions,
- lock gains when daily target is achieved,
- produce a full audit trail of actions and reasons.

## Future readiness
We will architect for later add-ons:
- Coinbase spot adapter
- Forex adapter (broker API)
- Stocks adapter (broker API)

MVP is Binance crypto spot.


## Auditability
All important actions are persisted as append-only events. Public pages show only sanitized events.
