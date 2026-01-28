# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Quantsail is an automated crypto spot trading system with private operator and public transparency dashboards. The system is designed to be built by AI agents without guesswork, with complete specifications in `docs/`.

**Critical: Read `GLOBAL_RULES.md` first and comply with all rules before any coding work.**

### Architecture

Three-tier system:
- **Engine** (Python): Trading logic, strategy execution, market data processing
- **API** (FastAPI): Authentication/RBAC, config management, public/private endpoints, WebSocket streaming
- **Dashboard** (Next.js): Private operator UI + public transparency pages

Data layer:
- **Postgres**: System of record (trades, orders, events, config)
- **Redis**: Ephemeral caches (rate limits, circuit breaker state, news cache)

Deployment model:
- **VPS**: Engine + API + Postgres + Redis (docker-compose)
- **Vercel**: Dashboard only (NEVER include secrets here)

## Reading Order for New Work

1. `docs/00_SYSTEM_OVERVIEW.md` - High-level system design
2. `docs/01_PRD.md` - Product requirements
3. `docs/02_ARCHITECTURE.md` - Technical architecture
4. `docs/09_CONFIG_SPEC.md` - Configuration structure
5. `docs/13_ENGINE_SPEC.md` - Engine state machine and interfaces
6. `docs/03_API_SPEC.md` - API endpoints and auth
7. `docs/04_DB_SCHEMA.md` - Database schema (authoritative)
8. `docs/05_UI_SPEC.md` - UI requirements
9. `docs/08_PROMPTS/` - Implementation prompts (execute in order)

## Development Commands

### Infrastructure
```bash
cd infra/docker && docker compose up -d     # Start Postgres + Redis
cd infra/docker && docker compose down      # Stop services
```

Database connections:
- Postgres: `localhost:5433` (container port 5432)
- Redis: `localhost:6380` (container port 6379)

### Dashboard (Next.js)
```bash
cd apps/dashboard && pnpm install
cd apps/dashboard && pnpm dev              # http://localhost:3000
cd apps/dashboard && pnpm lint             # ESLint + i18n check
cd apps/dashboard && pnpm typecheck        # TypeScript validation
cd apps/dashboard && pnpm e2e              # Playwright E2E tests
```

### API (FastAPI)
```bash
# Required environment variables:
# DATABASE_URL=postgresql+psycopg://quantsail:postgres@localhost:5433/quantsail
# GOOGLE_APPLICATION_CREDENTIALS=/path/to/firebase-service-account.json
# Optional: REDIS_URL=redis://localhost:6380/0

cd services/api && uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
cd services/api && uv run alembic upgrade head     # Run migrations
cd services/api && uv run pytest -q --cov          # Tests with 100% coverage requirement
cd services/api && uv run ruff check .             # Linting
cd services/api && uv run mypy .                   # Type checking
```

Health checks:
- API: `http://127.0.0.1:8000/v1/health`
- DB: `http://127.0.0.1:8000/v1/health/db`

### Engine
```bash
cd services/engine && uv run python -m quantsail_engine.main
cd services/engine && uv run pytest -q --cov       # Tests with 100% coverage
cd services/engine && uv run ruff check .          # Linting
cd services/engine && uv run mypy .                # Type checking
```

## Critical Development Rules

### Non-Negotiables
- **TDD everywhere**: 100% coverage for touched files; E2E for critical flows
- **No nested root folder**: Keep flat structure
- **i18n from day one**: English/Spanish only; no hardcoded UI strings
- **No mock data**: Always use real configuration, migrations, I/O
- **No "as any"** in TypeScript unless documented
- **Zero errors policy**: Zero ESLint/TypeScript/linter/test failures allowed

### Testing Requirements
- Write tests FIRST (TDD)
- Required coverage: 1 expected case + 1 edge case + 1 failure case minimum
- pytest enforces 100% coverage: `addopts = "-q --cov --cov-report=term-missing --cov-fail-under=100"`
- Keep tests in `tests/` folder mirroring app structure

### Security & Privacy
- **Public API sanitization**: NEVER expose in public endpoints:
  - `exchange_order_id`, `idempotency_key`
  - `ciphertext`, `nonce`
  - API keys or secrets
  - Internal IDs (use only when required)
- **Public events**: Only include `events` where `public_safe=true`
- **Dashboard on Vercel**: Must not contain ANY secrets
- **Firebase auth**: Private routes use `Authorization: Bearer <firebase_id_token>`

## Key Architectural Patterns

### Exchange-Agnostic Design
The engine uses an `ExchangeAdapter` interface for all market interactions:
```python
class ExchangeAdapter:
    def get_candles(symbol, timeframe, limit) -> candles
    def get_orderbook(symbol, depth_levels) -> bids/asks
    def place_order(symbol, side, type, qty, price?)  # Live later
```

Current: `BinanceSpotAdapter`. Future: Coinbase, Forex, Stocks adapters.

### Engine State Machine
```
IDLE → EVAL → ENTRY_PENDING → IN_POSITION → EXIT_PENDING → IDLE
```

Overlay state: `PAUSED_ENTRIES` (entries blocked; exits always allowed)

Per-symbol decision loop:
1. Fetch market data (candles + orderbook)
2. Compute indicators across timeframes
3. Run strategies → ensemble decision
4. Apply gates (profitability, circuit breakers, daily lock, news filter)
5. If allowed, create entry plan with exits (TP + SL)
6. Dry-run: simulate fills deterministically
7. Persist trade/order/events; update equity snapshot

### Profitability Gate
```
expected_net_profit_usd =
  expected_gross_profit_usd
  - fee_est_usd
  - slippage_est_usd
  - spread_cost_est_usd

Reject if expected_net_profit_usd < config.execution.min_profit_usd
```

### API Endpoint Structure
- **Private**: `/v1/*` (Firebase JWT + RBAC required)
- **Public**: `/public/v1/*` (rate-limited, sanitized responses)
- **WebSocket**: `/ws` (private), `/public/ws` (optional)

RBAC roles: `OWNER`, `CEO`, `DEVELOPER`, `ADMIN`

### Database Migration Strategy
Use Alembic for all schema changes:
```bash
cd services/api
uv run alembic revision -m "description"
uv run alembic upgrade head
```

Schema is authoritative in `docs/04_DB_SCHEMA.md` - update docs FIRST, then code.

### Event-Driven Audit Trail
All decisions are persisted as append-only events in the `events` table:
- `level`: INFO/WARN/ERROR
- `type`: See `docs/14_EVENT_TAXONOMY.md`
- `public_safe`: Boolean flag for public dashboard visibility
- `payload`: JSONB with event details

## Internationalization (i18n)

Dashboard uses `next-intl` with English/Spanish:
- Locale files: `apps/dashboard/messages/{en,es}.json`
- Check script: `pnpm i18n:check` (runs during lint)
- NEVER hardcode UI strings; always use `useTranslations()`

## Common Gotchas

### Configuration Management
Config is versioned in `bot_config_versions` table:
1. Create version: `POST /v1/config/versions`
2. Activate version: `POST /v1/config/activate/{version}`
3. Only one `is_active=true` row allowed (enforced by partial unique index)

### Dry-Run vs Live
MVP is dry-run only. All trades have `mode: "DRY_RUN"`.
- Orders have `status: "SIMULATED"`
- Never place real exchange orders until "ARM LIVE" milestone
- Engine still records full trade lifecycle for testing

### Exit Priority
Circuit breakers, news filters, and daily locks NEVER block exits (SL/TP).
Only entry signals are gated; risk management exits are always allowed.

## File References Format

When discussing code, use `file_path:line_number` format:
```
Entry logic is in services/engine/quantsail_engine/core.py:145
```

## Documentation Updates

When modifying features or behavior:
1. Update `docs/CHANGELOG.md` with what changed and why
2. Update `docs/10_FEATURES.md` with feature status checkboxes
3. Update relevant spec docs if interfaces change
4. Keep `todo.md` current with task progress

## Python/TypeScript Style

### Python (ruff + mypy)
- Line length: 100
- Target: Python 3.12
- Strict mypy mode enabled
- Use guard clauses and early returns

### TypeScript (ESLint + strict mode)
- React components: 200-250 lines ideal, 500 lines maximum
- Use TypeScript strict mode
- No `any` without documentation
- Use descriptive domain-specific names

## Tools & Versions

- Python: 3.12+ (managed by `uv`)
- Node: Specified in `.node-version` or `package.json` engines
- Postgres: 16
- Redis: 7
- Next.js: 16.1.5
- FastAPI: 0.128+

## Emergency Debugging

If you encounter "code diverges from docs":
1. **Docs are authoritative** - update docs first
2. Read the relevant spec in `docs/`
3. Fix code to match spec
4. Update `docs/CHANGELOG.md`
5. Run full test suite before committing
