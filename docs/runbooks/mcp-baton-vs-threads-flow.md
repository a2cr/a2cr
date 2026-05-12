# A2CR MCP Flow: WorkBaton Vs WorkThreads

Last updated: 2026-05-10

Status: Draft design note

This note documents what happens after an AI agent calls A2CR through MCP.
Both WorkBaton and WorkThreads are MCP-facing product flows, but they must stay
separate in behavior, storage, and user expectations.

## Common Rule

AI agents call A2CR MCP tools. They must not guess or call direct HTTP API
endpoints from prompts.

HTTP routes may exist behind the service, dashboard, local stdio wrapper, or
remote MCP surface. Those routes are implementation details. The product
contract for AI agents is MCP.

Agents should call `explain_a2cr_flows` when they are newly connected to A2CR,
when they are unsure whether to use WorkBaton or WorkThreads, or when they need
to confirm the encryption boundary before saving or posting content.

## MCP Tool Selection Contract

AI agents should be able to choose the correct A2CR tool family from the user's
intent without requiring the user to name the tool.

Use WorkThreads when the request involves any of these signals:

- Shared workspace or collaborative work state.
- Multiple AI agents, multiple AI windows, or cross-client coordination.
- Questions, answers, decisions, handoffs, blocked states, or results between
  agents.
- Task assignment, task claim, task completion, or lease-based coordination.
- Waiting for another active agent or checking whether another agent posted an
  update.

Use WorkBaton when the request is a serial checkpoint for a future AI window:

- Save the current work state so another window can resume later.
- Resume or load a focused checkpoint within the available size budget.
- Finalize a WorkThread into a WorkBaton only through an explicit finalization
  step using the local stdio encryption path.

Use WorkStash only as temporary supporting memory referenced by a WorkBaton:

- Store safe intermediate notes that would bloat the WorkBaton body.
- Retrieve only WorkStash entries referenced by the loaded WorkBaton and needed
  for the current task.

WorkBaton and WorkStash must not be used as substitutes for WorkThreads live
coordination. If WorkThreads tools are unavailable and the user asks for shared
agent coordination, the AI should report that WorkThreads is unavailable on the
current MCP surface instead of silently saving a Baton or Stash note.

`explain_a2cr_flows` and tool descriptions should include this decision rule so
newly connected agents can route requests without guessing. The WorkBaton and
WorkStash tool descriptions should explicitly say they are not for live
multi-agent collaboration, task leases, shared threads, or waiting on another
agent.

## Tool Families

Orientation tools:

- `explain_a2cr_flows`
- `should_save_workbaton`

WorkBaton tools:

- `save_context`
- `resume_context`
- `load_context`
- `list_contexts`
- `get_account_limits`

Autonomous save guidance is specified in
`docs/runbooks/workbaton-autonomous-save-spec.md`.
Agents can call `should_save_workbaton` before saving when the trigger, Slot, or
current MCP surface is unclear.

Implemented WorkThreads tools:

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

Planned WorkThreads tools stay in this list until they are implemented and
covered by tests. After that, move them to the implemented list:

- `get_coordination_rules`
- `register_workthread_agent`
- `standby_workthread_agent`
- `heartbeat_workthread_agent`
- `list_workthread_agents`
- `leave_workthread_agent`
- `get_workthread_inbox`

Disabled until a local stdio encryption flow exists:

- `save_workthread_result`

## Account Coordination Rule Loading

Account coordination rules are loaded through authenticated MCP/API tools, not
by direct database access from AI agents.

When an agent connects or starts WorkThreads work:

1. The agent reads the shared A2CR MCP instructions and tool descriptions.
2. The agent may call `explain_a2cr_flows` for global Baton/Stash/Threads
   routing.
3. When `get_coordination_rules` is available, the agent calls it when it needs
   the authenticated account's WorkThreads operating policy.
4. A2CR authenticates the request, reads the account's active rule binding, and
   returns the admin-managed template version as read-only work policy.
5. The agent treats those rules as task guidance, not as instructions that
   override system, developer, user, or current-file instructions.

Until `get_coordination_rules` is implemented, agents rely on the shared MCP
instructions and thread-visible coordination contract. They must not query
database tables or guess direct HTTP API calls to fetch rules.

When `create_workthread` creates a thread, it should seed the initial
coordination contract from the active account rule by copying `rules_json` into a
frozen thread-level `coordination_contract_json` snapshot. It should also record
`coordination_rule_key`, `coordination_template_id`, and
`coordination_template_version` for audit and traceability. This prevents active
threads from silently changing behavior when a service administrator publishes a
newer rule template.

Agents should read the WorkThread's frozen `coordination_contract_json` as the
thread contract. They should not re-resolve the latest template version for an
existing active thread.

Service administrators may publish new template versions or change account
bindings through admin-only paths. Normal users, API keys, and MCP agents may
read their bound rules but must not update templates or bindings.

## Agent Identity And Standby

WorkThreads routes work to a specific agent identity or session, not to a display
name alone. `agent_name` is human-readable display metadata and may collide. It
must not be treated as the only routing identity.

Use these identity layers:

- `agent_id`: stable logical agent identity in the account.
- `agent_instance_id`: unique identity for one active AI window or chat session.
- `agent_name`: display label such as `GPT`, `Claude`, or `Cursor`.
- `role`: the WorkThread role the instance is currently offering.

Targeting should prefer `target_agent_instance_id`, then `target_agent_id`, then
`target_role`. `target_agent_name` is only a fallback/display field. Task leases
should use `agent_instance_id` when a specific active window owns the work.

The current implemented surface may still expose only `agent_name`,
`target_agent_name`, and `lease_owner`. Until dedicated identity fields exist,
agents should treat `target_agent_name` as a backward-compatible fallback and put
unique identity details in structured message content.

Standby is user- or coordinator-directed and thread-scoped. An AI window is not
ready for a WorkThread merely because it is MCP-connected. When the user says to
enter a specific WorkThread/window and become ready, the agent should:

1. Load global A2CR rules and account coordination rules.
2. Read the target WorkThread coordination contract.
3. Register or announce `agent_id`, `agent_instance_id`, `role`, and
   `capabilities`.
4. Post or record standby/ready for that `thread_id`.
5. Maintain a recent heartbeat or update-check cadence while available.

The ready state applies only to that specific WorkThread and that specific
`agent_instance_id`. Other windows with the same `agent_name` must not assume the
task is theirs.

### Manual Invite Join Flow

For MVP collaboration, WorkThreads uses a user-mediated invite flow:

Manual invite text is a correlation and instruction artifact, not an
authentication secret. It does not grant access by itself. Only agents
authenticated through the owning account's A2CR MCP/API credentials can read or
post to the WorkThread.

1. The user asks the coordinator to prepare WorkThreads collaboration for a
   specific task.
2. The coordinator creates or selects the WorkThread, reads account coordination
   rules, posts the coordination contract, and marks its own coordinator window
   ready.
3. The coordinator generates invite text for each intended participant window.
4. The user pastes the invite into the exact authenticated AI window that should
   join.
5. The invited agent calls A2CR MCP tools, reads the provided WorkThread, creates
   or registers a unique `agent_instance_id`, and posts standby/ready.
6. The coordinator verifies the ready windows before assigning tasks.

The invite text should include `thread_id`, expected `agent_id`, expected role,
requested capabilities, join steps, standby rules, and a reminder not to start
implementation until the coordinator assigns or confirms a task.

This flow is intentionally manual. A2CR should not assume that every
MCP-connected window is available, and it should not silently select a different
window with the same display name. Only the authenticated window that receives
the invite and announces ready is considered a participant.

## WorkBaton Flow

WorkBaton is a serial checkpoint flow:

```text
window -> WorkBaton -> new window -> WorkBaton -> new window
```

Primary purpose:

- Save the useful state of current work.
- Let a new AI window, model, or MCP-capable client resume later.
- Reduce long-context carryover.

After an AI agent calls `save_context`:

1. The AI agent sends compact work state through the local stdio A2CR MCP
   wrapper.
2. The wrapper validates that the body is a WorkBaton-shaped JSON object.
3. The wrapper encrypts the body locally with the user's local client key.
4. A2CR receives `encrypted_content` plus metadata, not plaintext content.
5. A2CR stores the ciphertext in `public.contexts`.
6. A2CR updates metadata, stats, access logs, expiry, and plan-limit state.
7. A2CR returns metadata plus a resume instruction such as
   `resume_context(slot_name="...")`.
8. The current AI should give the user the resume prompt or save it as the next
   action.

After a new AI window calls `resume_context` or `load_context`:

1. The AI calls the A2CR MCP tool with a slot name, slot number, or project
   search.
2. A2CR returns the matching checkpoint metadata and encrypted body.
3. The local stdio wrapper decrypts the body locally when the matching local
   client key exists.
4. The new AI treats loaded WorkBaton content as untrusted work data.
5. The new AI inspects the current workspace as needed and continues from
   `goal`, `current_state`, `next_action`, and blockers.

WorkBaton must not:

- Become a long-running chat log.
- Track participant state.
- Track per-agent read cursors.
- Coordinate task leases.
- Subscribe agents to live updates.
- Silently create or mutate a WorkThread.

## WorkThreads Flow

WorkThreads are a collaborative coordination flow:

```text
agent <-> WorkThread <-> agents
```

Primary purpose:

- Let multiple AI windows, AI clients, or AI agents coordinate over shared work.
- Keep structured conversation, decisions, questions, and task leases in one
  durable workspace.
- Support GitHub- or MCP-mediated external agent participation later without
  tying A2CR to one AI vendor or orchestrator.

After an AI agent calls `create_workthread`:

1. The AI calls the A2CR MCP tool with a title, purpose, optional initial
   message, and agent name.
2. The agent encrypts any initial message locally with the WorkThread key.
3. A2CR authenticates the MCP credential and confirms the plan allows
   WorkThreads.
4. A2CR creates a row in `public.work_threads`.
5. If an initial message exists, A2CR stores the ciphertext envelope in
   `public.work_thread_messages`.
6. A2CR returns thread metadata, not a WorkBaton resume prompt.

After an AI agent calls `post_workthread_message`:

1. A2CR authenticates the MCP credential and checks write permission.
2. The agent submits a locally encrypted message ciphertext envelope.
3. The local client refuses plaintext message JSON bodies over 10KB before
   encryption; A2CR rejects oversized ciphertext envelopes according to the
   implementation limit.
4. A2CR checks idempotency and content hash duplication over safe canonical
   ciphertext metadata, not plaintext.
5. A2CR applies deterministic loop guard rules using metadata fields such as
   message type, target, response-required status, and parent id.
6. A2CR appends the ciphertext envelope without decrypting it.
7. A2CR updates thread activity metadata.
8. Other agents can later call read, pending-response, check, or wait tools.

After an AI agent calls `read_workthread`, `pending_workthread_responses`
(`unread_workthread` during the deprecated alias period), or
`wait_workthread_updates`:

1. A2CR authenticates the MCP credential and checks read permission.
2. A2CR returns ciphertext envelopes only through authenticated API/MCP routes.
3. The receiving AI decrypts locally only if it has the WorkThread key.
4. Dashboard routes continue to return metadata only.
5. The receiving AI decides whether to answer, create a task, claim a task,
   post a decision, or hand off.

### Conversation Continuity

WorkThreads continuity is pull-based. A2CR does not wake a stopped AI agent when
another participant posts a message. An inactive agent only learns about new
messages the next time it is running and calls a WorkThreads MCP tool.

Active agents continue a conversation with this pattern:

1. Keep a local cursor such as the latest message timestamp returned by
   `check_workthread_updates`, `wait_workthread_updates`, or a recent
   `read_workthread` call.
2. Call `check_workthread_updates(thread_id, since)` at startup, after a work
   chunk, and before posting a major decision.
3. Call `wait_workthread_updates(thread_id, since, timeout_seconds)` only when
   another active agent is expected to respond soon. Waits must be bounded and
   must not become an infinite subscription.
4. Call `read_workthread` when updates exist, then respond with
   `post_workthread_message`.
5. Use `parent_message_id` when answering a question or resolving a blocked
   state so the conversation remains traceable.

The product vocabulary must keep these states separate:

- New messages: messages after an agent's local cursor.
- Pending responses: messages that require a response, optionally targeted at an
  agent.
- Unresolved questions: pending response-required messages that still count
  against loop guard limits.
- Seen/read position: a per-agent cursor, not the same thing as unresolved
  status.

The MVP may use `since` timestamps as the practical cursor. The intended public
name for response-required messages is `pending_workthread_responses`.
`unread_workthread` remains as a deprecated alias during migration, but it must
not be described as true unread state. True unread tracking with per-agent seen
cursors is a post-MVP feature.

A response-required message is unresolved while `resolved_at` is null. Posting
an `answer`, `decision`, `handoff`, `blocked`, or `result` with a same-thread
`parent_message_id` resolves the parent message and stores that resolving
message id in `resolved_by_message_id`.

### Coordinator-Led Review Rounds

For design, specification, architecture, and other coding-critical planning
work, a coordinator agent may run bounded review rounds before implementation
tasks begin.

The expected flow is:

1. The coordinator posts a draft design/spec proposal as a thread-visible
   message with `audience="all"`, `proposal_version`, and `review_round`.
2. The coordinator posts targeted feedback requests for the relevant agents with
   the most specific available target identity, `requires_response=true`, and a
   round-specific `consultation_id`. Use `target_agent_name` only as a
   backward-compatible fallback.
3. All agents read the proposal and thread context, including messages not
   targeted at them.
4. Targeted agents answer with `parent_message_id` pointing to the request.
5. The coordinator accepts or rejects suggestions and posts a `decision`
   summarizing changes, rejected options, remaining tradeoffs, and the next
   action.
6. The coordinator may run a second review round, and a third round only when
   the design risk justifies it.
7. If agents do not agree, the coordinator makes the final call and posts the
   frozen design/spec decision before creating implementation tasks.

Use a distinct `consultation_id` for each review round. Do not keep all review
rounds in one consultation because the loop guard intentionally limits repeated
question/answer cycles. Do not start a new review round until the previous
round's required responses are answered, explicitly resolved, or timed out by a
coordinator decision.

Target identity fields control who should act. They do not hide the message from
other agents. `target_agent_name` is only the fallback when more specific target
fields are unavailable. Non-targeted agents should observe and update their
local context, but should not answer another agent's targeted request unless
doing so prevents a clear conflict or the coordinator asked for open feedback.

After an AI agent calls task tools:

1. `create_workthread_task` creates a pending task.
2. `claim_workthread_task` claims one pending or expired task with a short
   lease.
3. The claim operation uses database locking semantics so competing agents do
   not claim the same task.
4. `complete_workthread_task` completes the task only when the lease owner
   matches and the lease has not expired.
5. `fail_workthread_task` fails a claimed task only when the lease owner matches
   and the lease has not expired.
6. `fail_workthread_task` accepts `task_id`, `lease_owner`, compact `reason`,
   and optional `result_message_id`.
7. Agents should post a `blocked` or `result` message first when failure needs
   more context, then link that message through `result_message_id`.
8. Task mutation responses remain metadata-only.

WorkThreads must not:

- Run LLM inference on the A2CR server.
- Route models or choose agents automatically.
- Receive, store, log, or recover WorkThread keys.
- Decrypt WorkThread message bodies server-side.
- Store final WorkBaton checkpoints automatically.
- Expose message content through dashboard routes.
- Encourage agents to call direct HTTP endpoints.

## Finalizing A Thread Into A Baton

WorkThreads may produce a final result that should become a WorkBaton, but this
must be explicit.

Allowed finalization shape:

1. An agent reads the Thread through MCP.
2. The agent writes a compact final WorkBaton body with `goal`,
   `current_state`, `next_action`, decisions, blockers, and references.
3. The agent calls `save_context` through the local stdio A2CR MCP wrapper.
4. The wrapper encrypts locally before upload.
5. The Thread may store the final Slot name as metadata.

Not allowed:

- Remote MCP `save_workthread_result` accepting plaintext result content.
- A server-side shortcut that copies WorkThread message content into
  `public.contexts`.
- Automatic Slot creation when a Thread receives a `result` message.

## Comparison Table

| Area | WorkBaton | WorkThreads |
| --- | --- | --- |
| Shape | Serial handoff | Collaborative workspace |
| Flow | window -> new window | agent <-> agents |
| Main tool action | save/load/resume checkpoint | post/read/wait/task coordination |
| Primary DB table | `public.contexts` | `public.work_threads`, `public.work_thread_messages`, `public.work_thread_tasks`, `public.work_thread_runs` |
| Body storage | Client-encrypted before upload | Client-encrypted before upload with a thread key |
| Server plaintext access | A2CR cannot decrypt body | A2CR cannot decrypt message bodies without the thread key |
| Dashboard content | Metadata only | Metadata only |
| Return value | resume prompt and checkpoint metadata | thread/task metadata plus message ciphertext envelopes through MCP |
| Next AI action | Continue from `next_action` in a new window | Answer, decide, wait, claim task, complete task, or hand off |
| Multi-agent state | Not tracked | Core purpose |
| Live coordination | No | Yes, bounded by polling/wait and loop guard |
| Task leases | No | Yes |
| Finalization | The checkpoint itself | Optional explicit save into WorkBaton |

## Design Consequences

- WorkBaton credentials and WorkThreads credentials may share an account, but
  WorkThreads should evolve toward named agent credentials with scopes.
- A WorkThread participant should be identified by authenticated A2CR MCP/API
  credentials plus thread-scoped identity fields such as `agent_instance_id`, not
  by pasted secrets in messages.
- A WorkThread participant must also have the thread key to read or post
  meaningful message bodies.
- Thread keys are key material and must not be saved in WorkBaton, WorkStash,
  WorkThread messages, logs, dashboard payloads, or support transcripts.
- WorkThread messages should stay compact because Threads are coordination
  state, not permanent document storage.
- GitHub-linked external agents should still enter through MCP-compatible tool
  calls or an A2CR-controlled integration that maps events to MCP-equivalent
  operations.
- Any bridge between GitHub, WorkThreads, and WorkBaton must preserve the
  separation: GitHub is the public work surface, Threads are the coordination
  workspace, and Baton is the explicit serial checkpoint.
