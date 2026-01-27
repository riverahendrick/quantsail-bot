# Quantsail — Observability v1

## Metrics
Engine:
- pnl_realized_today_usd, drawdown_pct, gate_rejected_total, breaker_triggered_total,
  trades_opened_total, trades_closed_total, exchange_disconnects_total, order_failures_total

API:
- http_requests_total, auth_failures_total, rate_limited_total, ws_connections_active, db_latency_ms

## Alerts (recommended)
- Engine stopped unexpectedly
- DB unavailable
- Disconnect storm
- Order failure storm
- Breaker stuck active too long
