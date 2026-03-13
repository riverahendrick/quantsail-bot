# Quantsail — Feature Registry (Source of Truth)

## MVP — Crypto Spot (Binance)
### Core trading
- [x] Binance key management (encrypted)
- [ ] Symbol selection (enabled symbols + cadence)
- [x] Dry‑run default
- [x] Strategy outputs + ensemble decision (trend/mean‑reversion/breakout)
- [x] Fee + slippage profitability gate
- [x] Risk sizing + mandatory SL/TP (ATR-based dynamic sizing, trailing stop)
- [x] Circuit breakers (pause entries only)
- [x] Daily target lock (STOP/OVERDRIVE + trailing floor)
- [x] Negative news shock pause (high impact only)
- [x] Execution retry (3 attempts w/ exponential backoff)
- [x] Partial fill handling (accept valid partials, reject zero-fills)
- [x] Tick interval control + control plane integration
- [x] Open trade reconciliation on startup

### Data + transparency
- [x] Event taxonomy implemented everywhere
- [x] Trades/orders/equity snapshots persisted
- [x] WS streaming to dashboards (private WS with cursor resume)
- [x] Cursor-based resume on reconnect (no missed events)

### Security
- [x] AES‑GCM encrypted keys
- [x] RBAC for private endpoints
- [x] Public endpoints sanitized + rate limited
- [x] Redis-backed ControlPlane (stop/pause/resume)

### UI
- [x] Private operator dashboard
- [x] Public transparency dashboard
- [x] User management console (owner‑only)
- [x] Bot control (stop / pause entries / resume)
- [x] i18n EN/ES + tests preventing hardcoded strings

### Infrastructure
- [x] Engine + API Dockerfiles (uv-based, health checks)
- [x] Docker Compose (Postgres, Redis, API, Engine, Nginx, Certbot)
- [x] Nginx reverse proxy (SSL, WS upgrade, rate limiting)
- [x] GitHub Actions CI (lint → typecheck → test → build)
- [x] PostgreSQL backup script (pg_dump + 7-day rotation)

## Future (documented only)
- [ ] Coinbase adapter
- [ ] Forex
- [ ] Stocks
- [ ] Symbol selection config

_Last updated: 2026-03-12_
