# Disaster Recovery Runbook

This runbook defines the beta recovery baseline for A2CR. It is an operational
checklist, not a production SLA.

## Ownership

- Incident commander: decides whether to pause traffic, roll back, or continue
  with a forward-fix.
- Technical lead: runs Railway, Supabase, migration, and smoke-test steps.
- Communications owner: writes user-facing status updates when user impact is
  plausible.
- Decision maker: approves destructive recovery work after scope and backup
  point are confirmed.

Never commit or paste secrets. Do not put `DATABASE_URL`, DB passwords, OAuth
secrets, `SUPABASE_SERVICE_ROLE_KEY`, Railway variables, Fernet keys, API hash
or audit secrets, Authorization headers, API keys, local client key material,
or raw WorkBaton/WorkThreads bodies into chat, tickets, runbook notes, or
restore records.

## RTO/RPO Targets

Current status: testing / early beta. No production SLA.

Beta target:

| Scenario | Target RTO | Target RPO | Primary response |
| --- | ---: | ---: | --- |
| Bad frontend/backend deploy | 30 minutes | RPO 0 | Railway rollback |
| Missed migration or schema drift | 1 hour | RPO 0 | Forward-fix migration after readiness failure |
| App runtime outage | 2 hours | RPO 0 | Railway redeploy or rollback |
| Supabase transient outage | Provider-dependent | Provider-dependent | Communicate degraded status |
| DB data corruption | 24 hours | 24 hours or provider backup window | Restore to non-production first |
| Account/API key compromise | 1 hour to revoke | N/A | Revoke/rotate and notify affected user |
| Runtime secret exposure | 4 hours | N/A | Rotate secrets and redeploy |

Paid-production target, only after backup and monitoring are tested:

| Scenario | Target RTO | Target RPO |
| --- | ---: | ---: |
| Bad deploy | 15 minutes | RPO 0 |
| App runtime outage | 1 hour | RPO 0 |
| DB restore from backup | 4 hours | 1 hour to 24 hours depending on plan |
| Security incident containment | 1 hour | N/A |

## Backup Sources

Primary database backup source is Supabase managed backups and/or scheduled
exports depending on plan. If the Supabase plan does not provide the needed
retention or point-in-time restore, add scheduled exports before beta and record
where those exports are stored.

Recoverable from database backup:

- WorkBaton ciphertext and metadata
- user profiles and plan/settings metadata
- stats and access logs within retention
- API key hashes and prefixes
- WorkThreads metadata, messages, tasks, and runs

Not recoverable by A2CR:

- WorkBaton plaintext without the user's local client key
- a lost local client key or recovery key material
- data that expired or was pruned before the backup point
- external AI-client chat history that was never saved to A2CR

A2CR cannot recover client-encrypted WorkBaton bodies without the matching
local client key. The service can restore ciphertext and metadata, not the
user-owned local key.

Backup access must be restricted to the smallest operational group. Checking
backup status must not print secrets or connection strings.

## Restore Drill

Run the first restore drill before beta, then repeat after major schema changes
or backup provider changes.

1. Create or select a non-production Supabase project or isolated database.
2. Restore the latest production backup or scheduled export into that target.
3. Configure a non-production Railway environment against the restored target.
4. Run migration tracking without printing `DATABASE_URL`:

```bash
python scripts/check_migrations.py
```

5. Run schema readiness:

```text
GET https://a2cr.app/api/v1/health/readiness
```

6. Run hosted RLS/pooler smoke with two test users, never real customer users:

```bash
set A2CR_SMOKE_USER_A_ID=<TEST_USER_A_UUID>
set A2CR_SMOKE_USER_B_ID=<TEST_USER_B_UUID>
python scripts/smoke_rls_pooler.py
```

Expected: no DB URL, token, API key, password, or row content is printed.

7. Run dashboard/API/MCP smoke:

- `/api/v1/health`
- `/dashboard`
- `/mcp`
- Google login in the restored non-production environment
- API key issue and revoke
- MCP save, resume, load, and delete with test data
- WorkThreads list/read/unread/task claim with test data

8. Verify a restored WorkBaton ciphertext can be loaded and locally decrypted
   with the matching local client key. A2CR must not receive or print that key.
9. Record the restore drill result using the template below.

## Restore Drill Record

For each drill, record:

- date
- operator
- source backup or export identifier
- restored target environment
- restore duration
- RTO achieved
- RPO achieved
- readiness result
- RLS/pooler smoke result
- dashboard/API/MCP smoke result
- restored WorkBaton ciphertext load/decrypt result
- failures
- improvements and owner

Do not record DB URLs, passwords, tokens, Authorization headers, service-role
keys, local client keys, ciphertext bodies, or customer data.

## Bad Deploy

Use Railway rollback when code or frontend assets are faulty and the database
schema is still compatible with the previous image.

1. Roll back Railway to the previous successful image.
2. Re-run `/api/v1/health` and `/api/v1/health/readiness`.
3. Re-run dashboard/API/MCP smoke.
4. Rotate secrets before redeploying if the bad deploy may have exposed them.

## Migration Failure

Prefer forward-fix over rolling back database migrations. Do not roll back a
database migration unless that specific migration is proven faulty and a backup
point, affected row count, and forward-fix plan are recorded.

Before emergency SQL:

- confirm the exact purpose
- confirm expected affected objects and row count
- confirm backup point
- run inside an explicit transaction where possible
- avoid long table locks and heavy rewrites
- never paste secrets into SQL or notes
- define the forward-fix plan

After migration recovery, run `python scripts/check_migrations.py`, schema
readiness, hosted RLS/pooler smoke, and dashboard/API/MCP smoke before reopening
traffic.
