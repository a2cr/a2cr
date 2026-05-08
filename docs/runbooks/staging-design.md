# A2CR Staging Environment Design

Last updated: 2026-05-07

This document defines the intended staging environment for A2CR. Staging is a
non-public validation environment. It is production-like enough to test deploys,
migrations, auth, RLS, MCP, and rollback paths, but it must be isolated from
production data, production secrets, and normal users.

## Japanese Summary

STG は一般公開しない検証環境です。本番と同じコードを動かしますが、
Supabase project、Railway service、secret、test user、data は本番から分離します。
URLを知っているだけで安全とは扱わず、ログイン必須、STG専用データ、必要に応じた
Cloudflare Access などのアクセス制限で守ります。

## Current Status

As of the 2026-05-07 hosted setup check:

- Production-like Supabase project exists: `a2cr-production`
- No separate Supabase staging project has been confirmed
- Railway project `graceful-nurturing` is the current production candidate
- Railway project `heroic-enchantment` is empty and can be used as the first
  staging candidate
- `stg.a2cr.app` is not configured

Therefore, staging is not created yet. Only design and implementation guidance
exists.

## Goals

Staging must let us verify these changes before touching production:

- Supabase migrations from `001` through the latest repository migration
- `/api/v1/health` and `/api/v1/health/readiness`
- Supabase Auth and Google login callback behavior
- RLS isolation through the Supabase transaction pooler
- Dashboard metadata-only behavior
- API key issue and revoke flows
- MCP save, resume, load, list, and delete flows with test-only data
- WorkThreads smoke behavior with test-only data
- Railway deploy, restart, logs, redeploy, and rollback
- Cleanup and data-lifecycle maintenance commands
- Secret rotation dry runs
- Restore drill preparation after backups or scheduled exports exist

## Non-Goals

Staging is not:

- a public beta environment
- an automatic production failover target
- a hot standby database
- a place for real customer data
- a place for production API keys, production DB passwords, production OAuth
  secrets, or local client key material
- a substitute for production backups and restore drills

## Environment Shape

Production:

| Layer | Production |
| --- | --- |
| Domain | `https://a2cr.app` |
| Railway | `graceful-nurturing`, unless a later canonical production service is chosen |
| Supabase | `a2cr-production` |
| App env | `APP_ENV=production` |
| Data | real beta/production data after launch |

Staging:

| Layer | Staging |
| --- | --- |
| Domain | Initially Railway generated URL; later `https://stg.a2cr.app` if access control is added |
| Railway | `heroic-enchantment` or a dedicated `a2cr-staging` project |
| Supabase | new dedicated project such as `a2cr-staging` |
| App env | `APP_ENV=staging` |
| Data | test users and test data only |

## Visibility And Access

Staging should not be discoverable or usable by the general public.

Minimum baseline:

- Do not link staging from public product pages
- Do not index staging in public search metadata
- Require Supabase login for dashboard workflows
- Use only STG test users
- Use only STG API keys
- Keep production data out of STG
- Do not use production secrets in STG

Recommended once `stg.a2cr.app` is introduced:

- Put `stg.a2cr.app` behind Cloudflare Access or an equivalent allowlist
- Restrict access to the operator's account or a small tester group
- Keep the Railway generated URL unshared, or rotate/regenerate it if it leaks

URL secrecy alone is not access control. If a staging URL can be reached by
anyone who knows it, treat it as internet-exposed and keep all data fake.

## Isolation Rules

Never share these between production and staging:

- `DATABASE_URL`
- Supabase project ref
- Supabase Auth callback URL
- Railway variables
- `FERNET_KEY`
- `API_KEY_HASH_SECRET`
- `AUDIT_HASH_SECRET`
- Google OAuth client secret
- test user accounts
- API keys
- local client key material

Allowed to share:

- GitHub repository
- Dockerfile
- application code
- migration files
- CI checks
- public documentation with placeholders

## Supabase Staging Design

Create a dedicated Supabase project, preferably named `a2cr-staging`.

Configuration:

- Use the same region as production when practical, currently Tokyo
- Apply repository migrations in order
- Enable RLS for user-owned tables
- Create/use the least-privileged runtime role equivalent to `a2cr_app`
- Use a STG-only DB password
- Configure Supabase Auth for the STG origin
- Configure Google provider callback for the STG Supabase project
- Do not put `SUPABASE_SERVICE_ROLE_KEY` into Railway runtime variables

Supabase Free is acceptable for early STG with fake data. Production must have
backups or scheduled exports before beta or restore testing.

## Railway Staging Design

Use `heroic-enchantment` as the first staging candidate, or create a dedicated
Railway project named `a2cr-staging`.

Configuration:

- Deploy from the same GitHub repository
- Use the repository `Dockerfile` and `railway.json`
- Set `APP_ENV=staging`
- Set `A2CR_SERVICE_URL` to the STG origin plus `/mcp`
- Set `A2CR_PUBLIC_ORIGIN` to the STG origin
- Use Supabase STG JWKS/JWT settings
- Use STG-only runtime secrets
- Use healthcheck path `/api/v1/health`

Do not copy production Railway variables wholesale into staging.

## Required Staging Variables

Runtime variables:

```text
APP_ENV=staging
DATABASE_URL=<STG Supabase transaction pooler URL for a2cr_app>
FERNET_KEY=<STG-only Fernet key>
API_KEY_HASH_SECRET=<STG-only 32+ char secret>
AUDIT_HASH_SECRET=<STG-only 32+ char secret>
A2CR_SERVICE_URL=<STG origin>/mcp
A2CR_PUBLIC_ORIGIN=<STG origin>
A2CR_API_KEY_PREFIX=sk-a2cr
SUPABASE_JWKS_URL=<STG Supabase JWKS URL>
SUPABASE_JWT_AUDIENCE=authenticated
SUPABASE_JWT_ISSUER=<STG Supabase issuer URL>
```

Browser build variables:

```text
VITE_SUPABASE_URL=<STG Supabase URL>
VITE_SUPABASE_ANON_KEY=<STG Supabase publishable/anon key>
VITE_A2CR_SERVICE_URL=<STG origin>/mcp
VITE_A2CR_API_BASE=
```

Do not set:

```text
SUPABASE_SERVICE_ROLE_KEY
SUPABASE_JWT_SECRET
```

## Acceptance Criteria

Staging is considered usable only after all of these pass:

- Supabase STG project exists and is healthy
- Railway STG service exists and is healthy
- STG deploy is active
- `/api/v1/health` returns `{"status":"ok"}`
- `/api/v1/health/readiness` returns ready
- `python scripts/check_migrations.py` shows no pending migrations against STG
- `python scripts/smoke_rls_pooler.py` passes with two STG test users
- Google login returns to the STG dashboard, not production
- Dashboard can issue and revoke a STG API key
- MCP save/resume/load/list/delete works with test-only data
- WorkThreads smoke behavior works with test-only data
- Logs do not expose DB URLs, tokens, API keys, passwords, row content, or local
  client key material
- Railway redeploy or rollback has been tried in STG only
- Production data and production secrets are not used in STG

