# Quantsail — External Services (MVP vs Future)

## MVP (crypto spot)
### Market/execution data
- Binance API (market data + account/trading endpoints)
- Optional: CCXT (adapter abstraction) — only if it does not reduce control or testability

### News (negative shock pause only)
- CryptoPanic (high-impact negative news detection)

### Auth
- Firebase Authentication (JWT verification in API)

### Hosting
- VPS (engine+API+DB)
- Vercel (dashboard only)

## Future (documented, not required for MVP)
- Coinbase Exchange API (spot)
- Forex data/execution via broker API (e.g., OANDA/Interactive Brokers depending on jurisdiction)
- Stocks via broker API
- Alpha Vantage (useful for equities/forex historical data in backtests; not required for Binance-only crypto MVP)
