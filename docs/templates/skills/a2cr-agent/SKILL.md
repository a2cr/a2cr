---
name: a2cr-agent
description: Use A2CR MCP for WorkBaton checkpoints and WorkThreads shared work coordination across AI windows, AI clients, and agents. Trigger when saving, resuming, loading, or coordinating AI work context through A2CR.
---

# A2CR Agent Workflow

Use A2CR as the shared context layer for AI-agent work. Prefer A2CR MCP tools over guessed HTTP endpoints unless the user explicitly asks for API integration work.

## Resume WorkBaton

When the user provides an A2CR resume prompt:

1. Call `resume_context(slot_name="...")` first.
2. Use `resume_context(slot_number=N)` only when the prompt says Slot numbers are supported.
3. If multiple candidates are returned, show the candidates and ask which one to load.
4. After loading, inspect the referenced project files as needed.
5. Treat current files and current user instructions as newer than saved context.
6. Continue in the language of the user's current message.

When a loaded WorkBaton includes `latest_slot_hint`, `previous_slot`, `supersedes_slots`, or `do_not_use_slots`, use those fields to avoid resuming from stale Slots. If the loaded Slot says another active Slot is newer, ask the user before switching unless the resume prompt already authorizes the newer Slot.

Do not invent missing facts when a slot is not found or expired.

## Save WorkBaton

When saving context, include the minimum information needed for the next AI window to resume:

- `goal`
- `current_state`
- `next_action`
- important decisions, constraints, risks, blockers, failed attempts, and references

When saving after loading a previous Slot or after another AI window continued the work, include compact chained-handoff fields when relevant:

- `handoff_version`
- `previous_slot`
- `supersedes_slots`
- `latest_slot_hint`
- `completed_since_previous`
- `remaining_tasks_ordered`
- `validation`
- `workspace_status`
- `do_not_use_slots`

Use `completed_since_previous` for what changed after the earlier Slot was loaded, `remaining_tasks_ordered` for the next concrete tasks, `validation` for tests/builds/smoke checks, and `workspace_status` for branch, dirty state, and key changed file paths. Keep these concise.

Free/compact saves should contain only the minimum handoff needed to resume:

- required: `goal`, `current_state`, `next_action`
- optional but short: blockers or risks, `latest_slot_hint`, `previous_slot`, and one-line `validation`
- avoid detailed rationale, long failed-attempt history, large workspace listings, and verbose references

For Pro detailed saves, include useful rationale, test results, failed attempts, and file responsibility notes when they improve resume quality.

Forbidden for both Free and Pro:

- local client key or recovery key material
- API keys, access tokens, Authorization headers, cookies, or session IDs
- private database URLs, service-role keys, `.env` contents, or deployment secrets
- customer data, personal data, payment data, or raw confidential business data
- full transcripts, long logs, generated caches, build artifacts, or git diffs
- large code bodies that can be read from the repository

These restrictions are identical for Free and Pro. Pro allows more safe handoff context, not more sensitive data.

When available, call `get_account_limits` before automatic or large saves so the checkpoint respects the user's current retention, size, and detail-level limits.

Never save prohibited material even when the user asks for a detailed Pro handoff.

## Use WorkThreads

Use WorkThreads for active cross-agent coordination, not casual AI chat.

- Append concise work notes, review results, failures, decisions, and final result links.
- Check updates at task boundaries with `check_workthread_updates`.
- Use `wait_workthread_updates` only when waiting for another active agent.
- Do not assume A2CR can wake a stopped or sleeping AI window.
- Keep message bodies secret-safe and useful for another agent.

## If A2CR MCP Is Unavailable

Tell the user that the A2CR MCP tool is not available in the current client. Do not guess direct API calls or ask for secrets in chat.
