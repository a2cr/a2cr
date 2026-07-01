# A2CR Local Mode Specification

Status: superseded planning draft

This draft is retained for design history. As of 2026-06-24, the active public
product direction is local-only A2CR, documented in
`docs/local-only-saas-retirement-plan.md`. Cloud sync, hosted backup, and SaaS
upgrade paths in this older draft are no longer release targets for the public
distribution.

This document defines the planned local-first A2CR experience. The goal is to
make A2CR useful before a user creates an account, copies an API key, or sends
handoff content to a hosted service.

The core product promise is:

```text
Install in one step. Connect one AI client. Save and resume immediately.
```

Cloud sync, team sharing, hosted backup, and SaaS upgrade paths are out of
scope for the active public distribution.

## Goals

- Let a new user save and resume WorkBaton checkpoints without an A2CR account.
- Keep MCP tool names stable across local clients.
- Make setup feel automatic for Codex, Claude Code, Cursor, and generic MCP
  clients.
- Let multiple AI clients and agents share one project/workspace handoff memory.
- Store WorkBaton, WorkStash, and WorkThreads in one searchable local workspace.
- Provide a local browser UI for search, inspection, cleanup, and handoff
  review.
- Preserve the A2CR identity as a handoff system, not a generic transcript
  database.
- Preserve a handoff-first product boundary: local storage may contain rich
  searchable history, but resume should still happen through WorkBaton.
- Keep the public distribution local-only.

## Non-Goals

- Do not require a hosted service for first use.
- Do not require encryption-at-rest for local-only storage by default.
- Do not require automatic expiration for local-only storage by default.
- Do not turn WorkBaton into a full raw chat transcript store.
- Do not become a generic `remember`, `recall`, and `answer` memory product.
- Do not become an LLM proxy, context compression layer, or token optimization
  middleware.
- Do not silently rewrite `AGENTS.md`, `CLAUDE.md`, `A2CR.md`, or similar
  project memory files.
- Do not silently upload local content to A2CR Cloud.
- Do not require users to learn storage internals before their first save.

## Product Shape

A2CR's public product shape is local-only.

| Mode | First-use requirement | Storage | Best for |
|---|---|---|---|
| A2CR Local | No account or API key | Local SQLite | Single-machine coding work, multi-agent project handoffs, local search |

Cloud sync, hosted backup, and SaaS relay flows are outside the public release
and should not appear in first-run setup, MCP Registry metadata, or Anthropic
Directory reviewer instructions.

## Target Public OSS Model

The final public product should make A2CR Local the main public distribution and
publish that local workspace implementation as open source.

Target model:

| Layer | Target posture |
|---|---|
| A2CR Local Workspace | Main public OSS product. Includes local WorkBaton, WorkStash, WorkThreads, search, CLI, MCP server, and browser UI. |
| WorkBaton Format | Public specification and conformance surface. |
| SaaS / hosted relay | Retired from the public install story and kept outside the OSS repository. |

This transition should happen only after the local implementation is cleanly
separated from hosted-only code and private production surfaces. Until then,
current README and license files must continue to describe the actual published
license boundary accurately.

OSS readiness requirements:

- local mode code lives under `a2cr_mcp/local_workspace/`
- no private production code, secrets, deployment config, billing code, admin
  tooling, or internal runbooks are included
- local mode works without an A2CR account or API key
- the public quickstart is local-first
- the chosen license is OSI-approved and clearly documented before announcing
  the local implementation as OSS
- public setup does not require, promote, or silently configure cloud sync

## Local Workspace Object Model

A2CR Local should be a local workspace that includes three related but separate
objects:

```text
A2CR Local Workspace
  -> WorkBaton
  -> WorkStash
  -> WorkThreads
```

These objects should share project identity, actor provenance, local search,
browser UI, import/export, and backup paths. They should not collapse into one
generic memory table.

Implementation code for this local workspace should live in a dedicated source
folder, `a2cr_mcp/local_workspace/`, so local storage, search, WorkThreads, and
Web UI code do not mix with the existing hosted wrapper implementation.

| Object | Primary job | Typical content | Should not become |
|---|---|---|---|
| WorkBaton | The compact resume artifact for a future AI window. | Goal, current state, next action, decisions, blockers, validation, references, stale/supersession metadata. | A transcript, long log, file store, or generic memory answer. |
| WorkStash | Supporting notes that make a Baton stronger without bloating it. | Causal summaries, reproduction notes, API observations, validation details, research notes, referenced evidence. | A permanent knowledge base, raw file dump, or secret store. |
| WorkThreads | Active or archived coordination history across agents. | Thread title, participants, messages, task state, handoff discussions, unresolved coordination points. | The serial resume artifact or replacement for WorkBaton. |

The default local workflow should be:

```text
WorkThreads capture coordination while work is active.
WorkStash stores supporting evidence and longer explanations.
WorkBaton records the compact state needed to resume.
```

This means A2CR Local can be broad at rest while staying narrow at resume time.
The local database may store rich searchable context, but MCP resume responses
should guide the next AI window through a WorkBaton and only load WorkStash or
WorkThreads records when they are referenced and needed.

Object boundaries:

- WorkBaton may reference WorkStash and WorkThreads.
- WorkStash may be referenced by one or more WorkBatons or WorkThreads.
- WorkThreads may produce or reference WorkBatons when a thread reaches a
  handoff point.
- Search may cross all three objects, but search results should return handles
  and snippets before full bodies.
- Deleting or archiving one object should not silently delete referenced objects
  unless the user confirms a cleanup action.

## Handoff-First Boundary

A2CR Local may store more than a Baton, but it should always resume through a
Baton.

This boundary keeps A2CR distinct from generic memory and compression tools.
Local search, WorkStash, WorkThreads, event history, and the browser UI can help
an agent or user find context, but the stable serial resume artifact should
remain a WorkBaton with goal, current state, decisions, validation, blockers,
references, and next action.

The preferred flow is:

```text
local history/search -> selected evidence -> WorkBaton -> resumed AI window
```

A2CR should not advertise itself as a general purpose memory QA engine. It may
answer narrow operational questions about saved handoffs, but its primary job is
to preserve the state needed to continue work.

Similarly, A2CR should not route or compress provider traffic. It may coexist
with token compression tools, proxies, native model compaction, or agent memory
products, but local A2CR is responsible for handoff structure, not token
optimization.

## Multi-Agent Memory Model

A2CR Local should be a shared project/workspace memory for multiple AI agents,
not a private memory bound to one agent identity.

The primary namespace should be:

```text
workspace/project -> WorkBaton, WorkStash, WorkThreads, events
```

Agent identity is important as provenance, but it should not be the top-level
owner of the memory. Codex, Claude Code, Cursor, and other MCP clients should be
able to save into and resume from the same local workspace, subject to the same
safety rules.

Required provenance for saved records:

| Field | Purpose |
|---|---|
| `client_name` | Codex, Claude Code, Cursor, or another MCP client when known. |
| `agent_label` | Optional user or client-provided agent label. |
| `model_source` | Optional model family or provider label when available. |
| `session_id` | Optional local session/window identifier. |
| `created_by` | Stable local actor identifier when available. |
| `created_at` | Save timestamp. |
| `updated_at` | Last update timestamp. |

The UI should let users filter by client or agent, but the default view should
show the shared project state. This avoids fragmenting memory into one silo per
agent.

When multiple agents write to the same workspace, A2CR should preserve history
instead of silently overwriting meaning:

- new WorkBaton saves may supersede earlier Slots explicitly
- stale or contaminated Slots should be marked, not deleted automatically
- conflicting decisions should be visible in search and the UI
- WorkThreads should show participants and message provenance
- resume should prefer the newest non-stale Baton unless the user or agent asks
  for a specific Slot

The product distinction is:

```text
Agent memory remembers what one agent learned.
A2CR workspace memory preserves shared work state across agents.
```

## Installation UX

The simple path should be:

```bash
python -m pip install --upgrade a2cr-mcp
a2cr init codex --local
```

The second command must:

1. create the local A2CR data directory if needed
2. create or migrate the local SQLite database
3. detect the Codex MCP configuration path
4. write or update one MCP server named `a2cr-local`
5. preserve a timestamped backup before editing an existing config file
6. run a connection check
7. print the exact command needed to start using A2CR

The equivalent target commands should be:

```bash
a2cr init claude-code --local
a2cr init cursor --local
a2cr init generic --local --print-config
```

Every init command should support:

| Flag | Purpose |
|---|---|
| `--local` | Configure local storage. This should be the recommended default. |
| `--cloud` | Discontinued in the public local-only release. The CLI should return a clear error instead of writing cloud config. |
| `--dry-run` | Show the planned changes without writing files. |
| `--print-config` | Print JSON/TOML config for manual setup. |
| `--force` | Recreate the A2CR MCP entry after showing what will change. |
| `--db PATH` | Use a custom local SQLite database path. |

## CLI Commands

A new user-facing CLI entrypoint should be added:

```text
a2cr
```

The existing MCP server command should remain:

```text
a2cr-mcp
```

New public setup should use the dedicated local MCP command so there is no
ambiguous SaaS/local routing:

```text
a2cr-local-mcp
```

Codex local TOML should be:

```toml
[mcp_servers."a2cr-local"]
command = "a2cr-local-mcp"
args = []

[mcp_servers."a2cr-local".env]
A2CR_LOCAL_DB = "/path/to/a2cr.db"
```

`a2cr-mcp` remains a compatibility command that uses local storage. The
recommended user-facing MCP name is `a2cr-local`.

Required CLI commands:

| Command | Purpose |
|---|---|
| `a2cr init <client> --local` | Configure an AI client with an `a2cr-local` MCP server. |
| `a2cr init <client> --cloud` | Discontinued. Return a clear error explaining that public A2CR is local-only. |
| `a2cr doctor` | Verify the CLI, MCP command, database, and client config. |
| `a2cr status` | Show current mode, database path, project count, Slot count, and last save. |
| `a2cr ui` | Start the local browser UI on `127.0.0.1`. |
| `a2cr search <query>` | Search local WorkBaton, WorkStash, WorkThreads, and event metadata. |
| `a2cr export` | Export selected local handoff data. |
| `a2cr import` | Import local handoff data from an A2CR export. |

Nice-to-have commands:

| Command | Purpose |
|---|---|
| `a2cr prune` | Delete superseded or user-selected local entries. |
| `a2cr backup` | Create a local database backup. |
| `a2cr open` | Open the local data directory. |
| `a2cr config get/set` | Inspect or update local A2CR config. |

## Default Local Paths

Local mode should not create files inside a repository by default. It should use
per-user app data and identify projects by canonical root path plus git remote
metadata when available.

Default data paths:

| Platform | Default database path |
|---|---|
| Windows | `%LOCALAPPDATA%\A2CR\a2cr.db` |
| macOS | `~/Library/Application Support/A2CR/a2cr.db` |
| Linux | `$XDG_DATA_HOME/a2cr/a2cr.db` or `~/.local/share/a2cr/a2cr.db` |

Default config paths:

| Platform | Default config path |
|---|---|
| Windows | `%APPDATA%\A2CR\config.toml` |
| macOS | `~/Library/Application Support/A2CR/config.toml` |
| Linux | `$XDG_CONFIG_HOME/a2cr/config.toml` or `~/.config/a2cr/config.toml` |

Project-local storage may be offered later:

```bash
a2cr init codex --local --project-local
```

That mode may create `.a2cr/a2cr.db` in the current project, but it must add
`.a2cr/` to `.gitignore` or ask before doing so.

## Configuration Model

The local MCP server should support these environment variables:

| Variable | Purpose |
|---|---|
| `A2CR_MODE` | Optional compatibility variable. Public release resolves to local mode. |
| `A2CR_LOCAL_DB` | Optional exact SQLite database path. |
| `A2CR_CONFIG_DIR` | Optional config directory override. |
| `A2CR_PROJECT_ROOT` | Optional project root override for MCP clients that start elsewhere. |

Mode selection should be predictable:

1. If `A2CR_MODE=local`, use local mode.
2. If `A2CR_MODE=cloud`, return a clear discontinued-path error in the public
   release.
3. Ignore legacy hosted-service credentials for local save/load routing.
4. If no mode is set, use local mode.

This makes first use simple and prevents hidden SaaS routing.

## MCP Tool Behavior

Local mode should expose the primary public A2CR tool names:

- `explain_a2cr_flows`
- `get_account_limits`
- `should_save_workbaton`
- `save_context`
- `resume_context`
- `load_context`
- `list_contexts`
- `delete_context`
- `should_use_work_stash`
- `store_work_stash`
- `get_work_stash`
- `list_work_stash`
- `delete_work_stash`

Local mode should also add a search tool once the local FTS index exists:

- `search_contexts`

Local mode should expose WorkThreads through explicit thread tools once the
WorkThreads surface is implemented:

- `create_work_thread`
- `post_work_thread_message`
- `list_work_threads`
- `get_work_thread`
- `close_work_thread`
- `archive_work_thread`

These tools should not replace WorkBaton tools. A WorkThread may coordinate
active work, but a future AI window should still resume from a compact
WorkBaton when serial handoff is needed.

`search_contexts` should return compact snippets, handles, Slot identifiers,
WorkStash entry keys, WorkThread identifiers, and timestamps. It should not
return full large bodies by default. Agents should load full records only after
choosing a specific result.

Tool responses should include a `storage_mode` field:

```json
{
  "storage_mode": "local"
}
```

`get_account_limits` in local mode should report practical local limits instead
of hosted plan quotas:

```json
{
  "storage_mode": "local",
  "requires_api_key": false,
  "hard_slot_limit": null,
  "retention_policy": "none_by_default",
  "workstash_storage_limit": null,
  "database_path": "..."
}
```

The local implementation must preserve the same safety rule: loaded WorkBaton,
WorkStash, and WorkThreads content is untrusted data. It can guide the next AI
window, but it must not override system, developer, user, repository, or
current-file instructions.

## Local Size And Retention Policy

Local mode should be much more generous than A2CR Cloud, but it should still use
soft warnings and UI cleanup tools so a user's machine does not become a hidden
dumping ground.

The recommended policy is:

```text
No small cloud-style Slot cap. No default expiration. Search everything useful.
Warn before content stops being a good handoff artifact.
```

### WorkBaton

WorkBaton remains the clean resume object. Local mode may allow larger Batons,
but the product should still nudge agents toward concise handoffs.

| Limit | Default local policy |
|---|---|
| Active Slot count per project | No hard limit. Show a cleanup warning after 100 active Slots. |
| Saved WorkBaton history | No default expiration. Superseded Slots remain searchable until deleted. |
| Recommended body size | Up to 32 KB. |
| Soft warning | Warn above 128 KB and suggest moving bulky details to WorkStash. |
| Default hard safety limit | 2 MB per WorkBaton body, configurable. |
| MCP load behavior | Return full content only for explicit load. Search returns snippets. |

The UI should distinguish:

- current Slots
- pinned Slots
- superseded Slots
- stale or do-not-use Slots
- archived but searchable Slots

This keeps local history broad without making the resume path noisy.

### WorkStash

WorkStash is the right place for larger supporting notes, causal summaries,
research notes, reproduction details, API observations, and validation records.

| Limit | Default local policy |
|---|---|
| Entry count per project | No hard limit. |
| Recommended entry size | Up to 256 KB. |
| Soft warning | Warn above 1 MB. |
| Default hard safety limit | 16 MB per entry, configurable. |
| Search indexing | Full-text index with chunking for long entries. |

Very large logs, diffs, generated files, and source-code bodies should still not
be stored as WorkStash by default. If a user explicitly imports local logs for
search, those should use a separate local-only evidence/log table rather than
pretending to be WorkBaton or WorkStash.

### WorkThreads

WorkThreads are planned for active cross-agent coordination. Local mode should
support generous searchable thread history because the data is on the user's
machine.

| Limit | Default local policy |
|---|---|
| Open WorkThreads per project | No hard limit. Show cleanup warning after 100 open threads. |
| Thread message count | No hard limit. |
| Recommended message size | Up to 64 KB. |
| Soft warning | Warn above 256 KB and suggest WorkStash or local evidence import. |
| Default hard safety limit | 4 MB per message, configurable. |
| Closed thread retention | No default expiration. Closed threads stay searchable. |

The browser UI should make it easy to close, archive, search, and reopen
WorkThreads. MCP responses should summarize long threads and return message
handles rather than dumping entire thread histories into an AI context window.

### Database-Level Limits

Local mode should not set a small total database quota.

| Limit | Default local policy |
|---|---|
| Total database size | No hard cap. |
| Cleanup warning | Warn around 1 GB and offer prune/export/backup tools. |
| Search index size | No separate hard cap. Rebuildable from source tables. |
| Retention | Keep indefinitely by default. |

The UI should show database size, search index size, largest projects, largest
entries, and last backup time.

## Local Storage

Local mode should use SQLite with WAL enabled.

Required tables:

| Table | Purpose |
|---|---|
| `projects` | Known project roots, git remotes, display names, and last activity. |
| `actors` | Local client, agent, model, and session provenance records. |
| `workbatons` | Saved WorkBaton content, Slot metadata, supersession metadata, and timestamps. |
| `workstash_entries` | Supporting notes referenced by WorkBaton. |
| `workthreads` | Local WorkThread metadata, state, participants, and project mapping. |
| `workthread_messages` | Searchable local WorkThread message history. |
| `events` | Compact local event history such as save, load, resume, delete, import, export, and sync. |
| `settings` | Database-level settings and schema version. |

Recommended FTS5 tables:

| FTS table | Indexed content |
|---|---|
| `workbatons_fts` | goal, current_state, next_action, decisions, blockers, validation, references, client and agent labels |
| `workstash_fts` | entry_key, value, tags, client and agent labels |
| `workthread_messages_fts` | thread title, message body, participant labels, references |
| `events_fts` | event summaries and safe metadata |

Long bodies should be indexed in chunks so search can return precise snippets
without loading multi-megabyte records into an AI response.

Raw full chat transcripts should not be stored as a default data type. If a
future feature imports external conversation logs for search, that feature must
be explicit, local-only by default, and clearly separate from WorkBaton,
WorkStash, and WorkThreads.

## Browser UI

`a2cr ui` should start a local web UI and open the browser.

Default behavior:

- bind to `127.0.0.1`
- choose an available port automatically
- use a random local session token in the URL
- print a copy-pasteable full URL for users whose browser does not open
  automatically
- never expose the UI to the LAN by default
- never upload content in the public local-only release

Required views:

| View | Purpose |
|---|---|
| Dashboard | Recent projects, recent saves, current mode, database path, health state. |
| Project | WorkBaton Slots, WorkStash entries, and WorkThreads for one project. |
| Agents | Client and agent provenance, recent activity, and workspace participants. |
| Search | Full-text search across local WorkBaton, WorkStash, WorkThreads, and safe event metadata. |
| WorkBaton Detail | Full saved handoff content, human-readable view, JSON view, references, validation, supersession state. |
| WorkStash Detail | Full saved entry value, tags, referenced-by list, safe delete action. |
| WorkThread Detail | Agent-to-agent conversation messages, participants, message provenance, references, thread state, and safe archive/close actions. |
| Timeline | Save/load/resume/delete/import/export events for a project. |
| Cleanup | Superseded Slots, stale entries, and manual deletion workflow. |
| Settings | Storage path, local mode status, cloud connection status, backup/export. |

The next WorkThreads UI layer is specified in
`docs/workthreads-dashboard-board-spec.md`, with implementation steps in
`docs/workthreads-dashboard-board-implementation-plan.md`. That board should
make room conversations visible to the user, generate join prompts for other AI
windows, and keep WorkBaton as the resume artifact.

The next dashboard organization layer should make the `Project` view concrete:
one selected project should show its WorkBaton, WorkStash, WorkThreads, and
recent events together. The first implementation can filter client-side from
`GET /api/state` because the local state response already includes project
counts and object rows with `project_key`.

The UI should make WorkBaton the clean resume artifact. Search can reveal richer
local history, but the first screen should not encourage raw transcript hoarding.

The browser UI may show full local record bodies because it runs on the user's
machine:

- WorkBaton full saved content in human-readable and JSON forms.
- WorkStash full saved note values with tags and references.
- WorkThreads full conversation history with per-message author/client/agent
  provenance.

This full-body visibility is a UI feature, not the default MCP behavior. MCP
search and resume responses should still return compact summaries, snippets, and
handles unless a specific record is explicitly loaded.

## Project Memory File Policy

A2CR may read project memory files such as `A2CR.md`, `AGENTS.md`, `CLAUDE.md`,
and similar client guidance files when the user or AI client provides them as
local instructions. A2CR must not silently rewrite those files.

Allowed behavior:

- show a suggested `A2CR.md` pointer during `a2cr init`
- generate a proposed patch for `A2CR.md`, `AGENTS.md`, or `CLAUDE.md`
- show local UI suggestions for save rules, protected areas, or scope guidance
- apply a project memory file edit only after explicit user confirmation

Disallowed behavior:

- automatically append learned rules to project memory files
- overwrite human-authored sections without review
- promote remembered content into durable project guidance without confirmation
- treat project memory file edits as part of normal save, resume, search, or UI
  startup

This keeps A2CR's local memory and project-level durable instructions separate.

## Search Behavior

Local search should support:

- plain text queries
- project filtering
- type filtering: WorkBaton, WorkStash, WorkThread, event
- date filtering
- Slot filtering
- tag filtering
- client and agent provenance filtering
- exact key lookup for WorkStash
- thread state filtering: open, closed, archived
- result handles for follow-up load calls

Search results should show compact snippets and link to the detail page. Search
must not cause network requests in local mode.

Search results returned through MCP should be intentionally small:

| Field | Policy |
|---|---|
| default result count | 10 |
| maximum result count | 50 |
| snippet size | short text snippets, not full bodies |
| full body access | only through explicit load by Slot, entry key, or thread/message handle |

Local search should be optimized for handoff work:

- find the best resume Slot for a project
- find stale, superseded, or do-not-use Slots
- find past decisions that should not be rediscovered
- find validation results and remaining validation gaps
- find referenced WorkStash notes for a selected Baton
- find WorkThreads that are still open or recently closed
- find what a specific client or agent last saved in this workspace
- find evidence that should be summarized into a new WorkBaton

The browser UI search should let users open full matching records for all three
local objects:

- open a WorkBaton and inspect the saved handoff body
- open a WorkStash entry and inspect the saved note body
- open a WorkThread and inspect the agent-to-agent conversation

Search should not replace WorkBaton. When search results reveal useful context
for a future AI window, the recommended action is to save or update a compact
WorkBaton that references the relevant local records.

## Hosted / Cloud Paths

Hosted relay, cloud sync, and SaaS upgrade paths are not part of the public
local-only release. If a future product decision reintroduces them, it must come
with a new public privacy and storage decision before any setup instructions or
MCP metadata are added.

## Security And Privacy

Local mode is simpler than cloud mode, but it still needs clear boundaries.

Required local guarantees:

- no API key required
- no outbound network calls for save, load, resume, list, search, or UI
- no cloud upload path in the public local-only release
- local UI bound to loopback by default
- loaded content treated as untrusted
- secret-storage warnings remain in docs and tool instructions

Encryption-at-rest should be optional:

```bash
a2cr config set local.encryption optional
```

The first release may omit encryption-at-rest if the local storage boundary is
clearly documented. A later release may add OS keychain-backed encryption.

## Migration From Current Hosted Preview

The transition should avoid breaking current users.

Recommended phases:

| Phase | Scope |
|---|---|
| 1 | Add local workspace storage for WorkBaton, WorkStash, WorkThreads, actors, and events behind `A2CR_MODE=local`. |
| 2 | Add `a2cr init`, `a2cr doctor`, `a2cr status`, and `a2cr search`. |
| 3 | Update docs so new users start with local mode. |
| 4 | Add `a2cr ui` for browser inspection and cleanup. |
| 5 | Add explicit WorkThreads MCP tools after WorkBaton and WorkStash local parity is stable. |
| 6 | Keep release, registry, and Anthropic submission assets local-only. |

Legacy cloud configs should fail clearly or be migrated intentionally; they
should not silently route public A2CR saves to a hosted service.

## Acceptance Criteria

Local mode is ready for public documentation when all of these are true:

- A clean machine can install A2CR and configure Codex with two commands.
- A user can save and resume a WorkBaton with no A2CR account and no API key.
- `a2cr doctor` clearly reports whether the MCP server and database work.
- `get_account_limits` works in local mode without hosted service calls.
- Local save, list, load, resume, delete, WorkStash store, WorkStash load, and
  search are covered by tests.
- The local schema keeps WorkBaton, WorkStash, and WorkThreads separate while
  allowing cross-object references and search.
- Local WorkBaton Slot history has no small hard cap and no default expiration.
- Local WorkThreads are searchable without dumping full thread history into MCP
  responses.
- WorkThreads tests cover create, post, list, load, close, archive, and
  reference-from-WorkBaton behavior once thread tools are implemented.
- Local records preserve client and agent provenance while keeping project state
  shared across agents by default.
- Local search has handoff-specific tests for resume Slot lookup, stale Slot
  filtering, decision lookup, validation lookup, agent provenance lookup, and
  referenced WorkStash lookup.
- `a2cr init`, `a2cr ui`, save, resume, and search do not modify `AGENTS.md`,
  `CLAUDE.md`, `A2CR.md`, or similar files without explicit confirmation.
- Local mode does not act as an LLM proxy or compression layer.
- `a2cr ui` opens a local browser UI and shows saved WorkBaton and WorkStash
  bodies and WorkThreads conversation messages.
- Browser UI search can find and open WorkBaton, WorkStash, and WorkThreads
  records.
- Local mode makes no network calls during normal save/resume/search/UI usage.
- Cloud sync cannot happen without explicit user action.
- Generated local database files are not committed to this repository.

## Open Questions

- Should local mode become the default for the MCP Registry package, or should
  the Registry keep cloud setup until the local CLI is mature?
- Should project-local `.a2cr/` storage be supported in the first local release
  or deferred?
- Should the browser UI be implemented in Python first for packaging simplicity,
  or as a small bundled web app for a richer interface?
- Should local event history include failed save/load attempts, or only
  successful state transitions?
- What is the minimum useful WorkLedger shape once local event history exists?

## Design Summary

A2CR Local should be the frictionless entry point:

```text
Local first. No account. No API key. Same MCP tools. Searchable history. Browser UI.
Shared multi-agent workspace memory, rich local history, compact handoff through WorkBaton.
```

A2CR Cloud should remain the connected upgrade:

```text
Sync, backup, team handoff, encrypted relay, and auditability when the user needs it.
```

This keeps A2CR focused on AI work handoff while removing the biggest adoption
barrier for individual developers: needing a hosted account before the first
successful save. Generic memory remembers facts. Compression tools reduce
tokens. Agent memory belongs to one agent. A2CR preserves shared work state
across agents and hands off work.
