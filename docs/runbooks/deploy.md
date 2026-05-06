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
- Supabase migrations applied through SQL Editor:
  - `supabase/migrations/001_base_schema.sql`
  - `supabase/migrations/002_workthreads.sql`
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

2. Create a Railway service from the GitHub repository.

3. Confirm Railway uses `Dockerfile` and `railway.json`.

4. Add the variables above.

5. Deploy. The Dockerfile builds React first, installs Python dependencies, copies `web/dist`, then starts:

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
curl -fsS https://a2cr.app/dashboard | head
```

Expected:

- health returns `{"status":"ok"}`
- `/dashboard` returns the SPA shell
- `/api/missing` returns 404
- direct reload of `/login`, `/settings`, and `/pricing` returns the SPA shell
- requests with an unexpected `Origin` are rejected with 403
- Google login works through Supabase Auth
- Dashboard can issue an API key once
- MCP `resume_context` works from a fresh AI window
- Dashboard context and WorkThreads responses are metadata-only

## Cleanup Job

Create a protected Railway job using the same image and variables:

```bash
python -m services.maintenance expire-contexts
```

Recommended initial schedule: every 10 minutes.

The job only calls `SELECT app.expire_contexts()`. The database function logs `context.expire` with sanitized metadata and deletes only expired rows. It does not decrypt context bodies.

## Rollback

1. Roll back the Railway deployment to the previous successful image.
2. Do not roll back database migrations unless a specific migration is proven faulty.
3. If a secret may be exposed, revoke/rotate it before redeploying.
4. Confirm `/api/v1/health`, `/dashboard`, and `/mcp` after rollback.
