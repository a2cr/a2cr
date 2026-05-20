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

For `0.1.6`, the expected artifact name is:

```text
a2cr-0.1.6.mcpb
```

The GitHub Release URL pattern is:

```text
https://github.com/a2cr/a2cr/releases/tag/v0.1.6
```

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
build/mcpb/artifacts/a2cr-0.1.6.mcpb
build/mcpb/artifacts/SHA256SUMS.txt
```

The pack script writes `SHA256SUMS.txt` automatically. To verify it manually on
Windows:

```powershell
Get-FileHash .\build\mcpb\artifacts\a2cr-0.1.6.mcpb -Algorithm SHA256
```

On macOS/Linux:

```bash
shasum -a 256 build/mcpb/artifacts/a2cr-0.1.6.mcpb
```

## Install In Claude Desktop

1. Open Claude Desktop settings.
2. Go to Extensions.
3. Open Advanced settings.
4. Choose Install Extension.
5. Select the downloaded `a2cr-<version>.mcpb`.
6. Enter the A2CR API key in the extension settings UI.
7. Keep `A2CR Base URL` as `https://a2cr.app` unless testing a compatible
   deployment.
8. Restart Claude Desktop if the tools do not appear immediately.

The API key is sensitive. Do not paste real keys into public issues, screenshots,
or chat transcripts.

## Current Scope

The Node MCPB is the Claude Desktop packaging path. Keep it aligned with the
Python wrapper, but do not pretend it is a separate product.

Current MVP tools:

- `get_account_limits`
- `list_contexts`
- `save_context`
- `load_context`

The Python `a2cr-mcp` wrapper remains the full public wrapper path while the
Node MCPB reaches full WorkBaton / WorkStash parity for official submission.

## Version Alignment Rule

The dashboard uses the A2CR MCP compatibility version reported by local wrappers.
When the Python wrapper version changes, update the Node wrapper compatibility
constant, package version, MCPB manifest version, tests, and docs in the same
release. The two local MCP paths should report the same public compatibility
version unless there is an explicit compatibility exception in the release notes.

For `0.1.6`, both paths should report:

```text
X-A2CR-MCP-Version: 0.1.6
```

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
