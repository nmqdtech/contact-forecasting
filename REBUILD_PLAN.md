# Full-Stack Rebuild Plan
## Contact Volume Forecasting: Streamlit → FastAPI + React + PostgreSQL

---

## 1. Current Stack Assessment

| Layer | Current | Problem |
|---|---|---|
| UI | Streamlit 1.31 | No real-time updates, slow theme toggle, limited UX control |
| Logic | `forecasting_engine.py` (standalone class) | Already well-modularised — moves cleanly to backend service |
| State | `st.session_state` (in-memory, per-user, lost on refresh) | No persistence; every user starts from scratch |
| Storage | Temp files in `/tmp/` | Lost on container restart |
| Database | None | No history, no multi-user support |
| API | None (Streamlit handles everything) | No external integrations possible |

**What we keep:** `forecasting_engine.py` (the `ContactForecaster` class) is well-written and moves to `backend/app/core/` **unchanged**. All forecasting IP is preserved.

---

## 2. Target Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                          nginx (port 80/443)                     │
│                   SSL termination + reverse proxy                │
└────────────────────┬─────────────────────┬───────────────────────┘
                     │                     │
          /api/*  ───┘            /  ──────┘
                     │                     │
        ┌────────────▼──────┐   ┌──────────▼──────────┐
        │  FastAPI backend  │   │   React frontend    │
        │  Python 3.11      │   │   Vite + TypeScript │
        │  port 8000        │   │   port 3000 (dev)   │
        └────────┬──────────┘   └─────────────────────┘
                 │
        ┌────────▼──────────┐
        │    PostgreSQL 15  │
        │    port 5432      │
        └───────────────────┘
```

---

## 3. New Folder Structure

```
contact-forecasting/                     ← repo root
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   │       └── 0001_initial_schema.py
│   └── app/
│       ├── main.py                      # FastAPI app, CORS, lifespan, router mount
│       ├── config.py                    # Settings from env vars (pydantic-settings)
│       │
│       ├── core/                        # Pure forecasting logic — no HTTP, no DB
│       │   ├── forecasting_engine.py    # ← MOVED UNCHANGED from repo root
│       │   ├── data_processor.py        # Excel parsing, column validation
│       │   └── export_service.py        # Build Excel download bytes
│       │
│       ├── api/
│       │   └── v1/
│       │       ├── router.py            # Mounts all sub-routers under /api/v1
│       │       ├── uploads.py           # POST  /uploads
│       │       ├── channels.py          # GET   /channels
│       │       │                        # GET   /channels/{channel}/data
│       │       ├── training.py          # POST  /training
│       │       │                        # GET   /training/{job_id}
│       │       ├── forecasts.py         # GET   /forecasts/{channel}
│       │       │                        # GET   /forecasts/{channel}/monthly
│       │       │                        # GET   /forecasts/{channel}/backtest
│       │       │                        # POST  /forecasts/{channel}/regenerate
│       │       ├── seasonality.py       # GET   /seasonality/{channel}
│       │       ├── config.py            # GET   /config
│       │       │                        # PUT   /config/holidays
│       │       │                        # PUT   /config/targets
│       │       ├── summary.py           # GET   /summary
│       │       └── exports.py           # GET   /exports/forecasts
│       │                                # GET   /exports/summary
│       │
│       ├── db/
│       │   └── database.py              # SQLAlchemy async engine + session factory
│       │
│       ├── models/                      # SQLAlchemy ORM table definitions
│       │   ├── dataset.py
│       │   ├── observation.py
│       │   ├── channel_config.py
│       │   ├── monthly_target.py
│       │   ├── training_run.py
│       │   ├── forecast.py
│       │   └── backtest_result.py
│       │
│       ├── schemas/                     # Pydantic v2 request/response models
│       │   ├── upload.py
│       │   ├── channel.py
│       │   ├── training.py
│       │   ├── forecast.py
│       │   └── config.py
│       │
│       └── services/                    # Orchestration (DB + core logic)
│           ├── forecasting_service.py   # Wraps ContactForecaster, persists results
│           ├── channel_service.py       # Channel data CRUD
│           └── config_service.py        # Holiday / target config CRUD
│
├── frontend/
│   ├── Dockerfile
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── src/
│       ├── main.tsx
│       ├── App.tsx                      # Router + ThemeProvider
│       │
│       ├── api/                         # Typed API layer (axios + React Query)
│       │   ├── client.ts                # Axios instance with base URL + interceptors
│       │   ├── uploads.ts
│       │   ├── channels.ts
│       │   ├── training.ts
│       │   ├── forecasts.ts
│       │   └── config.ts
│       │
│       ├── components/
│       │   ├── layout/
│       │   │   ├── AppShell.tsx         # Sidebar + main content wrapper
│       │   │   ├── Sidebar.tsx
│       │   │   ├── Header.tsx
│       │   │   └── ThemeToggle.tsx      # Instant CSS-variable toggle (no page reload)
│       │   ├── charts/
│       │   │   ├── ForecastChart.tsx    # Daily line + CI band
│       │   │   ├── MonthlyChart.tsx     # Grouped bar: historical vs forecast
│       │   │   ├── BacktestChart.tsx    # Actual vs predicted holdout
│       │   │   └── SeasonalityChart.tsx # Monthly factor bars + weekly DOW
│       │   └── ui/                      # Reusable primitives (shadcn/ui base)
│       │       ├── Button.tsx
│       │       ├── Card.tsx
│       │       ├── Badge.tsx
│       │       ├── MetricCard.tsx
│       │       ├── ProgressBar.tsx
│       │       └── FileUploader.tsx
│       │
│       ├── pages/
│       │   ├── Dashboard.tsx            # Upload + train + KPI overview
│       │   ├── Forecasts.tsx            # Daily + monthly + backtest charts
│       │   ├── Analysis.tsx             # Seasonality + week comparison
│       │   ├── Settings.tsx             # Bank holidays + monthly targets config
│       │   └── Export.tsx               # Download buttons + summary table
│       │
│       ├── hooks/                       # TanStack Query wrappers
│       │   ├── useChannels.ts
│       │   ├── useForecasts.ts
│       │   ├── useTraining.ts           # Polls training job status
│       │   └── useConfig.ts
│       │
│       ├── store/
│       │   └── useAppStore.ts           # Zustand: active dataset, theme, channel selection
│       │
│       └── types/
│           └── index.ts                 # All shared TypeScript interfaces
│
├── nginx/
│   └── nginx.conf                       # Serves frontend, proxies /api to backend
│
├── docker-compose.yml                   # Development (hot-reload, open ports)
├── docker-compose.prod.yml              # Production (no exposed internal ports)
├── .env.example
└── README.md
```

---

## 4. API Endpoints

All routes are prefixed `/api/v1/`.

### 4.1 Uploads

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/uploads` | Upload Excel file (multipart). Parses, validates, inserts observations. Returns dataset metadata. |
| `GET`  | `/uploads` | List past uploads with metadata. |
| `DELETE` | `/uploads/{dataset_id}` | Soft-delete a dataset (sets `is_active=false`). |

**POST /uploads response:**
```json
{
  "dataset_id": "uuid",
  "filename": "historical_data.xlsx",
  "row_count": 1648,
  "channels": ["Calls", "Emails", "Chats", "Messages"],
  "date_min": "2024-01-01",
  "date_max": "2025-02-15"
}
```

---

### 4.2 Channels

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/channels` | List all channels with row count + date range. |
| `GET` | `/channels/{channel}/data` | Daily observations. Query params: `?from=YYYY-MM-DD&to=YYYY-MM-DD&granularity=daily\|monthly` |

---

### 4.3 Training (background job)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/training` | Start training all channels. Returns `job_id`. Runs as FastAPI `BackgroundTask`. |
| `GET`  | `/training/{job_id}` | Poll training status. Used by frontend to show per-channel progress. |

**POST /training body:**
```json
{
  "dataset_id": "uuid",
  "channels": ["Calls", "Emails"],
  "months_ahead": 15
}
```

**GET /training/{job_id} response:**
```json
{
  "job_id": "uuid",
  "status": "running",
  "progress": 0.5,
  "results": [
    {
      "channel": "Calls",
      "status": "completed",
      "config": ["add", "add", true],
      "aic": 3412.1,
      "message": "AIC=3412.1"
    },
    {
      "channel": "Emails",
      "status": "pending"
    }
  ]
}
```

---

### 4.4 Forecasts

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/forecasts/{channel}` | Full daily forecast (450 rows). Includes model metadata. |
| `GET` | `/forecasts/{channel}/monthly` | Monthly aggregated totals + CI for historical and forecast. |
| `GET` | `/forecasts/{channel}/backtest` | Backtest metrics + data. Query param: `?holdout_days=60` |
| `POST` | `/forecasts/{channel}/regenerate` | Trigger re-forecast (e.g. after config change). Background task. |

**GET /forecasts/{channel} response:**
```json
{
  "channel": "Calls",
  "model": {
    "config": ["add", "add", true],
    "aic": 3412.1,
    "backtest_mape": 7.3,
    "monthly_factors": {"1": 0.99, "6": 0.867, "11": 1.27}
  },
  "data": [
    {"date": "2025-02-16", "yhat": 1082.4, "yhat_lower": 941.2, "yhat_upper": 1223.6},
    ...
  ]
}
```

**GET /forecasts/{channel}/monthly response:**
```json
{
  "historical": [
    {"month": "2024-01", "total": 33558}
  ],
  "forecast": [
    {"month": "2025-03", "total": 35200, "lower": 30800, "upper": 39600}
  ]
}
```

**GET /forecasts/{channel}/backtest response:**
```json
{
  "metrics": {"mape": 7.3, "mae": 82.1, "rmse": 104.5, "holdout_days": 60},
  "data": [
    {"date": "2024-12-17", "actual": 1480, "predicted": 1352, "error_pct": 8.6}
  ]
}
```

---

### 4.5 Configuration

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/config` | Return current holiday and target config for all channels. |
| `PUT` | `/config/holidays` | Set or update holiday country for a channel. |
| `DELETE` | `/config/holidays/{channel}` | Remove holiday config for a channel. |
| `PUT` | `/config/targets` | Upsert monthly volume targets for a channel. |
| `DELETE` | `/config/targets/{channel}` | Remove all targets for a channel. |

**PUT /config/holidays body:**
```json
{"channel": "Calls", "country_code": "GB"}
```

**PUT /config/targets body:**
```json
{
  "channel": "Calls",
  "targets": {"2026-03": 35000, "2026-04": 36000, "2026-05": 34000}
}
```

---

### 4.6 Seasonality & Analysis

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/seasonality/{channel}` | Monthly factors + decomposed weekly DOW pattern. |
| `GET` | `/analysis/weeks` | Week-over-week comparison. Query params: `?channel=X&weeks=1,10,20&years=2024,2025` |
| `GET` | `/summary` | Aggregated summary table across all trained channels. |

---

### 4.7 Exports

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/exports/forecasts` | Excel download: one sheet per channel with daily forecast. |
| `GET` | `/exports/summary` | Excel download: summary table. |

---

## 5. Database Schema

PostgreSQL 15. All UUIDs use `gen_random_uuid()`.

```sql
-- ── Datasets ────────────────────────────────────────────────────────────────
CREATE TABLE datasets (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    filename    VARCHAR(255) NOT NULL,
    upload_ts   TIMESTAMPTZ DEFAULT NOW(),
    row_count   INTEGER,
    date_min    DATE,
    date_max    DATE,
    is_active   BOOLEAN     DEFAULT TRUE
);

-- ── Historical observations ─────────────────────────────────────────────────
CREATE TABLE channel_observations (
    id          BIGSERIAL   PRIMARY KEY,
    dataset_id  UUID        NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    channel     VARCHAR(100) NOT NULL,
    obs_date    DATE        NOT NULL,
    volume      NUMERIC(12,2) NOT NULL,
    UNIQUE (dataset_id, channel, obs_date)
);
CREATE INDEX idx_obs_channel_date ON channel_observations (channel, obs_date);

-- ── Per-channel holiday config ───────────────────────────────────────────────
CREATE TABLE channel_configs (
    id           UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    channel      VARCHAR(100) NOT NULL UNIQUE,
    country_code VARCHAR(10),                  -- NULL = no holidays
    updated_at   TIMESTAMPTZ  DEFAULT NOW()
);

-- ── Monthly volume targets ──────────────────────────────────────────────────
CREATE TABLE monthly_targets (
    id         UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    channel    VARCHAR(100) NOT NULL,
    month      CHAR(7)      NOT NULL,          -- 'YYYY-MM'
    volume     NUMERIC(14,2) NOT NULL,
    updated_at TIMESTAMPTZ  DEFAULT NOW(),
    UNIQUE (channel, month)
);

-- ── Training jobs ────────────────────────────────────────────────────────────
CREATE TABLE training_runs (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id          UUID         NOT NULL,     -- groups channels trained together
    channel         VARCHAR(100) NOT NULL,
    dataset_id      UUID         REFERENCES datasets(id),
    status          VARCHAR(20)  DEFAULT 'pending',  -- pending|running|completed|failed
    months_ahead    INTEGER      DEFAULT 15,
    -- Model output
    model_config    JSONB,        -- ["add","add",true]
    aic             NUMERIC(12,4),
    monthly_factors JSONB,        -- {"1":0.99,"6":0.867,...}
    error_message   TEXT,
    -- Timing
    created_at      TIMESTAMPTZ  DEFAULT NOW(),
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    -- Only one active run per channel
    is_active       BOOLEAN      DEFAULT TRUE
);
CREATE INDEX idx_training_job     ON training_runs (job_id);
CREATE INDEX idx_training_channel ON training_runs (channel, is_active);

-- ── Forecast rows ───────────────────────────────────────────────────────────
CREATE TABLE forecasts (
    id              BIGSERIAL    PRIMARY KEY,
    training_run_id UUID         NOT NULL REFERENCES training_runs(id) ON DELETE CASCADE,
    channel         VARCHAR(100) NOT NULL,
    forecast_date   DATE         NOT NULL,
    yhat            NUMERIC(12,2),
    yhat_lower      NUMERIC(12,2),
    yhat_upper      NUMERIC(12,2),
    UNIQUE (training_run_id, channel, forecast_date)
);
CREATE INDEX idx_forecasts_channel_date ON forecasts (channel, forecast_date);

-- ── Backtest result cache ────────────────────────────────────────────────────
CREATE TABLE backtest_results (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    training_run_id UUID         NOT NULL REFERENCES training_runs(id) ON DELETE CASCADE,
    channel         VARCHAR(100) NOT NULL,
    holdout_days    INTEGER      NOT NULL,
    mape            NUMERIC(8,4),
    mae             NUMERIC(12,4),
    rmse            NUMERIC(12,4),
    data            JSONB,        -- [{date, actual, predicted, error_pct}] for chart
    created_at      TIMESTAMPTZ  DEFAULT NOW(),
    UNIQUE (training_run_id, channel, holdout_days)
);
```

---

## 6. Technology Choices

### Backend
| Package | Version | Purpose |
|---------|---------|---------|
| `fastapi` | 0.111 | Web framework |
| `uvicorn[standard]` | 0.30 | ASGI server |
| `sqlalchemy[asyncio]` | 2.0 | ORM (async) |
| `asyncpg` | 0.29 | Async PostgreSQL driver |
| `alembic` | 1.13 | DB migrations |
| `pydantic-settings` | 2.x | Config from env vars |
| `python-multipart` | 0.0.9 | File upload parsing |
| `statsmodels` | 0.14.1 | Holt-Winters (unchanged) |
| `pandas` | 2.1.4 | Data processing (unchanged) |
| `numpy` | 1.26.3 | Numerics (unchanged) |
| `holidays` | 0.42 | Bank holidays (unchanged) |
| `openpyxl` | 3.1.2 | Excel read/write (unchanged) |

### Frontend
| Package | Purpose |
|---------|---------|
| `react` 18 + `react-dom` | UI framework |
| `vite` | Build tool + dev server |
| `typescript` | Type safety |
| `tailwindcss` | Utility CSS (instant theme toggle via CSS variables) |
| `@tanstack/react-query` | Server state, caching, background refetch |
| `axios` | HTTP client |
| `zustand` | Minimal client state (active channel, theme) |
| `recharts` | Charts (ForecastChart, MonthlyChart, BacktestChart) |
| `react-router-dom` v6 | Client-side routing |
| `@radix-ui/react-*` | Accessible UI primitives (shadcn/ui base) |
| `lucide-react` | Icons |

### Infrastructure
| Component | Choice |
|-----------|--------|
| Database | PostgreSQL 15 (DigitalOcean Managed DB or containerised) |
| Reverse proxy | nginx (static files + `/api` proxy) |
| Container registry | DigitalOcean Container Registry |
| Orchestration | Docker Compose (single Droplet) or DO App Platform |

---

## 7. Docker Compose Structure

```yaml
# docker-compose.prod.yml
services:

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: forecasting
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]
      interval: 10s
      retries: 5

  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@db:5432/forecasting
      CORS_ORIGINS: https://your-domain.com
    depends_on:
      db:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s

  frontend:
    build: ./frontend
    # nginx serves built static files + proxies /api to backend

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - certbot_certs:/etc/letsencrypt:ro
    depends_on:
      - backend
      - frontend

volumes:
  postgres_data:
  certbot_certs:
```

---

## 8. Implementation Phases

### Phase 1 — Backend foundation (no frontend)
1. Set up `backend/` with FastAPI + SQLAlchemy + Alembic
2. Move `forecasting_engine.py` → `backend/app/core/`
3. Implement DB models + Alembic migration
4. Implement `POST /uploads`, `GET /channels`, `POST /training`, `GET /training/{job_id}`
5. Implement `GET /forecasts/{channel}`, `/monthly`, `/backtest`
6. Implement config endpoints + exports
7. Add `docker-compose.yml` for backend + postgres
8. **Verify:** test all endpoints with curl / Postman

### Phase 2 — React frontend scaffold
1. Init Vite + TypeScript + Tailwind project in `frontend/`
2. Set up routing, AppShell, Sidebar, ThemeToggle
3. Build typed API client layer
4. Dashboard page: file upload → training progress → channel list
5. Forecasts page: daily chart + monthly chart + backtest expander
6. Settings page: holidays + monthly targets forms
7. Analysis + Export pages
8. **Verify:** end-to-end flow with sample Excel files

### Phase 3 — Production hardening
1. nginx config with SSL + static file serving
2. `docker-compose.prod.yml`
3. Environment variable management (`.env.example`)
4. Alembic migration in container entrypoint
5. DigitalOcean Droplet or App Platform deployment
6. Health checks + logging

---

## 9. Key Architectural Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Async backend | FastAPI + asyncpg | Non-blocking DB; training runs as background tasks |
| Model storage | JSONB config in DB; re-train on demand | Pickle of statsmodels objects is fragile across versions |
| Training job pattern | `job_id` + poll `/training/{job_id}` | Simple; no Redis/Celery needed for single-server deploy |
| Frontend charts | Recharts | Smaller bundle than Plotly; Tailwind-compatible |
| Theme system | CSS custom properties on `:root` toggled by Tailwind `dark:` class | Instant toggle — no page reload, no API call |
| DB per-channel index | `(channel, obs_date)` composite | Forecast queries always filter by channel + date range |
| Backtest caching | `backtest_results` table | Expensive to recompute; served from cache after first call |

---

## 10. Environment Variables

```bash
# .env.example
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/forecasting
DB_USER=forecasting
DB_PASSWORD=change_me
SECRET_KEY=change_me_32_chars_minimum
CORS_ORIGINS=http://localhost:3000
UPLOAD_MAX_MB=50
```

---

*Ready to implement. Start with Phase 1 — say **"implement Phase 1"** to begin.*
