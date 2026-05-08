# A2CR MCP Flow: WorkBaton Vs WorkThreads

Last updated: 2026-05-08

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

WorkThreads tools:

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
- future optional `fail_workthread_task`

Disabled until a local stdio encryption flow exists:

- `save_workthread_result`

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
2. A2CR authenticates the MCP credential and confirms the plan allows
   WorkThreads.
3. A2CR creates a row in `public.work_threads`.
4. If an initial message exists, A2CR stores it in `public.work_thread_messages`
   encrypted at rest with the A2CR service key.
5. A2CR returns thread metadata, not a WorkBaton resume prompt.

After an AI agent calls `post_workthread_message`:

1. A2CR authenticates the MCP credential and checks write permission.
2. A2CR checks idempotency and content hash duplication.
3. A2CR applies deterministic loop guard rules.
4. A2CR encrypts and appends the message.
5. A2CR updates thread activity metadata.
6. Other agents can later call read, unread, check, or wait tools.

After an AI agent calls `read_workthread`, `unread_workthread`, or
`wait_workthread_updates`:

1. A2CR authenticates the MCP credential and checks read permission.
2. A2CR returns messages only through authenticated API/MCP routes.
3. Dashboard routes continue to return metadata only.
4. The receiving AI decides whether to answer, create a task, claim a task,
   post a decision, or hand off.

After an AI agent calls task tools:

1. `create_workthread_task` creates a pending task.
2. `claim_workthread_task` claims one pending or expired task with a short
   lease.
3. The claim operation uses database locking semantics so competing agents do
   not claim the same task.
4. `complete_workthread_task` completes the task only when the lease owner
   matches and the lease has not expired.
5. Future `fail_workthread_task` should follow the same lease-owner rule.

WorkThreads must not:

- Run LLM inference on the A2CR server.
- Route models or choose agents automatically.
- Claim WorkBaton-equivalent client encryption.
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
| Body storage | Client-encrypted before upload | Encrypted at rest by A2CR service key |
| Server plaintext access | A2CR cannot decrypt body | Authenticated API/MCP routes may decrypt for owner |
| Dashboard content | Metadata only | Metadata only |
| Return value | resume prompt and checkpoint metadata | thread/message/task metadata or message content through MCP |
| Next AI action | Continue from `next_action` in a new window | Answer, decide, wait, claim task, complete task, or hand off |
| Multi-agent state | Not tracked | Core purpose |
| Live coordination | No | Yes, bounded by polling/wait and loop guard |
| Task leases | No | Yes |
| Finalization | The checkpoint itself | Optional explicit save into WorkBaton |

## Design Consequences

- WorkBaton credentials and WorkThreads credentials may share an account, but
  WorkThreads should evolve toward named agent credentials with scopes.
- A WorkThread participant should be identified by agent name and credential,
  not by pasted secrets in messages.
- WorkThread messages should stay compact because Threads are coordination
  state, not permanent document storage.
- GitHub-linked external agents should still enter through MCP-compatible tool
  calls or an A2CR-controlled integration that maps events to MCP-equivalent
  operations.
- Any bridge between GitHub, WorkThreads, and WorkBaton must preserve the
  separation: GitHub is the public work surface, Threads are the coordination
  workspace, and Baton is the explicit serial checkpoint.
