# Progress log

One line per working session. Newest last.

- 2026-09-29: M1 — local dev unblock (venv/npm/psycopg3 swap), Phase 2 closure (dashboard
  upload form wired, local storage fallback, shared `queue_parse`), stripped leaked Neon
  credentials from `.env.example`. E2E: register → login → merchant → upload → parsed.
- 2026-09-29: M2 — scoring engine (`app/engine/{extract,normalize,heuristics,scoring_model}.py`),
  pipeline wired into Celery task, `queue_parse` broker probe (Celery blocked API 110s when
  Redis was down), portable `Uuid` columns so tests run on SQLite. 15 tests green
  (test_parsing / test_auth / test_tenant_isolation); fixture is synthetic MTN-shaped CSV.
  E2E: upload 3.3s → ScoreReport (revenue 4500, consistency 84.7, tag strong).

Next: M3 — dashboard (stats/reports endpoints, api-keys, merchant/report pages).
- 2026-09-29: M3 � dashboard (Phase 4): stats/reports/api-key endpoints, statement list endpoint, consent timestamp in schema; frontend sidebar + overview/applicants/reports/report-detail (recharts)/api-keys pages, risk badge + format helpers. Checks: pytest 15 green, eslint clean, next build green, route smoke test via next start (307 guard + 200s).
- 2026-09-29: M4 — outbound webhooks + billing (Phase 5): `webhook_service` (HMAC-SHA256 signed
  deliveries, 3 attempts with backoff, WebhookLog), Celery task + dev inline delivery, fires
  `score.completed` after every score; `tenants.webhook_url/webhook_secret` migration; settings
  GET/PUT with SSRF guard (private targets refused in production, loopback allowed in dev) +
  delivery history; `billing_service` plan limits + monthly usage meter; settings page
  (org / plan usage / webhook config / recent deliveries). Checks: pytest 21 green, eslint 0
  errors, next build green, route smoke 307/200, live E2E — configure hook → upload → signed
  delivery verified at local receiver → logged delivered 200 → usage metered.

Next: M5 — hardening (statement status polling / re-queue), then M6 — docs + deploy.
- 2026-09-30: M5 - hardening (Phase 6): audit-trail middleware (audit_logs rows on every successful mutation, fail-open), 20/min upload rate limit, 4 security headers on FastAPI + Next, CORS from settings, stdlib JSON logging, optional Sentry, WhatsApp webhook validation, SSE-AES256 at rest + signed download endpoint, consent-audit CSV export, statement requeue endpoint (202/409) + frontend polling + retry, dashboard error boundary + loading skeleton + responsive sidebar/tables. Checks: pytest 30 green, eslint 0 errors, next build green, route smoke 307/200, live probes - audit row on Neon, security headers on both apps.

Next: M6 - docs + deploy (Railway/Vercel/WhatsApp credentials needed).
