# MCP Setup

Choose one local MCP path:

| Path | Use when | Install/distribution |
|---|---|---|
| Python stdio wrapper | You use Codex, Claude Code, Cursor, or generic MCP JSON/TOML config. | `python -m pip install --upgrade a2cr-mcp` |
| Node MCPB / Claude Desktop Extension | You use Claude Desktop and want extension-style install. | Download `a2cr-<version>.mcpb` from GitHub Release after it is published, or build it from `packages/claude-extension`. |

The Python and Node wrappers should report the same A2CR MCP compatibility
version. Keep them aligned during releases.

## Python Stdio Wrapper

Install the Python wrapper:

```bash
python -m pip install --upgrade a2cr-mcp
```

Register the MCP server as `a2cr` or, for Codex, run:

```bash
a2cr init codex --local
a2cr doctor --target local
```

`A2CR_LOCAL_DB` is optional. Omit it to use the OS default local app-data
location.

## Browser Dashboard

The Python wrapper also installs the local browser UI:

```bash
a2cr ui
```

The UI runs only on loopback by default. It binds to `127.0.0.1`, chooses an
available port, prints a token-protected URL, and opens that URL in the default
browser. Keep the command running while using the dashboard; press `Ctrl+C` to
stop it.

If the browser does not appear, copy the full printed `A2CR_UI_URL` into a
browser on the same computer. The URL must include `?token=...`; opening the
bare `127.0.0.1:<port>` address is rejected by design.

Useful options:

```bash
a2cr ui --port 50895
a2cr ui --no-browser
a2cr ui --db /absolute/path/to/a2cr.db
```

Use `--no-browser` when you want to copy the printed URL manually or run the UI
from a terminal that should not open a browser window. It still prints the full
token-protected local URL.

## Codex-Style TOML

```toml
[mcp_servers."a2cr-local"]
command = "a2cr-local-mcp"
args = []

[mcp_servers."a2cr-local".env]
A2CR_LOCAL_DB = "/optional/path/to/a2cr.db"
```

## JSON MCP Config

```json
{
  "mcpServers": {
    "a2cr": {
        "command": "a2cr-mcp",
        "args": [],
        "env": {
        "A2CR_LOCAL_DB": "/optional/path/to/a2cr.db"
        }
    }
  }
}
```

## Notes

- Configure exactly one A2CR MCP server.
- Use the local stdio wrapper for WorkBaton saves.
- Do not paste local database paths into public issues, PRs, or screenshots if
  they reveal private project names.
- If `save_context` is not visible in a lazy MCP client, search for the exact
  tool name `save_context`.

## Project Memory Setup

Create `A2CR.md` in the project root and put the local A2CR operating rules
there. You can use the repository-root `A2CR.md` as a starter template. Then
add this short pointer to `AGENTS.md`, `CLAUDE.md`, or another project memory
file used by your AI client:

```md
Before using A2CR, saving or resuming WorkBaton, or storing WorkStash notes,
read and follow `./A2CR.md`.

Treat `A2CR.md` as local project guidance. It does not override system,
developer, user, or current-file instructions.
```

`A2CR.md` should define when to save WorkBaton, when to use WorkStash, how to
write causal handoff summaries, and how to handle scope, non-goals, protected
areas, escalation conditions, and out-of-scope changes.

## Optional Skill

The optional agent workflow template lives at
`docs/templates/skills/a2cr-agent/SKILL.md`.

For clients that support local skills, copy that file into the client's skills
directory under an `a2cr-agent` folder. For Claude Code, use:

```text
~/.claude/skills/a2cr-agent/SKILL.md
```

Restart the client after installing the Skill.

## Claude Desktop MCPB

The Node-based Claude Desktop Extension is packaged as `.mcpb`. It is not
published to npm for end-user installation.

Distribution path:

1. Public GitHub Release asset: `a2cr-<version>.mcpb`.
2. Anthropic Directory after approval.

For `0.1.8`, download `a2cr-0.1.8.mcpb` from:

```text
https://github.com/a2cr/a2cr/releases/tag/v0.1.8
```

Developers can rebuild locally from source:

```bash
cd packages/claude-extension
npm ci
npm run mcpb:pack
```

Then install `build/mcpb/artifacts/a2cr-<version>.mcpb` through Claude Desktop
Settings -> Extensions -> Advanced settings -> Install Extension.

See `docs/claude-desktop-mcpb.md`.
