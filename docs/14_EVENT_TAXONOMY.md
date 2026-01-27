# Quantsail — Event Taxonomy v1

Rule: if a decision happens, emit an event. No secrets in payloads.

## Envelope
- ts, level, type, symbol?, trade_id?, payload, public_safe

## Required event types
System:
- system.started, system.stopped, config.activated, reconcile.completed

Signals:
- market.tick
- signal.generated
- ensemble.decision
- trade.candidate.created  # a candidate trade/plan exists before gating/execution

Gates:
- gate.profitability.passed
- gate.profitability.rejected

Risk:
- risk.position_sized

Breakers:
- breaker.triggered
- breaker.expired

Trades/Orders:
- trade.opened
- order.placed
- order.filled
- trade.closed

Daily lock:
- daily_lock.engaged
- daily_lock.floor_updated
- daily_lock.entries_paused

Security:
- security.key.added
- security.key.revoked
