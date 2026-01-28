# Phase 1 Progress (Spec Parity)

## API vs docs/03_API_SPEC.md
Status: In progress
- Verified endpoints listed in docs exist in code (health, status, config, exchanges, bot control, data, public, WS).
- Updated docs to include /v1/bot/arm, /v1/news/*, and user management endpoints.
- Remaining gaps:
  - Error schema not consistent across all endpoints (some return raw strings).
  - Public WS not implemented (spec lists as optional later).


## DB vs docs/04_DB_SCHEMA.md
Status: In progress
- Gaps fixed: added events.seq + uq_events_seq via Alembic migration.
- Added exchange_keys.is_active + uq_exchange_keys_active for active-key selection.

## Engine vs docs/13_ENGINE_SPEC.md
Status: Pending
- Validate state machine, gates, and execution behavior.

## UI vs docs/05_UI_SPEC.md + docs/17_UI_WIREFRAMES_TEXT.md
Status: Pending
- Verify pages/widgets/controls parity.

## GLOBAL_RULES.md compliance
Status: Pending
- Ensure no hardcoded secrets or mocks outside flags.
