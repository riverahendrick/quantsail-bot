# SCRATCHPAD

## Prompt 02 - Research Notes (2026-01-27)
Role: Database Migration Engineer

### Official references
- SQLAlchemy 2.0 declarative mapping and mapped_column usage.
- SQLAlchemy PostgreSQL dialect notes (UUID/JSON/JSONB types).
- Alembic tutorial + env.py target_metadata configuration.
- PostgreSQL information_schema.columns and pg_indexes catalog for schema verification queries.

### Decisions to confirm
- UUID generation: docs/04_DB_SCHEMA.md says "generated server-side" (no explicit DB default). Plan: application-side UUID defaults in SQLAlchemy; no DB server_default unless docs updated.
- Use information_schema + pg_indexes for deterministic schema verification tests.

### To-do for Prompt 02
- Add SQLAlchemy models + Alembic config/migration.
- Add schema verification integration tests (expected/edge/failure cases).
- Add DB smoke check endpoint.
- Run required commands and update docs.
### Notes during implementation
- psycopg required binary wheels on Windows; added psycopg[binary] after import error from libpq.
- Alembic offline SQL runs used to cover env.py and migration upgrade/downgrade for 100% coverage.

## Prompt 03 - Research Notes (2026-01-27)
Role: Security and API Engineer

### Official references
- Firebase Admin SDK verify_id_token and error behavior.
- FastAPI HTTPBearer + HTTPAuthorizationCredentials.
- FastAPI Request client host for per-IP rate limiting.
- Redis INCR + EXPIRE rate limiter pattern.

### Decisions to document in docs/03_API_SPEC.md
- Map Firebase token to local users via email claim (no DB change).
- Standard error schema and codes for 401/403/429.
- Public endpoint response shapes and sanitization rules.
- Public rate limit policy (60 requests/min/IP).

### Notes during implementation
- Verified Firebase Admin via Application Default credentials with explicit mypy casting.
- Added Redis-backed limiter with in-memory fallback and tests for both.
- Expanded private/public endpoint tests to enforce auth and sanitization rules.

## Prompt 04 - Research Notes (2026-01-27)
Role: Event Streaming Engineer

### Official references
- FastAPI WebSocket endpoints and WebSocket test client patterns.
- Starlette WebSocket close codes and disconnect handling.
- Psycopg connection settings for Postgres connectivity in integration tests.

### Decisions to document
- Use events.seq (bigint, unique) as the monotonic resume cursor.
- Keep WS private-only for now; public WS remains optional and must be sanitized later.
- Apply payload redaction on WS messages to avoid leaking secrets in debug payloads.

### Notes during implementation
- Added WS auth fallback for clients that cannot set headers (`?token=`).
- Implemented backlog + polling tail with heartbeats to keep idle connections alive.

## Prompt 05 - Research Notes (2026-01-27)
Role: Engine Loop & Persistence Engineer

### Official references
- SQLAlchemy Core INSERT + RETURNING for deterministic inserts.
- SQLAlchemy Engine/Connection context manager patterns for transaction safety.
- Psycopg connection pool usage guidance.

### Decisions to document
- Use a deterministic engine loop that emits events per docs/13_ENGINE_SPEC.md and docs/14_EVENT_TAXONOMY.md.
- Persist with the same Postgres schema as the API (events/trades/orders/equity_snapshots).
- Use a stub signal provider that can be toggled to emit ENTER_LONG for one tick in tests.
