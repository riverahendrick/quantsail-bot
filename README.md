# Quantsail — Crypto Spot Auto-Trading Bot

**Quantsail** is an automated cryptocurrency spot trading system designed for safety, profitability, and transparency. It features a **Private Operator Dashboard** for full control and monitoring, and a **Public Transparency Dashboard** for sharing live performance with investors.

## Key Features

- **Automated Spot Trading** — executes trades on Binance Spot based on configurable strategies
- **Multi-Strategy Engine** — supports EMA crossover, grid trading, and ensemble agreement
- **Circuit Breakers & Risk Controls** — automatic stop-loss triggers, daily P&L limits, and drawdown protection
- **Real-Time Dashboards** — monitor everything live from your browser
- **Public Transparency** — share sanitized, real-time performance data without exposing sensitive details
- **Multi-Language Support** — English and Spanish (EN/ES)
- **Execution Hardening** — retry with exponential backoff, partial fill handling
- **Production Infrastructure** — Dockerized deployment with SSL, CI/CD, and automated backups

## Architecture

| Component | Technology | Purpose |
|-----------|-----------|---------| 
| Dashboard | Next.js (React) | Operator and public web interface (Vercel) |
| API | FastAPI (Python) | REST API, authentication, data streaming (VPS) |
| Engine | Python | Trading strategies, risk management, order execution (VPS) |
| Database | PostgreSQL | System of record for trades, events, and configuration |
| Cache | Redis | Rate limiting, real-time data caching, control plane |
| Proxy | Nginx | SSL termination, WebSocket upgrade, rate limiting |
| CI | GitHub Actions | Lint → typecheck → test → build |

## Getting Started

### Local Development
👉 **See [SETUP_GUIDE.md](SETUP_GUIDE.md)** for complete step-by-step installation and setup instructions.

### VPS Production Deployment
👉 **See [docs/VPS_DEPLOYMENT_GUIDE.md](docs/VPS_DEPLOYMENT_GUIDE.md)** for deploying to a VPS with Docker, SSL, and automated backups.

## Dashboard URLs (After Setup)

| Dashboard | URL | Description |
|-----------|-----|-------------|
| **Admin Panel** | http://localhost:3000/app/overview | Full operator control panel |
| **Public Dashboard** | http://localhost:3000/public/overview | Investor-facing transparency view |
| **API Documentation** | http://localhost:8000/docs | Interactive API reference |

## Development Commands

| Service | Command | Description |
|---------|---------|-------------|
| Dashboard | `pnpm -C apps/dashboard dev` | Start dashboard locally |
| Dashboard | `pnpm -C apps/dashboard lint` | Run dashboard linting |
| Dashboard | `pnpm -C apps/dashboard exec tsc --noEmit` | TypeScript check |
| API | `uv -C services/api run ruff check .` | Lint API |
| API | `uv -C services/api run mypy .` | Type-check API |
| API | `uv -C services/api run pytest -q --cov` | Run API tests |
| Engine | `uv -C services/engine run ruff check .` | Lint engine |
| Engine | `uv -C services/engine run mypy .` | Type-check engine |
| Engine | `uv -C services/engine run pytest -q --cov` | Run engine tests |
| Infra | `docker compose -f infra/docker/docker-compose.yml up -d` | Start all services |

## License

Proprietary. All rights reserved.
