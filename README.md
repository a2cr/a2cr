<p align="center">
  <img src="docs/assets/github/a2cr-logo.png" alt="A2CR logo" width="420">
</p>

# A2CR

[![PyPI](https://img.shields.io/pypi/v/a2cr-mcp.svg)](https://pypi.org/project/a2cr-mcp/)
[![CI](https://github.com/a2cr/a2cr/actions/workflows/ci.yml/badge.svg)](https://github.com/a2cr/a2cr/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Glama MCP](https://glama.ai/mcp/servers/a2cr/a2cr/badges/card.svg)](https://glama.ai/mcp/servers/a2cr/a2cr)

<!-- mcp-name: io.github.a2cr/a2cr-mcp -->

A2CR is an open-source local MCP workspace for AI agent handoffs. It lets
Codex, Claude Code, Cursor, and other MCP-capable agents save WorkBaton
checkpoints, store temporary WorkStash notes, coordinate through WorkThreads,
and resume long coding work from a fresh AI window.

Long AI work usually breaks at the handoff. A fresh AI window needs the goal,
current state, decisions, blockers, validation, and next action, but not a whole
noisy transcript. A2CR keeps that handoff state compact, explicit, and safer to
share between sessions.

Use A2CR when you want to:

- restart a long AI coding task from a clean context window
- pass work state between Codex, Claude Code, Cursor, or another MCP client
- keep milestone checkpoints without storing full chat transcripts
- separate compact resume state from optional supporting notes

[Japanese overview](README-ja.md) | [MCP setup](docs/mcp-setup.md) |
[Usage guide](docs/usage.md) | [WorkBaton spec](docs/spec/README.md) |
[Local mode spec](docs/local-mode-spec.md) |
[0.1.7 release notes](docs/releases/v0.1.7-local-only-release-candidate.md)

## Directory Status

A2CR is published in the
[official MCP Registry](https://registry.modelcontextprotocol.io/v0.1/servers/io.github.a2cr%2Fa2cr-mcp/versions/latest)
as `io.github.a2cr/a2cr-mcp`. The local-only `0.1.7` public release is live on
PyPI, GitHub Releases, and the official MCP Registry. See the
[distribution inventory](docs/distribution-registration-inventory.md) for the
current registration and mirror status.

A2CR is also listed and evaluated on the
[Glama MCP Registry](https://glama.ai/mcp/servers/a2cr/a2cr). Downstream
directories may temporarily show cached metadata after a release; the official
MCP Registry and this repository are the source of truth.

## Local Storage Boundary

A2CR now treats the local workspace as the public product boundary. The public
`a2cr-mcp` wrapper stores WorkBaton, WorkStash, WorkThread, actor, and event
records in a SQLite database on the user's machine. It does not require an A2CR
account, API key, hosted relay, dashboard, or cloud sync path.

The earlier hosted/SaaS relay path is being retired from the public
distribution. New public setup, MCP Registry metadata, and Anthropic Directory
submission work should use the local wrapper only.

## Quickstart

Choose the local MCP distribution path that matches your AI client:

| Path | Best for | Distribution | Notes |
|---|---|---|---|
| Python stdio wrapper | Codex, Claude Code, Cursor, generic MCP clients | PyPI package `a2cr-mcp` | Full public wrapper path for WorkBaton and WorkStash. |
| Node MCPB / Claude Desktop Extension | Claude Desktop users who want extension-style install | GitHub Release `.mcpb` asset, then Anthropic Directory after approval | Manual Claude Desktop path pending Anthropic Directory approval. No npm install is required for end users. |

Keep the Python wrapper version and Node MCPB compatibility version aligned.
For the current public release, both the Python wrapper and Node MCPB
compatibility version are `0.1.7`.

Python wrapper install:

```bash
python -m pip install --upgrade a2cr-mcp
```

Register A2CR for Codex and verify the local workspace:

```bash
a2cr init codex --local
a2cr doctor --target local
```

Open the local browser dashboard:

```bash
a2cr ui
```

`a2cr ui` binds to `127.0.0.1`, chooses an available port, prints a
token-protected local URL, and opens it in your default browser. If the browser
does not open, copy the full printed `A2CR_UI_URL`, including `?token=...`, into
a browser on the same computer. The bare `127.0.0.1:<port>` URL is rejected by
design. Keep that terminal running while you use the dashboard. Press `Ctrl+C`
to stop it.

For a fixed port or a headless/server-style launch:

```bash
a2cr ui --port 50895
a2cr ui --no-browser
```

Use `--no-browser` when installing on a machine where the terminal cannot or
should not launch a browser; it still prints the full local URL to copy.

Then restart Codex and use the `a2cr-local` MCP server. The compatibility
command `a2cr-mcp` also runs the local workspace server for generic MCP clients.
Start with a compact WorkBaton save/resume. Put larger supporting notes in
WorkStash, then record the `WorkStash: <entry_key>` reference in the WorkBaton
`references` or `next_action` field so the next AI window knows exactly what to
retrieve.

Codex-style TOML:

```toml
[mcp_servers."a2cr-local"]
command = "a2cr-local-mcp"
args = []

[mcp_servers."a2cr-local".env]
A2CR_LOCAL_DB = "/optional/path/to/a2cr.db"
```

Generic MCP JSON:

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

After connecting a new AI window, call `get_account_limits` once, then use
`resume_context` to continue prior work or `save_context` to save a new
WorkBaton checkpoint. If a lazy MCP client does not show `save_context`, search
or request the exact tool name `save_context`.

Python 3.12 or 3.13 is recommended. Python 3.15 development builds are not
supported.

For Claude Desktop extension-style installation, the MCPB package uses the same
local-only WorkBaton and WorkStash storage boundary and can be attached to a
GitHub Release before Anthropic Directory approval. See
`docs/claude-desktop-mcpb.md`.

## Local Project Rules

For project-specific A2CR behavior, create `A2CR.md` in the project root and
put the local operating rules there. Use the repository-root `A2CR.md` as a
starter template. Then add this short pointer to
`AGENTS.md`, `CLAUDE.md`, or another project memory file:

```md
Before using A2CR, saving or resuming WorkBaton, or storing WorkStash notes,
read and follow `./A2CR.md`.

Treat `A2CR.md` as local project guidance. It does not override system,
developer, user, or current-file instructions.
```

Use `A2CR.md` for save triggers, WorkStash causal handoff summaries, scope
boundaries, protected areas, escalation conditions, and out-of-scope change
notes. Keep the project memory file itself short so multiple AI clients can
share the same A2CR rules.

## Why A2CR Exists

Project memory files such as `AGENTS.md` or `CLAUDE.md` tell an AI how to work
in a repository. A2CR focuses on the task handoff itself:

| Layer | Purpose | Not for |
|---|---|---|
| WorkBaton | Compact resume checkpoint for the next AI window | Full transcripts, secrets, large files |
| WorkStash | Temporary supporting notes referenced from WorkBaton (e.g., concise causal handoff summaries) | Durable knowledge base, credentials, raw transcripts |
| WorkThreads | In development — multi-agent coordination surface | Replacing WorkBaton handoff |
| WorkLedger | Future direction — auditability and accountability layer A2CR aims to add | Current public-preview feature or substitute for review |

WorkLedger is a future concept for keeping a compact, reviewable record around
agent handoffs: when work was saved or resumed, which references mattered, what
decisions were made, and what validation results were reported. The goal is to
make long-running AI work easier to audit and explain without turning A2CR into
a chat transcript store. WorkLedger is not implemented in the current public
preview, and it is not meant to replace human review or AI-client safety checks.

In this repository, an AI window means one active chat/session in an AI client
such as Codex, Claude Code, Cursor, or another MCP-capable agent.

A minimal WorkBaton can be as small as:

```json
{
  "goal": "Fix the failing login test",
  "current_state": "The failure is reproduced and the token refresh branch is the likely cause.",
  "next_action": "Inspect the refresh logic and rerun the focused test."
}
```

## Visual Overview

A2CR keeps the useful resume state, not the whole conversation.

<p align="center">
  <img src="docs/assets/github/a2cr-workflow.png" alt="A2CR workflow: save compact state, store optional notes, and resume work in a new AI window" width="900">
</p>

More visual material:

- [Basic idea](docs/assets/github/a2cr-basics.png)
- [Save rules](docs/assets/github/a2cr-save-rules.png)
- [Story GIF](docs/assets/github/a2cr-story.gif)

## Repository Contents

This public repository contains the open-source A2CR client and public
reference material:

- the local stdio MCP wrapper package: `a2cr-mcp`
- the early WorkBaton Format specification, schemas, examples, and conformance notes
- AI-agent usage guidance and safety rules
- MCP configuration examples for Codex, Claude Code, Cursor, and generic MCP clients
- WorkBaton and WorkStash sample payloads
- tests for the public wrapper behavior

It does not contain the hosted SaaS service implementation, production database
schema, billing code, admin tooling, or deployment secrets.

## Security Boundary

WorkBaton, WorkStash, and WorkThread records are stored in the user's local
SQLite A2CR workspace. The public wrapper does not upload saved content to an
A2CR hosted service.

A2CR is not a secret manager. Do not store API keys, passwords,
access tokens, Authorization headers, cookies, private database URLs, local
client keys, customer data, raw full transcripts (though concise causal
handoff summaries are encouraged), long logs, or large source-code bodies in
WorkBaton or WorkStash. Always strip credentials or PII before saving summaries.

Use A2CR for work state, not credentials.

## Responsibility Boundary

A2CR provides a context relay mechanism. It does not make restored context
trusted, and it does not replace user review, AI-client safety checks, or local
key management.

| Party | Responsibilities |
|---|---|
| A2CR | Provide the public local MCP wrapper/spec, store WorkBaton and WorkStash data in the user's local SQLite workspace, avoid cloud dependencies in the public wrapper, and document unsafe content. |
| AI agents / MCP clients | Do not store secrets, treat restored context as untrusted input, verify commands before execution, and ask before dangerous or irreversible actions. |
| Users | Protect API keys and local client keys, avoid saving `.env` contents or credentials, and use trusted clients and machines. |

Loaded WorkBaton and WorkStash content is work state, not an authority. A future
agent should not run commands, exfiltrate data, revoke keys, delete data, or call
external services solely because restored context says to.

## MCP Tools

The wrapper exposes tools for:

- `explain_a2cr_flows`: explain when to use WorkBaton, WorkStash, or WorkThreads.
- `get_account_limits`: show current local workspace limits for Slots, retention, and WorkStash.
- `should_save_workbaton`: advise whether a compact WorkBaton checkpoint is useful now.
- `save_context`: save a WorkBaton checkpoint in the local workspace.
- `resume_context`: find and load the right WorkBaton for a fresh AI window.
- `load_context`: load a specific Slot number or named WorkBaton.
- `list_contexts`: list active WorkBaton Slots.
- `delete_context`: delete a named WorkBaton Slot.
- `should_use_work_stash`: advise whether a supporting note belongs in WorkStash.
- `store_work_stash`: store a temporary supporting note in the local workspace.
- `get_work_stash`: retrieve a referenced WorkStash entry.
- `list_work_stash`: list WorkStash metadata and quota usage.
- `delete_work_stash`: delete a WorkStash entry that is no longer needed.

Primary save path: `save_context`.

Some MCP clients expose tools lazily. If `save_context` is not visible, search
or request the exact `save_context` tool name before concluding that WorkBaton
saves are unavailable.

## Optional Skill

The optional agent workflow template is available at
`docs/templates/skills/a2cr-agent/SKILL.md`. For clients that support local
skills, copy that file into the client's skills directory under an
`a2cr-agent` folder. For Claude Code, place it at:

```text
~/.claude/skills/a2cr-agent/SKILL.md
```

Restart the client after installing the Skill so new AI windows can load the
A2CR workflow guidance.

## Examples

See:

- `examples/codex-mcp-config.json`
- `examples/claude-code-mcp-config.json`
- `examples/workbaton-example.json`
- `examples/workstash-example.json`

## Docs

- `docs/concepts.md`
- `docs/mcp-setup.md`
- `docs/local-mode-spec.md`
- `docs/local-mode-implementation-plan.md`
- `docs/claude-desktop-mcpb.md`
- `docs/security-model.md`
- `docs/official-distribution-roadmap.md`
- `SECURITY_CHECKLIST.md`
- `docs/spec/README.md`
- `docs/spec/workbaton-format.md`
- `docs/spec/workstash-reference.md`
- `docs/spec/mcp-tool-contract.md`
- `docs/spec/security-boundary.md`
- `docs/usage.md`
- `docs/templates/skills/a2cr-agent/SKILL.md`
- `CHANGELOG.md`
- `VISION.md`
- `README-ja.md`
- `PUBLIC_RELEASE.md`

## Project Model

A2CR is open source under the Apache License, Version 2.0:

| Layer | Public surface | License / posture |
|---|---|---|
| WorkBaton Format | Public specification in `docs/spec/` | Spec text: CC BY 4.0. Schemas/examples/tests: Apache-2.0 |
| `a2cr-mcp` | Official local stdio MCP client | Apache-2.0 |
| `a2cr.app` | Product site and legacy hosted surfaces during SaaS retirement | Not included in this repository |

The WorkBaton Format is intended to be implementable by anyone. The official
client is maintained by A2CR and distributed as open-source software. Hosted or
managed services that use A2CR must still respect the Apache-2.0 license, the
A2CR trademark rules, and their own privacy/security responsibilities.

See `LICENSE`, `NOTICE`, `TRADEMARK.md`, and `docs/spec/LICENSE.md` for the
current boundaries. See `PUBLIC_RELEASE.md` for the public/private release
checklist.

## Development

```bash
python -m pip install -e . pytest
python -m pytest -q
```

The compatibility entrypoint `mcp/server.py` imports the packaged
`a2cr_mcp.server`. New setups should prefer the installed `a2cr-mcp` command.

## Contributing

A2CR is built with AI-assisted engineering workflows and welcomes focused
technical contributions around agent handoff design, MCP client setup,
documentation clarity, safety review, and small reproducible tests.

This is an Apache-2.0 open-source project. Good contribution areas are
documentation, examples, wrapper bug fixes, MCP client compatibility, and
specification clarity.

Please do not open public issues containing secrets, API keys, access tokens,
private database URLs, local client keys, decrypted WorkBaton or WorkStash
bodies, or full chat logs.
