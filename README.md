# Quantsail — Crypto Spot Auto-Trading Bot

**Quantsail** is an automated cryptocurrency spot trading system designed for safety, profitability, and transparency. It features a **Private Operator Dashboard** for full control and monitoring, and a **Public Transparency Dashboard** for sharing live performance with investors.

## Key Features

- **Automated Spot Trading** — executes trades on Binance Spot based on configurable strategies
- **Multi-Strategy Engine** — supports EMA crossover, grid trading, and ensemble agreement
- **Circuit Breakers & Risk Controls** — automatic stop-loss triggers, daily P&L limits, and drawdown protection
- **Real-Time Dashboards** — monitor everything live from your browser
- **Public Transparency** — share sanitized, real-time performance data without exposing sensitive details
- **Multi-Language Support** — English and Spanish (EN/ES)

## Architecture

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Dashboard | Next.js (React) | Operator and public web interface |
| API | FastAPI (Python) | REST API, authentication, data streaming |
| Engine | Python | Trading strategies, risk management, order execution |
| Database | PostgreSQL | System of record for trades, events, and configuration |
| Cache | Redis | Rate limiting and real-time data caching |

## Getting Started

👉 **See [SETUP_GUIDE.md](SETUP_GUIDE.md)** for complete step-by-step installation and setup instructions.

## Dashboard URLs (After Setup)

| Dashboard | URL | Description |
|-----------|-----|-------------|
| **Admin Panel** | http://localhost:3000/app/overview | Full operator control panel |
| **Public Dashboard** | http://localhost:3000/public/overview | Investor-facing transparency view |
| **API Documentation** | http://localhost:8000/docs | Interactive API reference |

## License

Proprietary. All rights reserved.
