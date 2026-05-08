# A2CR WorkThreads MVP Specification And Implementation Plan

Last updated: 2026-05-08

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
- WorkBaton body secrecy is stronger than WorkThreads body secrecy in the
  current design.
- The first external release should prefer a hidden or private Pro beta
  WorkThreads mode over a public Pro feature.

## Success Criteria

WorkThreads MVP is ready for private beta only when:

- Pro-only access is enforced across HTTP API, MCP, and dashboard paths.
- API-key and MCP routes can create, post, read, wait, and coordinate tasks.
- Dashboard routes return metadata only and never include message content.
- WorkThread message bodies are encrypted at rest, but are not marketed as
  client-encrypted or zero-knowledge.
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
- Read messages through authenticated API/MCP routes.
- Show dashboard metadata only.
- Poll or wait for updates.
- Create, claim, and complete lightweight tasks with leases.
- Detect duplicate messages with `idempotency_key` and content hash.
- Block runaway consultations with deterministic loop guard rules.

Not included in the MVP:

- Server-side LLM execution.
- Autonomous agent orchestration.
- Cross-account sharing.
- Public dashboard display of message bodies.
- File attachments.
- URL fetching, HTML rendering, browser previews, or content scraping.
- Long-term document storage.
- Final-result WorkBaton saving from remote HTTP/MCP.
- Client-encrypted WorkThreads parity with WorkBaton.
- Zero-knowledge claims.

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

## Security And Privacy Boundary

WorkThreads message bodies are encrypted at rest with the A2CR service key in
the current design. Authenticated API-key and MCP routes may decrypt and return
message content for the owning user. Dashboard routes must remain metadata-only.

This is different from WorkBaton:

- WorkBaton is client-encrypted before upload.
- A2CR cannot decrypt WorkBaton bodies without the user's local client key.
- WorkThreads are not covered by the WorkBaton client-encryption guarantee.

Public copy must say:

- WorkThreads are encrypted at rest.
- WorkThreads are for shared work coordination.
- Dashboard views are metadata-only.

Public copy must not say:

- WorkThreads are zero-knowledge.
- WorkThreads have the same secrecy boundary as WorkBaton.
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

Message content must remain compact. It must not contain secrets, API keys,
Authorization headers, private database URLs, full transcripts, long logs,
generated caches, or large source files that can be read from the repository.

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

Implementation gap to close:

- The current service treats all `requires_response=true` messages as
  unresolved. Before beta, either add explicit response resolution or rename the
  behavior so the product does not promise true unread/resolved semantics.

Recommended MVP resolution:

- Add `resolved_at` and `resolved_by_message_id` to `work_thread_messages`.
- When an `answer`, `decision`, `handoff`, `blocked`, or `result` has a
  `parent_message_id`, mark the parent message resolved if it belongs to the
  same thread and user.
- Count only unresolved `requires_response=true` messages in the loop guard.
- Keep dashboard responses metadata-only after this change.

## Task Lease Model

Tasks are coordination hints, not execution guarantees.

MVP behavior:

- Tasks start as `pending`.
- Agents claim one pending or expired task with a short lease.
- The claim transaction uses `FOR UPDATE SKIP LOCKED`.
- The lease owner must match when completing a task.
- Expired claims may be reclaimed.

Implementation gap to close:

- The database allows `failed` tasks, but the public API currently has no
  explicit fail route. Before beta, either add a small fail endpoint/tool or do
  not expose `failed` as a user-facing state.

Recommended MVP resolution:

- Add `fail_workthread_task` with the same lease-owner check as completion.
- Allow an optional `result_message_id` for failure context.
- Keep task mutation responses metadata-only.

## API And MCP Surface

AI clients and agents must use MCP tools for WorkThreads operations. They must
not guess or call direct HTTP API endpoints from prompts. HTTP routes may exist
as the implementation surface behind MCP and dashboard workflows, but the
agent-facing contract is MCP.

Keep these as the MVP surface:

- `create_workthread`
- `list_workthreads`
- `post_workthread_message`
- `read_workthread`
- `unread_workthread` or renamed pending-response equivalent
- `check_workthread_updates`
- `wait_workthread_updates`
- `create_workthread_task`
- `claim_workthread_task`
- `complete_workthread_task`
- optional `fail_workthread_task`

Keep disabled until the local stdio encryption flow exists:

- `save_workthread_result`

## Implementation Phases

### Phase 0: Scope Freeze

Work:

- Decide WorkThreads release mode: hidden, internal only, private Pro beta, or
  public Pro feature.
- Confirm the copy boundary for WorkThreads vs WorkBaton.
- Confirm whether the first beta needs task failure and response resolution.

Verify:

- Pricing, guide, README, and roadmap do not describe WorkThreads beyond the
  decided release mode.

### Phase 1: Local Correctness Gaps

Work:

- Add message response resolution or rename unresolved-response semantics.
- Add task failure support or remove failed state from user-facing promises.
- Add compact message body-size validation.
- Validate that `parent_message_id` belongs to the same thread and user before
  using it for resolution.
- Keep final-result saving disabled.

Verify:

- Unit tests cover response resolution, loop guard counts, task failure, parent
  thread mismatch, body-size rejection, and disabled final-result save.

### Phase 2: Surface And Documentation

Work:

- Update API/MCP descriptions to match the frozen scope.
- Update dashboard copy so WorkThreads is clearly beta or hidden.
- Update public docs so WorkThreads is not described as server-side execution
  or WorkBaton-equivalent secrecy.

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

- Enable WorkThreads only for trusted beta users with Pro grants or trials.
- Keep public checkout disabled unless billing is already verified.
- Collect failures around setup, loop guard, waits, and task leases.

Verify:

- No critical security or privacy issue remains open.
- Users understand WorkThreads is not WorkBaton-equivalent client encryption.

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
4. Smoke WorkBaton and WorkThreads in staging.
5. Invite private beta users.
6. Decide public beta or paid launch.

## Release Recommendation

Recommended first decision:

- WorkThreads should be hidden or internal-only until Core WorkBaton hosted
  smoke is green.
- WorkThreads can enter private Pro beta after Phase 1 and Phase 3 pass.
- WorkThreads should not become a public Pro feature until response resolution,
  task failure behavior, hosted smoke, legal/support copy, and backup/restore
  posture are verified.
