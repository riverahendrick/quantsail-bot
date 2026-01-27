# Quantsail — API Specification v6

## 1) Segmentation
- Private endpoints: `/v1/*` (Firebase JWT + RBAC)
- Public endpoints: `/public/v1/*` (no auth; sanitized)
- WebSocket: `/ws` (private) and `/public/ws` (optional later)

## 2) Private endpoints (MVP)
Health/Status
- GET `/v1/health`
- GET `/v1/status`

Config
- GET `/v1/config`  (active config)
- POST `/v1/config/versions` (create version)
- POST `/v1/config/activate/{version}`

Keys
- POST `/v1/exchanges/binance/keys`
- DELETE `/v1/exchanges/binance/keys/{key_id}`
- GET `/v1/exchanges/binance/keys/status` (no secrets)

Bot control
- POST `/v1/bot/start`
- POST `/v1/bot/stop`
- POST `/v1/bot/pause_entries`
- POST `/v1/bot/resume_entries`

Data
- GET `/v1/trades`
- GET `/v1/orders`
- GET `/v1/events`
- GET `/v1/equity`

## 3) Public endpoints (MVP)
- GET `/public/v1/summary`
- GET `/public/v1/trades`
- GET `/public/v1/events` (only public_safe=true)
- GET `/public/v1/heartbeat`

## 4) WebSocket schema
Envelope:
```json
{ "type":"status|event|trade|snapshot", "ts":"ISO8601", "payload":{} }
```
Private WS may include full payload; public feed must be sanitized.


## 5) Notes and compatibility
- v4 used a simple `PUT /v1/config`. v7 standardizes on **versioned configs**: create a version then activate it.
- If a simple update endpoint is desired later, it must still create a new version under the hood.
