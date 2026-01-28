# Quantsail — API Specification v6

## 1) Segmentation
- Private endpoints: `/v1/*` (Firebase JWT + RBAC)
- Public endpoints: `/public/v1/*` (no auth; sanitized)
- WebSocket: `/ws` (private) and `/public/ws` (optional later)

## 1.1) Auth and RBAC (MVP)
Auth header for private routes:
`Authorization: Bearer <firebase_id_token>`

User mapping:
- Decode Firebase ID token.
- Use the `email` claim to look up `users.email`.
- Capture `firebase_uid` in request context (not persisted yet).

RBAC roles (from DB):
- OWNER, CEO, DEVELOPER, ADMIN

Allowed roles (MVP):
- `/v1/health`, `/v1/health/db`, `/v1/status`, `/v1/trades`, `/v1/orders`, `/v1/events`, `/v1/equity`
  - allowed: OWNER, CEO, DEVELOPER
  - denied: ADMIN

## 1.2) Standard error schema
All errors use:
`{"detail": {"code": "<CODE>", "message": "<human message>"}}`

Codes:
- AUTH_REQUIRED (401) - missing/invalid token
- RBAC_FORBIDDEN (403) - role not permitted or user not found
- RATE_LIMITED (429) - public rate limit exceeded

## 2) Private endpoints (MVP)
Health/Status
- GET `/v1/health`
- GET `/v1/health/db`
- GET `/v1/status`

Status response (MVP):
```json
{ "status": "unknown|<env BOT_STATUS>", "ts": "ISO8601" }
```

Config
- GET `/v1/config`  (active config)
- POST `/v1/config/versions` (create version)
- POST `/v1/config/activate/{version}`

Keys
- POST `/v1/exchanges/binance/keys`
- DELETE `/v1/exchanges/binance/keys/{key_id}`
- GET `/v1/exchanges/binance/keys/status` (no secrets)
- PATCH `/v1/exchanges/binance/keys/{key_id}` (label update or rotate secrets)
- POST `/v1/exchanges/binance/keys/{key_id}/activate` (set active key)
  - Status responses include: id, exchange, label, key_version, created_at, revoked_at, is_active.

Bot control
- POST `/v1/bot/arm`
- POST `/v1/bot/start`
- POST `/v1/bot/stop`
- POST `/v1/bot/pause_entries`
- POST `/v1/bot/resume_entries`

Users (owner-only)
- GET `/v1/users`
- POST `/v1/users`
- PATCH `/v1/users/{user_id}`

Data
- GET `/v1/trades`
- GET `/v1/orders`
- GET `/v1/events`
- GET `/v1/equity`

News
- POST `/v1/news/ingest`
- GET `/v1/news/status`
- DELETE `/v1/news/pause`

## 3) Public endpoints (MVP)
- GET `/public/v1/summary`
- GET `/public/v1/trades`
- GET `/public/v1/events` (only public_safe=true)
- GET `/public/v1/heartbeat`

## 3.1) Public response shapes (sanitized)
Summary (latest equity snapshot):
```json
{
  "ts": "ISO8601|null",
  "equity_usd": "number|null",
  "cash_usd": "number|null",
  "unrealized_pnl_usd": "number|null",
  "realized_pnl_today_usd": "number|null",
  "open_positions": "number|null"
}
```

Trades (sanitized list, newest first, optional `?limit=100`):
```json
[
  {
    "symbol": "BTC/USDT",
    "side": "LONG",
    "status": "OPEN|CLOSED|CANCELED",
    "mode": "DRY_RUN|LIVE",
    "opened_at": "ISO8601",
    "closed_at": "ISO8601|null",
    "entry_price": "number",
    "exit_price": "number|null",
    "realized_pnl_usd": "number|null"
  }
]
```

Events (sanitized list, newest first, optional `?limit=100`):
```json
[
  {
    "ts": "ISO8601",
    "level": "INFO|WARN|ERROR",
    "type": "event.type",
    "symbol": "BTC/USDT|null",
    "payload": {}
  }
]
```

Heartbeat:
```json
{ "ok": true, "ts": "ISO8601" }
```

## 3.2) Sanitization rules (public)
Forbidden fields must never appear in public responses:
- exchange_order_id, idempotency_key
- ciphertext, nonce
- any API key or secret field
- internal IDs (id, trade_id)

Public events:
- only include rows with `public_safe=true`
- payload is filtered to remove forbidden fields

## 3.3) Public rate limiting
- Per-IP limit: 60 requests per minute (all public endpoints combined)
- Primary: Redis (INCR + EXPIRE)
- Fallback: in-memory limiter for local dev/tests
- `PUBLIC_LIST_LIMIT_DEFAULT` controls the default list size (default 100).

## 4) WebSocket schema
Private WS: `ws://<host>/ws`

Auth:
- Prefer `Authorization: Bearer <firebase_id_token>` header.
- Fallback for clients that cannot set headers: `?token=<firebase_id_token>`.

Cursor:
- `cursor` is the monotonic `events.seq` value.
- Client sends `?cursor=<last_seen_seq>` to resume.
- If omitted, the server treats it as `0` (start from earliest available).

Envelope:
```json
{
  "type": "status|event|trade|snapshot",
  "ts": "ISO8601",
  "cursor": 123,
  "event_type": "trade.opened",
  "level": "INFO|WARN|ERROR",
  "symbol": "BTC/USDT|null",
  "trade_id": "uuid|null",
  "public_safe": false,
  "payload": {}
}
```

Notes:
- `event_type` is the original event taxonomy value.
- `type` is derived from event_type (`trade.*` -> trade, `snapshot` -> snapshot, else event).
- Heartbeats are sent as `type="status"` with `payload={"ok": true}` when idle.
- Public WS is optional later and must be sanitized.


## 5) Notes and compatibility
- v4 used a simple `PUT /v1/config`. v7 standardizes on **versioned configs**: create a version then activate it.
- If a simple update endpoint is desired later, it must still create a new version under the hood.
