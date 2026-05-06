# A2CR Security Runbook

This runbook covers operational security for the Web SaaS MVP.

## Runtime Secret Rules

Never put these in the browser bundle, logs, GitHub, or support tools:

- `DATABASE_URL`
- `FERNET_KEY`
- `API_KEY_HASH_SECRET`
- `AUDIT_HASH_SECRET`
- `SUPABASE_JWT_SECRET`
- `SUPABASE_SERVICE_ROLE_KEY`
- Stripe and Google OAuth secrets

`SUPABASE_SERVICE_ROLE_KEY` must not exist in the normal Railway runtime. It is only for migrations or emergency admin work in a separate, short-lived environment.

## Client Key Rules

The local stdio MCP wrapper can create a client-encryption key file for client-encrypted WorkBaton slots.

- Do not commit local A2CR client key files.
- Do not print client keys in logs, tool responses, support messages, or screenshots.
- If a client key is lost, A2CR cannot recover client-encrypted WorkBaton bodies.
- WorkBaton depends on this local key. Creating a new key works for future saves, but it cannot decrypt slots saved with the old key.

## Content Visibility

Dashboards and ordinary admin/support views must not display:

- WorkBaton saved bodies
- WorkThreads message bodies
- AI prompts or AI response bodies
- full API keys
- Authorization headers

WorkBaton storage:

- WorkBaton is client-encrypted only.
- A2CR APIs reject plaintext WorkBaton bodies.
- Direct remote HTTP MCP saving is disabled for WorkBaton because encryption must happen before upload.
- The server stores and returns ciphertext and cannot decrypt WorkBaton bodies.

WorkThreads are a separate feature and are not covered by the WorkBaton client-encryption guarantee.

## Startup Guards

Production startup must fail when:

- `SUPABASE_SERVICE_ROLE_KEY` is present
- required Web SaaS env values are missing
- `FERNET_KEY` is not a valid Fernet key
- production `A2CR_SERVICE_URL` is not HTTPS
- production hash/audit secrets are too short

## Same-Origin Policy

Production is same-origin by default. React, FastAPI, and `/mcp` are served from the same public origin.

Unexpected browser `Origin` values are rejected with 403 and no `Access-Control-Allow-Origin` header. MCP/API clients that do not send `Origin` are unaffected.

## Tenant Isolation

Every Web SaaS request must resolve exactly one authenticated `user_id` before reading or writing product data.

Isolation layers:

- FastAPI services pass `user_id` into every product-data operation.
- `web_transaction(user_id)` opens a fresh SQLAlchemy session and sets `app.user_id` with `set_config(..., true)`, making the setting transaction-local so pooled connections do not retain the previous request's user context.
- Supabase RLS policies restrict user tables to `user_id = app.current_user_id()`.
- Application SQL keeps `user_id` predicates on account-owned rows, including id-based follow-up updates.
- Unique constraints for WorkBaton slots are scoped by `(user_id, slot_name)` and `(user_id, slot_number)`, not global slot names or numbers.

Encryption is a second line of defense, not the tenant-isolation boundary.

## Logging Rules

Access logs may contain:

- action
- result
- error code
- request id
- slot name
- size
- timestamp
- hashed IP / hashed user agent when needed

Access logs must not contain:

- saved body content
- API key or Authorization header
- raw IP address
- full User-Agent
- database URLs or secrets
- client encryption keys

## Monitoring Signals

Track these metrics/events:

- auth failure count
- rate-limit responses
- save/load/delete counts
- cleanup job failures
- DB connection errors
- unexpected origin rejections
- API key issue/revoke events

Initial alert paths:

- cleanup job failure: check Railway job logs, then run `python -m services.maintenance expire-contexts` manually
- auth anomaly: check rate-limited/auth failure counts and rotate affected API keys if needed
- DB errors: confirm Supabase availability, connection limit, and `a2cr_app` role permissions

## Incident Steps

1. Stop or roll back the affected Railway deploy.
2. Preserve logs without exporting secrets or request bodies.
3. Revoke exposed API keys.
4. Rotate runtime secrets if exposure is plausible.
5. Re-run smoke checks before reopening traffic.
