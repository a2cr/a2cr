# GPT Project Instructions For A2CR

Use these instructions when this project is opened in GPT / ChatGPT project
memory or copied into GPT custom instructions.

## A2CR Connection

A2CR MCP is the working-memory layer for this project. If A2CR MCP tools are
available, use them proactively. Do not guess direct HTTP API endpoints.

Use exactly one MCP server named `a2cr` when configuring A2CR. The user must
enter the API key into their MCP configuration themselves. Never ask the user to
paste an API key, Authorization header, private database URL, cookie, or other
secret into chat.

At the start of a session, if A2CR tools are available:

1. Call `get_account_limits` to verify the connection and current limits.
2. Call `explain_a2cr_flows` when newly connected or unsure whether to use
   WorkBaton, WorkStash, or WorkThreads.
3. Confirm briefly that A2CR is connected and that WorkBaton checkpoints will
   be saved at task milestones.

If A2CR tools are not available, continue normally and tell the user only when
the missing tools matter. Do not invent API calls or ask for secrets.

## WorkBaton

WorkBaton is for compact work-state handoff from one AI window to a future AI
window. Save only the information the next AI needs to continue:

- `goal`
- `current_state`
- `next_action`
- key decisions
- constraints and blockers
- concise validation status
- WorkStash `entry_key` references when supporting notes were stored

Save a WorkBaton checkpoint with `save_context` at task milestones, phase
completion, before context gets long, after important tests/builds pass, when a
clear blocker appears, or when the user is likely to switch tools, models, or
windows. Call `should_save_workbaton` first when unsure.

Use the local stdio A2CR MCP wrapper as the official WorkBaton save path so
content is encrypted locally before upload. Do not use remote HTTP endpoints for
WorkBaton saves.

When a resume prompt provides a Slot, first call:

- `resume_context(slot_name="...")`, or
- `resume_context(slot_number=N)`

Use `list_contexts` only when no Slot is provided and the user asks you to
search.

## WorkStash

WorkStash is temporary supporting memory referenced by WorkBaton. Use it when
details would bloat the WorkBaton but a future AI window may need them, such as:

- confirmed file paths
- API behavior notes
- reproduction details
- intermediate findings
- approach notes
- failed attempts
- concise validation summaries

When useful, store supporting notes with `store_work_stash` without waiting for
the user to ask. Record the returned `entry_key` in WorkBaton `references` or
`next_action` so the next window can retrieve it.

Retrieve only the WorkStash entries needed for the current task with
`get_work_stash(entry_key)`. Use `list_work_stash` only to locate metadata when
the key is missing. Delete entries with `delete_work_stash` when the task phase
is complete and the note is no longer useful.

Planned public-preview WorkStash limits are based on total encrypted storage
size, not number of notes:

- Free: 256KB total encrypted storage
- Pro: 2048KB total encrypted storage

WorkStash is not a durable knowledge base or file store.

## Never Save

Never save any of the following into WorkBaton or WorkStash:

- secrets
- API keys
- Authorization headers
- cookies
- private database URLs
- `.env` contents
- personal data
- full transcripts
- long logs
- generated caches
- git diffs
- large source-code bodies
- binary files or file-like payloads

If prohibited material is present, summarize safely or skip saving until it is
removed.

## Working Style

Keep changes simple and surgical. State assumptions when unclear, avoid
speculative features, and verify with focused tests or checks when changing
code. Continue in the language of the current user message.
