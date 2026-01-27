# Quantsail — Architecture v6

## 1) Component diagram (logical)
- Engine (Python): strategy → gating → execution → persistence
- API (FastAPI): auth/RBAC, key mgmt, config versioning, public/private endpoints, WS streaming
- Postgres: system-of-record for trades/orders/events/config
- Redis: ephemeral caches (rate limits, breaker cache, news cache)
- Dashboard (Next.js): private + public UI, calls API/WS

## 2) Exchange-agnostic design
Define a strict `ExchangeAdapter` interface and implement `BinanceSpotAdapter`.
Future: CoinbaseSpotAdapter, ForexBrokerAdapter, StockBrokerAdapter.

## 3) Data ownership
- Engine writes trades/orders/events/snapshots to Postgres.
- API reads from Postgres and streams to clients.
- Public endpoints use strict serializers to prevent leakage.

## 4) Deployment
- VPS runs engine + API + Postgres + Redis (docker-compose)
- Vercel runs dashboard only; it never sees secrets.
