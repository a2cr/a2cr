# A2CR Claude Extension

This package contains the in-progress Claude Desktop Extension / MCPB local
wrapper for A2CR.

The extension is intentionally local-first. It must preserve the same security
boundary as the Python `a2cr-mcp` wrapper: WorkBaton and WorkStash bodies are
validated and encrypted on the user's machine before upload to A2CR.

Status: WorkBaton MVP runtime, MCPB manifest metadata, and local MCPB packaging
are implemented for testing and manual GitHub Release distribution.
WorkStash tools, full tool parity, and final official submission assets are
still pending.

Implemented so far:

- `src/crypto.ts` implements Fernet-compatible local encryption/decryption with
  the Python wrapper's local key path and `kid` behavior.
- `src/api.ts`, `src/workbaton.ts`, and `src/tools.ts` implement safe HTTPS API
  calls, WorkBaton guardrails, local encryption/decryption, and the first four
  MCP tools: `get_account_limits`, `list_contexts`, `save_context`, and
  `load_context`.
- Runtime tool registration includes human-readable titles and MCP tool
  annotations for the current MVP tools.
- API calls include the public A2CR MCP compatibility version header so the
  dashboard can distinguish an up-to-date local wrapper from missing-version
  legacy activity.
- Keep that compatibility version aligned with the public Python `a2cr-mcp`
  version. When Python `a2cr-mcp` is bumped, update the Node wrapper constant
  and tests at the same time.
- `manifest.json` declares the Claude Desktop Extension metadata, required
  sensitive API-key configuration, default A2CR base URL, Windows/macOS
  compatibility, and the public privacy policy URL.
- `tests/crypto.test.ts` proves Node can decrypt Python Fernet fixtures and
  Python can decrypt Node Fernet tokens.
- The Vitest suite also covers safe HTTP diagnostics, URL path encoding,
  validation-before-upload, and load-time local decryption.
- `tests/stdio-smoke.test.ts` starts the compiled Node MCP server as a separate
  stdio process with a temporary local key and mock A2CR API, then verifies tool
  listing plus encrypted save/decrypted load behavior.

Packaging commands:

- `npm run mcpb:validate` validates `manifest.json` with
  `@anthropic-ai/mcpb@2.1.2`.
- `npm run mcpb:pack` builds `dist/`, creates a clean staging directory with
  production dependencies only, validates the staged manifest, and writes
  `build/mcpb/artifacts/a2cr-0.1.6.mcpb` plus
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

For `0.1.6`, `a2cr-0.1.6.mcpb` and `SHA256SUMS.txt` are attached to the public
GitHub Release.

## Privacy Policy

The A2CR Claude Desktop Extension is a local connector. It runs on the user's
machine, communicates with Claude Desktop over stdio, validates WorkBaton
content locally, and encrypts WorkBaton bodies locally before upload to the A2CR
hosted service. The hosted A2CR service stores ciphertext for WorkBaton bodies
created through this extension and does not receive the local client key.

Public privacy policy: https://a2cr.app/en/privacy

Data collection:

- The extension sends the configured A2CR API key to the A2CR hosted service as
  an Authorization header.
- The extension sends account-limit reads, Slot metadata reads, encrypted
  WorkBaton saves, and encrypted WorkBaton loads to `https://a2cr.app` by
  default.
- The extension sends wrapper metadata headers such as client type and A2CR MCP
  compatibility version so the dashboard can show current local-wrapper status.

Usage and storage:

- WorkBaton body content is validated and encrypted on the user's machine before
  upload.
- A2CR stores WorkBaton ciphertext, Slot metadata, account metadata, and access
  log metadata needed to operate the hosted service.
- The A2CR API key is entered through Claude Desktop extension settings and is
  treated as sensitive configuration by the MCPB manifest.

Third-party sharing:

- The extension is designed to communicate with the A2CR hosted service only.
- A2CR does not sell WorkBaton content.
- A2CR's hosted service infrastructure providers process service data as needed
  to operate `https://a2cr.app`.

Data retention:

- WorkBaton Slots follow the account's configured retention and expiry behavior.
- Access logs and operational metadata are retained as needed for service
  operation, abuse prevention, troubleshooting, and security review.
- If the local client key is lost, old client-encrypted WorkBaton bodies cannot
  be recovered by A2CR.

Contact:

- Support and issues: https://github.com/a2cr/a2cr/issues
- Security reporting: follow the repository `SECURITY.md`; do not disclose
  secrets, API keys, decrypted WorkBaton content, or vulnerability details in
  public issues.

## Reviewer Setup

Do not put reviewer credentials, API keys, or recovery material in this
repository. Provide a disposable A2CR reviewer account and API key through the
Anthropic submission form or another private reviewer channel.

Reviewer smoke path:

1. Download `a2cr-0.1.6.mcpb` from the public GitHub Release.
2. Install it in Claude Desktop with `Settings > Extensions > Advanced settings
   > Install Extension`.
3. Enter the disposable A2CR API key in the extension UI.
4. Keep `A2CR Base URL` as `https://a2cr.app`.
5. Run the read-only, save/load, and metadata checks in `VERIFY.md` with
   harmless test content only.

Known review scope:

- The MCPB currently exposes the four WorkBaton MVP tools:
  `get_account_limits`, `list_contexts`, `save_context`, and `load_context`.
- WorkStash MCPB parity is pending.
- Delete tools are intentionally omitted from the MCPB MVP until destructive
  action review is added.

Manual Claude Desktop verification:

- Follow `VERIFY.md` to install the generated `.mcpb`, enter the API key through
  Claude Desktop's extension UI, and exercise the MVP read/save/load tools with
  harmless test data.
