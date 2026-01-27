# Quantsail — Feature Registry (Source of Truth)

## MVP — Crypto Spot (Binance)
### Core trading
- [ ] Binance key management (encrypted)
- [ ] Symbol selection (enabled symbols + cadence)
- [ ] Dry‑run default
- [ ] Strategy outputs + ensemble decision (trend/mean‑reversion/breakout)
- [ ] Fee + slippage profitability gate
- [ ] Risk sizing + mandatory SL/TP
- [ ] Circuit breakers (pause entries only)
- [ ] Daily target lock (STOP/OVERDRIVE + trailing floor)
- [ ] Negative news shock pause (high impact only)

### Data + transparency
- [ ] Event taxonomy implemented everywhere
- [ ] Trades/orders/equity snapshots persisted
- [ ] WS streaming to dashboards

### Security
- [ ] AES‑GCM encrypted keys
- [ ] RBAC for private endpoints
- [ ] Public endpoints sanitized + rate limited

### UI
- [ ] Private operator dashboard
- [ ] Public transparency dashboard
- [ ] i18n EN/ES + tests preventing hardcoded strings

## Future (documented only)
- [ ] Coinbase adapter
- [ ] Forex
- [ ] Stocks

_Last updated: 2026-01-26_