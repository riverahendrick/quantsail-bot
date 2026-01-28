# PROMPT LOG

## Prompt 02 - Postgres schema + Alembic migrations + schema verification tests
Date: 2026-01-27
Role: Database Migration Engineer

### Plan (approved)
- Write schema verification tests first (tables/columns/indexes/constraints).
- Implement SQLAlchemy models and Alembic configuration.
- Create initial migration and apply to fresh DB.
- Add DB connection smoke check endpoint.
- Run required commands and update todo.md + docs/CHANGELOG.md (+ docs/04_DB_SCHEMA.md if needed).

### Progress log
- Read docs/04_DB_SCHEMA.md and PRD persistence notes.
- Researched official docs for SQLAlchemy 2.x, Alembic, and Postgres schema catalogs.
- Added SQLAlchemy models and Alembic config; generated initial migration and applied to Postgres.
- Added schema verification integration tests (tables/columns/indexes/constraints) and DB health endpoint.
- Added offline Alembic tests to ensure coverage; updated README with DB env + migration commands.

## Prompt 03 - API auth/RBAC + strict public sanitization router
Date: 2026-01-27
Role: Security and API Engineer

### Plan (approved)
- Update docs/03_API_SPEC.md with auth mapping, error schema, RBAC matrix, public responses, sanitization rules, and rate limit policy.
- Add TDD tests for auth/RBAC, public sanitization, and rate limiting.
- Implement Firebase JWT verification, RBAC dependency, private/public routers, and rate limiter.
- Run ruff, mypy, pytest, then update todo.md + docs/CHANGELOG.md (+ docs/10_FEATURES.md if scope changes).

### Progress log
- Updated docs/03_API_SPEC.md with auth/RBAC rules, error schema, public shapes, and rate limits.
- Added Firebase JWT verification, RBAC dependency, private/public routers, sanitization helpers, and rate limiting.
- Added unit/integration tests for auth edge cases, sanitization rules, and rate limiting (Redis + in-memory).
- Brought ruff, mypy, and pytest to green at 100% coverage.
- Updated README, CHANGELOG, FEATURES, and prompt checklist for Prompt 03.

## Prompt 04 - Event journal + WebSocket streaming (resume cursor)
Date: 2026-01-27
Role: Event Streaming Engineer

### Plan (draft)
- Confirm WS auth + cursor format in docs/03_API_SPEC.md.
- Add event repository helpers (append + query) and cursor parsing.
- Implement private /ws stream with backlog + tail + heartbeat.
- Add integration tests for streaming + resume.
- Run API tests and update todo.md + docs/CHANGELOG.md (+ docs/10_FEATURES.md if scope changes).

### Progress log
- Reviewed docs/03_API_SPEC.md, docs/04_DB_SCHEMA.md, docs/14_EVENT_TAXONOMY.md.
- Added events seq cursor to schema + migration; updated API spec with WS auth/cursor/envelope.
- Implemented events repo helpers, WS endpoint with backlog + heartbeat, and payload redaction.
- Added WS streaming/resume tests and helper coverage for cursor parsing and auth mapping.
- Started Docker services and ran pytest with 100% coverage after fixing WS auth/cursor tests and trade FK setup in event tests.
