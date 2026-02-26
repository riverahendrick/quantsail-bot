# Quantsail — Security & Operations v7

## 0) Rules
Follow all security requirements documented in this file.

## 1) Security
- AES-GCM encrypt exchange keys at rest
- never log secrets
- Vercel never receives secrets
- RBAC for all private endpoints
- rate limiting for public endpoints
- strict CORS allowlist and secure headers

## 2) Operations
- restart-safe reconciliation
- idempotent orders
- websocket reconnect handling
- alerting for breakers/disconnects/failed orders
