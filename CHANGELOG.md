# Changelog

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
