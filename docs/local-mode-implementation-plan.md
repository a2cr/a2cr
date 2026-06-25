# A2CR Local Mode Implementation Plan

Status: superseded planning draft

This draft is retained for design history. As of 2026-06-24, the active public
implementation direction is local-only A2CR, documented in
`docs/local-only-saas-retirement-plan.md`. The public package should not add or
promote cloud/SaaS setup paths.

This plan turns the local mode specification into a staged implementation. It
keeps the first useful release small: no account, no API key, local SQLite,
same core MCP tools, and WorkBaton resume working end to end.

The implementation should preserve the product model from
`docs/local-mode-spec.md`:

```text
A2CR Local Workspace
  -> WorkBaton
  -> WorkStash
  -> WorkThreads
```

The three objects share one local workspace, but they must stay separate:

- WorkBaton is the compact serial resume artifact.
- WorkStash is supporting evidence and longer explanations.
- WorkThreads is active or archived cross-agent coordination history.

Resume should still happen through WorkBaton.

## Current Baseline

The public Python package currently exposes:

- one package entrypoint: `a2cr-mcp`
- one main implementation file: `a2cr_mcp/server.py`
- hosted A2CR API calls through `httpx`
- client-side encryption for cloud WorkBaton and WorkStash saves
- WorkBaton and WorkStash MCP tools
- WorkThreads guidance text, but no local WorkThreads storage surface

The implementation should avoid a risky rewrite of `server.py` in one patch.
All new local mode implementation code should live under a dedicated package
folder:

```text
a2cr_mcp/local_workspace/
```

Existing files may receive only thin integration hooks: mode selection,
entrypoint wiring, and calls into `a2cr_mcp/local_workspace/`. Local storage,
search, WorkThreads, Web UI, and local CLI command implementations should not be
mixed into the existing hosted wrapper code.

## Code Organization Boundary

Use this folder layout for new local mode code:

```text
a2cr_mcp/
  server.py                  # existing MCP entrypoint; thin local/cloud routing only
  __main__.py                # existing a2cr-mcp entrypoint
  local_workspace/
    __init__.py
    config.py                # local/cloud mode selection and paths
    schema.py                # SQLite schema version and migrations
    db.py                    # SQLite connection, transactions, WAL setup
    models.py                # local record dataclasses or typed dicts
    guardrails.py            # local-safe validators reused by stores
    store.py                 # local workspace store facade
    workbaton.py             # WorkBaton local operations
    workstash.py             # WorkStash local operations
    workthreads.py           # WorkThreads local operations
    search.py                # FTS indexing and query behavior
    actors.py                # client, agent, model, and session provenance
    events.py                # local event history
    cli.py                   # a2cr user-facing CLI
    ui/
      __init__.py
      server.py              # loopback web UI server
      static/                # bundled UI assets if needed
      templates/             # server-rendered views if used
```

Tests for local mode should also stay separate:

```text
tests/local_workspace/
```

Allowed edits outside these folders:

- `a2cr_mcp/server.py`: call the local workspace facade when `A2CR_MODE=local`.
- `a2cr_mcp/__main__.py`: keep existing `a2cr-mcp` behavior.
- `pyproject.toml`: add the `a2cr` console script pointing at
  `a2cr_mcp.local_workspace.cli:main`.
- `README.md` and `docs/`: document local mode.
- `.gitignore`: only if project-local generated data is introduced.

Disallowed implementation pattern:

- Do not grow `a2cr_mcp/server.py` into a combined cloud/local/UI/search module.
- Do not put SQLite schema, Web UI, or WorkThreads implementation directly next
  to unrelated hosted API helper code.
- Do not put generated local databases or UI build output in tracked source
  folders.

## Target OSS Publication Model

The final public release should make the local workspace implementation the main
public A2CR product and publish that local code as OSS.

Target public split:

| Surface | Final public posture |
|---|---|
| `a2cr_mcp/local_workspace/` | Main OSS implementation. |
| WorkBaton / WorkStash / WorkThreads local schemas | Public, documented, and test-covered. |
| `a2cr-mcp` and `a2cr` CLI local mode | Local-first public distribution. |
| A2CR Cloud sync | Retired from the public 0.1.7 setup story. |
| Hosted production backend | Not part of the OSS release. |

Do not announce or document the package as OSS until these gates are complete:

- choose and apply the final OSI-approved license for the local workspace code
- audit the public repository for private-only files and hosted production code
- make local mode the default first-use path
- remove `A2CR_API_KEY` from local installs and MCP Registry metadata
- update README, package metadata, license files, and contribution docs
- verify local save, resume, search, UI, and WorkThreads with no network calls
- keep hosted/cloud sync out of the public 0.1.7 release path

The current source-available/open-core README wording should remain accurate
until the license transition is actually complete.

## Phase 0 - Test Harness And Internal Boundaries

Goal: make the codebase ready for local mode without changing user-visible
behavior.

Implementation tasks:

- Add the dedicated `a2cr_mcp/local_workspace/` package.
- Add local workspace modules:
  - `a2cr_mcp/local_workspace/config.py`
  - `a2cr_mcp/local_workspace/schema.py`
  - `a2cr_mcp/local_workspace/db.py`
  - `a2cr_mcp/local_workspace/models.py`
  - `a2cr_mcp/local_workspace/guardrails.py`
  - `a2cr_mcp/local_workspace/store.py`
  - `a2cr_mcp/local_workspace/workbaton.py`
  - `a2cr_mcp/local_workspace/workstash.py`
  - `a2cr_mcp/local_workspace/workthreads.py`
  - `a2cr_mcp/local_workspace/search.py`
  - `a2cr_mcp/local_workspace/actors.py`
  - `a2cr_mcp/local_workspace/events.py`
  - `a2cr_mcp/local_workspace/cli.py`
- Keep `a2cr_mcp/server.py` as the MCP entrypoint.
- Move or wrap only the pure helper logic needed by local mode. Avoid unrelated
  hosted refactors.
- Add tests that prove moved helpers keep existing behavior.
- Add a small storage interface used by MCP tools:

```text
Store.save_context(...)
Store.load_context(...)
Store.list_contexts(...)
Store.delete_context(...)
Store.store_work_stash(...)
Store.get_work_stash(...)
```

Exit criteria:

- Existing hosted behavior is no longer part of the public 0.1.7 release path.
- Existing stdio tests pass.
- No local mode behavior is advertised before storage works.
- New local implementation files are under `a2cr_mcp/local_workspace/`.
- New local tests are under `tests/local_workspace/`.

## Phase 1 - Local Configuration And SQLite Foundation

Goal: make local storage the default public runtime.

Implementation tasks:

- Implement mode selection:
  - default public runtime -> local store
  - legacy cloud flags -> do not re-enable hosted behavior
  - no mode and no API key -> local store
- Add default local paths:
  - Windows: `%LOCALAPPDATA%\A2CR\a2cr.db`
  - macOS: `~/Library/Application Support/A2CR/a2cr.db`
  - Linux: `$XDG_DATA_HOME/a2cr/a2cr.db` or `~/.local/share/a2cr/a2cr.db`
- Support `A2CR_LOCAL_DB` for tests and custom installs.
- Create SQLite migrations with WAL enabled.
- Add tables:
  - `settings`
  - `projects`
  - `actors`
  - `workbatons`
  - `workstash_entries`
  - `workthreads`
  - `workthread_messages`
  - `events`
- Add cross-reference tables:
  - `workbaton_references`
  - `workstash_references`
  - `workthread_references`
- Add generated local data paths to `.gitignore` only if project-local mode is
  later implemented.

Exit criteria:

- Importing `a2cr_mcp.server` without `A2CR_API_KEY` no longer fails.
- Local database creation works in a temporary test directory.
- Local mode makes no HTTP calls for `get_account_limits`.

## Phase 2 - WorkBaton Local Parity

Goal: make the first useful local MCP path work.

Implementation tasks:

- Implement local versions of:
  - `save_context`
  - `load_context`
  - `resume_context`
  - `list_contexts`
  - `delete_context`
  - `should_save_workbaton`
  - `get_account_limits`
- Preserve current WorkBaton validation and guardrails.
- Store WorkBaton JSON as structured JSON text.
- Store actor provenance:
  - client name
  - optional agent label
  - model source
  - session id
  - timestamps
- Support slot metadata:
  - `slot_name`
  - `slot_number`
  - pinned
  - stale
  - superseded
  - do-not-use
  - archived
- Implement `resume_context` candidate selection:
  - prefer explicit slot
  - otherwise newest non-stale non-archived WorkBaton for the project
  - return clear diagnostics when no candidate exists
- Return `storage_mode: "local"` in local tool responses.

Exit criteria:

- A user can save, list, load, resume, and delete a WorkBaton locally with no
  account and no API key.
- Tests assert local WorkBaton operations make no `httpx` calls.
- Loaded local WorkBaton content includes the same untrusted-content safety
  guidance as cloud-loaded content.

## Phase 3 - WorkStash Local Parity And References

Goal: make supporting notes work locally and connect them to WorkBaton.

Implementation tasks:

- Implement local versions of:
  - `store_work_stash`
  - `get_work_stash`
  - `list_work_stash`
  - `delete_work_stash`
  - `should_use_work_stash`
- Keep `entry_key` validation.
- Store tags and actor provenance.
- Add reference extraction from WorkBaton `references` values such as
  `WorkStash: <entry_key>`.
- Show referenced WorkStash entries in load/resume responses by handle, not by
  dumping full note bodies.
- Add cleanup protection:
  - warn before deleting referenced WorkStash entries
  - allow forced delete for explicit user action

Exit criteria:

- WorkStash entries can be stored, listed, loaded, searched by key, and deleted.
- WorkBaton references to WorkStash are preserved and queryable.
- Tests cover referenced entry deletion behavior.

## Phase 4 - Local Search

Goal: make local history useful without flooding the AI context window.

Implementation tasks:

- Add FTS5 tables:
  - `workbatons_fts`
  - `workstash_fts`
  - `workthread_messages_fts`
  - `events_fts`
- Add chunking for large WorkStash and WorkThread message bodies.
- Add MCP tool:
  - `search_contexts`
- Add CLI command:
  - `a2cr search <query>`
- Search filters:
  - project
  - object type
  - slot
  - tag
  - client
  - agent
  - thread state
  - date range
- Return compact results:
  - handle
  - object type
  - project
  - timestamp
  - short snippet
  - reason/match fields
- Add UI search result routes that open full local records:
  - WorkBaton saved content
  - WorkStash saved value
  - WorkThread conversation

Exit criteria:

- Search can find resume Slots, stale Slots, decisions, validation notes,
  referenced WorkStash entries, and WorkThread messages.
- MCP search defaults to small snippets and requires explicit load for full
  bodies.
- Browser UI search can open full matching WorkBaton, WorkStash, and WorkThread
  records.
- Search tests cover all three objects.

## Phase 5 - User-Facing CLI

Goal: make local setup and diagnostics easy.

Implementation tasks:

- Add console entrypoint:

```toml
a2cr = "a2cr_mcp.local_workspace.cli:main"
a2cr-local-mcp = "a2cr_mcp.entrypoints:local_main"
a2cr-cloud-mcp = "a2cr_mcp.entrypoints:cloud_main"
```

- Implement:
  - `a2cr init <client> --local`
  - `a2cr doctor`
  - `a2cr status`
  - `a2cr search <query>`
  - `a2cr open`
- `a2cr init` must support:
  - `codex`
  - `claude-code`
  - `cursor`
  - `generic --print-config`
  - `--dry-run`
  - `--force`
  - `--db PATH`
- Config edits must:
  - create timestamped backups
  - never write secrets
  - never silently rewrite `AGENTS.md`, `CLAUDE.md`, or `A2CR.md`

Exit criteria:

- A clean local install can configure Codex in two commands.
- Codex local config creates `a2cr-local` and runs `a2cr-local-mcp`.
- Codex cloud config creates `a2cr-cloud` and runs `a2cr-cloud-mcp`.
- `a2cr doctor` verifies Python version, package command, database, MCP config,
  and local mode selection.
- CLI tests run on Windows path shapes and POSIX path shapes.

## Phase 6 - WorkThreads Local Surface

Goal: add the third local workspace object after WorkBaton and WorkStash are
stable.

Implementation tasks:

- Implement tables and local store methods for:
  - create thread
  - post message
  - list threads
  - load thread
  - close thread
  - archive thread
- Add MCP tools:
  - `create_work_thread`
  - `post_work_thread_message`
  - `list_work_threads`
  - `get_work_thread`
  - `close_work_thread`
  - `archive_work_thread`
- Add thread state:
  - open
  - closed
  - archived
- Add participants and message provenance.
- Add thread references:
  - WorkBaton may reference WorkThread handles
  - WorkThread may reference WorkBaton slots
  - WorkThread may reference WorkStash entries
- Summarize long thread responses.

Exit criteria:

- WorkThreads can coordinate active work without replacing WorkBaton.
- Tests cover create, post, list, load, close, archive, and cross-object
  references.
- `resume_context` does not dump full thread history.

## Phase 7 - Local Browser UI

Goal: make the local workspace inspectable by humans.

Implementation tasks:

- Implement `a2cr ui`.
- Bind to `127.0.0.1` by default.
- Use an available port and random local session token.
- Add views:
  - Dashboard
  - Project
  - WorkBaton detail with full saved handoff content and JSON
  - WorkStash detail with full saved entry value
  - WorkThreads list
  - WorkThread detail with agent-to-agent conversation messages
  - Search
  - Agents
  - Timeline
  - Cleanup
  - Settings
- Add full local content inspection:
  - WorkBaton saved body, references, validation, stale/supersession state
  - WorkStash saved body, tags, and referenced-by records
  - WorkThread conversation messages, participants, message provenance, and
    references
- Add safe actions:
  - pin/unpin WorkBaton
  - mark stale
  - archive
  - delete with confirmation
  - export
  - backup
- Do not upload or sync from the UI without explicit user action.

Exit criteria:

- `a2cr ui` opens a browser and displays saved local WorkBaton and WorkStash
  bodies.
- `a2cr ui` displays WorkThreads conversation messages with participant and
  agent provenance.
- UI search can find and open WorkBaton, WorkStash, and WorkThread records.
- UI actions are covered by lightweight integration tests where practical.
- Browser UI does not bind to LAN by default.

## Phase 8 - Retired Cloud Connection And Sync

Goal: record the previously considered cloud-sync path as retired for the
0.1.7 local-only release.

Retired tasks:

- Do not add `a2cr cloud login`, `a2cr cloud status`, or `a2cr cloud sync` to
  the public 0.1.7 setup story.
- Do not document hosted backup or cloud sync as a public install path.
- Keep the local database primary and sufficient on its own.

Exit criteria:

- Local mode remains fully useful without cloud.
- Cloud sync cannot be enabled accidentally by legacy environment variables.
- Public docs and package metadata do not require an account, API key, hosted
  URL, or cloud connector.

## Suggested Pull Request Order

1. Add `a2cr_mcp/local_workspace/` and `tests/local_workspace/`.
2. Add configuration and storage interface in the local workspace package.
3. Add SQLite schema and migration tests.
4. Add local WorkBaton parity.
5. Add local WorkStash parity.
6. Add `search_contexts` and FTS.
7. Add `a2cr` CLI with `doctor`, `status`, and `search`.
8. Add `a2cr init <client> --local`.
9. Add local WorkThreads tools.
10. Add `a2cr ui`.
11. Add explicit cloud sync.
12. Update README, MCP Registry metadata, and release docs.

## Testing Strategy

Required test groups:

- Existing hosted stdio behavior.
- Mode selection.
- SQLite migration and schema integrity.
- WorkBaton local CRUD and resume candidate selection.
- WorkStash local CRUD and reference behavior.
- WorkThreads local lifecycle.
- FTS search and snippet behavior.
- No-network assertions in local mode.
- CLI config dry-run and backup behavior.
- Project memory files are not edited without explicit confirmation.
- Windows path handling for default local database and config paths.

## Release Strategy

Recommended release shape:

| Release | Scope |
|---|---|
| Local alpha 1 | Local WorkBaton only, hidden behind `A2CR_MODE=local`. |
| Local alpha 2 | WorkStash and local search. |
| Local beta 1 | `a2cr` CLI, `init`, `doctor`, and docs. |
| Local beta 2 | WorkThreads local surface. |
| Local beta 3 | Browser UI. |
| Local stable | Local-first docs, MCP Registry update, and SaaS-free public setup. |
| OSS public main | Local workspace becomes the main public OSS product after license and repository audit gates pass. |

Current implementation checkpoints:

| Checkpoint | Scope | Verification focus |
|---|---|---|
| P0 | `a2cr` CLI, `a2cr init codex --local`, `a2cr doctor`, package smoke. | Safe config writes, dry-run, backups, installed console scripts, legacy cloud setup rejected clearly. |
| P1 | Local WorkThreads MCP surface. | Create, post, list, load, close, archive, participants, references, search, no-network local mode. |
| P2 | Local browser UI, safe local actions, and stronger search filters. | `a2cr ui`, loopback token server, full local record inspection, pin/stale/archive/delete, backup/export, project/type/date/tag/state/agent/slot filters. |
| P3 | Dedicated local MCP command and legacy-cloud rejection. | `a2cr-local-mcp`, Codex `a2cr-local`, local doctor target, compatibility `a2cr-mcp` retained, legacy cloud setup rejected with a clear message. |

The public README should switch to local-first quickstart only after:

- local WorkBaton and WorkStash are stable
- `a2cr init codex --local` works
- `a2cr doctor` gives reliable diagnostics
- local mode has no unintended network calls

The public README should switch from source-available/open-core wording to OSS
wording only after:

- the final OSS license is committed
- private production surfaces are audited out of the public repository
- `a2cr_mcp/local_workspace/` is the main implementation path
- hosted/cloud functionality is outside the public 0.1.7 release path

## Risks And Mitigations

| Risk | Mitigation |
|---|---|
| Legacy hosted assumptions leak into public setup | Keep docs, examples, registry metadata, and tests local-only by default. |
| Local mode becomes generic memory | Keep WorkBaton as resume entrypoint and keep object boundaries in tests. |
| Search floods MCP context | Return snippets and handles by default; require explicit load for full bodies. |
| SQLite schema churn | Use versioned migrations from the first local implementation. |
| Config installers damage user files | Use dry-run, backups, and minimal MCP entry edits. |
| WorkThreads delays first release | Ship WorkBaton and WorkStash local parity first; add WorkThreads after. |
| Cloud/local behavior diverges too much | Keep shared validators, response fields, and MCP tool names where possible. |

## Definition Of Done

Local mode is implementation-complete when:

- `pip install a2cr-mcp` installs both `a2cr-mcp` and `a2cr`.
- `a2cr init codex --local` configures Codex safely.
- `a2cr doctor` confirms local database and MCP readiness.
- `save_context`, `resume_context`, `store_work_stash`, and `search_contexts`
  work with no API key.
- WorkBaton, WorkStash, and WorkThreads are stored separately but searchable
  together.
- New local mode implementation code lives under `a2cr_mcp/local_workspace/`
  except for thin entrypoint wiring.
- Local mode makes no network calls for save, load, resume, list, search, or UI.
- Browser UI can inspect full WorkBaton and WorkStash saved content, inspect
  WorkThreads conversation messages, search all three, and clean up local
  workspace data.
- Cloud sync is optional and explicit.
