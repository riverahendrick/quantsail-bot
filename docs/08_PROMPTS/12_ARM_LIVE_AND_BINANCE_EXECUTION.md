# Prompt 12 — ARM LIVE + Binance live execution

## Mandatory first steps (before anything else)
1) Open and read `GLOBAL_RULES.md` (repo root).
2) Confirm you will follow every rule (do not paste rules).
3) Confirm you will not create a nested repo root folder.
4) Use all available tools/skills/MCPs available in your environment and do best-practice research when needed.

## No‑guessing rule
- If anything is unclear, search `docs/` first.
- If still unclear, **update the relevant doc** before coding.
- Do not invent behavior or “assume” defaults beyond docs.

## End‑of‑prompt obligations
- Update `todo.md` (add a section for this prompt and check items).
- Update `docs/CHANGELOG.md` (what changed + why).
- Update `docs/10_FEATURES.md` only if scope changes.

## Testing policy
- TDD required.
- 100% coverage for all touched files.
- Run unit + integration + E2E (if relevant).
- Report exact commands and outputs.

## Final report format (must be included)
1) Files changed (bulleted)
2) Commands run (bulleted)
3) Test results (paste outputs)
4) Checklist updates (what was checked in todo.md + docs)
5) Notes / follow-ups (optional)


## Context (what we’re building)
Follow docs/01_PRD.md, docs/03_API_SPEC.md, docs/13_ENGINE_SPEC.md, and docs/14_EVENT_TAXONOMY.md. Build only the minimal slice needed for this prompt.

## Goal (this prompt only)
Implement ARM LIVE gate + live execution idempotency + reconciliation; add tests preventing accidental live orders.

## Non‑goals (explicitly do NOT do these)
- Do not bundle unrelated features.
- Do not change documented behavior without updating docs first.

## Deliverables (must exist at end)
- Code implementing the module goal.
- Unit tests and required integration/E2E tests.
- Updated todo.md and docs/CHANGELOG.md.

## Implementation steps (do in order)
1) Read the relevant docs.
2) Implement minimal slice.
3) Add tests first for core logic.
4) Add integration/E2E if UI or router behavior changes.
5) Update docs and report outputs.

## Tests to run and report
- Run lint + typecheck.
- Run unit tests with coverage.
- Run integration/E2E tests if applicable.

## Definition of Done (check all)
- [ ] Behavior matches docs
- [ ] Tests pass with 100% coverage for touched files
- [ ] Events emitted as required
- [ ] todo.md and CHANGELOG updated