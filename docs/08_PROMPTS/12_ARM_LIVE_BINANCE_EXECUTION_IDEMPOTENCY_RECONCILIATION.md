# Prompt 12 — ARM LIVE gate + Binance spot live execution (idempotent) + restart reconciliation

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
Live trading is the highest-risk part. We require strong safety: explicit arming, idempotency, reconciliation on restart, and tests that prevent accidental live trading.

## Goal (this prompt only)
Implement ARM LIVE two-step gate, Binance spot order execution via the adapter, idempotency keys to prevent duplicate orders, and restart reconciliation. Add tests proving safety.

## Scope boundaries (do NOT go beyond this)
- Do NOT add futures/leverage.
- Do NOT weaken sanitization.
- Do NOT allow any live order path without ARM LIVE.

## Files to touch (allowed edits/creates)
- services/engine/**
- services/api/**
- apps/dashboard/**
- tests/e2e/**
- todo.md
- docs/CHANGELOG.md
- docs/07_VALIDATION_AND_GO_LIVE.md (update gates/checklist if needed)

## Files you must update before marking complete
- todo.md
- docs/CHANGELOG.md
- docs/07_VALIDATION_AND_GO_LIVE.md (if any go-live gate changed)

## Deliverables (must exist at end)
- ARM LIVE API endpoints and short-lived arming token.
- Dashboard ARM LIVE UI modal/flow.
- BinanceSpotAdapter live order placement.
- Idempotency mechanism.
- Reconciliation on restart.
- Unit + integration tests ensuring no duplicates and no live without arming.

## Implementation steps (do in order; be explicit)
1) Implement ARM LIVE in API:
   - Two-step confirm: request arming → receive short TTL token → start live requires token.
   - Store arming state securely; log audit events.
2) Dashboard UI:
   - Add ARM LIVE button that opens a confirmation modal (two-step).
   - Display clear warnings and current mode.
3) Implement Binance live execution:
   - Add `BinanceSpotAdapter` methods for placing/canceling orders.
   - Ensure fees and order constraints respected.
4) Idempotency:
   - Use a deterministic client order id or an idempotency key stored in DB.
   - If a retry occurs, do not place a second order; instead fetch/attach existing order.
5) Restart reconciliation:
   - On engine startup, load open trades/orders from DB.
   - Query exchange for open orders.
   - Reconcile states and emit reconcile.completed event.
6) Tests:
   - Attempt live start without ARM token → must fail.
   - Simulate retry and verify only one exchange order is created.
   - Simulate restart and verify reconciliation restores state without duplicates.
   - E2E: ARM LIVE flow in UI (can be mocked in dev).
7) Update docs/go-live gates and todo/changelog.


## Tests to run and report (exact commands)
- API tests: `uv -C services/api run pytest -q --cov`
- Engine tests: `uv -C services/engine run pytest -q --cov`
- Dashboard E2E: `pnpm -C apps/dashboard exec playwright test`


## Acceptance checklist (must check all)
- [x] Live orders cannot happen without ARM LIVE token (test-proven)
- [x] Idempotency prevents duplicate orders (test-proven)
- [x] Reconciliation restores state after restart (test-proven)
- [x] E2E ARM LIVE flow passes (mocked acceptable)
- [x] todo.md + CHANGELOG updated

