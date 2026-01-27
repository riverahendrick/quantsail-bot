# Quantsail — Feature Registry (Source of Truth)

## MVP — Crypto Spot (Binance)
### Core trading
- [ ] Binance key management (encrypted)
- [ ] Symbol selection (enabled symbols + cadence)
- [x] Dry‑run default
- [ ] Strategy outputs + ensemble decision (trend/mean‑reversion/breakout)
- [x] Fee + slippage profitability gate
- [ ] Risk sizing + mandatory SL/TP
- [ ] Circuit breakers (pause entries only)
- [ ] Daily target lock (STOP/OVERDRIVE + trailing floor)
- [ ] Negative news shock pause (high impact only)

### Data + transparency
- [x] Event taxonomy implemented everywhere
- [x] Trades/orders/equity snapshots persisted
- [x] WS streaming to dashboards (private WS with cursor resume)

### Security
- [ ] AES‑GCM encrypted keys
- [x] RBAC for private endpoints
- [x] Public endpoints sanitized + rate limited

### UI
- [ ] Private operator dashboard
- [ ] Public transparency dashboard
- [x] i18n EN/ES + tests preventing hardcoded strings

## Future (documented only)
- [ ] Coinbase adapter
- [ ] Forex
- [ ] Stocks

_Last updated: 2026-01-27_