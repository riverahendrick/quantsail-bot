# Environment Setup (v1)

This repo uses environment variables for API, engine, and dashboard configuration.
Templates are in the `env/` folder.

## Where to place env files
- Dashboard (Next.js): copy `env/dashboard.env` to `apps/dashboard/.env.local`
- API (FastAPI): export variables from `env/api.env`
- Engine (Python): export variables from `env/engine.env`

## Load env files (PowerShell)
From repo root:

```powershell
# Dashboard
type env\dashboard.env | ForEach-Object { if ($_ -match '^[A-Z0-9_]+=') { $k,$v = $_ -split '=',2; $env:$k = $v } }

# API
type env\api.env | ForEach-Object { if ($_ -match '^[A-Z0-9_]+=') { $k,$v = $_ -split '=',2; $env:$k = $v } }

# Engine
type env\engine.env | ForEach-Object { if ($_ -match '^[A-Z0-9_]+=') { $k,$v = $_ -split '=',2; $env:$k = $v } }
```

## Load env files (bash)

```bash
set -a
source env/dashboard.env
source env/api.env
source env/engine.env
set +a
```

## Required keys and how to obtain them

### Firebase web config (dashboard)
1) In Firebase console, add/register a Web App for your project. The console will show a config snippet to copy. 
2) The config object includes fields like `apiKey`, `authDomain`, `projectId`, `storageBucket`, `messagingSenderId`, and `appId`. You can obtain this config at any time from the Firebase console. 
3) Copy values into `apps/dashboard/.env.local` via `env/dashboard.env`.

### Firebase Admin credentials (API)
1) Use Application Default Credentials and set `GOOGLE_APPLICATION_CREDENTIALS` to your service account JSON path. 
2) Place the JSON file on the API host and point the env var to that path.

Why this is used: the Firebase Admin SDK expects a service account for server-to-server access.
Client IDs/secrets are for OAuth flows, not Admin SDK operations.

### Binance API key (engine)
1) Create API keys in the Binance **API Management** page of your account. 
2) API keys can be configured with specific permissions (e.g., trading endpoints). 
3) Binance recommends IP restrictions for API keys. 

Recommended safety settings:
- Use spot-only permissions as needed for trading.
- Do NOT enable withdrawals on the trading key.
- Restrict IPs to your VPS if possible.

### MASTER_KEY (API encryption)
Generate a 32-byte hex key (64 hex chars):

```powershell
python - <<'PY'
import secrets
print(secrets.token_hex(32))
PY
```

Note: the engine also uses MASTER_KEY to decrypt active exchange keys stored in Postgres.

### CryptoPanic API key (news pause - optional until ingestion is wired)
1) Create a CryptoPanic account and generate an API key.
2) Set `CRYPTOPANIC_API_KEY` in `services/api/.env` or `env/api.env`.
3) This will be used once automated news ingestion is implemented (currently the API expects manual ingestion via `/v1/news/ingest`).

### Alpha Vantage API key (future backtesting)
1) Create an Alpha Vantage account and generate an API key.
2) Set `ALPHA_VANTAGE_API_KEY` in `services/engine/.env` or `env/engine.env`.
3) This is not required for the Binance crypto MVP; it will be used for equities/forex backtests later.


## References
- https://firebase.google.com/docs/web/setup
- https://firebase.google.com/docs/app-engine/tutorials/identity-platform
- https://cloud.google.com/docs/authentication/application-default-credentials
- https://developers.binance.com/docs/binance-spot-api-docs/rest-api/general-api-information
- https://developers.binance.com/docs/binance-spot-api-docs/testnet/rest-api
- https://cryptopanic.com/developers/api/
- https://www.alphavantage.co/support/#api-key

## Notes
- Do not store real secrets in public repos.
- Local .env files are gitignored; set production values in VPS and Vercel environment settings.
- `DATABASE_URL` and `REDIS_URL` should match local Docker Compose settings unless using remote services.
- Use the `postgresql+psycopg://` driver prefix with psycopg3.
- `NEXT_PUBLIC_WS_URL` is optional; if omitted, the dashboard derives it from `NEXT_PUBLIC_API_URL`.
