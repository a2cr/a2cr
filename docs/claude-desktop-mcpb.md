# Claude Desktop MCPB Distribution

This page documents the Node-based Claude Desktop Extension / MCPB path for
A2CR. It is the intended local Claude Desktop distribution artifact before
Anthropic Directory approval.

Do not describe this package as approved, listed, or officially reviewed by
Anthropic until approval has actually happened.

## Distribution Decision

A2CR has two local MCP distribution paths:

| Path | Primary client | Distribution point | Runtime expectation |
|---|---|---|---|
| Python `a2cr-mcp` | Codex, Claude Code, Roo Code, Cursor, generic MCP clients | PyPI | User or client environment has Python 3.12+ available. |
| Node MCPB | Claude Desktop | GitHub Release `.mcpb` asset, then Anthropic Directory after approval | Claude Desktop supplies the Node runtime for the extension. |

The Node package under `packages/claude-extension` is private on npm on purpose.
End users should not install it with `npm install`. They install the packaged
`.mcpb` file.

## GitHub Release Asset

For each public release that includes the Claude Desktop Extension, attach:

- `a2cr-<version>.mcpb`
- `SHA256SUMS.txt` or equivalent checksum text
- release notes that say this is a Claude Desktop MCPB package

For `0.1.7`, the expected artifact name is:

```text
a2cr-0.1.7.mcpb
```

The GitHub Release URL pattern is:

```text
https://github.com/a2cr/a2cr/releases/tag/v0.1.7
```

## Anthropic Automated Pickup

After the GitHub Release is published with the MCPB asset and checksum, send
Anthropic these details once so later releases can be picked up from GitHub:

- `owner/repo`: `a2cr/a2cr`
- tag pattern: `v*` (example: `v0.1.7`)
- asset filename: `a2cr-<version>.mcpb`
- checksum filename: `SHA256SUMS.txt`
- maintainer contact: fill in the human contact immediately before sending

A2CR currently publishes one cross-platform Node MCPB bundle for Claude Desktop
on macOS and Windows.

## Build Locally Before Publishing

From `packages/claude-extension`:

```bash
npm ci
npm test
npm run typecheck
npm run mcpb:validate
npm run mcpb:pack
```

Expected output:

```text
build/mcpb/artifacts/a2cr-0.1.7.mcpb
build/mcpb/artifacts/SHA256SUMS.txt
```

The pack script writes `SHA256SUMS.txt` automatically. To verify it manually on
Windows:

```powershell
Get-FileHash .\build\mcpb\artifacts\a2cr-0.1.7.mcpb -Algorithm SHA256
```

On macOS/Linux:

```bash
shasum -a 256 build/mcpb/artifacts/a2cr-0.1.7.mcpb
```

## Install In Claude Desktop

1. Open Claude Desktop settings.
2. Go to Extensions.
3. Open Advanced settings.
4. Choose Install Extension.
5. Select the downloaded `a2cr-<version>.mcpb`.
6. Review the extension metadata and complete the install.
7. Restart Claude Desktop if the tools do not appear immediately.

No A2CR account, API key, hosted base URL, or SaaS dashboard connection is
required. The MCPB stores WorkBaton data in a local file managed by the
extension.

The MCPB does not install the Python CLI or browser dashboard command. Users
who want the local browser UI should also install the Python wrapper and run:

```bash
python -m pip install --upgrade a2cr-mcp
a2cr ui
```

If the browser does not open automatically, copy the full printed
`A2CR_UI_URL` into a browser on the same computer. Keep the `?token=...` query
string; opening the bare `127.0.0.1:<port>` URL is rejected by design.

## Current Scope

The Node MCPB is the Claude Desktop packaging path. Keep it aligned with the
Python wrapper, but do not pretend it is a separate product.

Current submission-scope tools:

- `get_account_limits`
- `list_contexts`
- `save_context`
- `load_context`
- `store_work_stash`
- `get_work_stash`
- `list_work_stash`
- `delete_work_stash`

The Python `a2cr-mcp` wrapper remains the full public wrapper path for advanced
local workflows. The Node MCPB is the Claude Desktop package for local
WorkBaton and WorkStash use.

## Version Alignment Rule

The dashboard uses the A2CR MCP compatibility version reported by local wrappers.
When the Python wrapper version changes, update the Node wrapper compatibility
constant, package version, MCPB manifest version, tests, and docs in the same
release. The two local MCP paths should report the same public compatibility
version unless there is an explicit compatibility exception in the release notes.

For `0.1.7`, both paths should report:

```text
X-A2CR-MCP-Version: 0.1.7
```

## Release Alignment Checklist

Use this checklist for every public release that changes either the Python
wrapper or the Node MCPB. The default policy is a paired release: if
`a2cr-mcp` becomes `0.x.y`, the Node MCPB package and A2CR MCP compatibility
version should also become `0.x.y`.

Before opening the release PR:

- Update the Python package version in `pyproject.toml`.
- Update the MCP Registry metadata version in `server.json`.
- Update the Node MCPB package version in
  `packages/claude-extension/package.json`.
- Update the MCPB manifest version in
  `packages/claude-extension/manifest.json`.
- Update the Node wrapper compatibility header constant in
  `packages/claude-extension/src/version.ts`.
- Update README/docs references for the new version and release URL.
- Update tests that assert version strings, release asset names, or MCPB
  metadata.

Before publishing artifacts:

- Run the Python public repository tests.
- Run `npm test`, `npm run typecheck`, `npm run mcpb:validate`, and
  `npm run mcpb:pack` from `packages/claude-extension`.
- Confirm the generated artifact is named `a2cr-<version>.mcpb`.
- Confirm `SHA256SUMS.txt` contains the checksum for the same artifact.
- Inspect the packaged `manifest.json`, `README.md`, and `dist/tools.js` from
  the `.mcpb` archive when tool annotations or privacy text changed.

When publishing:

- Publish the Python package to PyPI first.
- Publish the matching MCP Registry version after the PyPI package exists.
- Attach `a2cr-<version>.mcpb` and `SHA256SUMS.txt` to the same GitHub Release.
- Make the release notes name both local paths and state whether their
  compatibility versions match.

Only use an unpaired release when there is an explicit compatibility exception.
In that case, document the mismatch in the release notes and avoid changing
dashboard "latest wrapper" expectations until both paths are aligned again.

## Public Wording

Before Anthropic approval, use:

```text
Claude Desktop Extension / MCPB for local installation.
```

After approval, the website and README may add:

```text
Available from the Anthropic Connectors Directory.
```

Do not use approval language early.
