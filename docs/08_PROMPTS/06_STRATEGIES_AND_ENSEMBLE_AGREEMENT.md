# Prompt 06 — Strategies (trend/mean‑reversion/breakout) + ensemble agreement gating

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
Your edge comes from disciplined, testable rules and multi-strategy confirmation. We must standardize outputs so later gates (profitability/risk/breakers) can operate uniformly.

## Goal (this prompt only)
Implement the 3 strategies with the standard output schema and an ensemble combiner enforcing min_agreement and confidence threshold. Must be deterministic on fixtures and emit correct events.

## Scope boundaries (do NOT go beyond this)
- Do NOT implement live execution.
- Do NOT change DB schema.
- Do NOT add ML/LLM decision making.
- Only implement strategy computation + ensemble decision + events.

## Files to touch (allowed edits/creates)
- services/engine/**
- packages/shared/** (schema optional)
- todo.md
- docs/CHANGELOG.md
- docs/13_ENGINE_SPEC.md (ONLY if clarifying missing exact fields)

## Files you must update before marking complete
- todo.md
- docs/CHANGELOG.md
- (optional) docs/13_ENGINE_SPEC.md if updated

## Deliverables (must exist at end)
- Strategy modules: trend, mean_reversion, breakout.
- Shared StrategyOutput schema.
- Ensemble combiner.
- Deterministic fixtures and tests.
- Events: signal.generated (per strategy) + ensemble.decision (aggregate).

## Implementation steps (do in order; be explicit)
1) Confirm standard output schema fields from docs/13_ENGINE_SPEC.md.
2) Implement indicator utilities (pure functions):
   - EMA, RSI, Bollinger Bands, ATR, ADX, Donchian channel.
   - Keep them deterministic and unit-tested.
3) Implement strategies:
   A) Trend:
      - Example rule: EMA fast > EMA slow AND ADX above threshold → ENTER_LONG (with confidence based on separation/ADX strength)
   B) Mean reversion:
      - Example rule: price touches lower Bollinger and RSI oversold → ENTER_LONG
   C) Breakout:
      - Example rule: close breaks above Donchian high with ATR filter → ENTER_LONG
   Each must return StrategyOutput with rationale fields containing the indicator values used.
4) Implement ensemble combiner:
   - Collect outputs.
   - Count ENTER_LONG votes with confidence >= threshold.
   - If votes >= min_agreement → decision ENTER_LONG else NO_TRADE/HOLD.
   - Build an explicit rationale listing which strategies agreed/disagreed and their key numbers.
5) Integrate into engine loop:
   - Replace stub signal provider with real strategies + ensemble.
   - Emit events for each strategy output and final decision.
6) Tests:
   - Provide fixture candle series that produce predictable decisions for each strategy.
   - Tests for ensemble cases: 0/3, 1/3, 2/3, 3/3 agreement.
7) Update todo.md + CHANGELOG.


## Tests to run and report (exact commands)
- Engine lint/typecheck: `uv -C services/engine run ruff check .` and `uv -C services/engine run mypy .`
- Engine tests: `uv -C services/engine run pytest -q --cov`


## Acceptance checklist (must check all)
- [ ] Each strategy is deterministic and unit-tested
- [ ] StrategyOutput schema matches docs and includes rationale numbers
- [ ] Ensemble respects min_agreement and confidence_threshold
- [ ] Correct events emitted for strategies and ensemble
- [ ] 100% coverage for touched files
- [ ] todo.md + CHANGELOG updated

