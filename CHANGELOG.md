# Changelog

## 0.1.8 - Public Metadata Refresh

- Refresh PyPI package metadata from the Apache-2.0 local-only public repository
  so downstream MCP directories stop inheriting older BUSL, Roo Code, hosted
  service, and API-key wording from the `0.1.7` PyPI description.
- Keep the official MCP Registry manifest, Python package, and Claude Desktop
  MCPB compatibility version aligned on `0.1.8`.
- Include the project-centered dashboard baseline and Dependabot dependency
  updates that landed after the `0.1.7` local-only release.

## 0.1.7 - Local-Only Workspace And Claude MCPB

- Publish `0.1.7` as the local-only public release, with release scope,
  expected artifacts, publish gates, and GitHub Release notes recorded in
  `docs/releases/v0.1.7-local-only-release-candidate.md`.
- Switch the public release line to local-only A2CR: no account, API key,
  hosted base URL, SaaS dashboard, remote MCP connector, or cloud sync is
  required for the public wrapper.
- Add local A2CR workspace support for WorkBaton, WorkStash, WorkThreads,
  search, CLI diagnostics, Codex local config generation, and a loopback
  browser UI behind the dedicated `a2cr-local-mcp` command.
- Add dedicated command entrypoints for `a2cr`, `a2cr-local-mcp`, and the
  compatibility `a2cr-mcp` path.
- Associate local WorkStash entries with project metadata so supporting notes
  can be searched and reviewed alongside related WorkBaton records.
- Add Claude Desktop MCPB local runtime support for WorkBaton and WorkStash,
  including local encryption, local storage, reviewer smoke prompts, and
  GitHub Release publishing guidance.
- Add local-mode tests and package smoke coverage for save, resume, WorkStash,
  search, WorkThreads, CLI doctor/init, and wheel installation.

- Record that `io.github.a2cr/a2cr-mcp` is published in the official MCP
  Registry with `0.1.7` as the latest active version.
- Document the two local MCP distribution paths: Python `a2cr-mcp` from PyPI
  and Node Claude Desktop MCPB from GitHub Release assets.
- Add Claude Desktop MCPB build, checksum, install, and wording guidance.
- Add Claude Directory submission notes, MCPB README privacy/reviewer guidance,
  and runtime tool annotation checks for the Claude Desktop MCPB.
- Clarify that the Node package is not an npm end-user distribution channel and
  must keep its compatibility version aligned with the Python wrapper.

## 0.1.6 - Causal Handoff Guidance

- Add local `A2CR.md` guidance for WorkBaton, WorkStash, causal handoff
  summaries, scope boundaries, protected areas, and escalation conditions.
- Align `AGENTS.md`, `CLAUDE.md`, and the reusable agent skill template around
  the `A2CR.md` local-rules pattern.
- Update MCP tool guidance so agents can store concise causal handoff summaries
  in WorkStash while keeping raw full transcripts, secrets, personal data, long
  logs, git diffs, generated caches, and large code bodies out of A2CR.
- Clarify that out-of-scope edits are not absolutely forbidden, but must satisfy
  explicit escalation conditions and be recorded with rationale.

## 0.1.5 - Public Preview Candidate

- Publish the `a2cr-mcp` local stdio wrapper package for WorkBaton and
  WorkStash handoff workflows.
- Add client-side encryption for WorkBaton and WorkStash bodies before upload
  through the official wrapper.
- Document the public WorkBaton Format, WorkStash reference, MCP tool contract,
  security boundary, and conformance notes.
- Add MCP setup examples for Codex-style TOML and JSON MCP clients.
- Add public repository safety checks that keep private SaaS service code,
  database material, billing, dashboard, operations, and deployment artifacts
  out of the distribution repository.
- Add guardrails that reject file-like payloads and credential-shaped content
  before WorkBaton saves are encrypted or posted.
- Clarify Public Preview launch criteria and the boundary between public
  wrapper/spec material and proprietary hosted service implementation.
