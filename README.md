# Contact Forecasting

A full-stack web application for forecasting contact centre volumes by channel.
Built with **FastAPI** (backend) + **React/TypeScript** (frontend), deployed on DigitalOcean with Docker Compose and automatic SSL via Let's Encrypt.

---

## Architecture

```
nginx (80/443) ──► frontend  (React SPA, served by nginx:alpine)
               ──► backend   (FastAPI + Holt-Winters, port 8000)
                       └──► db (PostgreSQL 16)
certbot         (auto-renews Let's Encrypt certs every 12 h)
```

---

## Local Development

### Prerequisites

- Docker 24+ with Compose v2 plugin
- Node 20+ (for frontend hot-reload)

### 1 — Start the database and backend

```bash
cp .env.example .env          # fill in DB_PASSWORD (other vars optional locally)
docker compose up db backend  # PostgreSQL + FastAPI on :8000
```

API docs: <http://localhost:8000/api/v1/docs>

### 2 — Start the frontend (hot-reload)

```bash
cd frontend
npm install
npm run dev                   # Vite dev server on :5173, proxies /api → :8000
```

Open <http://localhost:5173>

---

## Production Deployment (DigitalOcean Droplet)

### Prerequisites

| Item | Notes |
|------|-------|
| Droplet | Ubuntu 22.04, 2 vCPU / 4 GB RAM minimum |
| Domain | A/AAAA record pointing to the Droplet IP |
| SSH access | Root key loaded in your local `ssh-agent` |

### One-time setup

Export the required variables locally, then run `deploy.sh`:

```bash
export DOMAIN=forecasting.example.com
export CERTBOT_EMAIL=admin@example.com
export DB_PASSWORD=your_strong_password_here
export SERVER_IP=<droplet-ip>

bash deploy.sh
```

`deploy.sh` will:

1. Install Docker (CE + Compose plugin) on the Droplet
2. Configure UFW — opens ports 22, 80, 443
3. Clone this repository to `/opt/forecasting`
4. Write `/opt/forecasting/.env`
5. Obtain an initial SSL certificate via Certbot standalone mode
6. Build and start the production stack (`docker-compose.prod.yml`)

### Continuous deployment (GitHub Actions)

Every push to `main` triggers `.github/workflows/deploy.yml`, which SSH-es into the Droplet, pulls the latest code, rebuilds the `backend` and `frontend` images, and restarts all services (`up -d --remove-orphans`).

#### Required GitHub repository secrets

| Secret | Value |
|--------|-------|
| `DO_HOST` | Droplet IP or hostname |
| `DO_USER` | SSH user (e.g. `root`) |
| `DO_SSH_KEY` | Private SSH key (PEM, no passphrase) |

Add them at **Settings → Secrets and variables → Actions → New repository secret**.

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DOMAIN` | Prod only | Public domain name (e.g. `forecasting.example.com`) |
| `DB_USER` | Yes | PostgreSQL username |
| `DB_PASSWORD` | Yes | PostgreSQL password |
| `DB_NAME` | Yes | PostgreSQL database name |
| `DATABASE_URL` | Yes | Async URL for FastAPI (`postgresql+asyncpg://...`) |
| `SYNC_DATABASE_URL` | Yes | Sync URL for Alembic (`postgresql+psycopg2://...`) |
| `CORS_ORIGINS` | Yes | JSON array of allowed origins |
| `CERTBOT_EMAIL` | Prod only | Email for Let's Encrypt notifications |
| `UPLOAD_MAX_MB` | No | Max upload size in MB (default: 50) |

See `.env.example` for a complete template.

---

## Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── api/v1/          # FastAPI route handlers
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── services/        # Business logic (upload, training, forecasts)
│   │   └── main.py
│   ├── alembic/             # Database migrations
│   ├── forecasting_engine.py
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api/             # Typed API client (axios)
│   │   ├── components/      # Reusable UI + chart components
│   │   ├── hooks/           # TanStack Query hooks (with polling)
│   │   ├── pages/           # Dashboard, Forecasts, Analysis, Settings, Export
│   │   └── store/           # Zustand global state (persisted)
│   ├── nginx.conf
│   └── Dockerfile
├── nginx/
│   └── default.conf.template  # envsubst template (DOMAIN substituted at runtime)
├── docker-compose.yml         # Local development
├── docker-compose.prod.yml    # Production stack
├── deploy.sh                  # Initial Droplet setup script
└── .env.example
```

---

## Forecasting Model

Each channel is fitted with **Holt-Winters Exponential Smoothing**:

- **Outlier handling** — IQR winsorization before fitting (caps extremes at Q1−1.5×IQR / Q3+1.5×IQR)
- **Auto-selection** — tries `(mul, mul)`, `(add, mul)`, `(mul, add)`, `(add, add)`; picks lowest AIC; falls back to trend-only if all seasonal configs fail
- **Confidence intervals** — simulation-based (1 000 Monte-Carlo draws); 2.5th / 97.5th percentile bands
- **Monthly seasonality** — applied as multiplicative factors on top of the daily Holt-Winters output

Training runs asynchronously; the UI polls `GET /api/v1/training/{job_id}` every 2 seconds until complete.

---

## Manual Operations

### Run database migrations

```bash
docker compose exec backend alembic upgrade head
```

### View logs

```bash
# Production
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f nginx
```

### Force SSL renewal

```bash
docker compose -f docker-compose.prod.yml exec certbot certbot renew --force-renewal
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload
```
