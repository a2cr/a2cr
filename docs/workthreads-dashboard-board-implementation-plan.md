# WorkThreads Dashboard Board Implementation Plan

Status: Phase 2 baseline complete; board polish remains
Last checked: 2026-07-01
Repository scope: `public-release/`

This plan implements the dashboard-centered WorkThreads board described in
`docs/workthreads-dashboard-board-spec.md`.

## Current Baseline

Already implemented in local mode:

- SQLite tables for WorkThreads, messages, participants, references, actors,
  and events.
- MCP tools for create, post, list, load, close, and archive.
- Search across WorkThread messages and metadata.
- Dashboard WorkThreads tab with list, detail, participants, messages,
  references, close, and archive.
- Board API Phase 1:
  - join-prompt helper in `workthreads_board.py`
  - `POST /api/workthreads`
  - `POST /api/workthreads/<thread_key>/messages`
  - `GET /api/workthreads/<thread_key>/join-prompt`
  - endpoint tests in `tests/local_workspace/test_workthreads_board_api.py`
- Project-centered dashboard Phase 2 baseline:
  - `Projects` navigation and all-projects index
  - project detail view for WorkBaton, WorkStash, WorkThreads, and recent events
  - selected-project persistence in browser local storage
  - project-scoped WorkThread create-room form
  - project-scoped search shortcut
  - copy join-prompt button in WorkThread detail
- Local tests covering lifecycle, participants, references, search, truncation,
  close/archive, and cloud-unavailable behavior.

Main gaps:

- The project view is client-filtered from `GET /api/state`; add a dedicated
  project endpoint only if state payload size becomes a real issue.
- The create-room form currently lives in the selected project view, not the
  global WorkThreads view.
- No dashboard message composer in the rendered UI.
- No board-style cards or readable post conventions in the rendered UI.
- No automatic refresh or new-message highlighting.

## Phase 0 - Spec Alignment

Goal: keep the board UX separated from the lower-level local storage spec.

Tasks:

1. Add the board spec and implementation plan documents.
2. Link them from `docs/local-mode-spec.md`.
3. Keep wording clear that WorkThreads are coordination history, not the resume
   artifact and not a full autonomous orchestration layer.

Acceptance:

- Docs identify the dashboard board as the intended next WorkThreads UX.
- Docs preserve the WorkBaton / WorkStash / WorkThreads boundary.

## Phase 1 - Prompt Generator And UI API

Status: complete in the current public checkout.

Goal: make the dashboard able to create rooms and produce join prompts without
changing the existing SQLite schema.

Files:

- `a2cr_mcp/local_workspace/ui.py`
- optional helper: `a2cr_mcp/local_workspace/workthreads_board.py`
- tests under `tests/local_workspace/`

Tasks:

1. Add a pure helper that builds a join prompt from:
   - `thread_key`
   - `title`
   - `project_key`
   - optional `participant_label`
2. Add `POST /api/workthreads` to create a room by calling
   `store.create_work_thread`.
3. Add `POST /api/workthreads/<thread_key>/messages` to post a dashboard
   coordinator note by calling `store.post_work_thread_message`.
4. Add `GET /api/workthreads/<thread_key>/join-prompt` to return the generated
   prompt text.
5. Keep all endpoints behind the existing UI token.
6. Validate required fields and return compact JSON errors.

Acceptance:

- Dashboard API can create a room.
- Dashboard API can post a message.
- Dashboard API can return a join prompt for an existing room.
- Prompt text tells the invited AI to call `get_work_thread` and then
  `post_work_thread_message`.
- Prompt text says every board post is user-visible.

Suggested tests:

- prompt helper includes thread key, title, project, and safe posting rules
- create-room endpoint creates a WorkThread in a temporary DB
- message endpoint posts and registers a participant
- join-prompt endpoint returns not_found for missing rooms
- endpoint access still rejects missing or wrong UI token

## Phase 2 - Project-Centered Dashboard Views

Status: baseline complete in the current public checkout.

Goal: make project the primary local dashboard organizing lens, so users can
review WorkBaton, WorkStash, and WorkThreads together for one project.

Files:

- `a2cr_mcp/local_workspace/ui.py`
- `tests/local_workspace/test_search_ui_p2.py` or a new UI test module

Tasks:

1. Add a project selector or project list interaction from the dashboard
   project table.
2. Track the selected project in browser state, URL hash, or local state so a
   refresh preserves the selection.
3. Add a project detail surface with:
   - overview counts
   - recent project events
   - WorkBaton Slots filtered by `project_key`
   - WorkStash entries filtered by `project_key`
   - WorkThread rooms filtered by `project_key`
4. Add an `All projects` option that restores the current global lists.
5. Prefill WorkThread create-room project from the selected project.
6. Add a project-scoped search shortcut that sends
   `/api/search?project=<project_key>`.
7. Keep this first phase client-filtered from `GET /api/state`; add a dedicated
   project endpoint only if state payload size becomes a real problem.

Acceptance:

- A user can click/select a project and see that project's Baton/Stash/Threads
  without changing MCP configuration.
- A user can return to the global view.
- Creating a WorkThread from a project context keeps the same project key.
- Project-scoped search returns only matching project records.
- WorkBaton remains visually framed as the resume artifact, not as another
  thread post.

## Phase 3 - Board View UI

Goal: turn the current WorkThreads list/detail into a board-style work surface.

Files:

- `a2cr_mcp/local_workspace/ui.py`
- `tests/local_workspace/test_search_ui_p2.py` or a new UI test module

Tasks:

1. Add a `Create room` control to the WorkThreads view.
2. Add form fields:
   - title
   - thread key, with a generated slug default
   - project
   - commander label
   - initial message
3. Replace or augment the table with room cards or a denser board list:
   - title
   - state
   - project
   - participant count
   - message count
   - latest update
   - latest message preview
4. In room detail, add:
   - copy join prompt button
   - optional participant label field for prompt generation
   - coordinator/user message composer
   - participant chips
   - readable message cards
5. Keep close/archive actions visible but confirm destructive or hiding actions.

Acceptance:

- A user can create a room without using MCP directly.
- A user can copy a join prompt from the room detail.
- A user can read posts as a conversation board.
- A user can post a manual coordinator note.
- Participants remain visible in the room detail.

## Phase 4 - Refresh And New Message Detection

Goal: let the dashboard notice new posts without using database file size.

Files:

- `a2cr_mcp/local_workspace/ui.py`
- optional helper methods in `store.py` only if needed

Tasks:

1. Add a periodic refresh, initially every 3-5 seconds.
2. Compare previous and current `updated_at`, `message_count`, or latest
   message id per thread.
3. Mark rooms with unread or changed badges while the user remains on the page.
4. If a room detail is open, refresh that room's detail endpoint separately.
5. Preserve the selected room after refresh.
6. Avoid noisy full-page flicker.

Acceptance:

- A post from another AI window appears in the dashboard after polling.
- Changed rooms are visually marked.
- The dashboard does not treat database size as the source of truth.

Future optimization:

- Add a lightweight `GET /api/events?since=<timestamp>` or
  `GET /api/workthreads/changes?since=<timestamp>` endpoint if polling full
  state becomes heavy.

## Phase 5 - Message Conventions And Search Polish

Goal: make board posts understandable to users and easy to search.

Files:

- `a2cr_mcp/local_workspace/ui.py`
- `a2cr_mcp/local_workspace/store.py`
- `tests/local_workspace/test_workthreads_p1.py`
- docs and skill templates if needed

Tasks:

1. Render recommended post sections such as `Status:`, `Summary:`, `Next:`,
   and `References:` cleanly when present.
2. Continue escaping message HTML.
3. Keep long message truncation in MCP responses.
4. Add UI affordances for references so `WorkBaton:` and `WorkStash:` handles
   are easy to follow.
5. Update search result snippets to make WorkThread hits feel like board posts.

Acceptance:

- Users can understand thread messages without reading raw machine-oriented
  payloads.
- Long details are encouraged to move to WorkStash.
- WorkThread search still opens the room detail.

## Phase 6 - Validation And Release Readiness

Goal: prove the board works as a practical local workflow.

Validation steps:

1. Run targeted tests:

   ```powershell
   python -m pytest tests/local_workspace tests/test_mcp_stdio.py
   ```

2. Run public repository guard tests:

   ```powershell
   python -m pytest tests/test_public_repository.py
   ```

3. Run a live local smoke:
   - `a2cr doctor --target local`
   - start `a2cr ui`
   - create a room in the dashboard
   - copy the join prompt
   - use `a2cr-local` MCP from another AI window or the current test surface to
     post a join message
   - confirm the dashboard shows the new participant and post after refresh
   - close/archive the room

4. Re-run package smoke before public release if this ships with local mode:
   - `python -m build`
   - install the wheel in a clean temporary environment
   - verify the dashboard board flow still works from installed artifacts

Acceptance:

- The feature works without an A2CR account in local mode.
- No public-release diff includes private-production material.
- The user-visible board flow is documented and tested.
- WorkBaton remains the resume artifact in docs, prompts, and UI text.

## Implementation Order

Recommended order:

1. Keep Phase 1 prompt helper and endpoint tests green.
2. Add project selector/detail filtering for Baton/Stash/Threads.
3. Wire WorkThreads create-room UI and copy prompt.
4. Add message composer and readable message cards.
5. Add polling and changed-room badges.
6. Polish project-scoped search and references.
7. Run live dashboard smoke and package smoke.

This order keeps the dashboard useful immediately: first let a user understand
one project's saved state, then deepen the WorkThreads board workflow inside
that project context.

## Open Decisions

- Should the first board use cards, a dense table, or a hybrid list plus detail
  pane? Current A2CR UI is dense and operational, so a hybrid list/detail view is
  the safest first implementation.
- Should dashboard manual posts use `participant_label="user"` or a configurable
  coordinator label? A configurable label is more useful, with `user` as the
  default.
- Should unread state persist across page reloads? The first release can keep it
  in browser memory only.
- Should message types become schema fields? Not for the first release. Start
  with readable body conventions and add schema fields later only if filtering
  by type becomes important.
