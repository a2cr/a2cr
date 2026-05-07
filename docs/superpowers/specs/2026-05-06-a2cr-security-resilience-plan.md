# A2CR Security and Resilience Plan

Status: Draft, working document
Date: 2026-05-06

Important: This plan/spec is an internal planning document. It does not need to be committed or pushed unless the user explicitly asks.

## Purpose

This document defines the security and outage-resilience plan for A2CR / WorkBaton / WorkThreads.

The key product claim must stay precise:

- WorkBaton bodies are client-encrypted before upload.
- A2CR stores ciphertext and cannot decrypt WorkBaton bodies because the local client key stays in the user's local environment.
- A2CR still stores and must protect SaaS data such as account identity, user IDs, slot names, slot numbers, timestamps, sizes, usage logs, API key prefixes, runtime secrets, and operational metadata.

This is not a claim that "nothing can leak." Customer information and metadata remain normal SaaS security responsibilities.

## Reference Frameworks

- NIST Cybersecurity Framework 2.0: Govern, Identify, Protect, Detect, Respond, Recover.
- NIST SP 800-34 Rev. 1: contingency planning, business impact analysis, recovery prioritization.
- OWASP ASVS 5.0: application security verification requirements for web apps and APIs.
- OWASP API Security Top 10 2023: API authorization, authentication, object-level access, rate limit, and misconfiguration risks.
- CISA Cross-Sector Cybersecurity Performance Goals: practical high-impact safeguards for small teams.

## Scope

In scope:

- React/Vite dashboard
- FastAPI API and Streamable HTTP MCP endpoint
- Local stdio MCP wrapper and local client key guidance
- Supabase Auth, Supabase Postgres, RLS policies, migrations
- Railway runtime, Cloudflare DNS/origin, GitHub repository and CI
- API key issuance, revocation, hashing, and use
- Access logs, operational logs, alerts, incident response, recovery

Out of scope for this plan:

- Formal SOC 2 / ISO 27001 certification
- Payment/Stripe controls before billing is enabled
- Full endpoint-device management for user machines
- Zero-knowledge guarantee for WorkThreads until WorkThreads encryption is redesigned

## Asset Classification

| Class | Examples | Exposure impact | Required posture |
| --- | --- | --- | --- |
| S0 local-only secrets | local client key, decrypted WorkBaton body | WorkBaton body compromise | Never sent to A2CR; never logged; user-owned backup guidance |
| S1 runtime secrets | DB URL, DB password, OAuth secrets, API hash secret, audit secret, Fernet key, Supabase secret/service keys | Service compromise, customer metadata leak, account takeover paths | Railway/GitHub secrets only; rotate on suspicion; no browser bundle |
| S2 account/customer data | email, user_id, plan, OAuth account identifiers | Customer information leak | RLS, least privilege, logs minimized, incident notification plan |
| S3 WorkBaton server data | ciphertext, slot name, slot number, metadata, timestamps, size, model source | Metadata leak, denial of service, integrity loss | Treat as sensitive metadata; do not claim body visibility |
| S4 operational data | access logs, request IDs, hashed IP/UA, health metrics | Privacy and security signal leak | Sanitize and retain only as long as needed |
| S5 public data | guide, pricing, public docs, static assets | Reputation, misinformation | Review before publish |

## Threat Model

### Network interception

Expected control:

- HTTPS-only production origin.
- HSTS after production domain is stable.
- WorkBaton bodies remain ciphertext even if request payloads are captured.

Residual risk:

- Metadata in requests can still be observed if TLS is broken at an endpoint.
- Malicious local machine can read local client key and decrypted content.

### Database exfiltration

Expected control:

- WorkBaton body remains ciphertext.
- `a2cr_app` runtime role is least-privileged.
- RLS limits normal application access by user.

Residual risk:

- Account/customer data, slot metadata, access logs, and ciphertext leak.
- Attackers can analyze usage patterns even without decrypting bodies.

### Server compromise

Expected control:

- Existing WorkBaton bodies cannot be decrypted without the local client key.
- Runtime must not contain `SUPABASE_SERVICE_ROLE_KEY`.
- Runtime secrets can be rotated.

Residual risk:

- Attacker can read customer metadata and runtime secrets available to the app.
- Attacker can delete or corrupt ciphertext.
- Attacker can serve malicious frontend code to future users.
- Attacker may steal future API keys/JWTs passing through the compromised runtime.

### API key or JWT theft

Expected control:

- API keys are stored as HMAC hashes server-side.
- API keys can be revoked and re-issued.
- JWT signature, expiry, audience, and issuer are verified.

Residual risk:

- Stolen valid API key/JWT can act as the user until revoked/expired.
- Need auth-failure rate limiting and anomaly alerting.

### Tenant isolation bypass

Expected control:

- `web_transaction(user_id)` sets transaction-local `app.user_id`.
- RLS policies require `user_id = app.current_user_id()`.
- Application SQL also includes `user_id` predicates.

Residual risk:

- Future SQL changes can forget user predicates.
- Migration drift can silently break assumptions.

### Supply chain compromise

Expected control:

- Lockfiles exist for npm.
- Python dependencies are pinned via `requirements.txt`.

Residual risk:

- No automated dependency alerts or security scans are guaranteed yet.
- No release artifact provenance.

### Bad deploy or migration drift

Expected control:

- Local tests and build pass before deploy.
- Deploy runbook lists migrations.

Residual risk:

- Manual SQL migration steps can be missed.
- Health endpoint currently proves only basic app health, not schema readiness.

### Provider outage

Expected control:

- A2CR uses managed providers: Railway, Supabase, Cloudflare, GitHub.

Residual risk:

- Single-region / single-provider outage can take the service down.
- Free/Nano plans are not production-grade availability guarantees.

## Attack-Specific Countermeasure Matrix

This matrix turns likely attacks into concrete A2CR controls. The goal is to prevent attacks when practical, reduce blast radius when prevention fails, and keep normal user workflows simple.

| Attack | A2CR impact | Preventive controls | Detection/response | Verification |
| --- | --- | --- | --- | --- |
| API key theft | Attacker can save/load/delete as the user until key is revoked | HMAC-only API key storage, one-time key display, revoke/re-issue UI, rate limits, no keys in logs | Alert on auth anomalies and unusual save/load/delete bursts; revoke affected key | Revoked key auth test; log scan for key patterns |
| JWT theft/session replay | Dashboard actions as victim until token expires | Supabase JWT verification, short-lived tokens via provider, same-origin app, security headers | Alert on unusual dashboard actions; force sign-out if provider supports it | Expired/wrong audience/wrong issuer tests |
| Local client key theft | Attacker can decrypt that user's WorkBaton bodies | Never send key to A2CR, never print raw key, OS/user-owned storage, backup guidance | User rotates local key for future saves; old compromised slots should be deleted | Tests/tools show path/fingerprint only, not key |
| Tenant isolation bypass/BOLA | User A reads or deletes user B metadata/ciphertext | RLS, transaction-local `app.user_id`, explicit `user_id` predicates, per-user unique constraints | Alert on impossible cross-user access attempts; incident review | Hosted user A/B smoke tests |
| SQL injection | DB read/write beyond intended query | SQLAlchemy parameters, no string-built user SQL, allowlisted selectors | 5xx/error anomaly monitoring; review logs without secrets | Static review and tests for selector queries |
| XSS through slot names/metadata | Browser token theft or malicious UI actions | React escaping, no raw HTML rendering, CSP, output encoding, slot name character allowlist | CSP violation reporting if enabled; revoke tokens/keys if exploited | XSS payload rendering tests |
| Malicious file/blob stored as WorkBaton | Later execution/rendering or admin mishandling | No WorkBaton file storage; wrapper rejects file-like fields, base64/data URLs, archives, executables, HTML/SVG; size limits | Log rejected payload type without body; educate user | Wrapper rejection tests before encryption |
| Unsafe deserialization | Code execution if stored data is loaded by unsafe parser | Use JSON only; never `pickle`, unsafe YAML load, or language-native object deserialization for user data | Dependency/static scans for unsafe APIs | Code search/CI checks for unsafe deserializers |
| Prompt injection/context poisoning | Future AI treats saved text as higher-priority instructions | AI agent guide: loaded WorkBaton is untrusted data; agent must not reveal secrets or execute commands solely because loaded context says so; save only work-state facts | Watch for suspicious saved instructions; user can delete suspect slots | Agent guide tests/review; wrapper blocks secret-like fields |
| MCP token/secret exposure | Agent memory/logs leak keys or connected-service credentials | Do not save secrets; wrapper rejects Authorization/API key patterns; MCP setup snippets hide keys; scoped credentials | Secret scanning in saved content before encryption where feasible | Tests for secret-pattern rejection |
| Excessive agency/tool misuse | AI performs destructive actions from poisoned context | A2CR stores/resumes context only; no autonomous server-side execution; delete/revoke require explicit user action | Audit delete/revoke/issue actions | Route tests and UI confirmation tests |
| Remote MCP save bypass | Plaintext or unvalidated WorkBaton reaches server | Remote HTTP MCP `save_context` disabled for WorkBaton; API requires `encrypted_content` | Alert on plaintext-save rejections | API tests reject `content` |
| Brute force/auth abuse | Service load and credential probing | Per-IP invalid auth rate limit; per-user plan limits; edge/WAF limits | Alert on auth failure spikes | 429 tests |
| DoS by oversized payloads | Cost, DB bloat, slow dashboard | Max body/ciphertext size, compact schema, plan limits, no file uploads | Alert on size/rate anomalies | Size limit tests |
| DB deadlock or lock contention | Requests hang, fail, or amplify an outage under concurrency | Short transactions, consistent lock order, `lock_timeout`, `statement_timeout`, no AI/external waits inside DB transactions | Classify retryable DB errors and return safe retry responses with request IDs | Simulated SQLSTATE tests for deadlock/timeout |
| DB connection pool exhaustion | Normal users see slow or failed requests during bursts | Bounded pool settings, `pool_timeout`, app rate limits, capped long polling, edge throttles | Alert on pool timeout and DB saturation signals | Pool timeout error mapping tests |
| Concurrent WorkBaton saves | Slot limit bypass, duplicate slots, or confusing conflicts | User-scoped slot mutation lock, per-user unique constraints, idempotent overwrite semantics, safe unique-violation handling | Return conflict/retryable response without leaking SQL | Concurrent save tests |
| Concurrent WorkThreads posts | Loop guard bypass or inconsistent unresolved-question counts | Lock the thread row while enforcing loop guard; unique indexes for idempotency/content hash; keep task claim on `SKIP LOCKED` | Record loop guard blocks without message content | Concurrent loop-guard tests |
| DB exfiltration | Customer data/metadata/ciphertext leak | Least-privileged DB role, no service role in runtime, WorkBaton client encryption, minimized logs | Rotate DB/runtime secrets, notify based on metadata exposure scope | Startup guard tests; incident tabletop |
| DB tampering/deletion/ransomware | Slot loss, corrupted ciphertext, service disruption | Backups, restore drills, id-based user-scoped updates, Fernet detects ciphertext tamper on decrypt | Restore from backup; tell users if ciphertext may be lost/corrupt | Restore drill and decrypt restored test slot |
| Migration drift | Runtime 500s, dashboard failure, weak constraints | Schema readiness check, migration tracking, pre/post deploy smoke | Fail readiness before user traffic; forward-fix migration | Missing-column readiness test |
| Supply chain compromise | Malicious dependency or build artifact | Lockfiles, dependency audit, secret scanning, CodeQL/static analysis, limited CI secrets | Rotate secrets; rebuild from known-good commit | CI security checks |
| Malicious frontend/deploy | Future tokens/keys captured in browser | protected main branch, review for deploy changes, CSP, no third-party scripts unless necessary, rollback | Roll back Railway deploy; rotate potentially exposed credentials | Deploy diff review and rollback drill |
| CORS/origin bypass | Browser-based cross-origin abuse | Same-origin guard, no broad `Access-Control-Allow-Origin`, no wildcard credentials | Alert unexpected origin rejections | Origin rejection tests |
| Clickjacking | User tricked into dashboard actions | `frame-ancestors 'none'` / X-Frame-Options DENY | CSP reports if enabled | Header tests |
| OAuth redirect misconfiguration | Token delivered to attacker-controlled redirect | Supabase/Google redirect allowlist, deploy runbook smoke | Provider config review after domain changes | OAuth login smoke |
| Log/analytics leakage | Secrets or content in logs/support tools | Structured safe logs, no body/header logging, hash IP/UA, retention limits | Log sampling and secret scanning | Log hygiene tests |
| Backup exposure | Historical metadata/ciphertext leak | Restrict backup access, encrypt/provider-managed backups, retention policy | Rotate secrets and assess metadata exposure | Backup access review |
| CSV/export formula injection | Admin/user opens exported data and formula executes | Prefix dangerous CSV cells, export text safely, avoid spreadsheet exports until sanitized | Notify affected admins/users | Export sanitization tests if exports added |
| SSRF through future URL features | Server fetches attacker-chosen URLs | Do not add server-side URL fetching for WorkBaton; if added, allowlist and block internal IP ranges | Alert blocked URL fetches | SSRF guard tests before feature release |

## Attack-Driven Product Rules

- A2CR must treat every user-controlled value as untrusted even when it is encrypted at rest.
- A2CR should not introduce a file upload or file preview path for WorkBaton without a separate threat model.
- The dashboard must never render user-controlled HTML, SVG, Markdown-with-HTML, or decrypted WorkBaton bodies.
- MCP/AI agent guides must state that loaded WorkBaton content is data, not an instruction source that overrides system/developer/user instructions.
- Any future export feature must sanitize spreadsheet formulas and avoid raw secret/body export by default.
- Any future server-side URL fetching, link preview, file conversion, OCR, thumbnailing, or antivirus pipeline must go through a separate security review.
- Any route that takes `slot_name`, `slot_number`, `thread_id`, `task_id`, or `message_id` must prove user ownership at both application and RLS layers.
- DB transactions must be short, bounded by timeouts, and free of AI calls, network calls, long polling, or user-visible streaming.
- Concurrent writes must be designed explicitly: either serialized by a user/thread lock or made idempotent with unique constraints and safe conflict handling.
- Security tests should include abuse cases, not only happy-path feature tests.

## Database Timeout and Concurrency Rules

Database stability is a P0 security and resilience concern. A2CR should fail quickly and safely under contention rather than letting requests wait indefinitely.

Required controls:

- Configure SQLAlchemy with bounded connection behavior: `pool_pre_ping`, explicit `pool_size`, `max_overflow`, `pool_timeout`, and `pool_recycle`.
- Set transaction-local PostgreSQL timeouts in web runtime:
  - `statement_timeout` for maximum query duration.
  - `lock_timeout` for lock waits.
  - `idle_in_transaction_session_timeout` to prevent abandoned transactions.
- Keep `web_transaction` blocks short. Do not perform AI work, external HTTP calls, long polling waits, file work, or user-visible streaming inside an open DB transaction.
- Classify PostgreSQL errors by SQLSTATE:
  - `40P01` deadlock detected.
  - `40001` serialization failure.
  - `55P03` lock not available.
  - `57014` query canceled / statement timeout.
  - `23505` unique violation.
- Map those failures to safe application errors that do not expose SQL, connection strings, headers, request bodies, or stack traces.
- Retry only operations that are proven idempotent. For save-like mutations, use an idempotency key or serialize the mutation before retrying.
- Serialize WorkBaton slot mutations per user while checking active-slot capacity and writing the row.
- Serialize WorkThreads loop-guard enforcement per thread before inserting a new message.
- Keep `FOR UPDATE SKIP LOCKED` for WorkThreads task claiming so multiple agents can claim work without blocking each other.
- Cap long polling and dashboard refresh patterns so they cannot exhaust DB connections.

Residual risk:

- A provider outage or DB resource exhaustion can still make A2CR unavailable.
- A user with many clients can still hit rate limits during legitimate heavy work.
- The correct response is graceful degradation, clear retry guidance, and no secret leakage, not pretending the operation succeeded.

## Database Operational Trouble Matrix

This matrix covers non-malicious database failures that can still become security, availability, or data-integrity incidents.

| Trouble | A2CR impact | Preventive controls | Detection/response | Verification |
| --- | --- | --- | --- | --- |
| Unsafe migration locks | API requests block or time out during deploy | Split heavy migrations, avoid long table rewrites, add indexes concurrently where possible, run preflight on staging-like DB | Pause deploy/traffic, roll forward with smaller migration | Migration dry-run checklist |
| Migration drift | Code expects schema that production lacks | Migration tracking, schema readiness, deploy gate, post-deploy smoke | Fail readiness before user traffic; forward-fix migration | Missing object readiness tests |
| Slow query or missing index | Dashboard/API latency rises and pool fills | Index user-scoped queries, review `EXPLAIN`, avoid unbounded scans | Alert on slow endpoints and DB saturation; add targeted index | Query-plan review for hot routes |
| Access log growth | Rate-limit queries and dashboard logs become slow | Retention job, partial indexes, summary counters, cap UI list limits | Prune old logs; move to partitioning if needed | Retention job and index tests |
| Table/index bloat from TTL deletes | DB storage grows and queries degrade | Batched expiry, provider monitoring, avoid massive deletes in request path | Run vacuum/analyze through provider-safe process | Expiry load test and storage review |
| RLS context missing | User sees empty data or access breaks unexpectedly | All product DB access goes through `web_transaction`; transaction-local `app.user_id` every request | Treat as deploy failure; readiness/smoke catches it | User A/B RLS smoke |
| Pooler/session-state mismatch | RLS assumptions break with connection pooling | Use transaction-local `set_config(..., true)` every transaction; verify Supabase pooler mode before deploy | Disable unsafe pooler mode or adjust connection strategy | Hosted pooler smoke test |
| SECURITY DEFINER misuse | Privilege escalation or search path hijack | Fixed `search_path`, minimal returned data, no dynamic SQL unless strictly reviewed | Revoke or replace function; rotate impacted secrets if needed | Function audit test |
| Cascade delete surprise | Account deletion removes more or less than intended | Explicit account deletion plan, deletion dry-run summary, foreign-key review | Restore if accidental; communicate scope | Delete-path integration test |
| Backup restore gap | Backup exists but cannot restore service correctly | Restore drill, documented RTO/RPO, decrypt restored test WorkBaton ciphertext locally | Run restore drill; fix runbook gaps | Restore drill record |
| Timezone/TTL mismatch | Slots expire earlier/later than UI says | Store UTC in DB, convert only at display/API boundary, test DST-adjacent cases | Correct UI/API formatting; do not rewrite stored timestamps | TTL timezone tests |
| Plan downgrade over-limit state | Pro users returning to Free cannot save or lose data unexpectedly | Read/delete allowed, new saves blocked until within Free limits, clear UI status | Avoid automatic destructive cleanup; provide export/delete path | Downgrade behavior tests |
| Orphaned rows | Deleted accounts leave API keys/logs/messages | FK cascade review plus account deletion verification query | Cleanup migration/job if found | Orphan scan in maintenance |
| Bad manual SQL | Emergency changes corrupt data or bypass constraints | Prefer migrations, require transaction, backup point, peer review, rollback note | Stop write traffic if needed; restore/forward-fix | Admin runbook checklist |
| Sequence/ID/collision issue | Inserts fail or collide under unusual data repair | Use UUID defaults, avoid user-supplied primary keys except validated IDs | Treat as data repair incident | Insert smoke after migration |

Operational rules:

- Migrations must be small, reversible by forward fix, and run first in a staging-like database.
- Any migration touching user-owned tables, RLS, constraints, indexes, encryption columns, or expiry behavior must have a readiness check update.
- Hot user-facing queries must have bounded result limits and user-scoped indexes.
- Access logs are operational data, not permanent product data. They need retention and pruning from day one.
- Account deletion, downgrade, and expiry jobs must be designed as data lifecycle features, not ad hoc cleanup scripts.
- Manual SQL in production should be exceptional and recorded in the runbook with purpose, exact SQL, expected row count, and rollback/forward-fix plan.

## Security and Usability Design Principles

A2CR should reach a high security posture without turning normal use into a security ceremony.

Principles:

1. Secure defaults, low friction
   - The recommended path is local stdio MCP wrapper + client-encrypted WorkBaton.
   - Users should not need to understand cryptography to save or resume normal WorkBaton checkpoints.
   - Dangerous or unsupported paths should fail with plain, actionable messages.

2. Explicit friction only for irreversible or high-risk actions
   - Deleting slots, rotating local client keys, revoking API keys, and exporting data should require confirmation.
   - Routine save/load/resume should stay one-command or one-click.

3. Recoverability is part of usability
   - The UI and docs must explain that losing the local client key makes old WorkBaton bodies unrecoverable.
   - The wrapper should show the key file path without printing the key value.
   - Backup guidance should be simple enough for non-security users.

4. Treat saved content as untrusted data
   - A2CR should not offer arbitrary file storage for WorkBaton.
   - WorkBaton is structured work-state JSON, not a binary/file upload feature.
   - Clients should reject base64 blobs, archives, executables, large pasted logs, and attachment-like content before encryption.
   - The server cannot inspect encrypted plaintext, so client-side validation is the primary control.

5. Progressive disclosure
   - Normal dashboard views show slot health, expiry, size, and controls.
   - Advanced security details such as key ownership, metadata exposure, and incident limits should be available in guide/settings, not forced into every save.

6. One safe official path
   - The official stdio wrapper should be the convenient path.
   - Direct remote MCP save remains disabled for WorkBaton.
   - Setup snippets should be copyable and should not ask users to manually compose headers or raw API calls.

7. Clear metadata boundary
   - Users should understand that WorkBaton body content is hidden from A2CR, but account information and usage metadata are still stored by A2CR.
   - The product should avoid language that implies all customer data is invisible.

8. Guardrails over blame
   - The app should prevent common mistakes: plaintext save attempts, oversized content, missing schema, bad origin, invalid API key, and unsafe local key handling.
   - Error messages should say what to fix without exposing internals.

## High-Security Convenience Model

| User need | Convenience-preserving control | Security effect |
| --- | --- | --- |
| Save work quickly | One MCP `save_context` call through local wrapper | Encrypts before upload without extra user steps |
| Resume elsewhere | Copyable resume call/prompt from dashboard | Avoids manual API guessing and keeps body hidden |
| Avoid losing old slots | Show local key path and backup guidance | Reduces unrecoverable-key incidents |
| Delete stale slots | One trash action with confirmation | Keeps manual cleanup simple and auditable |
| Prevent unsafe files | Wrapper validates structured JSON before encryption | Blocks file-like payloads before server blindness |
| Understand exposure | Dashboard/guide explain body vs metadata boundary | Avoids false security expectations |
| Diagnose setup issues | Readiness endpoint and clear dashboard errors | Avoids vague failures and manual SQL guessing |
| Rotate credentials | Guided API key revoke/re-issue flow | Reduces long-lived key risk without CLI work |

## Content-Type Policy

WorkBaton should remain a work-state checkpoint, not a file container.

Allowed:

- Structured JSON fields such as `goal`, `current_state`, `next_action`, `decisions`, `constraints`, `problems`, `environment`, `background`, `summary`, `failed_attempts`, and `references`.
- Short exact strings needed for continuity: file paths, commands, error names, issue IDs, URLs, and concise snippets.

Rejected by official clients before encryption:

- Binary files or binary-like strings.
- Base64 blobs or data URLs.
- Archives such as zip/tar/7z.
- Executables, scripts intended to be run, Office macros, and serialized objects.
- Long logs, full chat transcripts, generated caches, or repository file bodies that can be read again from the repo.
- HTML/SVG intended for rendering.

Server-side enforcement:

- Require `encrypted_content`.
- Restrict `encrypted_content.alg`, `version`, `key_wrap.type`, and maximum ciphertext size.
- Store declared `payload_kind = "workbaton"` once schema supports it.
- Never render decrypted content in the dashboard.

Residual risk:

- A malicious client can encrypt disallowed content and lie about metadata.
- Because A2CR intentionally cannot decrypt WorkBaton bodies, server-side content inspection is not possible.
- This is acceptable only if A2CR's official UX and docs make WorkBaton a structured checkpoint feature, not a file upload feature.

## User Experience Requirements

The high-security path is acceptable only if these UX requirements are met:

- A first-time user can configure MCP with one copied snippet.
- The local key is created automatically by the wrapper.
- The key file path is visible in docs/settings, but the key value is never displayed.
- Save/resume/delete can be done without visiting Supabase, Railway, or raw API docs.
- Expired or deleted slots disappear without confusing error banners.
- Schema/deploy drift produces an operator-facing readiness error, not a user-facing mystery failure.
- Security warnings are specific and actionable.
- Public guides explain the metadata boundary in plain language.

## Security Control Plan

### Govern

Goals:

- Maintain accurate security claims.
- Assign ownership for security, incident response, and release approval.
- Keep plan docs separate from public marketing claims.

Controls:

- Public docs must say "WorkBaton body cannot be decrypted by A2CR" rather than "nothing leaks."
- Security issue intake path must be defined before public beta.
- Every release touching auth, RLS, encryption, logging, or migrations requires explicit security review.

### Identify

Goals:

- Know which data exists where.
- Detect schema drift before users see errors.

Controls:

- Data inventory table in docs.
- DB schema readiness check for required columns, constraints, functions, grants, and RLS policies.
- Dependency inventory and vulnerability monitoring.

### Protect

Goals:

- Prevent or reduce compromise impact.
- Keep WorkBaton plaintext outside A2CR.

Controls:

- Client-encrypted WorkBaton only.
- Local stdio wrapper required for save/decrypt.
- Reject plaintext WorkBaton bodies.
- Disable remote HTTP MCP save for WorkBaton.
- Enforce same-origin in production.
- Add HTTP security headers: HSTS, CSP, X-Content-Type-Options, Referrer-Policy, frame-ancestors, Permissions-Policy.
- Add authentication and API rate limiting.
- Keep service role out of runtime.
- Keep runtime secrets out of logs and browser bundle.
- Use scoped DB role and RLS.

### Detect

Goals:

- See attacks and failures early without logging sensitive content.

Controls:

- Structured logs for auth failures, rate limits, unexpected origins, DB errors, migration readiness failures, API key issue/revoke, context save/load/delete.
- Alerts for error-rate spikes, auth-failure spikes, cleanup failures, and provider health issues.
- Security event dashboard with no WorkBaton body visibility.

### Respond

Goals:

- Contain incidents quickly and rotate affected credentials.

Controls:

- Incident runbooks for DB leak, runtime compromise, API key leak, JWT/OAuth issue, bad deploy, migration failure, provider outage, and suspected local client key exposure.
- API key revocation path.
- Runtime secret rotation checklist.
- Customer communication template distinguishing body ciphertext from metadata exposure.

### Recover

Goals:

- Restore service and data integrity after failures.

Controls:

- Define RTO/RPO targets by maturity stage.
- Supabase backup/restore procedure.
- Export/restore test for metadata and ciphertext.
- Railway rollback procedure.
- Migration rollback/forward-fix procedure.
- Regular restore drills.

## Availability and Recovery Targets

Current status: testing / early prototype. No production SLA.

Beta target:

| Scenario | Target RTO | Target RPO | Notes |
| --- | ---: | ---: | --- |
| Bad frontend/backend deploy | 30 minutes | 0 | Railway rollback |
| Missed migration / schema drift | 1 hour | 0 | Readiness check should prevent recurrence |
| App runtime outage | 2 hours | 0 | Railway redeploy/rollback |
| Supabase transient outage | Provider-dependent | Provider-dependent | Communicate degraded status |
| DB data corruption | 24 hours | 24 hours or provider backup window | Requires tested restore |
| Account/API key compromise | 1 hour to revoke | N/A | Rotate and notify affected user |
| Runtime secret exposure | 4 hours | N/A | Rotate secrets and redeploy |

Paid-production target, only after backup/monitoring are tested:

| Scenario | Target RTO | Target RPO |
| --- | ---: | ---: |
| Bad deploy | 15 minutes | 0 |
| App runtime outage | 1 hour | 0 |
| DB restore from backup | 4 hours | 1 hour to 24 hours depending on plan |
| Security incident containment | 1 hour | N/A |

## High-Priority Gaps

1. Schema readiness is manual and fragile.
2. HTTP security headers are not yet explicitly enforced by the app.
3. Auth failure and unauthenticated endpoint rate limiting are not complete.
4. Monitoring/alerting is not yet codified.
5. Backup/restore drills are not yet defined or tested.
6. CI lacks mandatory dependency/security scanning gates.
7. Incident communication templates are not yet written.
8. WorkThreads encryption guarantee is weaker than WorkBaton and must not be marketed the same way.
9. Official client-side content validation does not yet reject file-like or attachment-like payloads before encryption.
10. Local client key backup/rotation UX is still mostly documentation-driven.

## Acceptance Criteria

A2CR can move from "early prototype" to "beta-ready" when:

- Hosted schema readiness check passes and fails safely on drift.
- Security headers are verified on `/`, `/dashboard`, `/api/v1/health`, and `/mcp`.
- Unexpected Origin is rejected in production.
- Auth/JWT/API-key tests pass, including expired/wrong audience/wrong issuer/invalid signature.
- RLS user A/B isolation is verified against hosted-like Postgres.
- Dashboard/API/MCP routes do not return WorkBaton plaintext.
- Rate limiting covers unauthenticated auth failures and authenticated save/load/delete abuse.
- Backup and restore drill has been performed once.
- Incident runbook can be followed without exposing secrets.
- Public docs distinguish WorkBaton body secrecy from metadata/customer data exposure.
- Official wrapper rejects file-like payloads and oversized unsafe content before encryption.
- Users can find local client key location and backup guidance without seeing the key value.

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
