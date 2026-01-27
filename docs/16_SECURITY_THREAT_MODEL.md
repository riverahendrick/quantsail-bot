# Quantsail — Threat Model v1

## Assets
- Exchange secrets
- Trade integrity
- Public reporting integrity
- Authentication tokens

## Key threats and mitigations
- Secret leakage: AES‑GCM at rest; redaction; secrets never leave VPS; no secrets in events.
- Unauthorized trading: RBAC + (later) ARM LIVE two-step token.
- Duplicate orders: (later) idempotency keys + reconciliation.
- Public leakage: strict public serializers; dedicated public router; tests for sanitization.
