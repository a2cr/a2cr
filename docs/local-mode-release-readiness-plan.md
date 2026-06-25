# A2CR Local Mode Release Readiness Plan

Status: 0.1.7 local-only release candidate plan
Last checked: 2026-06-25
Repository scope: `public-release/`

This plan tracks the work needed to move A2CR from a passing local
implementation to something users can install and use with a short, reliable
flow. As of 2026-06-25, `0.1.7` is the local-only release candidate in this
checkout; cloud/SaaS setup paths are being retired from the public setup story.

The release-candidate scope and release-note draft are recorded in
`docs/releases/v0.1.7-local-only-release-candidate.md`.

## Release Candidate Decision

`0.1.7` is the local-only public release candidate for A2CR.

Candidate means:

- the package metadata, local-only docs, and Claude MCPB compatibility version
  are aligned on `0.1.7`;
- the Python public wrapper is the normal install path for Codex, Claude Code,
  Cursor, and generic MCP clients;
- the Claude Desktop MCPB is the manual extension-style install path until
  Anthropic Directory approval;
- no hosted SaaS account, API key, hosted base URL, remote MCP connector, or
  cloud sync path is required for normal public setup;
- publish actions are still pending PR review/merge and one final post-merge
  verification pass.

## Current State

Local mode implementation is present in the public package checkout:

- `a2cr_mcp/server.py` routes MCP tools to local storage by default.
- `a2cr_mcp/local_workspace/` contains the local SQLite store, CLI helpers,
  loopback browser UI, Codex config writer, search, WorkBaton, WorkStash, and
  WorkThreads operations.
- `pyproject.toml` declares these console scripts:
  - `a2cr`
  - `a2cr-local-mcp`
  - compatibility command `a2cr-mcp`
- Local tests exist under `tests/local_workspace/`.

Latest verification in this checkout:

- 2026-06-25 release-candidate gate:
  - `python -m pytest tests/local_workspace tests/test_mcp_stdio.py
    tests/test_public_repository.py tests/test_spec_documents.py -q` passed
    with 82 tests.
  - `npm test`, `npm run typecheck`, `npm run mcpb:validate`, and
    `npm run mcpb:pack` passed in `packages/claude-extension`.
  - `python -m build` produced `a2cr_mcp-0.1.7.tar.gz` and
    `a2cr_mcp-0.1.7-py3-none-any.whl`.
  - Clean wheel smoke in a temporary venv passed: `a2cr`, `a2cr-local-mcp`,
    and compatibility `a2cr-mcp` installed; `a2cr-cloud-mcp` was absent;
    `a2cr doctor --target local` reported `ready: true`; `a2cr init codex
    --cloud` exited `2`; local save/load, WorkStash store/get, search, and
    WorkThread create passed.
- `a2cr doctor --target local` reported `ready: true`.
- `python -m pytest tests/local_workspace tests/test_mcp_stdio.py` passed.
- `python -m build` produced both sdist and wheel.
- The wheel installed into a clean temporary virtual environment, `a2cr init
  codex --local` created a temporary config, `a2cr doctor --target local`
  reported `ready: true`, and a temporary local DB smoke passed for save,
  resume, WorkStash store/get/search, and WorkThread create.
- After a Codex/MCP reload, the running `a2cr-local` MCP server successfully
  exposed and handled `get_account_limits`, WorkStash store/get, WorkBaton
  save/resume with a referenced WorkStash entry, `search_contexts` discovery of
  both records, and temporary WorkBaton/WorkStash deletion. Cleanup left only
  event history for the smoke marker, with no active WorkBaton or WorkStash
  records.
- `python -m pytest` passed in an earlier full-suite run.
- A direct temporary-database smoke test passed for:
  - `save_context`
  - `resume_context`
  - `search_contexts`
  - `create_work_thread`

The remaining gap is final release readiness. The working tree code is usable
directly, but a user machine may still have an older installed package or only
the compatibility `a2cr-mcp` command on `PATH` until a public release is cut.

Current usability note:

- Local WorkStash entries can be associated with a project explicitly through
  the MCP `project` argument, through `A2CR_PROJECT`, through
  `A2CR_PROJECT_ROOT`, or by falling back to the current working directory name.
  This keeps WorkStash search and UI grouping aligned with WorkBaton project
  lookup instead of dropping supporting notes into a generic default bucket.

Known packaging warnings:

- `python -m build` currently reports setuptools deprecation warnings for the
  `project.license` TOML table and license classifier. The current license file
  is source-available/BUSL-style text rather than a simple SPDX expression, so
  treat this as metadata cleanup before a future release rather than evidence
  that the local mode wheel failed to build.
- `MANIFEST.in` intentionally excludes some paths that may not exist in every
  checkout; setuptools reports those missing exclude/prune matches as warnings.

## Phase 1 - Make This Checkout Usable Locally

Goal: make the current public checkout usable from the maintainer machine before
publishing anything.

Steps:

1. Install the current checkout in editable mode:

   ```powershell
   cd C:\Users\sirot\Desktop\A2CR_workspace\public-release
   python -m pip install -e .
   ```

2. Verify the new commands resolve to the current Python environment:

   ```powershell
   where a2cr
   where a2cr-local-mcp
   where a2cr-mcp
   ```

3. Run local diagnostics:

   ```powershell
   a2cr doctor --target local
   ```

4. Configure Codex for local A2CR:

   ```powershell
   a2cr init codex --local --dry-run
   a2cr init codex --local
   ```

5. Restart Codex and verify the MCP server is visible as `a2cr-local`.

6. Run an end-to-end local user smoke:

   - save a compact WorkBaton with `save_context`
   - load it with `resume_context`
   - store and retrieve a WorkStash note
   - run `search_contexts`
   - create and read a WorkThread
   - open `a2cr ui` and confirm search/detail views work

Acceptance criteria:

- `a2cr doctor --target local` reports `ready: true`.
- Codex starts `a2cr-local` through `a2cr-local-mcp`.
- Save, resume, stash, search, and WorkThreads work without an A2CR account or
  API key.
- Local save, load, resume, search, and UI do not make outbound network calls.

## Phase 2 - Make Install And Use Simple

Goal: turn the user-facing setup into a small command sequence.

Target install flow:

```powershell
python -m pip install --upgrade a2cr-mcp
a2cr init codex --local
a2cr doctor --target local
```

Target first-use flow:

1. Restart the MCP client after `a2cr init`.
2. Ask the agent to save a handoff through A2CR.
3. Resume in a fresh AI window with `resume_context`.
4. Run `a2cr ui` to open the local browser dashboard. The command binds to
   `127.0.0.1`, prints a token-protected local URL, opens it in the default
   browser, and runs until the user presses `Ctrl+C`. If browser auto-open is
   unavailable, copy the printed `A2CR_UI_URL` including `?token=...`; the bare
   `127.0.0.1:<port>` URL is rejected by design.
5. Use `a2cr search <query>` or the browser dashboard when the user wants to
   inspect local history.

Documentation updates:

- Make the public README local-first for the simplest setup path.
- Remove cloud/SaaS setup from the public quickstart and default docs.
- Until local mode is published, clearly label the local quickstart as a source
  checkout or editable-install flow.
- Explain that local mode requires no A2CR account and no API key.
- Explain that `a2cr-local` is the recommended local MCP server name.
- Keep `a2cr-mcp` documented only as the compatibility command.
- Document `a2cr ui`, including loopback binding, tokenized URL, copy-paste
  fallback, `Ctrl+C` shutdown, `--no-browser`, `--port`, and `--db`.
- Add troubleshooting for:
  - command not found
  - old package still installed
  - Codex config missing `a2cr-local`
  - legacy cloud environment variables being ignored by local-only A2CR
  - local database path and backup location

Acceptance criteria:

- A new user can install, configure Codex, and pass doctor with three commands.
- The first visible workflow is save/resume, not configuration theory.
- The docs preserve the handoff-first boundary: WorkBaton is the resume object,
  WorkStash is supporting memory, and WorkThreads coordinate active work.

## Phase 3 - Package Validation

Goal: prove the package artifact works outside the source checkout.

Steps:

1. Build the distribution artifacts:

   ```powershell
   python -m build
   ```

2. Inspect the wheel contents and confirm it includes:

   - `a2cr_mcp/entrypoints.py`
   - `a2cr_mcp/local_workspace/`
   - local workspace tests or test fixtures when intentionally packaged
   - console scripts declared in `pyproject.toml`

3. Install the wheel in a clean virtual environment.

4. Verify commands:

   ```powershell
   a2cr --help
   a2cr doctor --target local
   a2cr init codex --local --dry-run
   a2cr-local-mcp
   ```

5. Run a temporary-database smoke test from the installed wheel:

   - save WorkBaton
   - resume WorkBaton
   - store WorkStash
   - search
   - create WorkThread

6. Confirm legacy cloud environment variables do not switch the installed
   package away from local mode.

Acceptance criteria:

- A clean environment does not depend on the source checkout.
- `a2cr-local-mcp` and compatibility `a2cr-mcp` are available on `PATH`.
- Existing `a2cr-mcp` compatibility behavior remains intact.
- Legacy cloud configuration does not silently re-enable remote behavior.

## Phase 4 - Public Release Flow

Goal: publish the local-first package without mixing private-production state
into the public release.

Steps:

1. Review the public diff for private-only files, secrets, tokens, recovery
   codes, local keys, or production-only configuration.
2. Update version and changelog.
3. Update README and local mode docs.
4. Run the full public test suite.
5. Run build and clean-install package smoke tests.
6. Open a public-release PR.
7. Merge after review.
8. Publish to PyPI.
9. Create or update the GitHub Release.
10. Update MCP Registry metadata only if the public registry flow should expose
    the new local command split.

Acceptance criteria:

- Public package is installable from PyPI.
- The public quickstart works from a clean machine.
- No private-production files or claims are included.
- Release notes clearly state that public A2CR now runs as a local workspace.

## Phase 5 - Post-Release Verification

Goal: confirm the published package works for real users.

Checks:

- Fresh install on Windows.
- Fresh install on macOS or Linux when available.
- `a2cr doctor --target local` reports ready after `a2cr init codex --local`.
- Codex can call `save_context` and `resume_context` through `a2cr-local`.
- `a2cr ui` binds only to loopback and uses a random token.
- `a2cr search` finds WorkBaton, WorkStash, WorkThreads, and event metadata.
- A user can recover from a stale or wrong MCP config using documented
  troubleshooting steps.

## Release Gates

Do not mark local mode release-ready until all of these are true:

- Local save, resume, stash, search, UI, and WorkThreads are tested.
- Public A2CR does not require an API key.
- Public A2CR does not call hosted A2CR for normal save/load/resume/list/search
  or UI usage.
- `a2cr init codex --local` makes a backup before modifying config.
- `a2cr doctor --target local` gives actionable diagnostics.
- Public docs do not describe A2CR as a generic memory store.
- WorkBaton remains the compact serial handoff artifact.
- WorkStash remains supporting memory, not a durable knowledge base.
- WorkThreads remain coordination history, not a replacement for WorkBaton.
- The compatibility `a2cr-mcp` path still works for existing users.

## Immediate Next Actions

1. Inspect the public diff for private-only content before any PR or release.
2. Open the public-release PR rather than pushing directly to `main`.
3. Re-run the final public test/build/package smoke after review and merge.
4. Tag `v0.1.7`, publish PyPI, create the GitHub Release, attach the MCPB and
   checksum, then update MCP Registry metadata if desired.
