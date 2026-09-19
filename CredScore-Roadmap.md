# CredScore — Startup Roadmap

## Architecture Overview

```
┌─────────────┐     ┌───────────────┐     ┌─────────────┐
│   Next.js   │────▶│  FastAPI Core │────▶│ PostgreSQL  │
│ (Lender UI) │     │   (Backend)   │     │  (Primary)  │
│   Vercel    │     │   Railway     │     └─────────────┘
└─────────────┘     └───────┬───────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
  ┌──────────┐       ┌──────────────┐    ┌──────────────┐
  │  Redis   │       │  Celery/RQ   │    │  WhatsApp    │
  │(Sessions │       │  (Parsing +  │    │  Business    │
  │ +Cache)  │       │   Scoring    │    │  API (Bot)   │
  └──────────┘       │   Queue)     │    └──────────────┘
                      └──────┬───────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌──────────┐  ┌────────────┐ ┌──────────────┐
        │pdfplumber│  │  Pandas /  │ │  S3 / Object │
        │ Tesseract│  │   NumPy    │ │   Storage    │
        │ (Parsing)│  │ (Scoring)  │ │ (Statements) │
        └──────────┘  └────────────┘ └──────────────┘
```

---

## Tech Stack

| Layer | Choice | Cost | Purpose |
|-------|--------|------|---------|
| Frontend | Next.js 14+ (App Router) | Free (Vercel) | Lender dashboard UI |
| Styling | Tailwind CSS | Free | Rapid UI development |
| Data Fetching | SWR | Free | Client-side caching + polling |
| Backend | Python 3.12 + FastAPI | Free (Railway) | API server & scoring engine |
| ORM / Migrations | SQLAlchemy 2.0 + Alembic | Free | Database models & migrations |
| Database | PostgreSQL (Neon) | Free tier | Persistent storage (JSONB for reports) |
| Cache/Sessions | Redis | Free tier (Railway) | Sessions + caching |
| Queue / Workers | Celery (or RQ) + Redis | Free | Async statement parsing & scoring |
| Auth | JWT + OAuth2 (API keys for lenders) | Free | Authentication & lender integrations |
| Statement Parsing | pdfplumber / PyPDF2 / Tesseract OCR | Free | Extracts tables from MoMo PDFs |
| Analytics Engine | Pandas / NumPy | Free | Heuristics, normalization, scoring |
| Merchant Channel | WhatsApp Business API (Meta Cloud API / Twilio) | Free (1,000 msgs/mo) | Zero-app merchant intake |
| File Storage | AWS S3 / Cloudflare R2 | Free tier | Raw statement storage (encrypted) |
| Monitoring | Sentry (free tier) | Free | Error tracking |

### Deployment

| Service | Platform | Cost |
|---------|----------|------|
| Frontend (Next.js) | Vercel | Free (hobby tier) |
| Backend (FastAPI) | Railway | Free tier ($5 credit/mo) |
| Database (PostgreSQL) | Neon | Free tier |
| Cache/Queue (Redis) | Railway | Free tier |
| File Storage | Cloudflare R2 | Free tier (10GB) |

### Cost Breakdown (Monthly)

| Item | 3 Lenders (Pilot) | 20 Lenders | 100 Lenders |
|------|--------------------|-----------|--------------|
| Vercel | Free | Free | $20 |
| Railway (API + workers) | Free | $25 | $150 |
| PostgreSQL (Neon) | Free | $20 | $69 |
| Redis | Free | $10 | $30 |
| Object Storage (R2) | Free | $5 | $25 |
| WhatsApp Business API | Free | $30 | $200 |
| OCR/Compute (Tesseract spikes) | Free | $10 | $50 |
| **Total** | **< GHS 200** | **< GHS 1,200** | **< GHS 6,500** |

---

## Database Schema (SQLAlchemy + Alembic)

`backend/app/models.py`:

```python
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, DateTime, ForeignKey, Numeric, JSON, Text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Tenant(Base):
    """A lending institution: MFI, bank, or fintech lender."""
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    org_type = Column(String, nullable=False)  # mfi, bank, fintech_lender
    contact_email = Column(String, nullable=False)
    subscription_plan = Column(String, default="pilot")  # pilot, growth, enterprise
    subscription_status = Column(String, default="trial")
    api_key_hash = Column(String, unique=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    users = relationship("User", back_populates="tenant")
    merchants = relationship("Merchant", back_populates="tenant")
    webhook_logs = relationship("WebhookLog", back_populates="tenant")
    audit_logs = relationship("AuditLog", back_populates="tenant")


class User(Base):
    """A lender-side staff account: admin, underwriter, viewer."""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    email = Column(String, nullable=False)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False)  # admin, underwriter, viewer
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="users")
    audit_logs = relationship("AuditLog", back_populates="user")


class Merchant(Base):
    """A micro-merchant/loan applicant being scored by a specific tenant."""
    __tablename__ = "merchants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    full_name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    business_name = Column(String, nullable=True)
    telco = Column(String, nullable=True)  # MTN, Telecel, AirtelTigo
    consent_verified = Column(Boolean, default=False)
    consent_timestamp = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="merchants")
    statements = relationship("Statement", back_populates="merchant")


class Statement(Base):
    """A raw MoMo statement file submitted for a merchant."""
    __tablename__ = "statements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_id = Column(UUID(as_uuid=True), ForeignKey("merchants.id"), nullable=False)
    source_channel = Column(String, nullable=False)  # whatsapp, web_upload, email
    file_url = Column(String, nullable=False)  # encrypted object storage path
    period_start = Column(DateTime, nullable=True)
    period_end = Column(DateTime, nullable=True)
    parse_status = Column(String, default="pending")  # pending, parsed, failed
    parse_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    merchant = relationship("Merchant", back_populates="statements")
    score_report = relationship("ScoreReport", back_populates="statement", uselist=False)


class ScoreReport(Base):
    """The generated credit-intelligence output for a statement."""
    __tablename__ = "score_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    statement_id = Column(UUID(as_uuid=True), ForeignKey("statements.id"), nullable=False)
    net_verified_revenue = Column(Numeric(12, 2), nullable=True)
    cash_flow_consistency = Column(Numeric(5, 2), nullable=True)  # 0-100
    average_daily_balance = Column(Numeric(12, 2), nullable=True)
    expense_ratio = Column(Numeric(5, 2), nullable=True)
    counterparty_concentration = Column(Numeric(5, 2), nullable=True)
    risk_tag = Column(String, nullable=True)  # strong, moderate, high_risk
    suggested_credit_limit = Column(Numeric(12, 2), nullable=True)
    raw_payload = Column(JSON, nullable=True)  # full structured JSON output
    created_at = Column(DateTime, default=datetime.utcnow)

    statement = relationship("Statement", back_populates="score_report")


class WebhookLog(Base):
    """Outbound delivery log of score reports pushed to lender systems."""
    __tablename__ = "webhook_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True)
    event_type = Column(String, nullable=False)  # score.completed, statement.failed
    payload = Column(JSON, nullable=False)
    response_status = Column(String, nullable=True)
    attempts = Column(String, default="0")
    delivered = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="webhook_logs")


class AuditLog(Base):
    """Immutable action log for compliance (DPC / BoG audit trail)."""
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    entity = Column(String, nullable=True)
    entity_id = Column(String, nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="audit_logs")
    user = relationship("User", back_populates="audit_logs")
```

### Run Migration
```bash
cd backend
alembic revision --autogenerate -m "init"
alembic upgrade head
```

---

## Project Structure

```
credscore/
├── frontend/                        # Next.js lender dashboard (Vercel)
│   ├── app/
│   │   ├── layout.tsx                # Root layout (Tailwind)
│   │   ├── page.tsx                  # Landing / marketing page
│   │   ├── login/
│   │   │   └── page.tsx
│   │   ├── register/
│   │   │   └── page.tsx
│   │   ├── dashboard/
│   │   │   ├── layout.tsx            # Sidebar layout
│   │   │   ├── page.tsx              # Overview stats
│   │   │   ├── merchants/
│   │   │   │   └── page.tsx          # Applicant list + upload
│   │   │   ├── reports/
│   │   │   │   ├── page.tsx          # Score report list
│   │   │   │   └── [id]/page.tsx     # Individual credit memo view
│   │   │   ├── api-keys/
│   │   │   │   └── page.tsx          # API key management
│   │   │   └── settings/
│   │   │       └── page.tsx          # Org/subscription settings
│   │   └── not-found.tsx
│   ├── components/
│   │   ├── ui/                       # Button, Card, Table, Modal, Input
│   │   ├── layout/                   # Sidebar, Header, DashboardLayout
│   │   ├── merchants/                # MerchantTable, UploadStatementForm
│   │   └── reports/                  # RiskTag, CashFlowChart, ScoreCard
│   ├── lib/
│   │   ├── api.ts                    # Axios instance → FastAPI backend
│   │   ├── auth.ts                   # Token management
│   │   └── types.ts                  # TypeScript interfaces
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── useMerchants.ts
│   │   └── useReports.ts
│   ├── middleware.ts                  # Auth guard
│   ├── tailwind.config.ts
│   └── package.json
│
├── backend/                          # FastAPI core (Railway)
│   ├── app/
│   │   ├── main.py                   # App entry point
│   │   ├── config.py                 # Env/settings (pydantic-settings)
│   │   ├── database.py               # SQLAlchemy engine/session
│   │   ├── models.py                 # ORM models (above)
│   │   ├── schemas/                  # Pydantic request/response schemas
│   │   │   ├── merchant.py
│   │   │   ├── statement.py
│   │   │   └── report.py
│   │   ├── routers/
│   │   │   ├── auth.py               # Login/register, API key issuance
│   │   │   ├── merchants.py          # Merchant CRUD
│   │   │   ├── statements.py         # Upload/ingest endpoints
│   │   │   ├── reports.py            # Score report retrieval
│   │   │   ├── whatsapp_webhook.py   # WhatsApp inbound webhook
│   │   │   ├── outbound_webhooks.py  # Lender webhook config
│   │   │   └── dashboard.py          # Stats/analytics
│   │   ├── engine/
│   │   │   ├── pdf_extractor.py      # pdfplumber / OCR fallback
│   │   │   ├── normalizer.py         # Tokenization & counterparty matching
│   │   │   ├── heuristics.py         # Velocity & frequency rules
│   │   │   └── scoring_model.py      # Final score computation
│   │   ├── services/
│   │   │   ├── whatsapp_service.py   # Send/receive WhatsApp messages
│   │   │   ├── storage_service.py    # S3/R2 upload & signed URLs
│   │   │   ├── webhook_service.py    # Outbound delivery + retries
│   │   │   └── billing_service.py    # Usage metering & subscriptions
│   │   ├── workers/
│   │   │   ├── celery_app.py         # Celery config
│   │   │   ├── parse_tasks.py        # Async statement parsing
│   │   │   └── score_tasks.py        # Async scoring + webhook dispatch
│   │   └── middleware/
│   │       ├── auth.py               # JWT / API key verification
│   │       ├── tenant.py             # Tenant context extraction
│   │       ├── rate_limiter.py       # Per-tenant limiting
│   │       └── audit.py              # Audit logging
│   ├── alembic/                      # Migrations
│   ├── tests/
│   │   ├── test_auth.py
│   │   ├── test_parsing.py
│   │   └── test_tenant_isolation.py
│   ├── .env.example
│   ├── requirements.txt
│   └── README.md
│
├── .env.example
├── .gitignore
├── roadmap.md
└── README.md
```

---

## Phase 1a: Backend Foundation + Auth (Days 1–3)

**Goal:** Multi-tenant FastAPI server with authentication and API key issuance.

### Deliverables
1. FastAPI app with middleware pipeline (CORS, Helmet-equivalent headers)
2. SQLAlchemy engine connected to Neon PostgreSQL + Alembic migrations
3. Redis connection for sessions/cache
4. JWT authentication (lender staff login/register)
5. API key issuance & verification (for lender system-to-system calls)
6. Role-based access middleware (admin / underwriter / viewer)
7. Tenant context middleware (extracts tenant_id from JWT or API key)
8. Rate limiting per tenant (slowapi + Redis)

### Dependencies
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install fastapi uvicorn[standard] sqlalchemy alembic psycopg2-binary
pip install python-jose[cryptography] passlib[bcrypt] pydantic-settings
pip install redis slowapi celery
pip install pdfplumber pypdf pytesseract pandas numpy
pip install boto3  # S3/R2 storage
```

---

## Phase 1b: Frontend Foundation (Days 3–5)

**Goal:** Next.js lender dashboard shell with Tailwind, routing, and API client.

### Deliverables
1. Next.js app with App Router + TypeScript
2. Tailwind CSS configured
3. Folder structure created
4. API client (`lib/api.ts`) pointing to FastAPI backend
5. Auth middleware (redirect to login if not authenticated)
6. Login/Register pages
7. Dashboard layout with sidebar (Merchants, Reports, API Keys, Settings)

### Dependencies
```bash
cd frontend
npx create-next-app@latest . --typescript --tailwind --app --eslint
npm install axios swr recharts
```

---

## Phase 2: Statement Ingestion + WhatsApp Bot (Days 5–9)

**Goal:** Zero-app merchant intake via WhatsApp and web upload.

### Deliverables
1. `POST /api/v1/statements/upload` endpoint (web form upload)
2. `POST /api/v1/webhooks/whatsapp` inbound webhook (Meta Cloud API / Twilio)
3. WhatsApp conversational flow: USSD instructions → OTP consent capture → file/document receipt
4. Consent record written to `merchants.consent_verified` with timestamp
5. Raw file stored encrypted in S3/R2, referenced via `statements.file_url`
6. Statement queued to Celery for async parsing
7. Idempotency check (avoid duplicate ingestion of the same statement)

### Flow
```
Merchant (WhatsApp/Web) → Upload/forward statement → OTP consent check
  → Store encrypted file → Create Statement row → Queue parse_task
  → Celery worker parses PDF/CSV → Update parse_status
```

---

## Phase 3: Parsing + Scoring Engine (Days 9–12)

**Goal:** Turn a raw statement into a structured, lender-ready score report.

### Deliverables
1. `pdf_extractor.py` — pdfplumber table extraction with Tesseract OCR fallback for scanned statements
2. `normalizer.py` — tokenizes counterparty strings, matches against commercial-entity dictionary
3. `heuristics.py` — velocity/frequency rules to separate business revenue from personal transfers
4. `scoring_model.py` — computes Net Verified Revenue, Cash-Flow Consistency, ADB, Expense Ratio, Counterparty Concentration, and Risk Tag
5. `ScoreReport` row created and linked to the `Statement`
6. Outbound webhook fired to the lender's registered endpoint with the JSON payload
7. Unit tests against sample MTN/Telecel statement fixtures

---

## Phase 4: Lender Dashboard (Days 12–15)

**Goal:** Full underwriter-facing web application.

### Deliverables
1. **Dashboard Overview** (`/dashboard`)
   - Stats cards (applications this month, avg. processing time, risk mix)
   - Recent score reports table
   - Quick action: upload new applicant statement

2. **Merchant/Applicant Management** (`/dashboard/merchants`)
   - List applicants with status (pending, parsed, scored, failed)
   - Upload statement form (manual underwriter path)
   - View consent record

3. **Score Reports** (`/dashboard/reports`)
   - Filterable table (by risk tag, date, merchant)
   - Individual report view: cash-flow chart, financial health tag, debt-service coverage, downloadable PDF credit memo
   - Export to CSV

4. **API Key Management** (`/dashboard/api-keys`)
   - Generate/revoke API keys
   - Usage this billing period

5. **Settings** (`/dashboard/settings`)
   - Org profile, subscription plan, webhook endpoint configuration

### Data Fetching Pattern
```typescript
// hooks/useReports.ts
import useSWR from 'swr';
import { api } from '@/lib/api';

export function useReports() {
  const { data, error, isLoading } = useSWR('/api/v1/reports', api.get);
  return { reports: data, isLoading, error };
}
```

---

## Phase 5: Billing + Webhooks (Days 15–17)

**Goal:** Usage-based billing and reliable outbound delivery to lender systems.

### Deliverables
1. Subscription plans:
   - Pilot: 14 days, 50 statements, 1 seat
   - Growth: GHS 800/mo, 500 statements included, GHS 8/statement overage
   - Enterprise: custom volume pricing + dedicated webhook SLA
2. Per-statement usage metering (`billing_service.py`)
3. Webhook delivery queue with retries (3 attempts, exponential backoff)
4. Webhook signature verification (HMAC) so lenders can trust payload authenticity
5. Invoice history view in dashboard

---

## Phase 6: Monitoring + Security + Compliance (Days 17–19)

**Goal:** Production-ready, audit-defensible platform.

### Deliverables
1. Sentry integration (error tracking)
2. Structured logging (structlog / Python logging + JSON formatter)
3. Immutable audit trail for all mutations (`audit_logs`)
4. Rate limiting:
   - 100 req/min per tenant (API)
   - 20 statement uploads/min per tenant
5. Input validation via Pydantic schemas
6. PII anonymization pass before any model-training data export
7. Encrypted-at-rest statement storage + signed, expiring download URLs
8. CORS configuration + security headers
9. DPC-aligned consent audit export (for regulatory review)

---

## Phase 7: Deploy + Demo (Days 19–21)

**Goal:** Live production deployment.

### Deliverables
1. **Vercel (Frontend)**
   - Connect GitHub repo
   - Set environment variables (`NEXT_PUBLIC_API_URL`)
   - Auto-deploy on push

2. **Railway (Backend + Workers)**
   - Connect GitHub repo
   - Set environment variables
   - Add Redis service
   - Connect to Neon PostgreSQL (`DATABASE_URL`)
   - Deploy Celery worker as a separate Railway service
   - Auto-deploy on push

3. **WhatsApp sandbox → production number switch**
4. **Demo script for investors/judges** (blank credit file vs. CredScore report, side by side)
5. **README with setup instructions**
6. **Postman collection for API testing**

---

## Future Phases (Post-Launch)

| Phase | Feature | Revenue Impact |
|-------|---------|-----------------|
| 8 | Bank statement ingestion (formal accounts) | Expands addressable applicant pool |
| 9 | POS/payment gateway integration (Hubtel, Paystack, Flutterwave) | Multi-channel data moat |
| 10 | Predictive cash-flow-crunch alerts | Premium tier upsell |
| 11 | Credit Reference Bureau (CRB) submission integration | Regulatory compliance tier |
| 12 | Direct telco Data Sharing Agreements | Removes manual USSD step |
| 13 | Public scoring API marketplace | Platform play |

---

## Key Metrics to Track

| Metric | Target | Why |
|--------|--------|-----|
| Statement parse accuracy | > 95% | Core trust driver |
| End-to-end scoring time | < 60 seconds | Fits loan-decision workflows |
| Webhook delivery success | > 99% | Lender integration reliability |
| Dashboard load time | < 2 seconds | UX |
| Uptime | 99.9% | Trust |
| Active lender tenants | 5 by month 3 | Growth |
| Statements processed/month | 1,000 by month 6 | Adoption |
| Tenant churn rate | < 5%/month | Retention |

---

## Subscription Plans

| Plan | Price | Statements Included | Overage | Features |
|------|-------|----------------------|---------|----------|
| Pilot | Free (14 days) | 50 | — | Core scoring, dashboard |
| Growth | GHS 800/mo | 500 | GHS 8/statement | Webhooks, CSV export, priority parsing |
| Enterprise | Custom | Custom | Custom | Dedicated SLA, DSA integration, CRB submission |

---

## API Endpoints

### Auth
```
POST   /api/v1/auth/register           — Register lender org + admin user
POST   /api/v1/auth/login              — Login
POST   /api/v1/auth/logout             — Logout
GET    /api/v1/auth/me                 — Current user
POST   /api/v1/auth/api-keys           — Issue API key
DELETE /api/v1/auth/api-keys/:id       — Revoke API key
```

### Merchants
```
GET    /api/v1/merchants               — List applicants
POST   /api/v1/merchants               — Create applicant record
GET    /api/v1/merchants/:id           — Get applicant
PUT    /api/v1/merchants/:id           — Update applicant
```

### Statements
```
POST   /api/v1/statements/upload       — Upload/ingest a statement (web)
GET    /api/v1/statements/:id          — Get statement + parse status
```

### Reports
```
GET    /api/v1/reports                 — List score reports
GET    /api/v1/reports/:id             — Get full score report (JSON)
GET    /api/v1/reports/:id/pdf         — Download credit memo (PDF)
```

### Webhooks
```
POST   /api/v1/webhooks/whatsapp       — Inbound WhatsApp bot webhook
POST   /api/v1/webhooks/config         — Register lender's outbound webhook URL
GET    /api/v1/webhooks/logs           — Delivery log/history
```

### Dashboard
```
GET    /api/v1/dashboard/stats         — Overview stats
```

### Billing
```
GET    /api/v1/billing/subscription    — Current plan + usage
POST   /api/v1/billing/subscribe       — Subscribe/upgrade plan
GET    /api/v1/billing/invoices        — Invoice history
```

---

## Environment Variables

### Backend (.env)
```env
# Server
PORT=8000
ENVIRONMENT=development

# Database (Neon PostgreSQL)
DATABASE_URL=postgresql://user:pass@ep-xxx.us-east-2.aws.neon.tech/credscore?sslmode=require

# Redis
REDIS_URL=redis://localhost:6379

# JWT
JWT_SECRET=your-secret-key
JWT_EXPIRES_IN=7d

# WhatsApp Business API
WHATSAPP_API_TOKEN=your-whatsapp-token
WHATSAPP_PHONE_NUMBER_ID=your-phone-id
WHATSAPP_VERIFY_TOKEN=your-webhook-verify-token

# Object Storage (S3/R2)
STORAGE_BUCKET=credscore-statements
STORAGE_ACCESS_KEY=your-access-key
STORAGE_SECRET_KEY=your-secret-key
STORAGE_ENDPOINT=https://xxx.r2.cloudflarestorage.com

# OCR
TESSERACT_CMD=/usr/bin/tesseract

# Sentry
SENTRY_DSN=your-sentry-dsn

# App
APP_URL=http://localhost:8000
WEBHOOK_SIGNING_SECRET=your-webhook-secret
```

### Frontend (.env.local)
```env
# API
NEXT_PUBLIC_API_URL=http://localhost:8000

# App
NEXT_PUBLIC_APP_NAME=CredScore
```
