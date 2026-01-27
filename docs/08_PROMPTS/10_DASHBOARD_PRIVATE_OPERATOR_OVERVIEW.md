# Prompt 10 — Private operator dashboard (overview) wired to real API/WS

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
Operator needs a beautiful, modern dashboard that shows status, performance, and WHY decisions happened. This must be accurate and not require reading logs.

## Goal (this prompt only)
Implement `/app/overview` private page with status banner, KPIs, daily lock widget, breakers widget, trades/events tables, and WS real-time updates. Add E2E tests.

## Scope boundaries (do NOT go beyond this)
- Do NOT implement all other private pages yet.
- Do NOT implement styling beyond a clean modern layout.
- Do NOT call public endpoints from private pages.

## Files to touch (allowed edits/creates)
- apps/dashboard/**
- tests/e2e/**
- todo.md
- docs/CHANGELOG.md
- docs/05_UI_SPEC.md (ONLY if missing UI requirements must be clarified first)

## Files you must update before marking complete
- todo.md
- docs/CHANGELOG.md
- (optional) docs/05_UI_SPEC.md if updated

## Deliverables (must exist at end)
- `/app/overview` implemented with i18n.
- Auth-protected route.
- Data wired to `/v1/*` endpoints and private WS.
- E2E tests verifying the page loads and key elements render.

## Implementation steps (do in order; be explicit)
1) Read docs/05_UI_SPEC.md and docs/17_UI_WIREFRAMES_TEXT.md.
2) Implement auth gating for private routes (Firebase client auth or server session approach; follow best practices).
3) Build page layout:
   - Status banner: running/paused/stopped + reason + until
   - KPI cards: equity, realized pnl today, win rate (placeholder if not computed yet), profit factor (placeholder)
   - Daily lock card: target, mode, realized, peak, floor, entries paused indicator
   - Breakers card: active breakers list + time remaining
   - Tables: open positions, recent trades, recent events
4) Wire data:
   - Fetch initial state via API.
   - Subscribe to WS for real-time updates (events/trades/snapshots) and update UI state.
5) Add E2E tests:
   - Seed minimal DB state or mock API to render predictable UI.
   - Verify the status banner and daily lock card render.
6) Ensure i18n:
   - All labels come from translations.
7) Update todo.md + CHANGELOG.


## Tests to run and report (exact commands)
- Dashboard: `pnpm -C apps/dashboard lint`
- Dashboard: `pnpm -C apps/dashboard typecheck`
- E2E: `pnpm -C apps/dashboard exec playwright test`


## Acceptance checklist (must check all)
- [ ] /app/overview renders with translated strings only
- [ ] Uses private endpoints + WS only
- [ ] E2E tests pass
- [ ] 100% coverage for touched UI logic files (as applicable) and no hardcoded strings
- [ ] todo.md + CHANGELOG updated

