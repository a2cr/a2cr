# A2CR Staging Environment Implementation Plan

Last updated: 2026-05-07

Status: Not started

This plan turns `docs/runbooks/staging-design.md` into concrete work. The plan
assumes staging is intentionally non-public: it uses separate infrastructure,
separate secrets, test-only users, test-only data, and access restrictions where
practical.

## Japanese Summary

STG作業はまだ未着手です。最初に Supabase の `a2cr-staging` project を作り、
次に migration、test user、Railway STG service、STG variables、Auth設定、
smoke test の順で進めます。secret値はchat、docs、Git、screenshotに残しません。

## Success Criteria

Staging setup is complete when:

- Supabase STG project exists
- Railway STG service exists
- STG deploy is healthy
- STG readiness passes
- STG migration check passes
- STG RLS/pooler smoke passes
- STG login works
- STG dashboard/API/MCP smoke passes
- STG redeploy or rollback has been tested
- STG is not generally visible or usable by the public
- No production data or production secrets are used in STG
- `docs/runbooks/deploy.md` records the final STG project name and public origin

## Phase 0: Safety Preparation

Status: Ready

### Task 0.1: Confirm environment names

Work:

- Treat `a2cr-production` as production Supabase
- Treat `graceful-nurturing` as the production Railway candidate until confirmed
- Choose `a2cr-staging` for Supabase STG
- Use `heroic-enchantment` or create `a2cr-staging` for Railway STG
- Start with the Railway generated URL for STG
- Add `stg.a2cr.app` only after deciding how to restrict access

Verify:

- Supabase dashboard clearly shows separate production and STG projects
- Railway dashboard clearly shows separate production and STG services/projects
- Operator checks the project name before every destructive action

### Task 0.2: Confirm secret handling

Work:

- Store secrets only in Supabase, Railway, or a password manager
- Do not paste secret values into chat, docs, Git, tickets, or screenshots
- Use placeholders in all notes

Never paste:

- `DATABASE_URL`
- DB passwords
- Supabase service-role key
- OAuth client secret
- Railway secret variables
- `FERNET_KEY`
- `API_KEY_HASH_SECRET`
- `AUDIT_HASH_SECRET`
- local client key material

Verify:

- Screenshots do not show secret values
- Docs contain only placeholders and public URLs

## Phase 1: Create Supabase STG

Status: Ready

### Task 1.1: Create the STG project

Work:

1. Open Supabase dashboard
2. Create a new project named `a2cr-staging`
3. Choose Tokyo region when practical
4. Generate a STG-only DB password
5. Store the password outside chat/docs/Git
6. Wait until the project is healthy

Verify:

- Supabase project selector shows both `a2cr-production` and `a2cr-staging`
- STG project overview shows healthy database status

### Task 1.2: Apply migrations to STG

Work:

Apply repository migrations in order:

```text
supabase/migrations/001_base_schema.sql
supabase/migrations/002_workthreads.sql
supabase/migrations/003_contexts_user_scoped_unique_repair.sql
supabase/migrations/004_contexts_encryption_mode.sql
supabase/migrations/005_contexts_client_encrypted_only.sql
supabase/migrations/006_db_resilience_baseline.sql
supabase/migrations/007_workthreads_message_uniqueness.sql
supabase/migrations/008_data_lifecycle_scan.sql
```

Verify:

```bash
python scripts/check_migrations.py
```

Expected:

- No pending migrations
- No DB URL or password printed

### Task 1.3: Create STG test users

Work:

- Create two STG-only test users through Supabase Auth or Google login
- Do not use real customer accounts
- Record only their UUIDs where needed for smoke commands

Verify:

- Two distinct STG user UUIDs exist
- Tokens and passwords are not pasted into chat/docs/Git

## Phase 2: Create Railway STG

Status: Start after Supabase STG is healthy

### Task 2.1: Create the STG service

Work:

1. Open Railway
2. Use `heroic-enchantment` or a new dedicated `a2cr-staging` project
3. Add a service from the GitHub repository
4. Confirm Railway uses the repository `Dockerfile`
5. Confirm healthcheck path is `/api/v1/health`

Verify:

- Railway has one STG service
- Production service is unchanged
- STG deploy reaches an active or healthy state

### Task 2.2: Add STG variables

Work:

Set runtime variables:

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

Set browser build variables:

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

Verify:

- Railway deploy does not fail startup validation
- Logs do not contain secret values
- STG does not connect to production Supabase

## Phase 3: Configure STG Auth And Visibility

Status: Start after Railway STG origin is known

### Task 3.1: Configure Supabase Auth redirect URLs

Work:

Set in Supabase STG:

```text
Site URL: <STG origin>
Redirect URLs:
- <STG origin>
- <STG origin>/login
- <STG origin>/dashboard
```

If Google OAuth is enabled, add the STG Supabase callback URL to the Google
OAuth client or create a STG-only OAuth client.

Verify:

- Google login returns to the STG dashboard
- Google login does not return to `https://a2cr.app`

### Task 3.2: Keep STG non-public

Work:

- Do not link STG from production pages
- Do not publish STG as a beta URL
- Keep data test-only
- If using `stg.a2cr.app`, put it behind Cloudflare Access or equivalent
- If Cloudflare Access is not configured yet, treat the Railway URL as
  internet-exposed and do not put sensitive data there

Verify:

- A non-tester cannot use dashboard workflows
- STG contains no production data
- STG is not linked from the public product site

## Phase 4: Run STG Smoke Tests

Status: Start after deploy and Auth configuration

### Task 4.1: Hosted checks

Work:

```bash
curl -fsS <STG origin>/api/v1/health
curl -fsS <STG origin>/api/v1/health/readiness
curl -fsS <STG origin>/dashboard
```

Verify:

- Health returns `{"status":"ok"}`
- Readiness returns ready
- Dashboard returns the SPA shell

### Task 4.2: Migration check

Work:

```bash
set DATABASE_URL=<STG_SUPABASE_TRANSACTION_POOLER_DATABASE_URL>
python scripts/check_migrations.py
```

Verify:

- Output reports all migrations applied
- No DB URL, password, token, or Authorization header is printed

### Task 4.3: RLS/pooler smoke

Work:

```bash
set DATABASE_URL=<STG_SUPABASE_TRANSACTION_POOLER_DATABASE_URL>
set A2CR_SMOKE_USER_A_ID=<STG_TEST_USER_A_UUID>
set A2CR_SMOKE_USER_B_ID=<STG_TEST_USER_B_UUID>
python scripts/smoke_rls_pooler.py
```

Verify:

- Output is exactly `RLS/pooler smoke: PASS`
- User A cannot see user B rows
- User B cannot see user A rows
- Transaction-local `app.user_id` resets after each transaction
- No DB URL, token, API key, password, or row content is printed

### Task 4.4: Dashboard and MCP smoke

Work:

1. Log in to the STG dashboard
2. Issue a STG API key
3. Configure an AI/MCP client with the STG URL and STG API key
4. Save, resume, load, list, and delete a test WorkBaton slot
5. Exercise basic WorkThreads flows with test-only data
6. Revoke the STG API key

Verify:

- Test-only data flows work
- Dashboard shows metadata only
- Full API key appears only at issue time
- Revoked key no longer authenticates
- Logs do not expose bodies, API keys, tokens, DB URLs, or local client keys

## Phase 5: Operational Drills

Status: Start after basic STG smoke passes

### Task 5.1: Railway redeploy or rollback drill

Work:

- Trigger a STG redeploy or roll back to a previous STG deploy
- Re-run health/readiness checks

Verify:

- Production is unaffected
- STG can be redeployed or rolled back independently

### Task 5.2: Secret rotation dry run

Work:

- Rotate one STG-only secret, for example `AUDIT_HASH_SECRET`
- Redeploy STG
- Re-run smoke checks

Verify:

- STG starts successfully
- Production secrets are unchanged
- Logs do not expose the rotated secret

### Task 5.3: Restore drill preparation

Work:

- Do not restore production data into STG until production backups or scheduled
  exports are enabled
- Before any restore drill, choose whether the target is `a2cr-staging` or a
  temporary project such as `a2cr-restore-drill`
- Write the cleanup/deletion plan before restoring

Verify:

- Restore target and cleanup plan are documented before destructive work
- No real customer data is used in ordinary STG smoke tests

## Final Documentation Update

After STG passes the acceptance criteria, update `docs/runbooks/deploy.md` with:

- final Supabase STG project name
- final Railway STG service/project name
- STG origin
- whether Cloudflare Access or another access control is enabled
- date of latest STG smoke pass
- date of latest STG redeploy or rollback drill

