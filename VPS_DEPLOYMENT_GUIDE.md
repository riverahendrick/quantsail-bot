# Quantsail — VPS Production Deployment Guide

> **Target**: Ubuntu 22.04+ VPS with Docker and Docker Compose installed.
> **Components**: Engine, API, PostgreSQL, Redis, Nginx (with SSL via Let's Encrypt).
> **Dashboard**: Deployed separately on Vercel (no secrets stored there).

---

## Prerequisites

| Requirement | Minimum |
|-------------|---------|
| Ubuntu | 22.04 LTS or later |
| Docker | 24.0+ |
| Docker Compose | v2 (included with Docker) |
| RAM | 2 GB |
| Disk | 20 GB SSD |
| Domain | Pointed to VPS IP (A record) |

### Install Docker (if not installed)

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Log out and back in for group change to take effect
```

---

## Step 1: Clone the Repository

```bash
cd /opt
git clone https://github.com/riverahendrick/quantsail-bot.git
cd quantsail-bot
```

---

## Step 2: Configure Environment Variables

Create a `.env` file in `infra/docker/`:

```bash
cp infra/docker/.env.example infra/docker/.env
nano infra/docker/.env
```

Fill in all required values:

```env
# ── Database ───────────────────────────────────────────────
POSTGRES_USER=quantsail
POSTGRES_PASSWORD=<generate-strong-password>
POSTGRES_DB=quantsail

# ── API ────────────────────────────────────────────────────
MASTER_KEY=<run: python3 -c "import secrets; print(secrets.token_hex(32))">
GOOGLE_APPLICATION_CREDENTIALS=/path/to/firebase-service-account.json

# ── Optional ───────────────────────────────────────────────
CRYPTOPANIC_API_KEY=<your-key-or-leave-blank>
```

### Generate MASTER_KEY

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### Firebase Service Account

1. Go to Firebase Console → Project Settings → Service Accounts
2. Click **"Generate New Private Key"**
3. Save the JSON file on the VPS (e.g., `/opt/quantsail-bot/secrets/firebase.json`)
4. Set `GOOGLE_APPLICATION_CREDENTIALS` to that path

---

## Step 3: Configure Nginx Domain

Edit `infra/docker/nginx.conf` and replace all instances of `YOUR_DOMAIN`:

```bash
sed -i 's/YOUR_DOMAIN/api.yourdomain.com/g' infra/docker/nginx.conf
```

---

## Step 4: Initial SSL Certificate

Start nginx temporarily for the ACME challenge:

```bash
cd infra/docker

# Start only nginx (HTTP mode) to get the initial certificate
docker compose up -d nginx

# Get the certificate
docker compose run --rm certbot certonly \
  --webroot -w /var/www/certbot \
  -d api.yourdomain.com \
  --email your@email.com \
  --agree-tos \
  --no-eff-email

# Stop nginx
docker compose down
```

---

## Step 5: Run Database Migrations

```bash
cd /opt/quantsail-bot/infra/docker

# Start only Postgres
docker compose up -d postgres

# Wait for it to be healthy
docker compose exec postgres pg_isready -U quantsail

# Run Alembic migrations from the API container
docker compose run --rm api uv run alembic upgrade head

# Stop Postgres (the full stack start will bring it back)
docker compose down
```

---

## Step 6: Start All Services

```bash
cd /opt/quantsail-bot/infra/docker
docker compose up -d
```

Verify everything is running:

```bash
docker compose ps
```

You should see all services as `Up (healthy)`:

| Service | Port | Status |
|---------|------|--------|
| postgres | 5432 | healthy |
| redis | 6379 | healthy |
| api | 8000 | healthy |
| engine | - | healthy |
| nginx | 80, 443 | running |
| certbot | - | running |

Test the API:

```bash
curl https://api.yourdomain.com/public/v1/heartbeat
# Should return: {"status": "ok"}
```

---

## Step 7: Configure Automated Backups

```bash
# Make the backup script executable
chmod +x /opt/quantsail-bot/infra/scripts/backup.sh

# Create backup directory
mkdir -p /var/backups/quantsail

# Add to crontab (runs every 6 hours)
(crontab -l 2>/dev/null; echo "0 */6 * * * POSTGRES_HOST=localhost POSTGRES_PORT=5433 /opt/quantsail-bot/infra/scripts/backup.sh") | crontab -

# Verify cron entry
crontab -l
```

---

## Step 8: Deploy Dashboard to Vercel

The Next.js dashboard is deployed separately on Vercel.

1. Connect the repo to Vercel
2. Set the root directory to `apps/dashboard`
3. Add environment variables in Vercel dashboard:

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_URL` | `https://api.yourdomain.com` |
| `NEXT_PUBLIC_WS_URL` | `wss://api.yourdomain.com/ws` |
| `NEXT_PUBLIC_FIREBASE_API_KEY` | Your Firebase web API key |
| `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN` | `yourproject.firebaseapp.com` |
| `NEXT_PUBLIC_FIREBASE_PROJECT_ID` | Your Firebase project ID |
| `USE_MOCK_DATA` | `false` |

4. Deploy

---

## Monitoring & Operations

### View logs

```bash
cd /opt/quantsail-bot/infra/docker

# All services
docker compose logs -f

# Specific service
docker compose logs -f engine
docker compose logs -f api
```

### Restart a service

```bash
docker compose restart engine
docker compose restart api
```

### Update to latest code

```bash
cd /opt/quantsail-bot
git pull origin main

cd infra/docker
docker compose build
docker compose up -d
```

### Restore from backup

```bash
# Find available backups
ls -la /var/backups/quantsail/

# Restore (stop engine first to prevent conflicts)
docker compose stop engine
gunzip -c /var/backups/quantsail/quantsail_20260312_120000.sql.gz | \
  docker compose exec -T postgres pg_restore -U quantsail -d quantsail --no-owner --clean
docker compose start engine
```

### SSL certificate renewal

Certbot auto-renews via the certbot container. To manually renew:

```bash
docker compose run --rm certbot renew
docker compose exec nginx nginx -s reload
```

---

## Security Checklist

- [ ] Firewall: Only ports 80, 443, and 22 (SSH) open
- [ ] SSH: Key-based auth only (disable password auth)
- [ ] Binance API key: IP-restricted to VPS IP
- [ ] Binance API key: Spot-only permissions, NO withdrawals
- [ ] MASTER_KEY: Unique, stored only in `.env` (never committed)
- [ ] Firebase service account JSON: Not in Git
- [ ] `.env` file: Permissions set to `600` (`chmod 600 .env`)
- [ ] Backups: Verified cron is running and backups are being created
- [ ] Monitoring: Set up uptime monitoring (e.g., UptimeRobot for the health endpoint)

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         VPS                                  │
│                                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐               │
│  │  Nginx   │───▶│   API    │───▶│ Postgres │               │
│  │ (SSL+WS) │    │(FastAPI) │    │          │               │
│  └──────────┘    └──────────┘    └──────────┘               │
│       │               │              │                       │
│       │               ▼              │                       │
│       │          ┌──────────┐        │                       │
│       │          │  Redis   │        │                       │
│       │          └──────────┘        │                       │
│       │               ▲              │                       │
│       │               │              │                       │
│       │          ┌──────────┐        │                       │
│       │          │  Engine  │───────▶│                       │
│       │          │(Trading) │        │                       │
│       │          └──────────┘        │                       │
│       │                                                      │
└───────│──────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────┐         ┌──────────────┐
│   Vercel     │         │   Binance    │
│ (Dashboard)  │         │  (Exchange)  │
└──────────────┘         └──────────────┘
```
