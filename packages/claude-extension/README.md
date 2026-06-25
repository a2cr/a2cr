# A2CR Claude Extension

This package contains the in-progress Claude Desktop Extension / MCPB local
wrapper for A2CR.

The extension is intentionally local-first. It must preserve the same security
boundary as the Python `a2cr-mcp` wrapper: WorkBaton and WorkStash bodies are
validated and stored on the user's machine without uploading saved content to
A2CR infrastructure.

Status: WorkBaton and WorkStash local runtime, MCPB manifest metadata, and
local MCPB packaging are implemented for testing and manual GitHub Release
distribution. Full Python-wrapper parity and final official submission assets
are still pending.

Implemented so far:

- `src/crypto.ts` implements Fernet-compatible local encryption/decryption with
  the Python wrapper's local key path and `kid` behavior.
- `src/localStore.ts`, `src/workbaton.ts`, `src/workstash.ts`, and
  `src/tools.ts` implement local storage, WorkBaton guardrails, WorkStash
  encryption/decryption, and the current eight MCP tools:
  `get_account_limits`, `list_contexts`, `save_context`, `load_context`,
  `store_work_stash`, `get_work_stash`, `list_work_stash`, and
  `delete_work_stash`.
- Runtime tool registration includes human-readable titles and MCP tool
  annotations for the current submission tools.
- Keep the compatibility version aligned with the public Python `a2cr-mcp`
  version. When Python `a2cr-mcp` is bumped, update the Node wrapper constant
  and tests at the same time.
- `manifest.json` declares the Claude Desktop Extension metadata,
  Windows/macOS compatibility, and the public privacy policy URL.
- `tests/crypto.test.ts` proves Node can decrypt Python Fernet fixtures and
  Python can decrypt Node Fernet tokens.
- The Vitest suite also covers safe HTTP diagnostics, URL path encoding,
  validation-before-save, and load-time local decryption.
- `tests/stdio-smoke.test.ts` starts the compiled Node MCP server as a separate
  stdio process with a temporary local key and local store file, then verifies
  tool listing plus local WorkBaton and WorkStash save/load/delete behavior.

Packaging commands:

- `npm run mcpb:validate` validates `manifest.json` with
  `@anthropic-ai/mcpb@2.1.2`.
- `npm run mcpb:pack` builds `dist/`, creates a clean staging directory with
  production dependencies only, validates the staged manifest, and writes
  `build/mcpb/artifacts/a2cr-0.1.7.mcpb` plus
  `build/mcpb/artifacts/SHA256SUMS.txt`.

The pack script intentionally excludes TypeScript sources, tests, and dev
dependencies from the generated MCPB artifact.

Distribution decision:

- Publish the generated `.mcpb` as a GitHub Release asset, not an npm package.
- Attach a SHA-256 checksum alongside the `.mcpb` asset.
- Keep the package version, manifest version, and `A2CR_MCP_COMPAT_VERSION`
  aligned with the public Python `a2cr-mcp` release.
- Do not claim Anthropic Directory approval until the listing is approved.
- Keep `SUBMISSION.md` current as the public-safe directory submission checklist
  for the MCPB package.

For `0.1.7`, publish `a2cr-0.1.7.mcpb` and `SHA256SUMS.txt` to the public
GitHub Release before sending Anthropic the automated pickup details.

## Privacy Policy

The A2CR Claude Desktop Extension is a local connector. It runs on the user's
machine, communicates with Claude Desktop over stdio, validates WorkBaton
content locally, and stores WorkBaton and WorkStash records in a local file on
the user's machine. It does not upload saved WorkBaton or WorkStash content.

Public privacy policy: https://github.com/a2cr/a2cr/blob/main/docs/privacy.md

Data collection:

- The extension does not require an A2CR account or API key.
- Account-limit reads, Slot metadata reads, WorkBaton saves/loads, and
  WorkStash store/load/list/delete operations are served from the local
  extension store.
- `A2CR_LOCAL_STORE_FILE` may be used during tests to point the extension at a
  disposable local store file.

Usage and storage:

- WorkBaton body content is validated on the user's machine before save.
- WorkBaton bodies and WorkStash values are encrypted locally before being
  written to the local store file.
- `list_contexts` and `list_work_stash` return metadata only, not stored body
  values.
- The MCPB manifest does not request sensitive remote-service configuration.

Third-party sharing:

- The extension is designed to run without A2CR hosted infrastructure.
- A2CR does not sell WorkBaton or WorkStash content.
- No third-party service receives saved WorkBaton or WorkStash content from
  this MCPB.

Data retention:

- WorkBaton Slots remain in the local store until overwritten or the local
  store file is deleted.
- WorkStash entries remain in the local store until deleted with
  `delete_work_stash` or by deleting the local store file.
- No hosted access logs are created by this MCPB's save/load path.
- If the local client key is lost, old client-encrypted WorkBaton bodies and
  WorkStash values cannot be recovered by A2CR.

Contact:

- Support and issues: https://github.com/a2cr/a2cr/issues
- Security reporting: follow the repository `SECURITY.md`; do not disclose
  secrets, API keys, decrypted WorkBaton content, or vulnerability details in
  public issues.

## Reviewer Setup

Do not put reviewer credentials, API keys, or recovery material in this
repository. The local-only MCPB reviewer path does not require an A2CR account
or API key.

Reviewer smoke path:

1. Download `a2cr-0.1.7.mcpb` from the public GitHub Release.
2. Install it in Claude Desktop with `Settings > Extensions > Advanced settings
   > Install Extension`.
3. Run the read-only, WorkBaton save/load, WorkStash store/get/list/delete, and
   metadata checks in `VERIFY.md` with harmless test content only.

Known review scope:

- The MCPB currently exposes WorkBaton and WorkStash local tools:
  `get_account_limits`, `list_contexts`, `save_context`, `load_context`,
  `store_work_stash`, `get_work_stash`, `list_work_stash`, and
  `delete_work_stash`.
- WorkThreads MCPB parity is pending and intentionally out of the first
  submission scope.
- `store_work_stash` can overwrite an existing entry key and is annotated as
  destructive for review safety.
- `delete_work_stash` is destructive and is annotated as such.
- The MCPB does not install the Python `a2cr ui` browser dashboard. Users who
  want the dashboard should install the Python `a2cr-mcp` package separately.

Manual Claude Desktop verification:

- Follow `VERIFY.md` to install the generated `.mcpb` and exercise the
  WorkBaton and WorkStash tools with harmless test data.
