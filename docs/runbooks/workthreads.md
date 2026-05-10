# WorkThreads Runbook

WorkThreads are Pro-only durable handoff threads for cross-window and cross-agent work. They are not a server-side LLM feature. A2CR stores client-encrypted append-only message bodies, task lease metadata, progress metadata, and final Slot links.

## Encryption Design

WorkThreads message bodies use local client-side encryption, like WorkBaton,
but with a thread-scoped shared key instead of a single-window private key. Only
AI windows or agents that know the WorkThread key can decrypt or post readable
messages for that thread. A2CR must not receive, store, log, or recover the
thread key.

The coordinator or user creates the WorkThread key locally and shares it only
with the specific authenticated agent windows that should participate. Key
distribution is outside the A2CR server boundary until a local stdio wrapper
flow exists for it. Invite text remains a correlation and instruction artifact;
it must not be treated as an auth token, and it should not contain key material
unless the user intentionally gives that key to the receiving AI window.

The security posture for WorkThreads is:

- Message bodies are encrypted locally before upload and stored as ciphertext.
- Message content JSON bodies are limited to 10KB before encryption.
- A2CR cannot decrypt WorkThread message bodies without the thread key.
- Agents without the thread key can see thread metadata but cannot read message
  bodies.
- Tenant isolation is enforced by RLS and `user_id` predicates.
- Thread keys must never be exposed in logs, dashboard payloads, WorkBaton
  Slots, WorkStash entries, support messages, or A2CR server responses.

Implementation status: any existing server-side WorkThread body encryption path
must be treated as a pre-beta implementation gap. WorkThreads must remain hidden
or internal-only until local thread-key encryption is implemented and covered by
tests.

## Content Boundary

- API-key and MCP routes may return WorkThread ciphertext and metadata for the
  authenticated user. Decryption happens locally in an agent/client that has the
  thread key.
- Dashboard routes return metadata only: title, purpose, status, loop status, message count, task count/status, agent names, last activity, and final Slot name.
- Dashboard and React payloads must never include `work_thread_messages.content`, prompts, or full AI responses.
- WorkThreads must not write to Core `contexts` except through the explicit final-result save path.
- WorkBaton is a serial checkpoint flow, while WorkThreads are a collaborative
  coordination flow. Do not use WorkBaton as a chat log, and do not let
  WorkThreads silently create or overwrite WorkBaton Slots.

## MCP Tools

Implemented MCP tools:

- `create_workthread`
- `list_workthreads`
- `post_workthread_message`
- `read_workthread`
- `pending_workthread_responses`
- `unread_workthread` as a deprecated alias for pending responses during
  migration
- `check_workthread_updates`
- `wait_workthread_updates`
- `create_workthread_task`
- `claim_workthread_task`
- `complete_workthread_task`
- `fail_workthread_task`

Planned MCP tools stay in this list until they are implemented and covered by
tests. After that, move them to the implemented list:

- `get_coordination_rules`
- `register_workthread_agent`
- `standby_workthread_agent`
- `heartbeat_workthread_agent`
- `list_workthread_agents`
- `leave_workthread_agent`
- `get_workthread_inbox`

Disabled until a local stdio encryption flow exists:

- `save_workthread_result`

Use MCP tools directly from AI clients. Do not guess or call direct HTTP API endpoints from client prompts.

Do not enable WorkThread final-result saving, file attachment, URL fetch, HTML/render preview, or AI-execution features without a dedicated security review and regression tests.

## Account Coordination Rules

A2CR can store account coordination rules as admin-managed, versioned templates
with per-account bindings. When the planned `get_coordination_rules` tool is
available, AI agents read these rules through authenticated MCP/API tools; they
do not query DB tables directly.

Rules are read-only for normal users, API keys, and MCP agents. Service
administrators update rules by publishing a new template version or changing an
account binding through admin-only migration/script/API paths. Prefer adding a
new version over overwriting an existing template.

New Google/Supabase Auth users should receive a default profile and default
coordination rule binding during onboarding. The onboarding path must be
idempotent and protected by unique constraints.

When a WorkThread is created, A2CR should seed the initial coordination contract
from the account's active rule by copying `rules_json` into a frozen
thread-level `coordination_contract_json` snapshot. It should also record
`coordination_rule_key`, `coordination_template_id`, and
`coordination_template_version` for audit and traceability. Existing active
threads should not silently change behavior just because a newer rule template is
published.

Agents should read the WorkThread's frozen `coordination_contract_json` as the
thread contract. They should not re-resolve the latest template version for an
existing active thread.

Coordination rules are work policy only. They must not override system,
developer, user, or current-file instructions, and they must not contain secrets,
API keys, Authorization headers, private database URLs, personal data, long logs,
or source-code bodies.

## Agent Identity And Standby

`agent_name` is display metadata only. It may be `GPT`, `Claude`, or `Cursor`,
and multiple windows may share the same name. Routing, readiness, and task leases
must use unique identities instead:

- `agent_id` for a stable logical agent within the account
- `agent_instance_id` for one active AI window or chat session
- `role` for the work the instance is offering on the thread
- `capabilities` for concise task-fit metadata

Prefer targeting in this order: `target_agent_instance_id`,
`target_agent_id`, `target_role`, then `target_agent_name` only as a fallback.
Task leases should use `agent_instance_id` when a specific active window owns the
task.

The current implemented API may still expose only `agent_name`,
`target_agent_name`, and `lease_owner`. Until the planned identity fields exist,
agents should treat `target_agent_name` as a backward-compatible fallback and put
unique identity details in structured message content.

Readiness is explicit and WorkThread-scoped. MCP connection alone does not make
an AI window ready. A window becomes ready only after the user or coordinator
directs it to join a specific WorkThread, it reads the coordination contract, and
it announces standby/ready with its unique `agent_instance_id`, role, and
capabilities. The ready state applies only to that thread and that window.

Until dedicated readiness tools exist, represent standby with a structured
WorkThread message that includes `agent_id`, `agent_instance_id`, `role`,
`capabilities`, and `status="ready"`.

## Manual Invite Join Flow

The MVP join flow is user-mediated. The user asks the coordinator to prepare a
WorkThread, the coordinator creates or selects the thread, posts the coordination
contract, and generates invite text for each participant window. The user then
pastes each invite into the exact authenticated AI chat window that should join.

Invite text is a correlation and instruction artifact, not an authentication
secret. It does not grant access by itself. Only agents authenticated through the
owning account's A2CR MCP/API credentials can read or post to the WorkThread.

The invited agent reads the WorkThread contract through A2CR MCP tools, reads
account rules when `get_coordination_rules` is available, generates or registers
a unique `agent_instance_id`, and posts a ready/standby message. The coordinator
should verify ready participants before assigning tasks or starting review
rounds.

Invite text should include the `thread_id`, expected `agent_id`, role, requested
capabilities, join steps, standby rules, and a reminder not to start
implementation until the coordinator assigns or confirms a task. Only the
authenticated window that received the invite and announced ready is a
participant.

## Conversation Continuity

WorkThreads are pull-based. A2CR does not push notifications to stopped AI
agents and does not wake an inactive AI window when another agent posts. An agent
learns about new messages only when it is running and calls a WorkThreads MCP
tool.

Agents should call `check_workthread_updates` at startup and after meaningful
work chunks. Use `wait_workthread_updates` only when another active agent is
expected to respond soon; waits are bounded and must not become an infinite
subscription. After updates are detected, the agent reads the thread and posts an
answer, decision, handoff, blocked state, or result.

Keep these states distinct:

- new messages after an agent's local cursor
- response-required messages waiting for an agent
- unresolved questions that count against loop guard limits
- per-agent seen/read position

`pending_workthread_responses` is the public name for unresolved
response-required messages waiting on an agent. `unread_workthread` remains as a
deprecated alias during migration, but it must be documented as a
pending-response query, not true unread state. True unread tracking with
per-agent seen cursors is a post-MVP feature.

A response-required message is unresolved while `resolved_at` is null. Posting
an `answer`, `decision`, `handoff`, `blocked`, or `result` with a same-thread
`parent_message_id` resolves the parent message and records the resolving
message id in `resolved_by_message_id`.

## Coordinator-Led Review Rounds

For design documents, specifications, and architecture choices, the coordinator
agent may run 2 review rounds by default and up to 3 rounds when the risk
justifies it.

The coordinator posts the draft to all agents, requests bounded feedback from
each relevant agent, reads the responses, accepts or rejects suggestions, and
posts a `decision` with the revised direction. If the agents do not agree, the
coordinator makes the final call and records the reason before implementation
tasks begin.

All agents should read the full review context, including messages targeted at
other agents, because those decisions can affect their own work. Target identity
fields mean who should act; they do not mean only that agent can read the
message. `target_agent_name` is only the fallback when more specific target
fields are unavailable.

Use a separate `consultation_id` per review round, and do not start the next
round until the previous round's required responses are answered, resolved, or
timed out by coordinator decision.

## Task Leases

`claim_workthread_task` uses a short database transaction with `FOR UPDATE SKIP LOCKED`. The transaction ends before any AI work begins. A task can be completed only by the matching `lease_owner` while the lease is active. Expired leases can be reclaimed.

`fail_workthread_task` uses the same lease-owner and active-lease checks as
completion. It accepts `task_id`, `lease_owner`, compact `reason`, and optional
`result_message_id`. Agents should post a `blocked` or `result` message first
when failure needs more context, then link it through `result_message_id`. Task
mutation responses remain metadata-only.

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

Core remains the source of truth for user id, plan, API key, and billing state.
WorkThreads can be disabled by not mounting `routers.workthreads` and hiding
`/api/dashboard/workthreads`; Core WorkBaton save/load/resume and `/mcp`
context tools remain independent.

AI agents use MCP tools as the product contract. Direct HTTP routes are an
implementation detail for the service and dashboard; client prompts must not
guess or call them.
