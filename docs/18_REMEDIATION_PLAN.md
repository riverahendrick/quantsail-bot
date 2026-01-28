# Quantsail Remediation Plan (v1)

## Objective
Close all gaps between documentation and implementation before backtesting, forward testing, and testnet.

## Guardrails
- No mocks in production paths unless explicitly gated by config.
- All changes must update todo.md and docs/CHANGELOG.md.
- Safety gates and exits must never be bypassed.

## Phase 1: Spec parity (Docs vs Code)
- [ ] API: Verify every endpoint + request/response shape in docs/03_API_SPEC.md
- [ ] DB: Verify migrations and runtime schema match docs/04_DB_SCHEMA.md
- [ ] Engine: Verify state machine + gates match docs/13_ENGINE_SPEC.md
- [ ] UI: Verify pages/widgets/controls match docs/05_UI_SPEC.md and docs/17_UI_WIREFRAMES_TEXT.md
- [ ] GLOBAL_RULES: Confirm no hardcoded secrets, no unsafe defaults, no mocks outside flags

## Phase 2: Safety + Execution
- [ ] Confirm live exit logic (SL/TP) works end-to-end
- [ ] Confirm ARM LIVE gates enforced in API, engine, and dashboard
- [ ] Validate breaker and daily-lock behavior with real market data
- [ ] Confirm encryption key handling and key storage lifecycle

## Phase 3: Quality + Tests
- [ ] Add missing unit/integration tests for any remediation fixes
- [ ] Add/extend E2E tests for new/changed dashboard routes
- [ ] Ensure 100% coverage for touched files

## Phase 4: Backtesting + Forward Test readiness
- [ ] Backtest harness configured (data sources, fee/slippage model, reproducible configs)
- [ ] Forward test plan (paper/testnet) defined with success criteria
- [ ] Runbook for go/no-go to testnet

## Owners
- Systems/QA: Hendrick
- Implementation: Engineering (Codex)

## Notes
- This file tracks remediation only. Execution/backtesting plans are defined after Phase 1-3.
