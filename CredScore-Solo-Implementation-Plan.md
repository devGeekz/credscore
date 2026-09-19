# CredScore — Solo Implementation Plan

## Working Model

You're building this alone, so the two-track structure from a multi-person plan collapses into a single sequential track. The risk isn't merge conflicts — it's **context-switching cost** and **building the frontend against an API that doesn't exist yet**. This plan is ordered to avoid both:

1. **Backend-first, per feature** — build and manually test each API endpoint (via curl/Postman) *before* touching the UI that consumes it. You never build UI against a guess.
2. **One feature, fully vertical, at a time** — for each feature, do backend → manual test → frontend → integration test, then move to the next feature. Don't build all backend first and all frontend second; you'll forget the API's shape by the time you get to the UI.
3. **Small, frequent commits on feature branches** — even solo, branches keep `main` always deployable and give you clean rollback points.

```
┌───────────────────────────────────────────────────────────┐
│                     SOLO BUILD LOOP                        │
│                                                             │
│   1. Write endpoint  →  2. curl/Postman test  →            │
│   3. Build matching UI  →  4. Click through it  →          │
│   5. Commit  →  6. Next feature                            │
└───────────────────────────────────────────────────────────┘
```

---

## Coordination Points (Do First, Even Solo)

These exist to protect *future-you* from *past-you's* forgotten decisions — not to coordinate with a second person.

### 1. Your Own API Contract (`api-contract.md`)

Write this before coding, even though you're the only consumer. Two reasons: it forces you to think through every endpoint's shape before you're deep in implementation, and it's your reference when you're building the frontend three days later and can't remember what a field was called.

**How to create it:**
1. List every feature the dashboard needs (upload statement, view report, manage API keys, etc.)
2. For each, define: URL, auth requirement, request body, success response, error response
3. Keep it updated as you build — if an endpoint's shape changes, update the doc *before* you forget why

**Example entry:**
```markdown
### Upload Statement
- **Endpoint:** POST /api/v1/statements/upload
- **Auth:** Bearer token required
- **Request Body:** multipart/form-data
  - `merchant_id`: string (uuid)
  - `file`: PDF/CSV
- **Success Response (201):**
  ```json
  {
    "id": "uuid",
    "merchant_id": "uuid",
    "parse_status": "pending",
    "created_at": "2026-09-18T10:30:00Z"
  }
  ```
- **Error Response (400):**
  ```json
  { "error": "Unsupported file type" }
  ```
```

---

### 2. Git Branching Strategy (Solo Version)

Simpler than a multi-person flow, but still worth the discipline — it's what lets you revert a bad day's work without losing a good one.

**Step 1: Initialize**
```bash
git init credscore && cd credscore
git checkout -b main
git commit --allow-empty -m "chore: init repo"
git checkout -b dev
git push -u origin dev
```

**Step 2: One feature branch per feature**
```bash
git checkout dev
git pull origin dev
git checkout -b feature/statement-upload
```

**Step 3: Commit often, in small units**
```bash
git add .
git commit -m "feat: add statement upload endpoint"
```

**Step 4: Merge back to dev when the feature works end-to-end**
```bash
git checkout dev
git merge feature/statement-upload
git push origin dev
git branch -d feature/statement-upload
```

**Step 5: Merge `dev` → `main` only at the end of each phase**, after the phase's deliverables all work together.

**Branch naming convention:** `feature/<short-name>`, e.g. `feature/whatsapp-webhook`, `feature/scoring-engine`, `feature/dashboard-reports`.

**The golden rule, solo edition:** never leave a branch half-working overnight without a WIP commit — you will not remember the broken state tomorrow.
```bash
git commit -m "wip: statement parser (broken — OCR fallback not wired up)"
```

---

### 3. Environment Variables

One person, one set of `.env` files — but still worth keeping backend and frontend env vars separate and documented, since you'll be switching directories constantly.

**`backend/.env`:**
```env
PORT=8000
ENVIRONMENT=development
DATABASE_URL=postgresql://user:pass@ep-xxx.neon.tech/credscore?sslmode=require
REDIS_URL=redis://localhost:6379
JWT_SECRET=your-secret-key
WHATSAPP_API_TOKEN=xxx
WHATSAPP_PHONE_NUMBER_ID=xxx
WHATSAPP_VERIFY_TOKEN=xxx
STORAGE_BUCKET=credscore-statements
STORAGE_ACCESS_KEY=xxx
STORAGE_SECRET_KEY=xxx
STORAGE_ENDPOINT=https://xxx.r2.cloudflarestorage.com
TESSERACT_CMD=/usr/bin/tesseract
SENTRY_DSN=xxx
APP_URL=http://localhost:8000
WEBHOOK_SIGNING_SECRET=xxx
```

**`frontend/.env.local`:**
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME=CredScore
```

Keep a `.env.example` of each in the repo (values stripped) so you can rebuild your local setup fast if a machine dies or you switch laptops.

---

## Daily Discipline (Solo Version)

No standups to give, but keep a **running log** — a single `progress.md` file, one line per day:

```markdown
- 2026-09-18: Built statement upload endpoint + tested via curl. Next: OCR fallback.
- 2026-09-19: OCR fallback done. Started frontend upload form.
```

This is cheap insurance: three weeks in, when something breaks, you'll want to know exactly what changed and when — a stand-in for the "ask your collaborator" step you don't have.

**When you're stuck:** timebox it. 45 minutes on a bug with no progress → step away, work on an unrelated task (e.g. a frontend polish item), come back later. Debugging alone has no second pair of eyes, so a fresh look after a break is your substitute.

---

## How to Test Your Work

### Backend
```bash
cd backend
uvicorn app.main:app --reload --port 8000
# Test with curl or Postman
curl http://localhost:8000/api/v1/auth/me
```

### Frontend
```bash
cd frontend
npm run dev
# Open http://localhost:3000
# Check browser console for errors
```

### Integration Test (You, Twice)
1. Run backend (`uvicorn ...`) in one terminal tab
2. Run frontend (`npm run dev`) in another
3. Open http://localhost:3000, log in, click through the flow you just built
4. If it works end-to-end, commit; if not, you know immediately which side broke it

---

## Phase 1: Foundation (Days 1–4)

| Day | Task | Files |
|-----|------|-------|
| 1 | Initialize backend project, install deps | `backend/requirements.txt` |
| 1 | Set up FastAPI app entrypoint | `backend/app/main.py` |
| 1 | Set up SQLAlchemy models + Alembic | `backend/app/models.py`, `alembic/` |
| 1 | Set up Neon Postgres connection | `backend/app/database.py` |
| 2 | Set up Redis client | `backend/app/config.py` |
| 2 | Auth: JWT + password hashing | `backend/app/routers/auth.py` |
| 2 | Tenant context middleware | `backend/app/middleware/tenant.py` |
| 2 | Role-based access middleware | `backend/app/middleware/rbac.py` |
| 3 | Rate limiter middleware | `backend/app/middleware/rate_limiter.py` |
| 3 | Error handling utils | `backend/app/utils/errors.py` |
| 3 | Pydantic request/response schemas | `backend/app/schemas/` |
| 3 | Run `alembic upgrade head` | Database ready |
| 4 | Initialize Next.js app | `frontend/` |
| 4 | Tailwind config | `frontend/tailwind.config.ts` |
| 4 | Folder structure (`app/`, `components/`, `lib/`) | `frontend/` |
| 4 | API client (axios) | `frontend/lib/api.ts` |

**Day 4 checkpoint:** backend runs on 8000, frontend runs on 3000, frontend can hit `GET /api/v1/auth/me` (even if it 401s), CORS works. Commit and merge `dev`.

---

## Phase 2: Auth UI + Statement Ingestion (Days 5–10)

| Day | Task | Files |
|-----|------|-------|
| 5 | Auth helpers (token storage) | `frontend/lib/auth.ts` |
| 5 | Auth middleware (redirect if not logged in) | `frontend/middleware.ts` |
| 5 | Login page | `frontend/app/login/page.tsx` |
| 6 | Register page | `frontend/app/register/page.tsx` |
| 6 | Root layout + dashboard shell | `frontend/app/layout.tsx`, `frontend/app/dashboard/layout.tsx` |
| 6 | **Integration test:** register → login → see empty dashboard | — |
| 7 | Statement upload endpoint (web) | `backend/app/routers/statements.py` |
| 7 | Object storage service (S3/R2) | `backend/app/services/storage_service.py` |
| 8 | WhatsApp inbound webhook | `backend/app/routers/whatsapp_webhook.py` |
| 8 | WhatsApp send/receive service | `backend/app/services/whatsapp_service.py` |
| 8 | OTP consent capture flow | `backend/app/routers/whatsapp_webhook.py` |
| 9 | Celery setup + `parse_tasks.py` skeleton | `backend/app/workers/` |
| 9 | Idempotency check on statement ingestion | `backend/app/services/*` |
| 10 | Upload statement form (web path) | `frontend/components/merchants/UploadStatementForm.tsx` |
| 10 | **Integration test:** upload a sample PDF from the dashboard, confirm a `Statement` row appears with `parse_status: pending` | — |

---

## Phase 3: Parsing + Scoring Engine (Days 10–14)

This phase is backend-heavy and closer to data-science work than typical CRUD — budget extra time and test against real sample statements early.

| Day | Task | Files |
|-----|------|-------|
| 10 | PDF table extraction (pdfplumber) | `backend/app/engine/pdf_extractor.py` |
| 11 | OCR fallback for scanned statements | `backend/app/engine/pdf_extractor.py` |
| 11 | Text normalizer / counterparty tokenizer | `backend/app/engine/normalizer.py` |
| 12 | Velocity & frequency heuristics | `backend/app/engine/heuristics.py` |
| 12 | Scoring model (revenue, ADB, expense ratio, risk tag) | `backend/app/engine/scoring_model.py` |
| 13 | Wire parsing + scoring into Celery task | `backend/app/workers/parse_tasks.py`, `score_tasks.py` |
| 13 | Unit tests against sample MTN/Telecel statement fixtures | `backend/tests/test_parsing.py` |
| 14 | Outbound webhook dispatch on score completion | `backend/app/services/webhook_service.py` |
| 14 | **Manual test loop:** feed 5–10 real/sample statements end-to-end, sanity-check the numbers by hand | — |

---

## Phase 4: Lender Dashboard (Days 14–18)

| Day | Task | Files |
|-----|------|-------|
| 14 | Dashboard overview stats endpoint | `backend/app/routers/dashboard.py` |
| 15 | Reports listing + detail endpoints | `backend/app/routers/reports.py` |
| 15 | SWR hooks for merchants/reports | `frontend/hooks/useMerchants.ts`, `useReports.ts` |
| 15 | Dashboard overview page | `frontend/app/dashboard/page.tsx` |
| 16 | Stats card + sidebar/header components | `frontend/components/ui/Card.tsx`, `frontend/components/layout/` |
| 16 | Merchant/applicant list page | `frontend/app/dashboard/merchants/page.tsx` |
| 17 | Score report list + filter UI | `frontend/app/dashboard/reports/page.tsx` |
| 17 | Individual report view (cash-flow chart, risk tag, PDF export) | `frontend/app/dashboard/reports/[id]/page.tsx` |
| 18 | API key management page + endpoint | `frontend/app/dashboard/api-keys/page.tsx`, `backend/app/routers/auth.py` |
| 18 | **Integration test:** full loop — upload statement → see it parse → see the score report render correctly in the UI | — |

---

## Phase 5: Billing + Webhooks (Days 18–20)

| Day | Task | Files |
|-----|------|-------|
| 18 | Subscription plans + usage metering | `backend/app/services/billing_service.py` |
| 19 | Webhook retry queue (3 attempts, backoff) | `backend/app/services/webhook_service.py` |
| 19 | Webhook signature verification (HMAC) | `backend/app/services/webhook_service.py` |
| 19 | Billing page + plan display | `frontend/app/dashboard/settings/page.tsx` |
| 20 | Webhook config UI (lender sets their endpoint URL) | `frontend/app/dashboard/settings/page.tsx` |
| 20 | **Integration test:** register a test webhook endpoint (e.g. webhook.site), confirm a score report delivers correctly | — |

---

## Phase 6: Monitoring + Security + Compliance (Days 20–23)

| Day | Task | Files |
|-----|------|-------|
| 20 | Sentry integration | `backend/app/main.py` |
| 21 | Structured logging (structlog) | `backend/app/utils/logger.py` |
| 21 | Audit log middleware (all mutations) | `backend/app/middleware/audit.py` |
| 21 | Rate limiting on API + statement uploads | `backend/app/middleware/rate_limiter.py` |
| 22 | Pydantic validation pass on every route | `backend/app/schemas/` |
| 22 | Encrypted-at-rest storage + signed download URLs | `backend/app/services/storage_service.py` |
| 22 | CORS hardening + security headers | `backend/app/main.py` |
| 23 | DPC-aligned consent audit export | `backend/app/routers/dashboard.py` |
| 23 | Error boundary + loading skeletons (frontend polish) | `frontend/components/ui/` |
| 23 | Mobile responsive pass | All page components |

---

## Phase 7: Deploy + Demo (Days 23–26)

| Day | Task |
|-----|------|
| 24 | Deploy backend + Celery worker to Railway |
| 24 | Deploy frontend to Vercel |
| 24 | Connect Neon database, set `DATABASE_URL` |
| 24 | Add Redis service on Railway |
| 25 | Configure all production environment variables |
| 25 | WhatsApp sandbox → production number switch |
| 25 | Full end-to-end test in production |
| 26 | Demo script (blank credit file vs. CredScore report, side by side) |
| 26 | README + setup instructions |
| 26 | Postman collection export |
| 26 | Merge `dev` → `main`, tag release |

---

## Solo Build Timeline

```
Day  1-4:    Foundation — backend skeleton, then frontend skeleton
Day  5-10:   Auth UI + statement ingestion (web + WhatsApp)
Day  10-14:  Parsing & scoring engine (heaviest backend work)
Day  14-18:  Lender dashboard (consumes everything built so far)
Day  18-20:  Billing + webhooks
Day  20-23:  Security, compliance, polish
Day  23-26:  Deploy + demo
```

This is longer than a two-person plan on the same scope (~26 days vs. ~21) — that gap is expected and healthy; don't compress it by skipping the manual test steps, since those are what catch bugs before they compound.

---

## Risk Mitigation (Solo-Specific)

| Risk | Mitigation |
|------|------------|
| No second pair of eyes to catch bugs | Manual integration test after every feature, not just at phase boundaries |
| Losing context between backend and frontend work | Keep `api-contract.md` current; re-read it before switching sides |
| Burnout / stalling on a hard bug (e.g. OCR accuracy) | Timebox debugging sessions; work on an unrelated task, come back fresh |
| Forgetting why a decision was made | `progress.md` daily log — one line is enough |
| Scope creep (adding "just one more feature") | Treat the phase deliverables list as the definition of done; log new ideas in a `later.md`, don't build them now |
| A single bad merge breaking everything | Feature branches + `dev`, only promote to `main` at phase boundaries |

---

## Deliverables Checklist

### Backend
- [ ] FastAPI server running
- [ ] SQLAlchemy models migrated to Neon via Alembic
- [ ] JWT auth + API key issuance working
- [ ] WhatsApp inbound webhook receiving statements
- [ ] Web upload endpoint working
- [ ] Celery parsing + scoring pipeline running end-to-end
- [ ] Outbound webhook delivery with retries
- [ ] Rate limiting active
- [ ] Sentry integrated
- [ ] Tests passing (`test_parsing.py`, `test_auth.py`, `test_tenant_isolation.py`)

### Frontend
- [ ] Next.js app running
- [ ] Tailwind styled
- [ ] Login/Register pages
- [ ] Dashboard layout + sidebar
- [ ] Merchant/applicant management page
- [ ] Score report list + detail view (with chart + PDF export)
- [ ] API key management page
- [ ] Settings + webhook config page
- [ ] Mobile responsive

### Overall
- [ ] `api-contract.md` written and kept current
- [ ] `progress.md` daily log maintained
- [ ] Git branching discipline followed (`dev` + feature branches)
- [ ] Environment variables configured in both `backend/.env` and `frontend/.env.local`
- [ ] End-to-end flow working in production
- [ ] Demo script ready
- [ ] README complete
