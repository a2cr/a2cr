# WorkThreads Runbook

WorkThreads are Pro-only durable handoff threads for cross-window and cross-agent work. They are not a server-side LLM feature. A2CR stores encrypted append-only messages, task lease metadata, progress metadata, and final Slot links.

## Content Boundary

- API-key and MCP routes may read decrypted WorkThread messages for the authenticated user.
- Dashboard routes return metadata only: title, purpose, status, loop status, message count, task count/status, agent names, last activity, and final Slot name.
- Dashboard and React payloads must never include `work_thread_messages.content`, prompts, or full AI responses.
- WorkThreads must not write to Core `contexts` except through the explicit final-result save path.

## MCP Tools

- `create_workthread`
- `list_workthreads`
- `post_workthread_message`
- `read_workthread`
- `unread_workthread`
- `check_workthread_updates`
- `wait_workthread_updates`
- `create_workthread_task`
- `claim_workthread_task`
- `complete_workthread_task`
- `save_workthread_result`

Use MCP tools directly from AI clients. Do not guess or call direct HTTP API endpoints from client prompts.

## Task Leases

`claim_workthread_task` uses a short database transaction with `FOR UPDATE SKIP LOCKED`. The transaction ends before any AI work begins. A task can be completed only by the matching `lease_owner` while the lease is active. Expired leases can be reclaimed.

## Loop Guard

Loop guard rules are deterministic and do not call an LLM:

- max 6 messages per `consultation_id`
- max 3 question messages per `consultation_id`
- max 3 unresolved questions per thread
- max 3 repeated waits for the same reason in one hour
- duplicate `content_hash` or `idempotency_key` is rejected
- after guard block, only `decision`, `handoff`, `blocked`, or `result` messages can be posted

Loop guard audit rows use `work_thread_runs.reason` and never store message content.

## Separation Boundary

Core remains the source of truth for user id, plan, API key, and billing state. WorkThreads can be disabled by not mounting `routers.workthreads` and hiding `/api/dashboard/workthreads`; Core WorkBaton save/load/resume and `/mcp` context tools remain independent.
