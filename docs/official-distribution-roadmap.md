# Official Distribution Roadmap

This roadmap records how A2CR should approach official MCP-related
distribution channels after the first public release.

It is intentionally separate from `server.json`. The current public artifact is
the local stdio wrapper `a2cr-mcp`; Claude and OpenAI directory submissions need
different packaging and security decisions.

## Decision Summary

A2CR should use this order:

1. Publish the public repository, PyPI package, and official MCP Registry entry.
2. Prepare a Claude Desktop Extension / MCPB package for the local wrapper.
3. Design an OpenAI Apps SDK app only after the remote MCP security model is
   explicit.
4. Consider a Claude Remote MCP submission after the same remote security model
   is ready.

The first official listing target is the neutral MCP Registry entry
`io.github.a2cr/a2cr-mcp`. Claude and OpenAI should not block the initial public
release.

## Why The Order Matters

The current A2CR wrapper encrypts WorkBaton and WorkStash bodies locally before
upload. A2CR stores ciphertext and does not receive the local client key.

Remote MCP directory submissions change that boundary. If a remote MCP server
receives plaintext WorkBaton content in a tool call and then encrypts it on the
server, A2CR has received plaintext. That is a different privacy model.

For that reason:

- local distribution channels come first
- remote distribution channels require a written security decision
- any remote app must clearly disclose what the hosted service can see
- full `save_context` / `store_work_stash` remote flows should not be submitted
  until the plaintext boundary is acceptable or avoided

## Roadmap

| Phase | Target | Artifact | Status | Exit criteria |
|---|---|---|---|---|
| P0 | Public release | `a2cr/a2cr`, `a2cr-mcp==0.1.5`, docs, examples | Prepared | Public repo is pushed, tests pass, package builds, PyPI release is live. |
| P1 | Official MCP Registry | `server.json` for `io.github.a2cr/a2cr-mcp` | Ready after PyPI | Registry dry run passes, publish succeeds, search result is visible. |
| P2 | Claude local distribution | Claude Desktop Extension / MCPB wrapping `a2cr-mcp` | Next | Local encryption is preserved, manifest includes privacy policy links, setup is tested in Claude Desktop, submission assets are ready. |
| P3 | OpenAI app distribution | Apps SDK remote MCP app or narrower read-only companion | Later | Public HTTPS remote MCP exists, Developer Mode testing passes, OAuth/privacy/test prompts/assets are ready, plaintext boundary is approved. |
| P4 | Claude remote distribution | Remote MCP connector or MCP App | Later | Remote OAuth, tool annotations, Origin validation, test account, privacy docs, and hosted-service scaling are ready. |

## Channel Design

### Official MCP Registry

Use the current local stdio package.

- Registry name: `io.github.a2cr/a2cr-mcp`
- Package: PyPI `a2cr-mcp`
- Transport: `stdio`
- Manifest: `server.json`
- Submission note: publish to PyPI before publishing registry metadata, because
  PyPI ownership verification uses the README `mcp-name` marker.

This is the correct first public listing because it matches the current
artifact and does not require changing the local encryption model.

### Claude

Claude has two useful paths for A2CR:

1. Claude Desktop Extension / MCPB for the local stdio wrapper.
2. Remote MCP connector later, if the hosted-service privacy boundary is
   intentionally changed or a client-side encryption design is added.

The local path is first because it preserves the current A2CR security model.
Do not try to submit the raw PyPI stdio package directly to the Claude
Connectors Directory. Claude's current docs say local MCP servers distributed
through registries such as PyPI are not listed directly; local distribution
should be packaged as MCPB or a plugin.

Claude MCPB readiness checklist:

- package the existing `a2cr-mcp` stdio command as a Desktop Extension
- include a manifest with privacy policy URLs
- provide human-readable tool names
- annotate tools with read/write/destructive hints where supported
- verify install, update, and uninstall on Claude Desktop
- prepare logo, favicon, public documentation, and support contact
- prepare a reviewer setup path that uses a test account with no production
  secrets

Remote Claude connector readiness checklist:

- expose a public HTTPS remote MCP endpoint
- support OAuth 2.0 for user authentication
- validate `Origin` headers where applicable
- document exactly what data leaves Claude and what A2CR stores
- provide tool annotations for read-only and destructive behavior
- provide a test account and step-by-step reviewer instructions

### OpenAI

The current `a2cr-mcp` local stdio package is not the right artifact for OpenAI
public distribution. OpenAI's current public path is an Apps SDK app backed by a
remote MCP server, submitted through the dashboard-based review flow. When an
approved app is published, OpenAI can create a Codex plugin distribution from
that app.

OpenAI should therefore be a later phase.

Preferred OpenAI design options:

1. Read-only companion app first: expose safe discovery, documentation, status,
   account limits, or read-only WorkBaton lookup patterns. This reduces write
   risk but does not fully replace the local wrapper.
2. Full A2CR handoff app later: expose save, resume, WorkStash, and delete
   flows only after OAuth, consent, tool hints, review UX, and plaintext
   handling are designed.

OpenAI readiness checklist:

- build a public HTTPS remote MCP server, not a local stdio server
- test the app in ChatGPT Developer Mode
- decide whether the app is read-only or can mutate A2CR state
- if authenticated, use OAuth-compatible authentication
- provide app metadata, privacy policy, support contact, icon/logo, screenshots,
  and test prompts
- mark tool behavior accurately, especially write and destructive actions
- document the prompt-injection and data-sharing risks for restored context
- confirm that the app's privacy model still matches A2CR's public security
  claims before submission

## Remote Security Gate

Before any OpenAI or Claude remote submission, answer these questions in a
public-safe design note:

- Does the remote MCP server ever receive plaintext WorkBaton or WorkStash
  bodies?
- If yes, is the public privacy policy updated to say so?
- If no, where does encryption happen before the hosted service receives data?
- Can users delete remote data and revoke access?
- Which tools are read-only, which mutate state, and which can delete data?
- What reviewer test account and seeded data will be used?
- What rate limits and abuse controls protect the hosted service?

Until those answers are written, remote directory submissions should remain
blocked.

## Public Assets To Prepare

- public product page for A2CR
- privacy policy and security page
- support contact
- logo and favicon assets
- short tagline and longer directory description
- screenshots or app response images where required
- reviewer test account with disposable data
- release notes for the first public version
- public docs for install, setup, local key behavior, and safe usage

## Non-Goals For The Initial Public Release

- No private SaaS backend source release.
- No dashboard, billing, database, Supabase, Railway, or operations release.
- No remote OpenAI or Claude directory submission that changes A2CR's privacy
  boundary without explicit documentation.
- No public examples containing real API keys, local client keys, database URLs,
  WorkBaton bodies from real users, or access logs.

## References

- https://modelcontextprotocol.io/registry/quickstart
- https://modelcontextprotocol.io/registry/package-types
- https://modelcontextprotocol.io/registry/authentication
- https://claude.com/docs/connectors/overview
- https://claude.com/docs/connectors/directory
- https://claude.com/docs/connectors/building/submission
- https://developers.openai.com/api/docs/mcp
- https://developers.openai.com/apps-sdk/
- https://developers.openai.com/apps-sdk/deploy/submission
