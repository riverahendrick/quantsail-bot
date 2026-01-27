# Quantsail — Master Checklist

> Every prompt must add a section here and check it off when complete.

## Project milestones
### M0 — Repo bootstrapped
- [x] Next.js dashboard scaffolded in `apps/dashboard` (no nested root)
- [x] FastAPI scaffolded in `services/api`
- [x] Engine scaffolded in `services/engine`
- [x] Postgres + Redis via `infra/docker/docker-compose.yml`
- [x] Baseline lint/typecheck/test commands working

### M1 — Data + audit trail
- [ ] Postgres schema migrated (Alembic)
- [ ] Event taxonomy implemented end‑to‑end
- [x] WS streaming functional (private)

### M2 — Trading logic (dry‑run)
- [x] Strategy outputs + ensemble gating implemented
- [x] Fee+slippage profitability gate implemented
- [ ] Risk sizing + exits implemented
- [ ] Circuit breakers + daily lock implemented
- [x] Dry‑run trades and equity snapshots persisted

### M3 — Dashboards
- [ ] Private operator dashboard functional
- [ ] Public transparency dashboard functional and sanitized
- [ ] E2E tests for critical pages

### M4 — Live (later)
- [ ] ARM LIVE flow implemented
- [ ] Binance spot live execution (idempotent) + reconciliation

## Prompt 00 — Setup (scaffold generators; NO hand-creating boilerplate)
- Role: Setup & Scaffold Engineer
- [x] Verify repo root (no nested folder) and review setup-related docs
- [x] Scaffold Next.js dashboard in `apps/dashboard` via official generator (pnpm, TS, ESLint, App Router)
- [x] Initialize `services/api` with uv + FastAPI `/v1/health` and a unit test
- [x] Initialize `services/engine` with uv package, entrypoint, and unit test
- [x] Create `infra/docker/docker-compose.yml` for Postgres + Redis with volumes
- [x] Add `infra/scripts` start/stop/test helpers
- [x] Smoke-test: infra up, API health, dashboard dev, engine import
- [x] Update README commands section
- [x] Update `docs/CHANGELOG.md`
- [x] Mark checklist complete + add Review section

### Review
- Scaffolded Next.js dashboard with pnpm and added a typecheck script.
- Initialized FastAPI and engine uv projects with minimal entrypoints and tests (100% coverage).
- Added Docker Compose for Postgres/Redis plus infra helper scripts, and documented commands in README.

## Prompt 01 — Guardrails: lint/typecheck/tests + i18n EN/ES enforcement
- Role: Quality Guardrails Engineer
- [x] Research official docs for Next.js i18n, next-intl (or built-in), and Playwright setup
- [x] Add dashboard i18n wiring (EN/ES) + locale switcher and `/public/overview`
- [x] Add automated guard against hardcoded UI strings
- [x] Add Playwright baseline E2E for `/public/overview`
- [x] Add ruff + mypy + pytest coverage config in API and Engine
- [x] Run required commands and capture outputs
- [x] Update `docs/CHANGELOG.md` and mark checklist complete
- [x] Add Review section

### Review
- Added next-intl with EN/ES messages, server action locale switch, and `/public/overview`.
- Added i18n guard script wired into lint and a Playwright E2E baseline.
- Added ruff/mypy/pytest coverage config for API and Engine; all checks green at 100% coverage.

## Hydration warning fix — suppress external attribute mismatch
- Role: Frontend Reliability Engineer
- [x] Add hydration mismatch suppression on root layout
- [x] Run dashboard lint/typecheck
- [x] Update `docs/CHANGELOG.md`
- [x] Add Review section

### Review
- Added hydration suppression flags on the root layout to avoid external attribute mismatches.

## Prompt 02 - Postgres schema + Alembic migrations + schema verification tests
- Role: Database Migration Engineer
- [x] Review `docs/04_DB_SCHEMA.md` + PRD persistence notes for exact schema requirements
- [x] Research official docs for SQLAlchemy 2.x, Alembic, and Postgres information_schema/pg_indexes queries
- [x] Add SQLAlchemy models and Alembic config for required tables
- [x] Create initial Alembic migration and apply on fresh DB
- [x] Add schema verification integration test (tables/columns/indexes)
- [x] Add DB connection smoke check endpoint or internal check
- [x] Run required commands and capture outputs
- [x] Update `docs/CHANGELOG.md` (and `docs/04_DB_SCHEMA.md` if clarified)
- [x] Add Review section

### Review
- Added SQLAlchemy models and Alembic migrations for the documented schema, plus DB connectivity checks.
- Added schema verification tests for tables/columns/indexes/constraints and Alembic offline coverage tests.

## Prompt 03 - API auth/RBAC + strict public sanitization router
- Role: Security and API Engineer
- [x] Review docs/03_API_SPEC.md and PRD transparency/security requirements
- [x] Research official docs for Firebase JWT verification, FastAPI auth dependencies, and Redis rate limiting
- [x] Update docs/03_API_SPEC.md with auth mapping, RBAC matrix, error schema, public shapes, and rate limits
- [x] Add TDD tests for auth/RBAC, sanitization, and rate limiting
- [x] Implement Firebase JWT verification and role mapping
- [x] Implement RBAC dependency and private endpoints
- [x] Implement public router with strict sanitization
- [x] Implement public rate limiting (Redis preferred, in-memory fallback)
- [x] Run required commands and capture outputs
- [x] Update docs/CHANGELOG.md and docs/10_FEATURES.md (if scope changes)
- [x] Add Review section

### Review
- Added Firebase JWT auth with RBAC enforcement and test coverage for auth edge cases.
- Implemented public sanitized endpoints with Redis/in-memory rate limiting and safety tests.
- Updated docs and developer commands for auth and rate limit configuration.

## Prompt 04 - Event journal + WebSocket streaming (resume cursor)
- Role: Event Streaming Engineer
- [x] Review docs/03_API_SPEC.md, docs/04_DB_SCHEMA.md, and docs/14_EVENT_TAXONOMY.md
- [x] Research official docs for FastAPI WebSockets and TestClient WS usage
- [x] Define cursor format and document in API spec
- [x] Add event repository functions (append + query)
- [x] Implement private WS endpoint with cursor resume + heartbeat
- [x] Add integration tests for WS streaming and resume
- [x] Run required commands and capture outputs
- [x] Update docs/CHANGELOG.md and docs/10_FEATURES.md (if scope changes)
- [x] Add Review section
### Review
- Added WS auth, cursor resume, heartbeat, and payload redaction coverage.
- Expanded WS tests for invalid cursor, RBAC rejection, auth failures, tail streaming, and idle heartbeats.

## Prompt 05 - Engine dry-run core loop + persistence (no strategies yet)
- Role: Engine Loop & Persistence Engineer
- [x] Review docs/13_ENGINE_SPEC.md + docs/14_EVENT_TAXONOMY.md
- [x] Research official docs for SQLAlchemy Core and psycopg connection patterns
- [x] Add deterministic engine loop + stub signal provider (HOLD → ENTER_LONG once)
- [x] Persist trade/orders/events/equity snapshot for dry-run entry
- [x] Add unit tests for loop transitions + persistence
- [x] Add integration test: run one tick, assert DB rows, verify WS stream includes events
- [x] Run required commands and capture outputs
- [x] Update docs/CHANGELOG.md and docs/10_FEATURES.md (if scope changes)
- [x] Add Review section

### Review
- Implemented complete trading engine state machine with 5 states (IDLE, EVAL, ENTRY_PENDING, IN_POSITION, EXIT_PENDING)
- Added Pydantic configuration models with JSON file + environment variable support
- Implemented stub market data and signal providers for deterministic testing
- Added profitability gate with PnL calculation (gross profit - fees - slippage - spread)
- Implemented DryRunExecutor with entry simulation (creates Trade + 3 Orders) and exit checking (SL/TP hit detection)
- Created EngineRepository wrapping SQLAlchemy operations with equity calculation and snapshot persistence
- Built TradingLoop orchestrator coordinating all components with per-symbol state machines
- Added stub database models for independent testing (ready for API service integration later)
- Updated main.py entry point with config loading, database session, and component wiring
- Created 145 unit and integration tests across 17 test files with 98% coverage
- Emits events: system.started/stopped, market.tick, signal.generated, trade.opened/closed, order.placed/filled, gate.profitability.passed/rejected
- Engine runs deterministically with full audit trail and graceful shutdown (SIGINT/SIGTERM handlers)

## CLI Task: Configurable Max Ticks
- Role: Engine Engineer
- [x] Make max_ticks configurable via environment variable in `services/engine/quantsail_engine/main.py`
- [x] Update tests to verify configuration

## Prompt 06 - Strategies (trend/mean‑reversion/breakout) + ensemble agreement gating
- Role: Strategy & Quant Engineer
- [x] Implement indicator utilities (pure functions, no numpy/pandas)
- [x] Implement strategies (Trend, Mean Reversion, Breakout) with StrategyOutput schema
- [x] Implement EnsembleCombiner with min_agreement and confidence threshold logic
- [x] Update BotConfig to include strategy parameters
- [x] Integrate EnsembleSignalProvider into the engine loop (main.py)
- [x] Ensure events (signal.generated, ensemble.decision) are emitted correctly
- [x] Add comprehensive unit and integration tests (100% coverage)
- [x] Update docs/CHANGELOG.md and docs/10_FEATURES.md
- [x] Add Review section

### Review
- Implemented pure Python indicators: EMA, RSI, Bollinger Bands, ATR, ADX, Donchian Channels with full test coverage.
- Implemented 3 deterministic strategies (Trend, Mean Reversion, Breakout) returning structured StrategyOutput with rationale.
- Built EnsembleCombiner that aggregates votes and confidence, enforcing min_agreement thresholds.
- Updated BotConfig to support per-strategy configuration and ensemble settings.
- Integrated EnsembleSignalProvider into the main engine loop, emitting detailed per-strategy `signal.generated` and aggregate `ensemble.decision` events.
- Achieved 100% test coverage across all new indicators, strategies, and integration logic.
