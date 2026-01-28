# Prompt 09 — Daily target lock (STOP/OVERDRIVE) + trailing floor

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
You explicitly want the bot to hit a daily goal and protect it. This feature enforces the daily target behavior and prevents giving back profits.

## Goal (this prompt only)
Implement daily target lock exactly as in the PRD: STOP mode and OVERDRIVE mode with trailing floor. Must be fully tested with target→peak→floor scenarios.

## Scope boundaries (do NOT go beyond this)
- Do NOT implement UI pages.
- Do NOT change breaker logic.
- Only implement daily lock accounting, state, and entry enforcement + events.

## Files to touch (allowed edits/creates)
- services/engine/**
- todo.md
- docs/CHANGELOG.md

## Files you must update before marking complete
- todo.md
- docs/CHANGELOG.md

## Deliverables (must exist at end)
- Daily PnL accounting (realized).
- Daily lock state tracker (target, peak, floor).
- STOP mode enforcement.
- OVERDRIVE mode floor updates and enforcement.
- Events: daily_lock.engaged, floor_updated, entries_paused.
- Comprehensive tests.

## Implementation steps (do in order; be explicit)
1) Implement realized PnL today calculation:
   - Sum closed trade pnl in today’s timezone (configurable timezone, default project timezone).
   - Ensure the “day boundary” is consistent in tests.
2) STOP mode:
   - When realized_pnl_today >= target: pause entries for remainder of the day.
3) OVERDRIVE mode:
   - Maintain peak_realized_pnl_today.
   - Compute floor = max(target, peak - trailing_buffer).
   - If realized falls to floor: pause entries (optionally force close depending on config; if not implemented yet, document and stub with explicit TODO and tests for current behavior).
4) Integrate into entry pipeline:
   - Daily lock check occurs after breakers but before trade.opened.
5) Emit events at the correct moments:
   - daily_lock.engaged when first reaching target
   - daily_lock.floor_updated when peak increases and floor changes
   - daily_lock.entries_paused when enforcement happens
6) Tests (must be explicit):
   - Hit target in STOP and verify entries blocked
   - In OVERDRIVE: reach target, then reach peak, then reduce realized to floor and verify entries paused
7) Update todo.md + CHANGELOG.


## Tests to run and report (exact commands)
- Engine tests: `uv -C services/engine run pytest -q --cov`


## Acceptance checklist (must check all)
- [x] STOP mode pauses entries after target reached
- [x] OVERDRIVE updates floor and enforces it (scenario test)
- [x] Events emitted correctly
- [x] 100% coverage for touched files
- [x] todo.md + CHANGELOG updated

