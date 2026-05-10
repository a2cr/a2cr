# A2CR WorkThreads MVP Specification And Implementation Plan

Last updated: 2026-05-10

Status: Draft for Stage 0 product scope freeze

This plan defines the first practical WorkThreads scope before implementation
continues. It is intentionally conservative: WorkThreads should prove durable
cross-window and cross-agent coordination before A2CR markets it as a public
Pro feature.

For the shared MCP entrypoint and the flow difference between WorkBaton and
WorkThreads, see `docs/runbooks/mcp-baton-vs-threads-flow.md`.

## Assumptions

- A2CR remains model-neutral, client-neutral, and orchestration-neutral.
- WorkThreads are a shared work-state layer, not a server-side AI execution
  system.
- Core WorkBaton save/load/resume remains independent from WorkThreads.
- AI agents interact with A2CR through MCP tools, not guessed direct HTTP API
  calls.
- AI agents can call `explain_a2cr_flows` to learn the Baton/Threads split and
  encryption boundaries before choosing a tool.
- WorkThread message-body secrecy should match the WorkBaton local-encryption
  boundary, using a thread-scoped shared key known only to participating agents.
- The first external release should be the free WorkBaton + WorkStash preview.
  WorkThreads should remain hidden or internal-only while OSS/community, payment,
  and remaining legal work are stabilized.

## Success Criteria

WorkThreads MVP is ready for private beta only when:

- Pro-only access is enforced across HTTP API, MCP, and dashboard paths.
- API-key and MCP routes can create, post, read, wait, and coordinate tasks.
- Account coordination rules are loaded from admin-managed, versioned rule
  templates and exposed to agents as read-only work policy.
- Dashboard routes return metadata only and never include message content.
- WorkThread message bodies are encrypted locally before upload; A2CR stores
  ciphertext and metadata only.
- Only agents that know the WorkThread key can decrypt or post readable
  messages for that thread.
- Loop guard behavior is deterministic, tested, and does not call an LLM.
- Task leases are short, reclaimable after expiry, and protected by
  `FOR UPDATE SKIP LOCKED`.
- Final-result saving into WorkBaton remains disabled unless a local stdio
  encryption flow is implemented and tested.
- Hosted smoke tests pass in staging before any external beta user relies on
  WorkThreads.

## Product Boundary

WorkThreads are for active coordination between AI windows, AI clients, or AI
agents that are already authenticated to the same A2CR account.

WorkBaton and WorkThreads must not collapse into one product behavior:

- WorkBaton is a serial handoff checkpoint: window -> new window -> new window.
- WorkThreads are collaborative workspaces: agent <-> agents over shared work.
- WorkBaton should not become a long-running chat log.
- WorkThreads should not silently write WorkBaton checkpoints.
- Moving a Thread result into a Baton must be an explicit finalization action
  through the local stdio encryption path.
- Loading a Baton may create or seed a Thread only when the user or agent
  explicitly asks for collaborative work.

Included in the MVP:

- Create a WorkThread with title, purpose, and optional initial message.
- List WorkThreads as metadata.
- Append structured messages.
- Read encrypted messages through authenticated API/MCP routes and decrypt them
  locally when the agent has the WorkThread key.
- Show dashboard metadata only.
- Poll or wait for updates.
- Create, claim, and complete lightweight tasks with leases.
- Detect duplicate messages with `idempotency_key` and content hash.
- Block runaway consultations with deterministic loop guard rules.
- Read account-bound coordination rules and seed new WorkThreads with a
  versioned coordination contract snapshot.
- Distinguish display agent names from unique agent/session identities for
  routing, task leases, and readiness.

Not included in the MVP:

- Server-side LLM execution.
- Autonomous agent orchestration.
- Cross-account sharing.
- Public dashboard display of message bodies.
- File attachments.
- URL fetching, HTML rendering, browser previews, or content scraping.
- Long-term document storage.
- Final-result WorkBaton saving from remote HTTP/MCP.
- Server-side WorkThread body decryption.
- Server-generated or server-recoverable WorkThread keys.
- Broad zero-knowledge marketing claims beyond the specific message-body
  encryption boundary.
- User-editable coordination rule authoring.
- Automatically treating every MCP-connected AI window as ready for every
  WorkThread.

## Neutrality Contract

WorkThreads must not depend on one AI vendor, one coding client, or one
orchestration framework.

The implementation should preserve these constraints:

- No model routing decisions.
- No hidden prompt execution.
- No server-side inference dependency.
- No client-specific state format beyond MCP/API request fields.
- Structured content should remain readable by Claude, Codex, Cursor, Roo, and
  other MCP-capable clients.

## Account Coordination Rules

A2CR may provide account-specific coordination rules to AI agents so each
contract account has a consistent WorkThreads operating policy.

Rules are stored as admin-managed templates plus account bindings, not as
per-user private tables. The database should use shared tables with `user_id` or
account ownership columns and RLS/user predicates for isolation.

Recommended data model:

- `coordination_rule_templates`
  - `id`
  - `rule_key`
  - `version`
  - `status`
  - `rules_json`
  - `created_at`
  - `updated_at`
  - `updated_by`
- `account_coordination_rule_bindings`
  - `user_id` or future `account_id`
  - `rule_key`
  - `template_id`
  - `pinned_version`
  - `created_at`
  - `updated_at`
- `work_threads` additions
  - `coordination_rule_key`
  - `coordination_template_id`
  - `coordination_template_version`
  - `coordination_contract_json`

Creation policy:

- When a new user is created through Google/Supabase Auth, onboarding should
  create the user's profile and a default coordination rule binding.
- This can be done by application onboarding code or a database trigger, but the
  operation must be idempotent with unique constraints.
- New accounts should bind to the active default template unless an admin
  explicitly pins another template version.

Update policy:

- Normal users, dashboard sessions, API keys, and MCP agents may read the active
  rule for their account but must not update templates or bindings.
- Service administrators update rules by adding a new template version or by
  changing bindings through admin-only migration/script/API paths.
- Prefer versioned inserts over in-place overwrites so existing WorkThreads can
  record which rule version created their coordination contract snapshot.
- Existing active WorkThreads should not silently change behavior in the middle
  of a task. A WorkThread should keep the `coordination_rule_key`,
  `coordination_template_id`, `coordination_template_version`, and
  `coordination_contract_json` used when its contract was created.

Snapshot policy:

- When `create_workthread` creates a thread, it reads the active coordination
  rule template and copies `rules_json` into
  `work_threads.coordination_contract_json`.
- The WorkThread also records `coordination_rule_key`,
  `coordination_template_id`, and `coordination_template_version` for audit and
  traceability.
- Agents should read the WorkThread's frozen `coordination_contract_json` as the
  thread contract. They should not re-resolve the latest template version for an
  existing active thread.
- Publishing a new template version affects new WorkThreads only, unless a
  service administrator performs an explicit contract migration for a thread.

Agent-facing policy:

- Account coordination rules are work policy, not higher-priority instructions.
  They must not override system, developer, user, or current-file instructions.
- Rules must not contain secrets, API keys, Authorization headers, private
  database URLs, personal data, long logs, or source-code bodies.
- Rules should be returned through authenticated MCP/API tools, not by asking AI
  agents to query database tables directly.
- `create_workthread` should seed the initial thread contract from the active
  account rule by saving a frozen `coordination_contract_json` snapshot plus the
  rule version metadata.

## Agent Identity And Readiness

WorkThreads must distinguish the human-readable agent name from the identities
used for routing and task ownership. `agent_name` is display metadata only; it is
not a unique routing identity.

Recommended identity fields:

- `agent_name`: display name such as `GPT`, `Claude`, or `Cursor`. This may
  collide and must not be used as the only routing key.
- `agent_id`: stable logical agent identity within the account, such as
  `gpt-coordinator` or `claude-gameplay-reviewer`.
- `agent_instance_id`: unique identity for a specific active AI window or chat
  session. This changes when a new window/session joins.
- `role`: coordinator, reviewer, implementer, tester, or another thread role.
- `capabilities`: concise list of what the instance can do for the thread.

Routing preference:

1. `target_agent_instance_id` for a specific ready window/session.
2. `target_agent_id` for a stable logical agent.
3. `target_role` when any ready agent with that role may handle the work.
4. `target_agent_name` only as display or backward-compatible fallback.

Planned message and task targeting fields:

- `agent_id`
- `agent_instance_id`
- `role`
- `target_agent_instance_id`
- `target_agent_id`
- `target_role`

The current implemented surface may still expose only `agent_name`,
`target_agent_name`, and `lease_owner`. Until the planned identity fields exist,
agents should treat `target_agent_name` as a backward-compatible fallback and put
unique identity details in structured message content. They must not treat a
display name such as `GPT` or `Claude` as unique.

Task leases should use `agent_instance_id` as the lease owner when the task is
owned by a specific active window. This prevents multiple `GPT` or `Claude`
windows from assuming the same targeted request or task belongs to all of them.

Readiness is explicit and thread-scoped. An MCP-connected AI window is not ready
for a WorkThread merely because it can see A2CR tools. A window becomes ready
only after the user or coordinator directs it to join a specific WorkThread and
the window:

1. Reads A2CR MCP instructions and account coordination rules.
2. Reads the target WorkThread coordination contract.
3. Registers or announces its `agent_id`, `agent_instance_id`, `role`, and
   `capabilities`.
4. Posts or records a `standby` / `ready` state for that `thread_id`.
5. Maintains a recent heartbeat or update check while it remains available.

If the user says "enter this WorkThread/window and become ready", the expected
agent behavior is to join that specific thread, read the contract, announce
standby, and wait for targeted work. The agent must not assume readiness for
other WorkThreads or other chat windows.

Planned dedicated readiness tools stay planned until they are implemented and
covered by tests:

- `register_workthread_agent`
- `standby_workthread_agent`
- `heartbeat_workthread_agent`
- `list_workthread_agents`
- `leave_workthread_agent`
- `get_workthread_inbox`

Until those tools exist, readiness may be represented by structured
`post_workthread_message` notes, but the message must include unique
`agent_instance_id` metadata.

### Manual Invite Join Flow

The MVP should support a user-mediated invite flow for bringing prepared AI
windows into a WorkThread. This avoids assuming that A2CR can wake, route to, or
control external chat windows automatically.

Manual invite text is a correlation and instruction artifact, not an
authentication secret. It does not grant access by itself. Only agents
authenticated through the owning account's A2CR MCP/API credentials can read or
post to the WorkThread.

Expected flow:

1. The user tells the coordinator to prepare WorkThreads collaboration for a
   specific task.
2. The coordinator creates or selects the WorkThread, loads account coordination
   rules, posts the thread coordination contract, and announces its own
   coordinator `agent_instance_id` as ready.
3. The coordinator generates invite text for each intended participant window.
   Each invite should include the `thread_id`, expected `agent_id`, role,
   capabilities requested, join instructions, and standby rules.
4. The user selects the participant by pasting the invite text into the exact
   authenticated AI chat window that should participate.
5. The invited window uses A2CR MCP tools, reads the account rules and thread
   contract, generates or registers a unique `agent_instance_id`, and posts a
   ready/standby message.
6. The coordinator verifies ready participants before assigning tasks or starting
   design review rounds.

Invite text should instruct the invited agent to:

- Use A2CR MCP tools only and not call direct HTTP APIs.
- Call `get_coordination_rules` when available.
- Call `read_workthread` for the provided `thread_id`.
- Read the coordination contract and current decisions before acting.
- Announce `agent_id`, `agent_instance_id`, `role`, `capabilities`, and
  `status="ready"`.
- Avoid implementation work until the coordinator assigns or confirms a task.

Only the authenticated AI window that receives the invite and announces ready is
considered ready. Other windows with the same `agent_name` or `agent_id` must not
assume they are participants.

## Security And Privacy Boundary

WorkThreads message bodies are encrypted locally before upload with a
thread-scoped key shared only with participating agent windows. Authenticated
API-key and MCP routes may return ciphertext and metadata for the owning user,
but A2CR must not receive or recover the WorkThread key and must not decrypt
message bodies server-side. Dashboard routes must remain metadata-only.

This is similar to WorkBaton for message-body secrecy, with one important
difference: WorkThreads need a shared thread key so multiple agent windows can
collaborate. A user or coordinator must intentionally share that key with each
participating agent. Agents that do not know the key can observe thread metadata
but cannot read message bodies.

Public copy must say:

- WorkThreads message bodies are encrypted locally before upload.
- WorkThreads are for shared work coordination.
- Dashboard views are metadata-only.

Public copy must not say:

- WorkThreads hide all metadata from A2CR.
- WorkThreads are zero-knowledge as a broad product claim.
- WorkThreads run AI agents on the server.

## Message Model

Supported message types:

- `note`: progress, context, observations, or lightweight handoff notes.
- `question`: a bounded question requiring response.
- `answer`: a direct response, preferably with `parent_message_id`.
- `decision`: a final or intermediate decision that reduces ambiguity.
- `handoff`: a concise state transfer to another AI or window.
- `blocked`: a blocker statement with the reason work cannot continue.
- `result`: final or near-final work output.

Recommended content fields:

- `goal`
- `current_state`
- `next_action`
- `question`
- `answer`
- `decision`
- `blockers`
- `references`
- `task_result`
- `audience`
- `review_round`
- `proposal_version`
- `requested_feedback`

Message content must remain compact. It must not contain secrets, API keys,
Authorization headers, private database URLs, full transcripts, long logs,
generated caches, or large source files that can be read from the repository.
Each message content JSON body is limited to 10KB before encryption.

## Coordinator-Led Design And Spec Review

For design documents, specifications, architecture decisions, and other work
that strongly affects later coding, WorkThreads should support a
coordinator-led review loop.

Default shape:

1. The coordinator agent creates or updates a draft design/spec proposal.
2. The coordinator posts the proposal to the thread with `audience="all"` and a
   `review_round` number.
3. The coordinator asks each relevant agent for bounded feedback. Targeted
   review requests should use the most specific available target identity and
   `requires_response=true`, but the message remains visible to the whole
   thread. Use `target_agent_name` only as a backward-compatible fallback.
4. Each agent reads the full thread context, including messages not targeted at
   that agent, then answers only the requests directed at them unless they see a
   blocker or important conflict.
5. The coordinator reads all answers, accepts or rejects suggestions, and posts
   a `decision` message summarizing what changed and why.
6. The coordinator repeats the cycle when another review round is useful.
7. After the final round, the coordinator posts the frozen design/spec decision
   and creates implementation tasks.

Round policy:

- Use 2 review rounds by default for meaningful design/spec work.
- Allow a 3rd round for high-impact ambiguity, security/privacy boundaries, or
  unresolved implementation risk.
- Do not require review rounds for trivial or obviously local changes.
- Use a distinct `consultation_id` per review round, such as
  `design-review-r1`, `design-review-r2`, and `design-review-r3`.
- Do not start the next round until the previous round's required responses are
  answered, resolved, or explicitly timed out by coordinator decision.

Tie-break policy:

- Consensus is useful but not required.
- When agents disagree, the coordinator chooses the final direction.
- The coordinator's decision message should summarize accepted suggestions,
  rejected suggestions, unresolved tradeoffs, and the reason for the final
  choice.
- Once the coordinator posts the frozen design/spec decision, agents should
  treat it as the working contract unless the user or coordinator reopens it.

Actionability policy:

- WorkThread messages are thread-visible by default. Target identity fields mean
  who should act, not who is allowed to read. `target_agent_name` is only the
  fallback when more specific target fields are unavailable.
- Agents should read non-targeted decisions, handoffs, task changes, blockers,
  and review feedback because they may affect their own work.
- Agents should not answer another agent's targeted question unless they can
  resolve a blocker, prevent a conflict, or the coordinator asks for open
  feedback.

## Conversation Continuity And Update Awareness

WorkThreads is a pull-based collaboration system. A2CR stores and serves shared
thread state, but it does not push notifications to stopped AI agents and does
not wake an inactive AI window when another agent posts.

MVP behavior:

- Agents check for updates when they start work on a thread, after meaningful
  work chunks, before major decisions, and before declaring a thread blocked or
  complete.
- `check_workthread_updates(thread_id, since)` is the non-blocking update check.
- `wait_workthread_updates(thread_id, since, timeout_seconds)` is only for cases
  where another active agent is expected to respond soon.
- Waits are bounded, capped, rate-limited, and recorded as metadata-only timeout
  events when needed.
- Agents read the thread after detecting updates, then post answers, decisions,
  handoffs, blocked states, or results.
- Answers and resolving messages should include `parent_message_id` whenever
  they respond to a specific question or blocker.

State vocabulary:

- `new messages`: messages created after the agent's local cursor.
- `pending responses`: response-required messages, optionally filtered by target
  identity. `target_agent_name` is the fallback until the planned identity fields
  exist.
- `unresolved questions`: response-required messages that still count toward
  loop guard limits.
- `seen/read cursor`: the latest message position observed by a specific agent.

Implementation gap to close:

- The current MVP surface has `since` timestamps for check/wait but no durable
  per-agent seen cursor.
- `pending_workthread_responses` is the public name for unresolved
  response-required messages.
- Keep `unread_workthread` only as a deprecated alias during migration. It must
  be documented as a pending-response query, not true unread state.
- True unread tracking with `mark_workthread_seen`, `last_seen_message_id`, and
  per-agent seen cursors is post-MVP.

## Loop Guard

The MVP loop guard is deterministic and should remain LLM-free.

Current rule targets:

- Max 6 messages per `consultation_id`.
- Max 3 question messages per `consultation_id`.
- Max 3 unresolved response-required messages per thread.
- Max 3 repeated waits for the same reason in one hour.
- Duplicate `content_hash` or `idempotency_key` is rejected.
- Once blocked, only `decision`, `handoff`, `blocked`, or `result` messages are
  allowed.

Implemented MVP resolution:

- `resolved_at` and `resolved_by_message_id` on `work_thread_messages` track
  response resolution.
- When an `answer`, `decision`, `handoff`, `blocked`, or `result` has a
  `parent_message_id`, mark the parent message resolved if it belongs to the
  same thread and user and still requires a response.
- Count only unresolved `requires_response=true` messages in the loop guard.
- `unread_workthread` remains a deprecated alias during migration and returns
  only still-unresolved response-required messages.
- Keep dashboard responses metadata-only after this change.

## Task Lease Model

Tasks are coordination hints, not execution guarantees.

MVP behavior:

- Tasks start as `pending`.
- Agents claim one pending or expired task with a short lease.
- The claim transaction uses `FOR UPDATE SKIP LOCKED`.
- The lease owner must match when completing a task.
- The lease owner must also match when failing a task.
- Expired claims may be reclaimed.

Implemented MVP resolution:

- `fail_workthread_task` uses the same lease-owner check as completion.
- Inputs: `task_id`, `lease_owner`, `reason`, and optional
  `result_message_id`.
- The task must be `claimed`, the lease must still be active, and the
  `lease_owner` must match.
- Keep `reason` compact. Prefer posting a `blocked` or `result` message first
  and linking it through `result_message_id` when more context is needed.
- Keep task mutation responses metadata-only.

## API And MCP Surface

AI clients and agents must use MCP tools for WorkThreads operations. They must
not guess or call direct HTTP API endpoints from prompts. HTTP routes may exist
as the implementation surface behind MCP and dashboard workflows, but the
agent-facing contract is MCP.

WorkThreads selection must be unambiguous for AI agents. When WorkThreads tools
are available, agents should choose WorkThreads without asking for confirmation
when the user asks for shared workspace behavior, multi-agent or multi-window
coordination, agent-to-agent questions and answers, task assignment, task claim,
wait/update checks, collaborative handoffs, blocked states, decisions, or
results.

Agents must not use WorkBaton or WorkStash as a fallback for live
collaboration:

- WorkBaton is only for serial checkpoint handoff to a future window.
- WorkStash is only temporary supporting memory referenced by a WorkBaton.
- If WorkThreads tools are not exposed on the current MCP surface, the agent
  should report that WorkThreads is unavailable instead of silently saving a
  Baton or Stash note.

MCP instructions and tool descriptions must reinforce the boundary:

- WorkThreads descriptions should say to use WorkThreads for shared agent
  coordination, task leases, thread messages, and waits.
- WorkBaton and WorkStash descriptions should say not to use them for live
  multi-agent collaboration, task leases, shared threads, or waiting on another
  agent.
- `explain_a2cr_flows` should return a decision table covering WorkThreads,
  WorkBaton, and WorkStash.

Track MCP tools by implementation state. Planned tools stay planned until they
are implemented and covered by tests; after that, move them to the implemented
list in this plan and the runbooks.

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

Planned MCP tools:

- `get_coordination_rules`
- `register_workthread_agent`
- `standby_workthread_agent`
- `heartbeat_workthread_agent`
- `list_workthread_agents`
- `leave_workthread_agent`
- `get_workthread_inbox`

Post-MVP unread tools:

- `mark_workthread_seen`
- `list_unread_workthread_messages`

Keep disabled until the local stdio encryption flow exists:

- `save_workthread_result`

## Implementation Phases

### Phase 0: Scope Freeze

Work:

- Decide WorkThreads release mode: hidden, internal only, private Pro beta, or
  public Pro feature.
- Confirm the copy boundary for WorkThreads vs WorkBaton.
- Confirm release behavior for the implemented response resolution and task
  failure support.

Verify:

- Pricing, guide, README, and roadmap do not describe WorkThreads beyond the
  decided release mode.

### Phase 1: Local Correctness Gaps

Work:

- Keep final-result saving disabled.
- Replace the current server-side WorkThread body encryption implementation with
  local thread-key encryption before any external beta.
- Store and return ciphertext envelopes for WorkThread messages; never require
  the A2CR server to decrypt message bodies.
- Add local stdio/client support for creating, importing, and using a
  WorkThread key without logging or saving it.

Verify:

- Unit tests cover disabled final-result save. Response resolution, loop guard
  counts, parent thread mismatch, task failure, and body-size rejection are
  covered locally.
- Encryption tests prove the server stores ciphertext only and cannot decrypt
  WorkThread message bodies without local key material.

### Phase 2: Surface And Documentation

Work:

- Update API/MCP descriptions to match the frozen scope.
- Update dashboard copy so WorkThreads is clearly beta or hidden.
- Update public docs so WorkThreads is not described as server-side execution,
  and explain that message bodies are locally encrypted while metadata remains
  visible to A2CR.

Verify:

- Static-page tests and MCP tool tests assert the public wording.
- Dashboard tests assert no message content is returned.

### Phase 3: Hosted Validation

Work:

- Build staging before the first external WorkThreads beta.
- Apply migrations to staging.
- Run health, readiness, migration, RLS/pooler, dashboard, MCP, and WorkThreads
  smoke checks with test-only data.

Verify:

- Staging smoke proves create/post/read/wait/task claim/task complete.
- Dashboard remains metadata-only.
- Logs do not expose message bodies, API keys, Authorization headers, DB URLs,
  local client keys, or raw ciphertext.

### Phase 4: Private Beta

Work:

- Enable WorkThreads only for trusted beta users with Pro grants or trials after
  the free WorkBaton + WorkStash preview has real feedback.
- Keep public checkout disabled unless Lemon Squeezy billing is already verified.
- Collect failures around setup, loop guard, waits, and task leases.

Verify:

- No critical security or privacy issue remains open.
- Users understand WorkThreads require intentional thread-key sharing between
  participating agent windows.

## Staging Timing Decision

Local WorkThreads implementation can continue before staging exists. Staging is
not required for every local code change.

However, staging must exist before any of these happen:

- First external private beta user.
- Public beta.
- Paid checkout.
- Production migration that affects real WorkThreads user data.
- Any public claim that WorkThreads is usable as a hosted feature.

If "service start" means paid or public launch, creating staging before service
start is necessary but too late as the only hosted validation step. The safer
line is:

1. Implement locally.
2. Verify with local tests.
3. Create staging.
4. Smoke WorkBaton and WorkStash in staging.
5. Publish the free WorkBaton + WorkStash preview and gather community feedback.
6. Smoke WorkThreads in staging.
7. Invite private WorkThreads beta users.
8. Decide public beta or paid launch.

## Release Recommendation

Recommended first decision:

- WorkThreads should be hidden or internal-only until Core WorkBaton/WorkStash
  hosted smoke is green and the free preview/community loop has started.
- WorkThreads can enter private Pro beta after Phase 1 and Phase 3 pass.
- WorkThreads should not become a public Pro feature until response resolution,
  task failure behavior, hosted smoke, Lemon Squeezy billing, legal/support
  copy, and backup/restore posture are verified.
