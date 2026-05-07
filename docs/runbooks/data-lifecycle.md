# Data Lifecycle Runbook

This runbook defines non-destructive checks for plan downgrade and account
deletion. It is intentionally count-only until a reviewed cleanup command is
implemented.

## Pro To Free Downgrade

Always run the downgrade dry-run before changing a user profile from Pro to
Free.

The dry-run reports:

- active WorkBaton count
- active WorkBatons over the Free Slot limit
- active WorkBatons over the Free body-size limit
- detailed WorkBatons that Free cannot create
- WorkBatons with Pro-only retention
- access logs older than the Free retention window
- profile settings that must be reset to Free-compatible values

The dry-run must not delete rows, update the profile, select WorkBaton body
content, or print encrypted payloads. Existing Pro-created WorkBatons are
customer data; do not destroy or silently orphan them during downgrade.

## Account Delete Dry-Run

Run account delete dry-run before any product-data cleanup. It returns row
counts only for:

- `user_profiles`
- `contexts`
- `stats`
- `api_keys`
- `access_logs`
- `work_threads`
- `work_thread_messages`
- `work_thread_tasks`
- `work_thread_runs`

The dry-run must not select or print `contexts.content`, `api_keys.key_hash`,
`work_thread_messages.content`, Authorization headers, tokens, DB URLs, or
local client key material.

## Delete Order

1. Confirm user identity and legal/account request scope.
2. Run account delete dry-run and record counts only.
3. Run the reviewed product cleanup, when implemented.
4. Run the orphan scan for the same user id and confirm all product-owned row
   counts are zero.
5. Delete the Supabase Auth user only after product cleanup and orphan scan
   succeed.

If any count is unexpected, pause and use the migration/manual SQL checklist in
`docs/runbooks/deploy.md`. Do not run destructive SQL without a backup point,
expected row count, and forward-fix plan.
