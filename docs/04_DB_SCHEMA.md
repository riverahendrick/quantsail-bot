# Quantsail — Database Schema v7 (Postgres, Explicit)

Rule: no guessing. If code diverges, update this doc first.

## Conventions
- All timestamps are `timestamptz` in UTC.
- Primary keys are UUIDs (generated server-side).
- JSON payloads are `jsonb`.
- Events are append-only.

## 1) users
Stores operator accounts and roles (MVP is single-tenant but future-ready).

Columns:
- id uuid PK
- email text UNIQUE NOT NULL
- role text NOT NULL  -- enum: OWNER, CEO, DEVELOPER, ADMIN (future)
- created_at timestamptz NOT NULL DEFAULT now()

Indexes:
- unique(email)

## 2) exchange_keys
Encrypted exchange API credentials (ciphertext only).

Columns:
- id uuid PK
- exchange text NOT NULL  -- "binance"
- label text NULL        -- human label
- ciphertext bytea NOT NULL
- nonce bytea NOT NULL
- key_version int NOT NULL DEFAULT 1
- created_by uuid NULL REFERENCES users(id)
- created_at timestamptz NOT NULL DEFAULT now()
- revoked_at timestamptz NULL

Constraints:
- (exchange, label) optional uniqueness is allowed but not required

Security:
- plaintext never stored; never returned from API.

## 3) bot_config_versions
Versioned bot configuration.

Columns:
- id uuid PK
- version int UNIQUE NOT NULL  -- monotonic
- config_json jsonb NOT NULL
- config_hash text NOT NULL    -- sha256 of canonical json
- created_by uuid NULL REFERENCES users(id)
- created_at timestamptz NOT NULL DEFAULT now()
- activated_at timestamptz NULL
- is_active boolean NOT NULL DEFAULT false

Constraints:
- Only one row may have is_active=true (enforce via partial unique index).

Indexes:
- unique(version)
- unique where is_active=true

## 4) trades
A trade is a position lifecycle. MVP spot assumes 0/1 open position per symbol (config controlled).

Columns:
- id uuid PK
- symbol text NOT NULL               -- "BTC/USDT"
- side text NOT NULL                -- "LONG" (spot buy then sell)
- status text NOT NULL              -- OPEN, CLOSED, CANCELED
- mode text NOT NULL                -- DRY_RUN, LIVE
- opened_at timestamptz NOT NULL
- closed_at timestamptz NULL

Entry:
- entry_price numeric(24,10) NOT NULL
- entry_qty numeric(24,10) NOT NULL
- entry_notional_usd numeric(24,10) NOT NULL

Exits (planned):
- stop_price numeric(24,10) NOT NULL
- take_profit_price numeric(24,10) NOT NULL
- trailing_enabled boolean NOT NULL DEFAULT false
- trailing_offset numeric(24,10) NULL

Result:
- exit_price numeric(24,10) NULL
- realized_pnl_usd numeric(24,10) NULL
- fees_paid_usd numeric(24,10) NULL
- slippage_est_usd numeric(24,10) NULL
- notes jsonb NULL  -- rationale summary, gate breakdown snapshot, etc.

Indexes:
- (symbol, opened_at desc)
- status

## 5) orders
Order attempts (live later; dry-run can still record simulated orders).

Columns:
- id uuid PK
- trade_id uuid NOT NULL REFERENCES trades(id) ON DELETE CASCADE
- symbol text NOT NULL
- side text NOT NULL             -- BUY/SELL
- order_type text NOT NULL       -- MARKET/LIMIT
- qty numeric(24,10) NOT NULL
- price numeric(24,10) NULL
- status text NOT NULL           -- PLACED, FILLED, CANCELED, FAILED, SIMULATED
- exchange_order_id text NULL    -- live only; never exposed publicly
- idempotency_key text NULL      -- live only
- created_at timestamptz NOT NULL DEFAULT now()
- updated_at timestamptz NOT NULL DEFAULT now()

Indexes:
- trade_id
- (symbol, created_at desc)
- exchange_order_id

## 6) equity_snapshots
Periodic snapshots for charts and daily lock.

Columns:
- id uuid PK
- ts timestamptz NOT NULL
- equity_usd numeric(24,10) NOT NULL
- cash_usd numeric(24,10) NOT NULL
- unrealized_pnl_usd numeric(24,10) NOT NULL
- realized_pnl_today_usd numeric(24,10) NOT NULL
- open_positions int NOT NULL
- meta jsonb NULL

Indexes:
- (ts desc)

## 7) events
Append-only domain events.

Columns:
- id uuid PK
- seq bigint UNIQUE NOT NULL    -- monotonic cursor for WS resume
- ts timestamptz NOT NULL
- level text NOT NULL           -- INFO/WARN/ERROR
- type text NOT NULL            -- see docs/14_EVENT_TAXONOMY.md
- symbol text NULL
- trade_id uuid NULL REFERENCES trades(id) ON DELETE SET NULL
- payload jsonb NOT NULL
- public_safe boolean NOT NULL DEFAULT false

Indexes:
- unique(seq)
- (ts desc)
- type
- symbol
- public_safe

## Notes on public sanitization
Public endpoints must:
- filter events to public_safe=true,
- remove exchange_order_id, idempotency_key, ciphertext, nonce,
- optionally bucket sizes and delay timestamps.
