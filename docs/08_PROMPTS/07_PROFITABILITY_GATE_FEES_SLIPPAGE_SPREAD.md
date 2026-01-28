# Prompt 07 — Profitability gate (fees + slippage + spread) with full breakdown events

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
This is the core of your requirement: never take trades that become unprofitable after costs. The gate must be auditable and test-proven.

## Goal (this prompt only)
Implement a fee+slippage+spread profitability estimator and gate. Reject entries if expected net profit < execution.min_profit_usd. Emit pass/reject events with complete breakdown.

## Scope boundaries (do NOT go beyond this)
- Do NOT change strategy logic.
- Do NOT implement live execution.
- Only implement profitability estimation and gating + events + tests.

## Files to touch (allowed edits/creates)
- services/engine/**
- packages/shared/** (optional)
- todo.md
- docs/CHANGELOG.md
- docs/09_CONFIG_SPEC.md (ONLY if missing constraints must be clarified)

## Files you must update before marking complete
- todo.md
- docs/CHANGELOG.md
- (optional) docs/09_CONFIG_SPEC.md if updated

## Deliverables (must exist at end)
- Fee estimator (maker/taker bps).
- Orderbook depth slippage estimator.
- Spread cost estimator.
- Profitability calculation.
- Gate integration into engine.
- Events: gate.profitability.passed/rejected including breakdown.
- Unit tests covering adverse conditions.

## Implementation steps (do in order; be explicit)
1) Implement fee estimator:
   - fee_usd = notional_usd * (fee_bps/10_000)
   - Use taker_bps for market orders by default; respect config.
2) Implement slippage estimator using orderbook depth:
   - Given desired notional/qty, walk the book levels to compute expected average fill price.
   - slippage_usd = (avg_fill_price - best_price) * qty (direction-aware)
   - Must handle insufficient depth (treat as reject or huge slippage; document and test).
3) Implement spread cost estimate:
   - spread_bps = (ask - bid)/mid * 10_000
   - spread_cost_est_usd can be approximated as half-spread * qty or full spread depending on order type; document choice and be consistent.
4) Profitability calculation:
   - expected_gross_profit_usd based on proposed TP vs entry price and qty.
   - expected_net_profit_usd = gross - fees - slippage - spread_cost
   - Compare with execution.min_profit_usd.
5) Integrate gate into entry pipeline:
   - After ensemble says ENTER_LONG but before trade.opened, run gate.
   - If reject: do NOT open trade; emit reject event and record the decision.
6) Events:
   - gate.profitability.passed/rejected with payload including:
     entry_price, tp_price, qty, gross, fee, slippage, spread, net, threshold, decision.
7) Tests:
   - Low liquidity orderbook → reject
   - High spread → reject
   - High fees → reject
   - Normal conditions → pass
8) Update todo.md + CHANGELOG.


## Tests to run and report (exact commands)
- Engine tests: `uv -C services/engine run pytest -q --cov`


## Acceptance checklist (must check all)
- [x] Gate rejects trades below min_profit_usd after costs
- [x] Pass/reject events include complete breakdown
- [x] Insufficient orderbook depth behavior is defined and tested
- [x] 100% coverage for touched files
- [x] todo.md + CHANGELOG updated