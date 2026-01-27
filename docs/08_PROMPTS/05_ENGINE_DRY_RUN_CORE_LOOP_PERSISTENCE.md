# Prompt 05 — Engine dry‑run core loop + persistence (no strategies yet)

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
We need a working end-to-end pipeline before strategy complexity: engine loop → create a trade candidate → persist events/trades/orders/snapshots → stream to API/WS.

## Goal (this prompt only)
Implement a deterministic dry-run engine loop skeleton that can create a simulated trade candidate and persist the required DB records + events. No real strategies yet; use a fixed stub signal for now.

## Scope boundaries (do NOT go beyond this)
- Do NOT implement live trading.
- Do NOT implement final strategies (that’s Prompt 06).
- Do NOT implement profitability gate math beyond a placeholder event; that’s Prompt 07.
- Keep it deterministic and testable.

## Files to touch (allowed edits/creates)
- services/engine/**
- services/api/** (only if needed for WS/DB integration)
- packages/shared/** (optional schemas)
- todo.md
- docs/CHANGELOG.md

## Files you must update before marking complete
- todo.md
- docs/CHANGELOG.md

## Deliverables (must exist at end)
- Engine loop per-symbol with deterministic tick.
- Persist: events, a simulated trade, simulated orders (entry/tp/sl), equity snapshot.
- Integration test proving records exist and are streamed via WS.

## Implementation steps (do in order; be explicit)
1) Read docs/13_ENGINE_SPEC.md and docs/14_EVENT_TAXONOMY.md.
2) Implement engine skeleton:
   - configuration loader (from env or local json for now; real config activation already exists in API)
   - per-symbol loop runner that calls `on_tick(symbol)` deterministically.
3) Implement a stub “signal provider”:
   - Always returns HOLD until test triggers ENTER_LONG for one tick.
   - This avoids strategy complexity and makes tests deterministic.
4) Implement persistence layer:
   - Use API’s DB schema/models or shared models; write to Postgres tables.
   - Create a trade + orders: entry, tp, sl.
   - Create events: market.tick, trade.candidate.created, trade.opened, order.placed, order.filled, snapshot.
5) Implement equity snapshot update:
   - In dry-run, simulate fills at a deterministic price.
6) Tests:
   - Unit tests for engine loop state transitions.
   - Integration test: run one tick → verify DB rows created and events appear in WS stream.
7) Update todo.md + CHANGELOG.


## Tests to run and report (exact commands)
- Engine: `uv -C services/engine run pytest -q --cov`
- API (if integration/WS used): `uv -C services/api run pytest -q --cov`
- Infra: `cd infra/docker && docker compose up -d`


## Acceptance checklist (must check all)
- [ ] Engine loop runs deterministically in tests
- [ ] Trade/orders/events/snapshot persisted in DB for a simulated entry
- [ ] WS stream shows the emitted events
- [ ] 100% coverage for touched files
- [ ] todo.md + CHANGELOG updated

