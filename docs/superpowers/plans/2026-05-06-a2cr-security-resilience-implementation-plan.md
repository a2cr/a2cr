# A2CR Security and Resilience Implementation Plan

Status: Draft, working implementation plan
Date: 2026-05-06

Important: This implementation plan is an internal planning document. It does not need to be committed or pushed unless the user explicitly asks.

Related spec: `docs/superpowers/specs/2026-05-06-a2cr-security-resilience-plan.md`

## Goal

Harden A2CR against realistic attacks and operational failures without overstating the product guarantee.

Success means:

- WorkBaton plaintext remains outside A2CR.
- Customer/account metadata is protected as SaaS data.
- Missing migrations and bad deploys are detected before users hit broken dashboard/API flows.
- Incidents and outages have concrete response and recovery procedures.
- The beta service can be operated with known RTO/RPO targets.

## Non-Goals

- Do not implement SOC 2 / ISO 27001 compliance in this plan.
- Do not promise that customer metadata cannot leak.
- Do not claim WorkThreads has the same client-encrypted guarantee as WorkBaton until redesigned.
- Do not add speculative enterprise admin features before core hardening is complete.

## Phase 0: Truthful Security Baseline

Status: Ready to start
Priority: P0

### Task 0.1: Update Public Security Claims

Scope:

- `SECURITY.md`
- `docs/runbooks/security.md`
- website guide copy if needed

Implementation:

- State that WorkBaton bodies are client-encrypted and not decryptable by A2CR.
- State that account data, usage metadata, access logs, and operational data remain protected SaaS data and may be exposed in a server/DB incident.
- Explicitly exclude WorkThreads from the WorkBaton client-encryption guarantee.

Verify:

- Search docs for absolute claims such as "nothing leaks", "zero knowledge", or "cannot leak".
- Confirm public docs distinguish body secrecy from metadata/customer-data exposure.

### Task 0.2: Define Incident Roles and Contact Path

Scope:

- `SECURITY.md`
- `docs/runbooks/security.md`

Implementation:

- Define security contact path: private GitHub advisory until a support address exists.
- Define incident commander, technical lead, communications owner, and decision maker for shutdown/rollback.
- Add "do not paste secrets into chat/tickets" rule.

Verify:

- `SECURITY.md` has a concrete private report path.
- Incident runbook can be followed by a new maintainer.

## Phase 1: Fail Closed on Schema and Runtime Drift

Status: Ready to start
Priority: P0

### Task 1.1: Add Web Schema Readiness Check

Scope:

- Create `services/schema_readiness.py`
- Update `main.py` lifespan or health routes
- Add tests in `tests/test_deployment.py` or new `tests/test_schema_readiness.py`

Implementation:

- Check required tables: `user_profiles`, `contexts`, `stats`, `api_keys`, `access_logs`, WorkThreads tables if enabled.
- Check required columns: `contexts.encryption_mode`, `contexts.encryption_version`, `contexts.encryption_metadata`, slot number fields, stats counters.
- Check required functions: `app.current_user_id`, `app.resolve_api_key`, `app.record_context_save`, `app.record_context_load`, `app.record_context_delete`, `app.expire_contexts`.
- Check uniqueness: `(user_id, slot_name)` and `(user_id, slot_number)`.
- Check RLS enabled on user-owned tables.
- Add `/api/v1/health/readiness` returning safe status without secrets.
- In production, fail startup or readiness when required schema is missing.

Verify:

- Unit tests simulate missing column/function/constraint.
- Hosted smoke can call readiness before dashboard testing.
- A missing `encryption_mode` column cannot produce a vague dashboard `Request failed`.

### Task 1.2: Track Migration State

Scope:

- Supabase migrations
- New migration table or metadata function
- Deploy runbook

Implementation:

- Create `app.schema_migrations` or use a Supabase-compatible migration record.
- Record applied migration IDs for `001` through current.
- Add a small script to print pending migrations.
- Keep manual SQL snippets out of normal operations once migration tracking exists.

Verify:

- Running the script on production-like DB shows all expected migration IDs.
- Applying a migration twice is safe or rejected with a clear message.

## Phase 1.5: Database Timeout, Locking, and Concurrency Safety

Status: Ready to start
Priority: P0

### Task 1.5.1: Add DB Pool and Transaction Timeouts

Scope:

- `services/db.py`
- `services/config.py`
- tests in `tests/test_deployment.py` or `tests/test_db_resilience.py`

Implementation:

- Configure the web SQLAlchemy engine with explicit `pool_size`, `max_overflow`, `pool_timeout`, `pool_recycle`, and existing `pool_pre_ping`.
- Add safe environment defaults for production and staging.
- In `web_transaction`, set transaction-local PostgreSQL timeouts:
  - `statement_timeout`
  - `lock_timeout`
  - `idle_in_transaction_session_timeout`
- Keep timeout values short enough to avoid request pileups but long enough for normal save/load/dashboard queries.
- Do not set these for the local SQLite prototype.

Verify:

- Tests assert web runtime creates an engine with bounded pool settings.
- Fake-session tests assert transaction-local timeout statements are executed before application SQL.
- A slow/blocked query cannot wait indefinitely.

### Task 1.5.2: Classify DB Deadlock, Timeout, and Conflict Errors

Scope:

- New helper such as `services/db_errors.py`
- `main.py` exception handling
- DB-facing services where domain-specific conflicts are expected
- tests in `tests/test_db_resilience.py`

Implementation:

- Classify PostgreSQL SQLSTATE codes:
  - `40P01`: deadlock detected
  - `40001`: serialization failure
  - `55P03`: lock not available
  - `57014`: query canceled / statement timeout
  - `23505`: unique violation
- Return safe application errors:
  - retryable deadlock/serialization/lock timeout: 503 or 409 with `Retry-After`
  - user-caused unique slot conflict: 409
  - unexpected DB failure: generic 500 with request ID
- Never include SQL text, DB URL, headers, request bodies, stack traces, or raw exception repr in client responses.
- Log only safe diagnostic code, request ID, route/action, and SQLSTATE.

Verify:

- Unit tests simulate each SQLSTATE and assert response code/message.
- Error hygiene tests prove SQL and secrets do not appear in JSON responses.

### Task 1.5.3: Serialize WorkBaton Slot Mutations

Scope:

- `services/web_context.py`
- `services/limits.py`
- Supabase migration if advisory-lock helper or constraint change is needed
- concurrent tests

Implementation:

- Serialize save/delete mutations for one user's WorkBaton slots using one of:
  - PostgreSQL advisory transaction lock keyed by user id, or
  - `SELECT ... FOR UPDATE` on the user's `user_profiles` row.
- Keep the critical section small: expire old rows, check plan/capacity, assign slot number, insert/update/delete, write stats/logs.
- Preserve existing per-user unique constraints on `(user_id, slot_name)` and `(user_id, slot_number)`.
- Handle unique violations as safe conflicts instead of leaking DB errors.
- Retry only idempotent operations. Do not blindly retry save mutations unless the request has an idempotency key or the overwrite target is deterministic.

Verify:

- Concurrent saves to the same slot produce one final row and no 500.
- Concurrent saves to different new Free slots cannot exceed 3 active slots.
- Concurrent saves racing on slot number return success/conflict deterministically.
- Delete/save races do not expose another user's row.

### Task 1.5.4: Harden WorkThreads Concurrent Writes

Scope:

- `services/workthreads.py`
- `supabase/migrations/*`
- tests in `tests/test_workthreads.py` or `tests/test_db_resilience.py`

Implementation:

- Lock the target `work_threads` row with `FOR UPDATE` while enforcing loop guard and inserting a message.
- Add or confirm unique indexes for:
  - `(thread_id, idempotency_key)` when `idempotency_key IS NOT NULL`
  - `(thread_id, content_hash)` if duplicate-content rejection remains a product rule
- Keep `claim_workthread_task` on `FOR UPDATE SKIP LOCKED`.
- Keep long polling outside any long-lived DB transaction.
- Cap `wait_workthread_updates` and ensure repeated waits cannot exhaust DB connections.

Verify:

- Concurrent `question` posts cannot bypass unresolved-question or consultation limits.
- Duplicate idempotency/content hash races return 409, not duplicate rows.
- Multiple agents can claim different tasks without blocking each other.

### Task 1.5.5: Add DB-Protective Abuse Limits

Scope:

- `services/limits.py`
- `routers/dashboard.py`
- `routers/web_context.py`
- `routers/mcp_http.py`
- WorkThreads routes/tools
- Cloudflare/Railway notes

Implementation:

- Add per-IP rate limits for invalid JWT/API key attempts.
- Add per-user limits for:
  - context delete
  - dashboard refresh/list endpoints
  - API key issue/revoke
  - WorkThreads create/message/read/wait/task claim
- Add a stricter cap for concurrent or repeated `wait_workthread_updates` calls.
- Keep plan limits for normal save/load, but treat abuse limits as operational protection rather than product entitlement.
- Prefer edge/WAF throttles for anonymous bursts and app-level limits for authenticated user-aware actions.

Verify:

- Repeated invalid auth returns 429 without hitting expensive DB paths repeatedly.
- Repeated dashboard refresh/delete/API-key mutation returns 429.
- WorkThreads wait/read bursts return 429 or bounded timeout rather than tying up DB connections.

## Phase 1.6: Database Operations Hardening

Status: Ready to start
Priority: P0/P1

### Task 1.6.1: Add Migration Safety Checklist and Dry-Run Flow

Scope:

- Supabase migrations
- `docs/runbooks/deploy.md`
- new helper script if useful

Implementation:

- Require each production migration to state:
  - purpose
  - expected affected objects
  - expected row count when data is changed
  - lock risk
  - readiness check impact
  - forward-fix plan
- Split heavy schema/data changes into small migrations.
- Prefer non-blocking index creation where available.
- Add staging-like dry-run steps before production SQL.
- Document when to pause user traffic or delay deploy.

Verify:

- Deploy runbook includes migration dry-run and lock-risk checklist.
- New migrations cannot skip readiness impact notes.

### Task 1.6.2: Review Hot Queries and Add Index Coverage

Scope:

- `services/web_context.py`
- `services/dashboard.py`
- `services/workthreads.py`
- `supabase/migrations/*`
- tests or docs for query/index expectations

Implementation:

- List hot queries for:
  - dashboard context list/stats/access logs
  - context save/load/resume/delete
  - hourly rate-limit counts
  - WorkThreads list/read/unread/update/wait/task claim
- Confirm each hot query has a user-scoped index and bounded result limit.
- Add targeted indexes for `access_logs(user_id, action, created_at)`, WorkThreads read/update paths, and expiry paths if missing.
- Add `EXPLAIN` review steps to the deploy runbook for production-like data volume.

Verify:

- Query/index checklist exists.
- Tests or static checks confirm key index definitions are present in migrations.
- No dashboard or WorkThreads list route exposes an unbounded `LIMIT`.

### Task 1.6.3: Add Access Log Retention and Bloat Controls

Scope:

- Supabase migrations/functions
- `services/maintenance.py`
- deploy/operations runbook
- tests

Implementation:

- Add a safe retention job for `access_logs` based on plan or global retention policy.
- Keep access-log pruning batched so it does not lock or bloat tables aggressively.
- Keep stats counters separate from raw logs so deleting old logs does not break totals.
- Define when to add partitioning if log volume grows.
- Monitor table size and slow log queries before public beta.

Verify:

- Retention job deletes only old rows and never stores/returns secrets.
- Stats remain correct after old logs are pruned.
- Runbook explains how to inspect table size and bloat symptoms.

### Task 1.6.4: Verify RLS, Pooler, and Transaction Context in Hosted Environment

Scope:

- hosted smoke tests
- `services/db.py`
- deploy runbook

Implementation:

- Add a hosted smoke test using two users:
  - user A cannot list/load/delete user B contexts.
  - user A cannot see user B WorkThreads metadata.
  - API key auth and dashboard JWT auth both set transaction-local `app.user_id`.
- Verify the Supabase connection mode does not break transaction-local RLS context.
- Keep `SET LOCAL` / `set_config(..., true)` inside every `web_transaction`.

Verify:

- Hosted user A/B smoke passes against the actual deployment connection string.
- RLS context is reset between requests and cannot leak across pooled connections.

### Task 1.6.5: Harden Data Lifecycle: Expiry, Downgrade, and Account Delete

Scope:

- WorkBaton expiry
- WorkThreads expiry/future retention
- billing/effective-plan implementation plan
- account deletion implementation plan

Implementation:

- Keep expiry jobs non-decrypting and metadata-only.
- Define Pro-to-Free downgrade behavior:
  - existing over-limit data is not automatically destroyed
  - read/delete remains allowed
  - new saves are blocked until within Free limits
- Define account deletion behavior:
  - revoke API keys
  - delete WorkBaton rows
  - delete or retain access logs according to privacy/abuse policy
  - delete WorkThreads rows when implemented
  - delete Supabase Auth user only after product data cleanup succeeds
- Add orphan-row maintenance checks.

Verify:

- Downgrade tests cover over-slot and over-size state.
- Account delete dry-run/checklist describes exactly what will be removed.
- Orphan scan finds no rows after deletion test.

### Task 1.6.6: Add SECURITY DEFINER and Manual SQL Review

Scope:

- Supabase migrations
- `docs/runbooks/security.md`
- `docs/runbooks/deploy.md`
- tests in `tests/test_rls.py`

Implementation:

- Audit all `SECURITY DEFINER` functions.
- Require fixed `search_path`.
- Require least returned data.
- Avoid dynamic SQL unless specifically reviewed.
- Add a manual SQL checklist:
  - run inside transaction where possible
  - confirm expected row count
  - never paste secrets
  - capture purpose and forward-fix plan

Verify:

- Static tests assert `SECURITY DEFINER` functions set `search_path`.
- Runbook has manual SQL safety checklist.

## Phase 2: HTTP and API Attack Surface Hardening

Status: Planned
Priority: P0

### Task 2.1: Add Security Headers Middleware

Scope:

- `main.py`
- tests in `tests/test_deployment.py`

Implementation:

- Add `Strict-Transport-Security` in production.
- Add `X-Content-Type-Options: nosniff`.
- Add `Referrer-Policy: strict-origin-when-cross-origin` or stricter.
- Add `X-Frame-Options: DENY` or CSP `frame-ancestors 'none'`.
- Add `Permissions-Policy` with unnecessary browser features disabled.
- Add CSP after testing required Supabase/Auth connections:
  - `default-src 'self'`
  - `base-uri 'self'`
  - `object-src 'none'`
  - `frame-ancestors 'none'`
  - `connect-src 'self' https://*.supabase.co`
  - keep script/style rules compatible with Vite output before tightening.

Verify:

- Tests assert headers on `/`, `/dashboard`, `/api/v1/health`, `/mcp`.
- Browser login still works.
- No inline guide/static rendering breaks.

### Task 2.2: Add Rate Limiting and Abuse Controls

Scope:

- auth paths in `routers/dashboard.py`, `routers/web_context.py`, `routers/mcp_http.py`
- `services/limits.py`
- Cloudflare/Railway configuration notes

Implementation:

- Add per-IP unauthenticated failure limits for invalid JWT/API key attempts.
- Add per-user authenticated limits for save/load/delete beyond existing hourly plan checks.
- Add stricter limits for API key issue/revoke.
- Add response code and safe message for rate-limited requests.
- Prefer provider/WAF limits for edge traffic, app limits for account-aware controls.

Verify:

- Tests for repeated invalid auth returning 429.
- Tests for valid traffic below threshold still passing.
- Access logs do not store raw tokens or raw IPs.

### Task 2.3: Improve Error Hygiene

Scope:

- `main.py`
- service exception handling
- tests

Implementation:

- Convert unexpected DB/schema errors into generic 500 with request ID.
- Log safe diagnostic code server-side without body/secrets.
- Keep validation errors useful but not secret-revealing.

Verify:

- Simulated DB error does not leak SQL, DB URL, stack trace, Authorization header, or request body.
- Client sees a stable error shape.

## Phase 2.5: Attack-Specific Regression Backlog

Status: Planned
Priority: P0/P1

Related spec section: Attack-Specific Countermeasure Matrix.

### Task 2.5.1: Add Abuse-Case Regression Tests

Scope:

- `tests/test_security_abuse_cases.py`
- existing dashboard/API/MCP tests

Implementation:

- Add tests for:
  - user A cannot access user B objects by changing `slot_name`, `slot_number`, `thread_id`, or `task_id`
  - dashboard metadata route never returns WorkBaton body
  - remote MCP save remains disabled
  - plaintext WorkBaton save remains rejected
  - oversized ciphertext and malformed encrypted envelopes are rejected
  - unexpected browser Origin is rejected in production/staging
  - error responses do not include SQL, stack traces, DB URLs, Authorization headers, or request bodies

Verify:

- Tests fail if a future route forgets user scoping or returns plaintext.
- Tests run in normal `python -m pytest -q`.

### Task 2.5.2: Add Metadata XSS and CSV Injection Tests

Scope:

- dashboard API tests
- frontend rendering tests if available
- future export code if added

Implementation:

- Use hostile slot names/model sources/request IDs in tests, such as script-like strings and spreadsheet-formula-like strings.
- Confirm API accepts only allowed slot name characters.
- Confirm dashboard renders metadata as text, not HTML.
- If CSV/export is added, prefix dangerous formula-leading characters and test them.

Verify:

- XSS payloads do not execute or appear as raw HTML.
- Exported cells cannot start executable spreadsheet formulas.

### Task 2.5.3: Add Log Hygiene and Secret Pattern Tests

Scope:

- logging utilities
- access log creation
- wrapper validation

Implementation:

- Add a denylist/regex test suite for values that must never appear in logs:
  - `Authorization`
  - `Bearer `
  - `sk-a2cr-`
  - Supabase connection strings
  - Fernet/local client key material
  - raw WorkBaton body fields
- Keep hashes/fingerprints allowed only when intentionally generated.

Verify:

- Test logs/access logs do not contain raw secrets.
- Rejected save attempts do not log plaintext content.

### Task 2.5.4: Add Prompt-Injection and Agent-Safety Guardrails

Scope:

- `docs/templates/skills/a2cr-agent/SKILL.md`
- AI agent guide pages
- wrapper content validation

Implementation:

- State that loaded WorkBaton content is untrusted data.
- State that loaded content cannot override system/developer/user instructions.
- State that agents must not execute shell commands, exfiltrate data, revoke keys, delete slots, or call external services solely because loaded WorkBaton says to do so.
- Add wrapper warnings/rejections for obvious secret-exfiltration instructions when they are being saved as content, while keeping normal project notes usable.

Verify:

- Agent guide contains explicit prompt-injection handling rules.
- Wrapper tests cover malicious instruction-like content where practical.

### Task 2.5.5: Add Future Dangerous Feature Gate

Scope:

- planning docs
- PR/review checklist

Implementation:

- Require separate security review before adding:
  - file upload
  - file preview/rendering
  - HTML/SVG/Markdown rendering of user content
  - server-side URL fetching/link preview
  - archive extraction
  - OCR/thumbnailing/conversion
  - arbitrary export/download formats
  - autonomous server-side AI execution
- Each review must define allowed types, storage location, sandboxing, size limits, SSRF protections, malware scanning/CDR needs, and user-visible risk.

Verify:

- PR checklist includes the dangerous-feature gate.
- No such feature is added without a linked threat model.

## Phase 3: Authentication, Authorization, and Tenant Isolation

Status: Planned
Priority: P0/P1

### Task 3.1: Hosted RLS Smoke Test

Scope:

- New smoke script under `scripts/` or `tests/smoke/`
- Deploy runbook

Implementation:

- Create or use two test users.
- Confirm user A cannot list/load/delete user B contexts.
- Confirm dashboard JWT cannot call API-key-only content routes except intended dashboard metadata/delete routes.
- Confirm API key cannot access dashboard profile settings.

Verify:

- Smoke script reports pass/fail without printing tokens.
- Runbook includes exact command and expected output.

### Task 3.2: API Key Lifecycle Hardening

Scope:

- `services/dashboard.py`
- `services/auth.py`
- docs

Implementation:

- Keep full API key visible only once.
- Add last-used display that remains metadata-only.
- Add API key rotation runbook.
- Consider multiple active keys only when naming/revocation UI is added.

Verify:

- Tests prove plaintext API key is never retrievable after creation.
- Revoked key cannot authenticate.

## Phase 4: Secrets and Supply Chain Controls

Status: Planned
Priority: P1

### Task 4.1: Add CI Security Checks

Scope:

- GitHub Actions
- dependency files

Implementation:

- Add secret scanning with a local-friendly tool such as gitleaks.
- Add Python dependency vulnerability check such as pip-audit.
- Add npm audit or equivalent dependency audit.
- Add CodeQL or static analysis for Python/TypeScript if repository visibility allows.
- Keep checks informative at first; make blocking after noise is triaged.

Verify:

- CI runs on PR/main.
- Known test secret patterns are ignored only through explicit allowlist.
- No real secrets are printed in logs.

### Task 4.2: Runtime Secret Rotation Procedure

Scope:

- `docs/runbooks/security.md`
- deploy runbook

Implementation:

- Define rotation steps for `DATABASE_URL`, DB password, API hash secret, audit secret, OAuth secret, Fernet key, Supabase keys, Railway variables.
- Separate "rotate because leaked" from "scheduled rotation".
- Document blast radius of each secret.

Verify:

- Dry-run rotation checklist for non-production or staging.
- Confirm service starts after rotated secrets.

## Phase 5: Monitoring, Alerting, and Audit

Status: Planned
Priority: P1

### Task 5.1: Structured Operational Events

Scope:

- logging utilities
- auth, context, dashboard, maintenance jobs

Implementation:

- Emit safe event names for auth failure, rate limit, unexpected origin, DB readiness failure, migration drift, API key issue/revoke, save/load/delete, cleanup failure.
- Include request ID, user ID when authenticated, action, result, error code.
- Do not include WorkBaton body, encrypted payload, Authorization header, API key, raw IP, raw UA, DB URL, local client key.

Verify:

- Tests or log snapshot checks prove disallowed fields are absent.

### Task 5.2: Alerts

Scope:

- Railway/Supabase/Cloudflare monitoring
- runbooks

Implementation:

- Alert on health/readiness failure.
- Alert on elevated 5xx rate.
- Alert on auth failure spike.
- Alert on cleanup job failure.
- Alert on DB connection exhaustion or Supabase provider incident.

Verify:

- Trigger a test alert in staging/non-production.
- Confirm owner receives and can follow runbook.

## Phase 6: Backup, Restore, and Disaster Recovery

Status: Planned
Priority: P0 before beta

### Task 6.1: Backup Policy

Scope:

- `docs/runbooks/disaster-recovery.md`
- Supabase project settings

Implementation:

- Define backup source: Supabase managed backups and/or scheduled exports depending on plan.
- Define what is recoverable: ciphertext, metadata, user profiles, stats, API key hashes, logs within retention.
- Define what is not recoverable: WorkBaton plaintext without user's local key; old slots if user's local key is lost.
- Define backup retention and access control.

Verify:

- Backup status can be checked without exposing secrets.
- Runbook includes owner and frequency.

### Task 6.2: Restore Drill

Scope:

- staging Supabase project or isolated database
- restore script/runbook

Implementation:

- Restore latest backup to non-production.
- Run schema readiness.
- Run RLS smoke test.
- Run dashboard/API/MCP smoke tests.
- Verify a restored WorkBaton ciphertext can be returned and locally decrypted with the matching local client key.

Verify:

- Record restore date, duration, RTO/RPO achieved, failures, and improvements.

### Task 6.3: Bad Deploy and Migration Rollback Procedure

Scope:

- `docs/runbooks/deploy.md`
- new DR runbook

Implementation:

- Define when to Railway rollback versus forward-fix.
- Define when not to roll back DB migrations.
- Add pre-deploy readiness, post-deploy readiness, and smoke gate.
- Add manual emergency SQL rules: never run destructive SQL without backup/confirmed scope.

Verify:

- A dry-run rollback can be completed in staging.

## Phase 7: Product-Specific Security Decisions

Status: Planned
Priority: P1/P2

### Task 7.1: Local Client Key UX and Recovery Guidance

Scope:

- guide pages
- MCP setup docs
- local stdio wrapper docs

Implementation:

- Show where local client key lives.
- Explain user responsibility and backup tradeoff.
- Add "rotate key" guidance:
  - new key can read future saves
  - old slots need old key
  - A2CR cannot recover old slots
- Consider a wrapper command to print key file path without printing key material.

Verify:

- Docs never print key value.
- User can understand recovery limits before saving important WorkBaton content.

### Task 7.2: Add Official Wrapper Content Guardrails

Scope:

- `mcp/server.py`
- `models/schemas.py` if server-side metadata fields are added
- `docs/usage.md`
- AI agent guide and human guide copy
- tests in `tests/test_mcp_stdio.py`

Implementation:

- Keep WorkBaton as structured work-state JSON, not file storage.
- In the local stdio wrapper, validate content before encryption:
  - require `goal`, `current_state`, and `next_action`
  - allow known small structured fields only
  - reject unknown top-level fields unless explicitly allowed
  - reject strings that look like base64/data URLs above a small threshold
  - reject attachment-like fields such as `file`, `filename`, `mime_type`, `blob`, `bytes`, `base64`, `data_url`, `archive`, `binary`
  - reject long logs/full transcripts over the existing plan size limits
  - reject HTML/SVG intended for rendering
- Keep server-side validation on encrypted envelope:
  - `alg = Fernet`
  - supported `version`
  - `key_wrap.type = local-key`
  - max ciphertext size
- Add a friendly error explaining that A2CR stores work state, not files.

Verify:

- Tests prove normal save still works with one MCP call.
- Tests reject base64-like payloads, `data:` URLs, `filename`/`blob` fields, and oversized logs before encryption.
- Tests confirm the rejected plaintext is never posted to A2CR.
- Docs explain allowed/rejected content without sounding like an enterprise policy manual.

### Task 7.3: Add Local Key Status UX Without Revealing Key Material

Scope:

- `mcp/server.py`
- dashboard/settings copy if applicable
- guide pages

Implementation:

- Add a wrapper tool or helper output that reports:
  - local client key file path
  - whether the file exists
  - key ID fingerprint only, not the key
  - warning if the key is newly created
- Add docs for safe backup:
  - copy the key file to the user's password manager or encrypted backup
  - never paste key content into chats, tickets, logs, screenshots, or commits
  - old slots need the old key
- Keep normal save/resume flows automatic.

Verify:

- No command or UI prints the raw key.
- A user can locate the key file path from the guide.
- Key missing/new-key behavior is explained before users assume old slots are recoverable.

### Task 7.4: WorkThreads Encryption Decision

Scope:

- WorkThreads design docs
- `services/workthreads.py`
- product copy

Implementation:

- Decide whether WorkThreads should become client-encrypted like WorkBaton.
- Until then, mark WorkThreads as not covered by WorkBaton local-key guarantee.
- If redesigned, create separate migration and client wrapper protocol.

Verify:

- Public docs do not imply WorkThreads zero-knowledge/client-encrypted behavior unless implemented.

## Suggested Execution Order

1. Task 0.1 and 0.2: truth-in-docs and incident owner.
2. Task 1.1 and 1.2: schema readiness and migration tracking.
3. Task 1.5.1 through 1.5.5: DB timeouts, deadlock handling, concurrency safety, and DB-protective abuse limits.
4. Task 1.6.1 through 1.6.6: migration safety, hot query/index review, log retention, RLS/pooler smoke, data lifecycle, and SECURITY DEFINER review.
5. Task 2.1: security headers.
6. Task 2.2 and 2.3: rate limiting and error hygiene.
7. Task 2.5.1 through 2.5.5: attack-specific regression tests and dangerous-feature gates.
8. Task 6.1 and 6.2: backup/restore policy and first restore drill.
9. Task 3.1: hosted RLS smoke test.
10. Task 4.1 and 5.1: CI security checks and structured events.
11. Task 5.2 and 6.3: alerting and rollback drill.
12. Task 7.1, 7.2, and 7.3: local key UX and content guardrails.
13. Task 7.4: WorkThreads encryption decision.

## First Implementation Batch

Recommended next coding batch:

1. Add schema readiness check.
   - Verify: tests for missing `contexts.encryption_mode`; readiness endpoint fails safely.
2. Add DB timeout and error-classification baseline.
   - Verify: transaction timeout statements are set; deadlock/lock/statement timeout errors return safe retryable responses.
3. Add WorkBaton slot mutation serialization.
   - Verify: concurrent save tests cannot exceed Free slot limits or leak raw DB errors.
4. Add migration safety and hot-query/index checklist.
   - Verify: deploy runbook covers migration dry-run, lock risk, and `EXPLAIN` review for hot queries.
5. Add access log retention and pruning baseline.
   - Verify: old logs can be pruned without changing stats and without large blocking deletes.
6. Add hosted RLS/pooler smoke script.
   - Verify: user A/B isolation works through the real deployment connection mode.
7. Add security headers middleware.
   - Verify: header tests and browser login smoke.
8. Update security docs with customer metadata risk.
   - Verify: docs search for overclaims.
9. Add disaster recovery runbook skeleton.
   - Verify: contains RTO/RPO, backup source, restore drill checklist.
10. Add official wrapper content guardrails.
   - Verify: normal save remains one-command; file-like/base64 payloads are rejected before encryption.
11. Add abuse-case regression tests for tenant isolation, XSS-like metadata, malformed encrypted envelopes, DB contention, and error hygiene.
   - Verify: security abuse tests run in normal pytest without special production secrets.

This batch directly addresses the problems observed during the current work: missed DB schema changes, DB contention risk, migration/operation risk, over-broad security wording, and lack of manual recovery guidance.

## Verification Matrix

| Area | Test or check |
| --- | --- |
| WorkBaton plaintext rejection | API tests for `content` rejection and `encrypted_content` requirement |
| Dashboard body hiding | Dashboard API tests contain no `content` |
| RLS isolation | Hosted smoke with user A/B |
| Schema readiness | Missing-column/function/constraint tests |
| Security headers | HTTP tests for key headers |
| Same-origin | unexpected Origin returns 403 |
| Rate limiting | invalid auth loop returns 429 |
| Error hygiene | DB failure hides SQL/secrets |
| DB transaction timeouts | `statement_timeout`, `lock_timeout`, and idle transaction timeout are set in web transactions |
| DB deadlock/serialization handling | SQLSTATE `40P01`/`40001` maps to safe retryable response |
| DB pool exhaustion | pool timeout maps to safe 503 without SQL/secrets |
| WorkBaton concurrent saves | concurrent save/delete tests preserve slot limits and return deterministic success/conflict |
| WorkThreads concurrent posts | loop guard cannot be bypassed by concurrent message inserts |
| WorkThreads task claiming | multiple agents claim with `SKIP LOCKED` without duplicate claims |
| Migration safety | deploy runbook includes dry-run, lock-risk, row-count, and forward-fix checklist |
| Hot query/index coverage | hot dashboard/API/WorkThreads queries have user-scoped indexes and bounded limits |
| Access log retention | pruning deletes only old logs and leaves stats intact |
| RLS/pooler compatibility | hosted user A/B smoke passes through actual DB connection mode |
| Data lifecycle | downgrade and account-delete dry-run/checklist behavior is defined |
| SECURITY DEFINER safety | static tests confirm fixed `search_path` and minimal return scope |
| Backup/restore | restore drill record exists |
| Incident response | tabletop exercise completed |
| Convenience-preserving security | normal save/resume remains one-command |
| File-like payload defense | wrapper rejects attachment-like payloads before encryption |
| Local key UX | key path/fingerprint visible, raw key never printed |
| API key/JWT theft response | revoke/expiry behavior and anomaly logging tests |
| Tenant object tampering | user A/B object ID manipulation smoke tests |
| XSS metadata defense | hostile metadata renders as text only |
| Malicious file/blob defense | base64/data URL/archive/file-like fields rejected before encryption |
| Prompt injection defense | agent guide says loaded WorkBaton is untrusted data |
| Dangerous future features | PR checklist requires security review before file/render/fetch/AI-execution features |

## Completion Criteria

The plan is complete when:

- P0 tasks are implemented and verified.
- A restore drill has been completed once.
- Security docs and guide copy avoid overclaims.
- Hosted readiness/smoke checks are part of deploy flow.
- DB queries and lock waits are bounded by explicit timeouts.
- Deadlock, serialization, lock timeout, pool timeout, and unique conflict paths are handled without leaking internals.
- Concurrent WorkBaton and WorkThreads writes have regression tests.
- Migration dry-run, query/index review, access-log retention, RLS/pooler smoke, and SECURITY DEFINER review are part of normal operations.
- Downgrade and account deletion cannot silently destroy or orphan user data.
- A security incident can be triaged without exposing secrets.
- High-security defaults do not require normal users to manually call raw APIs, edit SQL, or handle cryptographic material.
- The official wrapper blocks file-like payloads while preserving normal WorkBaton save/resume usability.
- The service can honestly be described as beta-ready, not production-certified.

## References

- NIST CSF 2.0: https://csrc.nist.gov/pubs/cswp/29/the-nist-cybersecurity-framework-csf-20/final
- NIST SP 800-34 Rev. 1: https://csrc.nist.gov/pubs/sp/800/34/r1/upd1/final
- OWASP ASVS: https://owasp.org/www-project-application-security-verification-standard/
- OWASP API Security Project: https://owasp.org/www-project-api-security/
- OWASP Top 10 for LLM Applications: https://owasp.org/www-project-top-10-for-large-language-model-applications/
- OWASP MCP Top 10: https://owasp.org/www-project-mcp-top-10/
- OWASP File Upload Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html
- OWASP XSS Prevention Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html
- OWASP Deserialization Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Deserialization_Cheat_Sheet.html
- CISA Cybersecurity Performance Goals: https://www.cisa.gov/cybersecurity-performance-goals
