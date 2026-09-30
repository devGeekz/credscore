# CredScore

Alternative-credit scoring for African micro-merchants. Lenders upload a merchant's
mobile-money / bank statement export, and CredScore parses the transactions, computes a
0–100 score with a risk band, and returns a full report (cash flow, consistency,
expenses, suggested limit) — plus a lender dashboard, outbound webhooks, and a WhatsApp
consent/statement flow.

## Architecture

```
   lender staff                     WhatsApp customers
        │                                │
        ▼                                ▼
┌───────────────────┐          ┌──────────────────────┐
│ Next.js dashboard │          │ WhatsApp Cloud API   │
│ (frontend/)       │          │ inbound webhook ─────┐
└─────────┬─────────┘          └──────────────────────┘
          │ REST + JWT                    │
          ▼                               ▼
┌─────────────────────────────────────────────────────┐
│ FastAPI  backend/app                                │
│  routers: auth · merchants · statements · reports   │
│           settings · webhooks · dashboard           │
│  audit middleware · rate limits · security headers  │
└──────┬──────────────┬───────────────┬───────────────┘
       │              │               │
       ▼              ▼               ▼
┌────────────┐  ┌─────────────┐  ┌──────────────────────┐
│ Postgres   │  │ Object store│  │ Redis + Celery       │
│ (Neon)     │  │ S3/R2/local │  │ parse + webhook tasks│
└────────────┘  └─────────────┘  └─────────────────────┘
                                      │
                 without Redis: tasks run inline in dev
```

## Local setup

Requires Python 3.13, Node 22. Redis and S3 are optional in dev.

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows; on unix: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env        # set DATABASE_URL (Neon or local postgres)
alembic upgrade head
uvicorn app.main:app --reload  # http://localhost:8000
```

### Frontend

```bash
cd frontend
npm install
copy .env.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev                    # http://localhost:3000
```

### Worker (optional in dev)

With no Redis, statement parsing and webhook delivery run inline when you upload —
functionally identical, just synchronous. To run them as background tasks:

```bash
# start redis, set RATE_LIMIT_STORAGE_URI= (empty) and REDIS_URL in backend/.env
celery -A app.workers.celery_app worker -l info
```

## Environment variables

`backend/.env.example` (synced with `app/config.py`):

| var | default | notes |
|---|---|---|
| `DATABASE_URL` | — (required) | postgres, e.g. Neon with `?sslmode=require` |
| `REDIS_URL` | `redis://localhost:6379` | broker for celery |
| `RATE_LIMIT_STORAGE_URI` | `""` | `memory://` in dev without redis |
| `JWT_SECRET` | — (required) | long random string |
| `JWT_EXPIRES_IN` | `7d` | |
| `ENVIRONMENT` | `development` | `production` enables HSTS + SSRF guard |
| `APP_URL` | `http://localhost:8000` | public API URL |
| `CORS_ORIGINS` | `""` | comma-separated; prod = your Vercel URL(s) |
| `SENTRY_DSN` | `""` | empty = Sentry disabled |
| `WEBHOOK_SIGNING_SECRET` | `dev-secret` | HMAC key for `X-CredScore-Signature` |
| `STORAGE_BUCKET` | `""` | empty = files go to `backend/storage/` |
| `STORAGE_ENDPOINT` / `STORAGE_ACCESS_KEY` / `STORAGE_SECRET_KEY` | `""` | S3/R2-compatible |
| `WHATSAPP_API_TOKEN` / `WHATSAPP_PHONE_NUMBER_ID` / `WHATSAPP_VERIFY_TOKEN` | `""` | optional |

`frontend/.env.example`: `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_APP_NAME`.

## API walkthrough

All routes are under `/api/v1` except `GET /health`. Auth: `POST /auth/register` or
`POST /auth/login` → `access_token`; send `Authorization: Bearer <token>`.

| group | endpoints |
|---|---|
| auth | `register`, `login`, `me`, api-keys: `GET/POST/DELETE /auth/api-keys` |
| merchants | `GET/POST /merchants`, `GET /merchants/{id}` |
| statements | `POST /statements/upload` (multipart `merchant_id` + `file`, 20/min), `GET /statements`, `GET /statements/{id}`, `POST /statements/{id}/requeue` (202 / 409), `GET /statements/{id}/download` |
| reports | `GET /reports`, `GET /reports/{id}`, `GET /reports/export` (CSV) |
| dashboard | `GET /dashboard/stats`, `GET /dashboard/consent-export` (consent audit CSV) |
| settings | `GET/PUT /settings` (org, plan, webhook URL/secret), `GET /settings/webhooks` (delivery history) |
| webhooks | `GET/POST /webhooks/whatsapp` (Cloud API verify + inbound) |
| health | `GET /health` |

Outbound: after each score the API POSTs `score.completed` to the tenant's configured
URL, signed `X-CredScore-Signature: sha256=HMAC_SHA256(secret, raw_body)`, 3 attempts.

## Testing

```bash
cd backend
.venv\Scripts\python.exe -m pytest   # 30 tests, sqlite fixture db

cd frontend
npm run lint
npx next build
```

Tests never touch Neon: a fixture spins up sqlite and repoints the app's sessions at it.

## Demo script (blank statement → scored report)

1. Register: `POST /api/v1/auth/register` (`{"email","password","name","role"}`) → token.
2. Create a merchant: `POST /api/v1/merchants` → `{"full_name","phone"}` → `id`.
3. Upload: `POST /api/v1/statements/upload` with form fields `merchant_id=<id>` and
   `file=@tests/fixtures/momo_sample.csv`.
4. Poll `GET /api/v1/statements/{id}` until `parse_status` is `parsed`
   (or requeue a `failed` one: `POST /statements/{id}/requeue`).
5. `GET /api/v1/reports` → open `GET /reports/{id}` for the full score breakdown.
6. Optionally configure a webhook URL in the dashboard settings page (or
   `PUT /settings`), then re-upload — the signed `score.completed` delivery shows up
   under Recent deliveries.
