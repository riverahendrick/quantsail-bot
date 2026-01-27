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
- [x] Postgres schema migrated (Alembic)
- [x] Event taxonomy implemented end‑to‑end
- [x] WS streaming functional (private)

### M2 — Trading logic (dry‑run)
- [x] Strategy outputs + ensemble gating implemented
- [x] Fee+slippage profitability gate implemented
- [ ] Risk sizing + exits implemented
- [x] Circuit breakers implemented (news pause stubbed for later)
- [ ] Daily lock implemented
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

## Prompt 07 - Profitability gate (fees + slippage + spread)
- Role: Risk & Engine Engineer
- [x] Implement fee, slippage, and spread estimators in `gates/estimators.py`
- [x] Update `BotConfig` with maker/taker fee parameters
- [x] Upgrade `ProfitabilityGate` to compute detailed breakdown and return rich result
- [x] Integrate real estimators into `TradingLoop` entry pipeline (before gate check)
- [x] Add `gate.liquidity.rejected` event for insufficient orderbook depth
- [x] Update `gate.profitability.passed` / `rejected` events with full payload
- [x] Add comprehensive tests for estimators and integration scenarios (low liquidity, high fees)
- [x] Update docs/CHANGELOG.md
- [x] Add Review section

### Review
- Implemented `CostEstimator` logic for fees (bps), slippage (orderbook walk), and spread cost.
- Enhanced `ProfitabilityGate` to provide a full pass/fail breakdown including gross/net profit and all costs.
- Integrated estimators into `TradingLoop` to calculate real-time `TradePlan` values before entry.
- Added strict liquidity checks raising `gate.liquidity.rejected` if orderbook depth is insufficient.
- Added comprehensive integration tests covering liquidity failure, profitability rejection, and max position limits.

## Prompt 08 - Circuit Breakers + Negative News Pause (entries only; exits always allowed)
- Role: Safety & Risk Engineer
- [x] Implement BreakerManager with entries_allowed() and exits_allowed() (exits always True)
- [x] Implement volatility spike trigger (ATR multiple threshold)
- [x] Implement spread/slippage spike trigger (spread_bps threshold)
- [x] Implement consecutive losses trigger (losing trade count)
- [x] Implement exchange instability trigger (MVP stub - always False)
- [x] Implement breaker expiry logic with configurable pause_minutes
- [x] Integrate breaker checks into TradingLoop entry pipeline (before opening trades)
- [x] Emit breaker.triggered and breaker.expired events with full context
- [x] Add gate.breaker.rejected event when entry blocked
- [x] Add comprehensive unit tests for all trigger functions
- [x] Add integration tests proving entries blocked when breakers active
- [x] Add safety tests proving exits NEVER blocked by breakers
- [x] Achieve 100% coverage for all breaker modules
- [x] Update docs/CHANGELOG.md
- [x] News pause integration with API ingestion and Redis cache
- [x] Mark checklist complete + add Review section

### Acceptance Checklist
- [x] Each breaker triggers and expires per config
- [x] Entries are blocked during breakers/news pause
- [x] Exits are never blocked (test-proven in test_breaker_exits_safety.py + test_news_pause.py)
- [x] Correct breaker events emitted (breaker.triggered, breaker.expired, gate.breaker.rejected, gate.news.rejected)
- [x] 100% coverage for touched files (breaker + cache modules at 100%)
- [x] todo.md + CHANGELOG updated

### Review
- Implemented BreakerManager that tracks active breakers with automatic expiry on entries_allowed() calls.
- Created four circuit breaker trigger functions: volatility spike (ATR multiple), spread/slippage spike (spread_bps), consecutive losses (trade count), and exchange instability (stub).
- Integrated breaker checks into TradingLoop EVAL state before entry planning; exits always allowed.
- Added 30 comprehensive tests across 4 test files with 100% coverage for all breaker modules.
- Emits breaker.triggered (WARN), breaker.expired (INFO), and gate.breaker.rejected (WARN) events with full context.
- **News Pause**: Implemented full negative news pause integration with POST /v1/news/ingest endpoint (filters negative+high impact only), Redis/in-memory cache, engine integration via BreakerManager.entries_allowed(), and gate.news.rejected event emission. Added 3 API cache tests, 6 API endpoint tests (auth required), 6 engine pause tests, and 3 engine integration tests. Exits never blocked. Enabled via config.breakers.news.enabled (default False).

## Prompt 09 - Daily target lock (STOP/OVERDRIVE) + trailing floor
- Role: Safety & Risk Engineer
- [x] Implement realized PnL today calculation (timezone aware) in EngineRepository
- [x] Update BotConfig with DailyConfig (target_usd, mode, buffer, timezone)
- [x] Implement DailyLockManager with STOP and OVERDRIVE logic
- [x] Implement peak PnL reconstruction from trade history
- [x] Integrate DailyLockManager into TradingLoop entry pipeline
- [x] Emit daily_lock.engaged, daily_lock.floor_updated, daily_lock.entries_paused events
- [x] Add unit tests for DailyLockManager (STOP and OVERDRIVE scenarios)
- [x] Add integration tests for TradingLoop proving entries blocked
- [x] Achieve 100% coverage for all daily lock modules
- [x] Update docs/CHANGELOG.md and mark checklist complete

### Acceptance Checklist
- [x] STOP mode pauses entries after target reached
- [x] OVERDRIVE updates floor and enforces it (scenario test)
- [x] Events emitted correctly
- [x] 100% coverage for touched files
- [x] todo.md + CHANGELOG updated

### Review
- Implemented `DailyLockManager` supporting STOP and OVERDRIVE modes with timezone-aware PnL calculation.
- Added `get_today_realized_pnl` and `get_today_closed_trades` to `EngineRepository`.
- Implemented peak PnL reconstruction to ensure state persists across restarts (calculates peak from historical equity curve of the day).
- Integrated into `TradingLoop` to block entries when target/floor conditions are met, emitting `gate.daily_lock.rejected`.
- Added comprehensive unit and integration tests covering target hit, peak tracking, floor updates, and floor breaches.
- Achieved 100% test coverage for all new components.