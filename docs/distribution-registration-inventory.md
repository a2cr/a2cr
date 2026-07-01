# A2CR Distribution And Registration Inventory

Last checked: 2026-07-01
Repository scope: `public-release/`
Public source of truth: `https://github.com/a2cr/a2cr`
Canonical MCP server name: `io.github.a2cr/a2cr-mcp`
Canonical public package: `a2cr-mcp==0.1.7`

This inventory records where A2CR is published, registered, mirrored, or
discussed as an MCP server. Treat GitHub, PyPI, the official MCP Registry, and
the GitHub Release as canonical. Downstream directories may cache old README,
license, version, or setup text.

## Canonical Public Surfaces

| Surface | URL | Current status | Version | Source of truth | Next action |
|---|---|---|---|---:|---|
| Public repository | `https://github.com/a2cr/a2cr` | Public OSS repository, Apache-2.0 public release line. | `main` after the 0.1.7 release and post-release docs work. | Yes | Keep release work in PR flow; do not push directly to `main` unless explicitly approved. |
| PyPI | `https://pypi.org/project/a2cr-mcp/` | Latest package is published. | `0.1.7` | Yes | Recheck immediately after every package release. |
| Official MCP Registry | `https://registry.modelcontextprotocol.io/v0.1/servers/io.github.a2cr%2Fa2cr-mcp/versions/latest` | Active latest Registry entry for stdio package `a2cr-mcp`. | `0.1.7` | Yes | Publish only new immutable versions after the matching PyPI package is live. |
| Registry manifest | `server.json` | Local stdio package manifest with optional `A2CR_LOCAL_DB` only. | `0.1.7` | Yes | Keep `server.json`, PyPI package metadata, and Registry version aligned. |
| GitHub Release | `https://github.com/a2cr/a2cr/releases/tag/v0.1.7` | Published release with MCPB asset and checksum file. | `v0.1.7` | Yes | Keep MCPB compatibility version aligned with the Python wrapper. |
| Homepage | `https://a2cr.app/` | Retired-SaaS explanation surface for A2CR usage. It is not the active SaaS product. | Explains local-only public line. | Support surface | Keep wording aligned with GitHub public docs. Consider serving `/privacy` and `/en/privacy` as 200 for directory reviewers. |
| AI-readable site summary | `https://a2cr.app/llms.txt` | Public explanation of the local-only A2CR boundary. | Explains local-only public line. | Support surface | Keep in sync when public setup or distribution changes. |

## Downstream MCP Directories And Mirrors

These surfaces are useful for discovery, but they are not canonical. Some are
scraped from older README or Registry data and may still mention the retired
hosted service, `A2CR_API_KEY`, older version `0.1.6`, Roo Code, or pre-Apache
license wording.

| Surface | URL | Observed status on 2026-07-01 | Current action |
|---|---|---|---|
| Glama | `https://glama.ai/mcp/servers/a2cr/a2cr` | Listed as a Python/local MCP server and exposes current WorkThread tools, but the overview can still include older README text about hosted service, `0.1.6`, and stale license signals. | Monitor after public README changes propagate; request refresh if stale install guidance remains visible. |
| MCP Pub | `https://mcp.pub/servers/a2cr/` | Listed as active and updated 2026-06-25 with local setup commands, but still includes stale Roo Code and old license commentary. | Monitor and request refresh after Apache-2.0 README propagates. |
| MCP.so | `https://mcp.so/server/a2cr/A2CR` | Listed with install command, but its example config still points at `A2CR_BASE_URL` / hosted service assumptions. | Treat as stale; request correction only after canonical docs are fully clean. |
| Vibehackers | `https://vibehackers.io/mcp/a2cr-mcp` | Listed as `v0.1.6` and still requires hosted A2CR API key in setup guidance. | Treat as stale; request correction or wait for registry resync. |
| Claude Code Marketplaces | `https://claudemarketplaces.com/mcp/io.github.a2cr/a2cr-mcp` | Listed as active, but summary and configuration still mention hosted service/API key and older README snippets. | Treat as stale; request refresh once the post-release docs PR lands. |

## Claude And OpenAI Distribution State

| Channel | Current state | Version | Blocking decision |
|---|---|---|---|
| Claude Desktop MCPB manual install | Published as `a2cr-0.1.7.mcpb` on the GitHub Release, with `SHA256SUMS.txt`. | `0.1.7` | None for manual install. |
| Anthropic Directory / automated MCPB pickup | Not claimed as approved. GitHub Release assets are ready for pickup or submission flow. | `0.1.7` | Public privacy/support URLs should be reviewer-friendly before submission or resubmission. |
| OpenAI Apps / remote MCP | Future phase only. The current public artifact is a local stdio MCP server, not a hosted remote MCP app. | N/A | Remote plaintext/privacy boundary must be written before any full remote save/resume app submission. |
| Claude remote MCP connector | Future phase only. | N/A | Same remote plaintext/privacy boundary as OpenAI. |

## Current Public Setup Truth

The public setup path is local-only:

```powershell
python -m pip install --upgrade a2cr-mcp
a2cr init codex --local
a2cr doctor --target local
```

Normal public setup does not require an A2CR account, API key, hosted base URL,
hosted SaaS dashboard, remote MCP connector, or cloud sync path.

## Follow-Up Checklist

- Keep this inventory current before every public release.
- After post-release docs land, re-check downstream directory text and request
  corrections for any setup that still asks for `A2CR_API_KEY` or
  `A2CR_BASE_URL`.
- Decide whether the hosted explanation surface should serve simple 200 privacy
  pages at `/privacy` and `/en/privacy` for directory reviewers.
- Do not represent Anthropic Directory, OpenAI Apps, or Claude remote MCP
  approval as complete until there is explicit approval evidence.
