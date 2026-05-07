# A2CR Deploy Runbook

This runbook describes the MVP deployment path: one Railway service serves the React/Vite SPA, FastAPI APIs, and Streamable HTTP MCP at the same public origin.

## Current Hosted Setup Status

Last updated: 2026-05-06

Completed:

- Cloudflare domain purchased and active: `a2cr.app`
- Supabase organization/project created:
  - Organization: `A2CR`
  - Project: `a2cr-production`
  - Project ref: `pemqlmrochfnwthslxco`
  - Region: Northeast Asia (Tokyo)
  - Current plan for testing: Free / Nano
- Supabase migrations applied through SQL Editor at the initial setup:
  - `supabase/migrations/001_base_schema.sql`
  - `supabase/migrations/002_workthreads.sql`
- Current app code also requires these later migrations before dashboard/context smoke tests:
  - `supabase/migrations/003_contexts_user_scoped_unique_repair.sql`
  - `supabase/migrations/004_contexts_encryption_mode.sql`
  - `supabase/migrations/005_contexts_client_encrypted_only.sql`
  - `supabase/migrations/006_db_resilience_baseline.sql`
  - `supabase/migrations/007_workthreads_message_uniqueness.sql`
- RLS verification passed for 9 public tables:
  - `access_logs`
  - `api_keys`
  - `contexts`
  - `stats`
  - `user_profiles`
  - `work_thread_messages`
  - `work_thread_runs`
  - `work_thread_tasks`
  - `work_threads`
- Runtime DB role exists: `a2cr_app`
- `a2cr_app` password was set manually in Supabase SQL Editor.
- Google Cloud project created:
  - Name: `A2CR`
  - Project ID: `a2cr-495417`
- Google OAuth web client created:
  - Name: `A2CR Supabase Auth`
  - Authorized JavaScript origin: `https://a2cr.app`
  - Authorized redirect URI: `https://pemqlmrochfnwthslxco.supabase.co/auth/v1/callback`
- Supabase Google provider is enabled.

Still pending:

- Railway project creation
- Railway environment variables
- Railway deployment
- Cloudflare DNS pointing `a2cr.app` to Railway
- Supabase Auth URL configuration for the deployed site
- Confirm/apply Supabase migrations `003` through `005` in the production project
- Hosted smoke tests for `/api/v1/health`, `/dashboard`, `/mcp`, Google login, API key issue, MCP save/resume, and WorkThreads
- Stripe setup
- Supabase Pro upgrade before real beta/production

## Production Shape

- Runtime: Railway Dockerfile service
- Database/Auth: Supabase Postgres and Supabase Auth
- Public origin: one Cloudflare-managed domain pointing to Railway
- API health: `/api/v1/health`
- Web UI: `/login`, `/dashboard`, `/settings`, `/pricing`
- MCP endpoint: `/mcp`
- Cleanup job: protected Railway job using `python -m services.maintenance expire-contexts`

## Supabase Values

Public/non-secret values:

```text
VITE_SUPABASE_URL=https://pemqlmrochfnwthslxco.supabase.co
SUPABASE_JWKS_URL=https://pemqlmrochfnwthslxco.supabase.co/auth/v1/.well-known/jwks.json
SUPABASE_JWT_AUDIENCE=authenticated
SUPABASE_JWT_ISSUER=https://pemqlmrochfnwthslxco.supabase.co/auth/v1
```

Connection shape for Railway:

```text
DATABASE_URL=postgresql+psycopg://a2cr_app.pemqlmrochfnwthslxco:<A2CR_APP_DB_PASSWORD>@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres
```

Notes:

- Use the transaction pooler connection from Supabase Connect.
- Use the `a2cr_app` role, not `postgres`.
- URL-encode the password part in `DATABASE_URL` if it contains reserved characters such as `@`, `:`, `/`, `?`, `#`, or `%`.
- Store the `a2cr_app` password in a password manager and Railway variables only.
- Do not set `SUPABASE_SERVICE_ROLE_KEY` on the Railway runtime.
- This Supabase project uses asymmetric JWT signing. Use `SUPABASE_JWKS_URL`; do not require `SUPABASE_JWT_SECRET`.

## Railway Variables

Required runtime variables:

```text
APP_ENV=production
DATABASE_URL=postgresql+psycopg://a2cr_app.pemqlmrochfnwthslxco:<A2CR_APP_DB_PASSWORD>@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres
FERNET_KEY=<Fernet.generate_key() output>
API_KEY_HASH_SECRET=<32+ random chars>
AUDIT_HASH_SECRET=<32+ random chars>
A2CR_SERVICE_URL=https://a2cr.app/mcp
A2CR_PUBLIC_ORIGIN=https://a2cr.app
A2CR_API_KEY_PREFIX=sk-a2cr
SUPABASE_JWKS_URL=https://pemqlmrochfnwthslxco.supabase.co/auth/v1/.well-known/jwks.json
SUPABASE_JWT_AUDIENCE=authenticated
SUPABASE_JWT_ISSUER=https://pemqlmrochfnwthslxco.supabase.co/auth/v1
```

Required browser build variables:

```text
VITE_SUPABASE_URL=https://pemqlmrochfnwthslxco.supabase.co
VITE_SUPABASE_ANON_KEY=<Supabase publishable key>
VITE_A2CR_SERVICE_URL=https://a2cr.app/mcp
VITE_A2CR_API_BASE=
```

Do not set:

```text
SUPABASE_SERVICE_ROLE_KEY
SUPABASE_JWT_SECRET
```

For this project, JWT validation uses JWKS.

## Secret Handling

Never commit or paste these values into chat:

- Supabase DB password
- `a2cr_app` DB password
- Google OAuth Client Secret
- Supabase secret keys / service role keys
- Railway variables containing secrets
- `FERNET_KEY`
- `API_KEY_HASH_SECRET`
- `AUDIT_HASH_SECRET`

Allowed to record in docs:

- Domain names
- Supabase project ref
- Supabase project URL
- JWKS URL
- Google Cloud project ID
- OAuth redirect URI

## Build And Deploy

1. Confirm `main` is green locally:

```bash
python -m pytest -q
cd web
npm ci
npm run build
```

2. For every production migration, record this review before running SQL:

- purpose
- expected affected objects
- expected changed row count for data changes
- lock risk and whether user traffic should be paused
- readiness check impact
- forward-fix plan

Prefer small migrations and non-blocking indexes. Run the SQL first on a staging-like database, then check pending migrations without printing `DATABASE_URL`:

```bash
python scripts/check_migrations.py
```

3. Apply all Supabase migrations in order before deploying app code that depends on them:

```text
supabase/migrations/001_base_schema.sql
supabase/migrations/002_workthreads.sql
supabase/migrations/003_contexts_user_scoped_unique_repair.sql
supabase/migrations/004_contexts_encryption_mode.sql
supabase/migrations/005_contexts_client_encrypted_only.sql
supabase/migrations/006_db_resilience_baseline.sql
supabase/migrations/007_workthreads_message_uniqueness.sql
```

4. Create a Railway service from the GitHub repository.

5. Confirm Railway uses `Dockerfile` and `railway.json`.

6. Add the variables above.

7. Deploy. The Dockerfile builds React first, installs Python dependencies, copies `web/dist`, then starts:

```bash
uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
```

## Supabase Auth URL Configuration

After Railway is deployed and `a2cr.app` points to it, configure Supabase Auth URLs:

```text
Site URL: https://a2cr.app
Redirect URLs:
- https://a2cr.app
- https://a2cr.app/login
- https://a2cr.app/dashboard
```

Keep the Google OAuth redirect URI in Google Cloud as:

```text
https://pemqlmrochfnwthslxco.supabase.co/auth/v1/callback
```

## Smoke Checks

Run after every deploy:

```bash
curl -fsS https://a2cr.app/api/v1/health
curl -fsS https://a2cr.app/api/v1/health/readiness
curl -fsS https://a2cr.app/dashboard | head
```

Expected:

- health returns `{"status":"ok"}`
- readiness returns `ready: true`; if it returns 503, apply/fix migrations before routing users to the deploy
- `/dashboard` returns the SPA shell
- `/api/missing` returns 404
- direct reload of `/login`, `/settings`, and `/pricing` returns the SPA shell
- requests with an unexpected `Origin` are rejected with 403
- Google login works through Supabase Auth
- Dashboard can issue an API key once
- MCP `resume_context` works from a fresh AI window
- Dashboard context and WorkThreads responses are metadata-only

## Hot Query And Index Review

Review `EXPLAIN` on production-like data before public beta and after migrations
that touch these paths:

- dashboard context list, stats, and access logs
- context save/load/resume/delete
- hourly rate-limit counts over `access_logs`
- WorkThreads list/read/update/wait/task claim

Required index coverage:

- `contexts(user_id, expires_at)`
- `contexts(user_id, slot_number)`
- `contexts(expires_at)`
- `access_logs(user_id, created_at DESC)`
- `access_logs(user_id, action, created_at DESC)`
- WorkThreads user/thread/message/task indexes from `002_workthreads.sql`

Keep user-facing list/read routes bounded by explicit limits.

## Troubleshooting Dashboard Request Failed

If `/dashboard` loads the profile/header but shows a red `Request failed` banner,
check Railway logs for `/api/dashboard/contexts` or `/api/dashboard/stats`.
After the WorkBaton client-encryption update, those endpoints require
`public.contexts.encryption_mode`. Apply these migrations if the column or
constraint is missing:

```text
supabase/migrations/004_contexts_encryption_mode.sql
supabase/migrations/005_contexts_client_encrypted_only.sql
```

This is a Supabase schema migration, not a Railway/Vite variable change.

## Troubleshooting New Slot Saves

If overwriting an existing WorkBaton Slot works but saving a new Slot returns 500,
first ensure the app version calls `SELECT app.expire_contexts()` before slot
capacity checks. This prevents expired rows from blocking new inserts while the
scheduled cleanup job is delayed.

Then check whether an older global unique constraint remains on
`contexts.slot_name` or `contexts.slot_number`:

```sql
SELECT conname, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'public.contexts'::regclass
  AND contype = 'u'
ORDER BY conname;

SELECT indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename = 'contexts'
  AND indexdef ILIKE '%UNIQUE%'
ORDER BY indexname;
```

Expected uniqueness is per user:

```text
UNIQUE (user_id, slot_name)
UNIQUE (user_id, slot_number)
```

If `UNIQUE (slot_name)` or `UNIQUE (slot_number)` appears, apply
`supabase/migrations/003_contexts_user_scoped_unique_repair.sql`.

## Cleanup Job

Create a protected Railway job using the same image and variables:

```bash
python -m services.maintenance expire-contexts
```

Recommended initial schedule: every 10 minutes.

The job only calls `SELECT app.expire_contexts()`. The database function logs `context.expire` with sanitized metadata and deletes only expired rows. It does not decrypt context bodies.

Access logs are operational data. Prune old rows in batches with:

```sql
SELECT app.prune_access_logs(interval '30 days', 1000);
```

Run repeated batches only as needed, and confirm stats counters still represent totals rather than relying on retained raw logs.

## Rollback

1. Roll back the Railway deployment to the previous successful image.
2. Do not roll back database migrations unless a specific migration is proven faulty.
3. If a secret may be exposed, revoke/rotate it before redeploying.
4. Confirm `/api/v1/health`, `/dashboard`, and `/mcp` after rollback.
