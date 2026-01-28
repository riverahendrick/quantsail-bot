# Quantsail — Feature Registry (Source of Truth)

## MVP — Crypto Spot (Binance)
### Core trading
- [x] Binance key management (encrypted)
- [ ] Symbol selection (enabled symbols + cadence)
- [x] Dry‑run default
- [x] Strategy outputs + ensemble decision (trend/mean‑reversion/breakout)
- [x] Fee + slippage profitability gate
- [ ] Risk sizing + mandatory SL/TP
- [x] Circuit breakers (pause entries only)
- [x] Daily target lock (STOP/OVERDRIVE + trailing floor)
- [x] Negative news shock pause (high impact only)

### Data + transparency
- [x] Event taxonomy implemented everywhere
- [x] Trades/orders/equity snapshots persisted
- [x] WS streaming to dashboards (private WS with cursor resume)

### Security
- [x] AES‑GCM encrypted keys
- [x] RBAC for private endpoints
- [x] Public endpoints sanitized + rate limited

### UI
- [x] Private operator dashboard
- [x] Public transparency dashboard
- [x] User management console (owner‑only)
- [x] i18n EN/ES + tests preventing hardcoded strings

## Future (documented only)
- [ ] Coinbase adapter
- [ ] Forex
- [ ] Stocks

_Last updated: 2026-01-28_
