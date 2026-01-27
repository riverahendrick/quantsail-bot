# Prompt 08 — Circuit breakers + negative news shock pause (entries only; exits always allowed)

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
Safety is mandatory. Breakers reduce tail-risk and protect the daily goal. They must never block exits.

## Goal (this prompt only)
Implement all breakers (volatility, spread/slippage, consecutive losses, exchange instability) and negative news shock pause. Breakers pause entries only. Emit breaker events and prove exits continue.

## Scope boundaries (do NOT go beyond this)
- Do NOT implement UI pages.
- Do NOT implement live execution.
- Only implement breaker state, triggers, expiry, and enforcement in entry pipeline.

## Files to touch (allowed edits/creates)
- services/engine/**
- services/api/** (only for news ingestion cache)
- todo.md
- docs/CHANGELOG.md
- docs/18_EXTERNAL_SERVICES.md (optional if clarifying providers)

## Files you must update before marking complete
- todo.md
- docs/CHANGELOG.md

## Deliverables (must exist at end)
- Breaker manager module.
- Breaker triggers and expiry.
- News pause integration (negative high-impact only).
- Events breaker.triggered/breaker.expired.
- Tests proving exits are not blocked.

## Implementation steps (do in order; be explicit)
1) Breaker manager:
   - Central component that tracks active breakers with expiry times.
   - Expose `entries_allowed()` and `exits_allowed()` (exits always true).
2) Implement triggers:
   - Volatility spike: ATR multiple or sudden candle range
   - Spread/slippage spike: based on spread_bps or slippage estimate
   - Consecutive losses: count losing trades within day/session
   - Exchange instability: repeated disconnects/rate limit errors (simulated in tests)
3) Implement expiry:
   - Each breaker has pause_minutes; after expiry entries resume automatically.
4) News pause (negative only):
   - API ingests CryptoPanic (or stub provider) and marks a cache key when negative high-impact appears.
   - Engine consults cache; if active → pause entries.
   - Do NOT use news to enter trades; only to pause.
5) Enforce in engine:
   - Before opening any new trade, check entries_allowed.
   - For exits (TP/SL/close), ignore breaker state.
6) Emit events:
   - breaker.triggered and breaker.expired with breaker_id, reason, until timestamp.
7) Tests:
   - Trigger each breaker and verify entries blocked
   - Verify exits still execute while breaker active
   - Verify expiry resumes entries
8) Update todo.md + CHANGELOG.


## Tests to run and report (exact commands)
- Engine tests: `uv -C services/engine run pytest -q --cov`
- API tests (if news ingestion added): `uv -C services/api run pytest -q --cov`


## Acceptance checklist (must check all)
- [ ] Each breaker triggers and expires per config
- [ ] Entries are blocked during breakers/news pause
- [ ] Exits are never blocked (test-proven)
- [ ] Correct breaker events emitted
- [ ] 100% coverage for touched files
- [ ] todo.md + CHANGELOG updated

