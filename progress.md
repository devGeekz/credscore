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
