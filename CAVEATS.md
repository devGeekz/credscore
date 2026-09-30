# CredScore — Known Caveats

Honest list of limitations as of the MVP (`main` @ team-members commit).
Nothing here blocks a demo; items are ordered by how much they matter.

## 1. Product gaps

- **Billing is metering only.** Plans cap monthly uploads and the usage
  meter works, but there is no payment or upgrade flow (Stripe etc.).
- **No email anywhere.** No invites (teammates get a password you set for
  them), no "report ready" notifications, no password reset.

## 2. Trust & scoring

- **Statement authenticity is unchecked.** A PDF is trivially editable.
  CredScore scores whatever file it is given — no bureau cross-check, no
  fraud detection, no watermark/format verification against MTN originals.
- **Thresholds are reasoned, not backtested.** The consistency/concentration
  cut-offs and the 25%-of-monthly-revenue limit formula were set by
  judgement, never validated against actual loan defaults. Tune once real
  performance data exists.
- **Parser proven against the sample fixture only.** Real MTN/bank statement
  layouts may need format tweaks; a working PDF from
  `statements.mtn.com.gh` should be tried early.
- **No OCR.** Scanned or photographed statements (images) do not parse —
  only text-layer PDFs and CSVs (Tesseract deliberately not used).

## 3. Security

- **JWTs are not revocable.** Logout deletes the cookie only; a stolen
  7-day token stays valid until expiry. No refresh tokens, no blacklist.
- **No email verification at signup**, and the password rule is
  `minLength 8` only (no complexity/breach checks).
- **No CSP header** (deliberate deferral — needs Next.js nonce plumbing).
  The other four security headers are set on both apps.

## 4. Infrastructure (production unproven)

- **The production path has never run.** Real Redis/Celery broker, real S3
  bucket, Vercel hosting, WhatsApp production number — all configured for,
  none exercised end-to-end. Dev runs tasks inline against local disk.
  *(Blocked on: Railway + Vercel accounts, WhatsApp prod credentials,
  webhook.site URL.)*
- **Rate-limit storage is `memory://` in dev** — per-instance only. Prod
  must use Redis-backed limits.
- **WhatsApp consent flow depends on Meta webhook delivery** — sandbox
  tested only; the media-download path has not seen a real Meta payload.
- **Sentry has no DSN configured** — the hook exists but nothing reports.
- **Local statement files are plaintext** (SSE-AES256 applies to S3 only).
- **No cron/backup policy for the storage bucket** — Neon backs up the DB;
  files depend on the bucket provider's defaults once configured.

## 5. Testing & quality

- **Frontend has zero automated tests** — all UI behavior was verified by
  hand (lint + build + route smoke only).
- **No load or penetration testing** — rate limits and tenant isolation are
  unit-tested, not stress-tested.
- **PDF parsing edge cases** (multi-page headers, wrapped rows, mixed
  encodings) only covered by one fixture.

## Already fixed

- ~~Roles are labels, not limits~~ — `require_admin` guards settings,
  API keys and team management; `require_write` blocks viewers from
  merchants/uploads/requeue.
- ~~One user per organization~~ — team management (admin-created users,
  roles, Settings-page form) added in the latest commit.
- ~~Missing security headers~~ — 4 headers on FastAPI + Next, HSTS in prod.
- ~~No audit trail~~ — every successful mutation writes an `audit_logs` row
  (identity captured from the dashboard's bearer header too).
- ~~Stuck statements~~ — requeue endpoint + dashboard polling/retry button.

## Suggested order to burn this down

1. Try one real MTN-generated statement end-to-end
2. Production deploy (needs credentials) + Redis-backed rate limits
3. Refresh tokens / shorter expiry + password reset flow
4. Frontend smoke tests (Playwright, ~5 journeys)
