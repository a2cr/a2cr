# A2CR Claude Extension

This package contains the in-progress Claude Desktop Extension / MCPB local
wrapper for A2CR.

The extension is intentionally local-first. It must preserve the same security
boundary as the Python `a2cr-mcp` wrapper: WorkBaton and WorkStash bodies are
validated and encrypted on the user's machine before upload to A2CR.

Status: WorkBaton MVP runtime, MCPB manifest metadata, and local MCPB packaging
are implemented for testing and pre-submission GitHub Release distribution.
WorkStash tools, full tool parity, reviewer instructions, and official
submission assets are still pending.

Implemented so far:

- `src/crypto.ts` implements Fernet-compatible local encryption/decryption with
  the Python wrapper's local key path and `kid` behavior.
- `src/api.ts`, `src/workbaton.ts`, and `src/tools.ts` implement safe HTTPS API
  calls, WorkBaton guardrails, local encryption/decryption, and the first four
  MCP tools: `get_account_limits`, `list_contexts`, `save_context`, and
  `load_context`.
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

Manual Claude Desktop verification:

- Follow `VERIFY.md` to install the generated `.mcpb`, enter the API key through
  Claude Desktop's extension UI, and exercise the MVP read/save/load tools with
  harmless test data.
