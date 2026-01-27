# Prompt 04 — Event journal + WebSocket streaming (resume cursor)

## Mandatory first step (before anything else)
1) Open and read `GLOBAL_RULES.md` in the repo root.
2) Confirm you will follow EVERY rule in it (do not paste the rules).
3) Confirm you will NOT create a nested repo root folder (no repo-inside-repo).
4) Use all available tooling and MCPs (linters, typecheckers, tests, formatting, search, best‑practice research when needed).

## No‑guessing rule (critical)
If anything is unclear:
- First, search for the answer in `docs/`.
- If missing, **update the relevant spec doc** (PRD/spec) BEFORE implementing code.
- Do NOT invent behavior, defaults, UI content, or security rules.

## End‑of‑task updates (mandatory)
- Update `todo.md` (add a section for this prompt and check items).
- Update `docs/CHANGELOG.md` (what changed + why).
- Update `docs/10_FEATURES.md` ONLY if feature scope changes.

## Testing policy (non‑negotiable)
- TDD required.
- 100% coverage for all touched files.
- Run unit tests + integration tests (when touching DB/API/engine integration) + E2E tests (when touching UI routes).
- Provide exact commands run and copy/paste outputs.

## Required final report format (must be included)
1) Files changed (bulleted)
2) Commands run (bulleted)
3) Test results (paste outputs)
4) Checklist updates (todo.md + docs)
5) Notes / follow‑ups (optional)


## Context (why this exists)
Transparency requires real-time streaming of decisions without leaking secrets. WS must be restart-safe with cursor resume.

## Goal (this prompt only)
Implement event writing/reading utilities and a WS endpoint that streams events/trades/snapshots with cursor resume. Add integration tests that prove engine/API can publish and clients can resume.

## Scope boundaries (do NOT go beyond this)
- Do not implement strategies yet.
- Do not implement live trading.
- Do not add UI features beyond test harnesses.

## Files to touch (allowed edits/creates)
- services/api/**
- (optional) services/engine/** only for a tiny publisher stub used in tests
- todo.md
- docs/CHANGELOG.md

## Files you must update before marking complete
- todo.md
- docs/CHANGELOG.md

## Deliverables (must exist at end)
- Event repository functions (append-only).
- WS endpoint `/ws` that streams DB-backed updates.
- Cursor resume support.
- Integration tests covering streaming and resume.

## Implementation steps (do in order; be explicit)
1) Implement event repository:
   - append_event(type, payload, level, public_safe, symbol?, trade_id?)
   - query_events(limit, cursor, filters)
2) Define a cursor format (monotonic; event id bigserial is ideal).
3) Implement WS endpoint:
   - On connect: optionally accept last_seen_cursor.
   - Send backlog (events after cursor) then tail new ones.
   - Use heartbeat pings and handle disconnect cleanly.
4) Add integration tests:
   - Insert events into DB.
   - Connect WS client, receive events.
   - Disconnect, insert more, reconnect with cursor, verify only new events arrive.
5) Ensure public-safe discipline:
   - WS here is private; public WS is optional later (do NOT implement unless required by docs).
6) Update todo.md + CHANGELOG.


## Tests to run and report (exact commands)
- API tests: `uv -C services/api run pytest -q --cov`
- If tests require infra: `cd infra/docker && docker compose up -d`


## Acceptance checklist (must check all)
- [ ] WS streams events from DB
- [ ] Cursor resume works and is test-proven
- [ ] No secrets are logged in WS payloads (tests can check redaction rules if implemented)
- [ ] 100% coverage for touched files
- [ ] todo.md + CHANGELOG updated

