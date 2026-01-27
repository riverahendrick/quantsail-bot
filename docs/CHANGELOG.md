# Changelog — Quantsail

## Unreleased
- 2026-01-27: **Strategies & Ensemble**: Implemented Trend (EMA/ADX), Mean Reversion (Bollinger/RSI), and Breakout (Donchian/ATR) strategies. Added pure-Python technical indicators and an EnsembleCombiner that aggregates strategy votes with configurable confidence thresholds. Updated engine loop to emit detailed `signal.generated` and `ensemble.decision` events.
- 2026-01-27: **Engine Dry-Run Core Loop**: Implemented complete trading engine with state machine (IDLE→EVAL→ENTRY_PENDING→IN_POSITION→EXIT_PENDING), deterministic dry-run execution, profitability gate, per-symbol orchestration, equity tracking, and full event emission. Added stub database models for testing, 145 tests passing with 98% coverage. Entry point ready for signal integration.
- 2026-01-27: Added event streaming support with an append-only events repository, WS cursor resume, heartbeat messages, and payload redaction.
- 2026-01-27: Expanded WS coverage for auth/cursor/heartbeat paths and ensured event tests respect trade foreign keys.
- 2026-01-27: Added Firebase JWT auth + RBAC enforcement for private API routes, plus sanitized public endpoints with rate limiting and full test coverage.
- 2026-01-27: Implemented SQLAlchemy models + Alembic migrations for the documented Postgres schema, added DB health endpoint and schema verification tests.
- 2026-01-27: Suppressed root layout hydration mismatches caused by external attributes in the dashboard.
- 2026-01-27: Added dashboard i18n (EN/ES), public overview page, Playwright baseline E2E, and a hardcoded-string guard; configured ruff/mypy/pytest coverage in API and Engine.
- 2026-01-27: Scaffolded dashboard (Next.js), API (FastAPI + uv), and engine (uv package), added local Docker Compose for Postgres/Redis, and introduced basic infra scripts and tests.
- 2026-01-26: Created documentation pack v7. Major expansion of PRD (detailed epics, acceptance criteria, checklists) and prompt pack (small scope prompts with high detail).

- 2026-01-26: Merged v4 missing docs (security ops, validation, glossary), expanded DB schema explicit columns, merged folder structure and overview, added prompt index/mapping, added candidate event.

- 2026-01-26: Preserved v4 prompt files under docs/08_PROMPTS/ and added compatibility redirect stubs at original v4 paths.