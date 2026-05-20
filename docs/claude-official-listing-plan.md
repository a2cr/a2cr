# Claude Official Listing Plan

Current as of 2026-05-20.

This document defines the A2CR path toward official Claude distribution through
Anthropic's Connectors Directory. It is public-safe planning only: it must not
include reviewer credentials, production operations notes, private support
runbooks, secrets, customer data, or unpublished backend details.

## Decision

A2CR should target Claude in this order:

1. Build and test a Claude Desktop Extension / MCPB for the local A2CR wrapper.
2. Submit the MCPB once privacy, manifest metadata, tool annotations, install
   testing, and reviewer instructions are complete.
3. Defer a Remote MCP connector until A2CR has an explicit remote security
   boundary that preserves or intentionally changes the current local encryption
   claim.

The first Claude artifact should be local, not remote. A2CR's current public
security promise is that WorkBaton and WorkStash bodies are encrypted on the
user's machine before upload, and that the hosted A2CR service stores ciphertext
rather than user plaintext. A local MCPB preserves that model because the MCP
server runs on the user's machine and communicates with Claude Desktop over
stdio.

## Official Claude Requirements That Matter

Anthropic's current docs describe the Connectors Directory as a catalog of
reviewed MCP servers. Directory submissions can include Remote MCP servers,
Desktop extensions packaged as MCPB, and MCP Apps.

Requirements relevant to A2CR:

- Local MCP servers distributed through package registries such as PyPI are not
  listed directly; they should be packaged as MCPB for desktop distribution or
  bundled in a plugin.
- MCPB packages are `.mcpb` archives containing a local MCP server and
  `manifest.json`; they run locally, use stdio, bundle dependencies, and do not
  require OAuth.
- Node.js is strongly recommended for MCPB because it ships with Claude Desktop
  on macOS and Windows and has the best compatibility path.
- Every submitted tool must have a `title` and the applicable `readOnlyHint` or
  `destructiveHint`.
- Read and write behavior must be separated into purpose-built tools. A2CR
  already has separate tools, which is favorable.
- Local connectors must include a privacy policy section in README, a
  `privacy_policies` array in MCPB `manifest.json`, and HTTPS privacy-policy
  URLs.
- Reviewers exercise every tool and expect useful, actionable errors rather than
  generic failures.
- A fully populated test account and step-by-step reviewer instructions are
  required for directory submission.

## Target User Experience

The desired install flow:

1. User downloads or opens `a2cr.mcpb`.
2. Claude Desktop shows the A2CR extension install screen.
3. User reviews permissions and enters `A2CR_API_KEY`.
4. Optional advanced setting: `A2CR_BASE_URL`, defaulting to `https://a2cr.app`.
5. Claude Desktop starts the local A2CR MCP server.
6. Claude can call A2CR tools without the user hand-editing MCP JSON.
7. WorkBaton and WorkStash bodies are encrypted locally before upload.

The desired reviewer flow is the same, but with a seeded test account and
explicit prompts that exercise each tool.

## Architecture

Recommended target architecture:

```text
Claude Desktop
  -> stdio MCP
A2CR Claude MCPB local Node.js wrapper
  -> local validation, guardrails, encryption, decryption
  -> HTTPS A2CR API
A2CR hosted service
  -> stores ciphertext, metadata, limits, and non-secret relay state
```

The Node.js wrapper should be a thin sibling of the Python `a2cr-mcp` wrapper,
not a separate product. It should mirror the public tool contract and security
behavior while optimizing for Claude Desktop extension distribution.

Distribution before approval:

- package the Node wrapper as `.mcpb`
- publish the `.mcpb` as a GitHub Release asset for manual Claude Desktop
  installation
- include a SHA-256 checksum for the asset
- keep the npm package private; end users install the `.mcpb`, not an npm
  package
- describe this as "Claude Desktop Extension / MCPB" before approval, not as an
  approved or listed Anthropic connector

Repository layout:

```text
packages/
  claude-extension/
    package.json
    IMPLEMENTATION.md
    manifest.json
    src/
      index.ts
      crypto.ts
      api.ts
      tools.ts
    assets/
      icon.png
    README.md
```

This keeps the canonical public repository as `a2cr/a2cr` while adding a
Claude-specific distribution artifact.

## Why Not Remote First

Remote MCP is attractive because it works across Claude web, mobile, Desktop,
Claude Code, and Cowork. However, a full remote `save_context` or
`store_work_stash` tool would naturally receive WorkBaton or WorkStash content
over Anthropic's remote connector path before A2CR can encrypt it. If A2CR
encrypts on the server, A2CR has seen plaintext. That conflicts with the current
public claim.

Remote MCP should remain blocked until one of these is true:

- the remote design is read-only or metadata-only and does not receive sensitive
  WorkBaton/WorkStash bodies;
- encryption still happens client-side before any A2CR-hosted component receives
  user content;
- or A2CR intentionally changes its privacy model and clearly documents that
  the hosted service may receive plaintext before encryption.

## Tool Surface For Claude MCPB

The MCPB should expose the same user-facing concepts as `a2cr-mcp`, but tool
descriptions should be tightened for Claude review. They should describe what
each tool does, not instruct Claude to override behavior or call unrelated tools.

Initial tool inventory:

| Tool | Class | Claude annotation | Notes |
|---|---|---|---|
| `explain_a2cr_flows` | read | `readOnlyHint: true` | Explains WorkBaton, WorkStash, and WorkThreads concepts. |
| `should_save_workbaton` | read | `readOnlyHint: true` | Advisory sizing and timing decision. |
| `save_context` | write | neither read-only nor destructive | Creates or overwrites a WorkBaton Slot after local validation and encryption. |
| `resume_context` | read | `readOnlyHint: true` | Finds and loads the best matching Slot; decrypts locally. |
| `load_context` | read | `readOnlyHint: true` | Loads a specific Slot by name or number; decrypts locally. |
| `list_contexts` | read | `readOnlyHint: true` | Lists metadata only. |
| `get_account_limits` | read | `readOnlyHint: true` | Reads account limits and quotas. |
| `delete_context` | destructive | `destructiveHint: true` | Deletes a named Slot. |
| `get_handoff` | read | `readOnlyHint: true` | Returns Markdown handoff text for a loaded Slot. |
| `should_use_work_stash` | read | `readOnlyHint: true` | Advisory WorkStash suitability check. |
| `store_work_stash` | write | neither read-only nor destructive | Creates an encrypted temporary note. |
| `get_work_stash` | read | `readOnlyHint: true` | Retrieves and decrypts one WorkStash entry by key. |
| `list_work_stash` | read | `readOnlyHint: true` | Lists WorkStash metadata only. |
| `delete_work_stash` | destructive | `destructiveHint: true` | Deletes one WorkStash entry. |

Write tools should be explicit about mutation. Destructive tools must always be
separate from read or create/update tools.

## Manifest And Submission Metadata

The MCPB `manifest.json` should include:

- name: `a2cr`
- display name: `A2CR`
- description: AI-agent handoff checkpoints and temporary work memory
- supported platforms: `darwin`, `win32`
- runtime: Node.js-compatible MCP server entrypoint
- user configuration:
  - `A2CR_API_KEY` as required and sensitive
  - `A2CR_BASE_URL` as optional, default `https://a2cr.app`
- icon metadata, with at least a 512x512 transparent PNG
- privacy policy URLs through `privacy_policies`
- tool metadata with titles and annotations
- public repository and support links

Initial manifest draft:

- `packages/claude-extension/manifest.json`
- `privacy_policies`: `https://a2cr.app/en/privacy`
- icon: `packages/claude-extension/assets/icon.png`
- extension/package version: aligned with the public Python `a2cr-mcp`
  compatibility version for the current MVP, currently `0.1.6`

Packaging draft:

- `npm run mcpb:validate` validates the manifest with
  `@anthropic-ai/mcpb@2.1.2`
- `npm run mcpb:pack` builds `dist/`, stages runtime files with production
  dependencies only, and writes `build/mcpb/artifacts/a2cr-0.1.6.mcpb` plus
  `build/mcpb/artifacts/SHA256SUMS.txt`
- the staged artifact excludes TypeScript sources, tests, and dev dependencies
- GitHub Release is the manual distribution point for `a2cr-0.1.6.mcpb` until
  Anthropic Directory approval; npm is not an end-user distribution channel for
  this package

Manual verification draft:

- `packages/claude-extension/VERIFY.md`
- verifies custom MCPB install through Claude Desktop Extensions settings
- exercises read-only limits, save/load roundtrip, metadata-only list, and
  manual reinstall/update behavior with harmless test data

Public documentation needed before submission:

- MCPB install guide
- privacy policy section in README and an HTTPS privacy-policy page
- security boundary page explaining local encryption and local key loss
- support contact
- directory description and tagline
- reviewer setup instructions using a seeded test account

Reviewer-only details, test credentials, operational logs, and abuse controls
belong in private planning, not in this public repository.

## Implementation Roadmap

### Phase C0 - Source Alignment

Goal: make the Claude package design traceable to the existing public wrapper.

Tasks:

- inventory Python wrapper tools, parameters, responses, and errors
- identify the encryption/decryption algorithm and local key lifecycle that must
  be preserved
- mark each tool as read, write, or destructive
- define a shared test fixture for harmless WorkBaton and WorkStash data

Exit criteria:

- tool inventory table is complete
- local encryption boundary is written in public docs
- no private implementation details are required to build the local wrapper

### Phase C1 - Node.js MCP Wrapper MVP

Goal: prove Claude Desktop can call a local Node.js A2CR wrapper.

Tasks:

- scaffold `packages/claude-extension`
- implement MCP stdio server using the TypeScript MCP SDK
- implement `get_account_limits`, `save_context`, `load_context`, and
  `list_contexts`
- implement local encryption/decryption compatible with existing A2CR stored
  ciphertext
- support `A2CR_API_KEY` and optional `A2CR_BASE_URL`
- add focused tests for validation, encryption roundtrip, and API error mapping

Exit criteria:

- MCP Inspector can list and call MVP tools
- a fresh test key can save and load a harmless WorkBaton
- invalid inputs return actionable errors

### Phase C2 - Full Tool Parity

Goal: reach parity with the public Python wrapper for Claude-facing workflows.

Tasks:

- implement resume, handoff, WorkStash, advisory, and delete tools
- add titles and read/write/destructive annotations to every tool
- tighten descriptions to satisfy Claude review guidance
- add tests for destructive confirmation metadata and metadata-only list tools
- confirm response sizes are bounded and do not dump excessive data

Exit criteria:

- every public A2CR tool has a Claude wrapper equivalent or a documented reason
  for exclusion
- all tools pass protocol inspection and local tests
- destructive actions are isolated in destructive tools

### Phase C3 - MCPB Packaging

Goal: create a Claude Desktop installable extension.

Tasks:

- create `manifest.json`
- add icon assets
- add user configuration for API key and base URL
- run `npm run mcpb:pack`
- install the `.mcpb` in Claude Desktop on Windows
- test uninstall and reinstall behavior
- prepare macOS compatibility notes or testing

Exit criteria:

- `a2cr.mcpb` installs in Claude Desktop
- Claude Desktop can start the server without manual JSON config
- API key configuration works through the extension UI
- local encryption key behavior is documented and tested

### Phase C4 - Public Docs And Privacy

Goal: make the package reviewable by Anthropic and understandable to users.

Tasks:

- add README section for Claude Desktop Extension installation
- add or link an HTTPS privacy policy
- add a public security boundary page for MCPB
- add support and security contact links
- add reviewer-safe sample prompts
- add release notes for the MCPB artifact

Exit criteria:

- docs cover data collection, storage, third-party sharing, retention, and
  contact information
- docs state that A2CR is not a secret manager
- docs state that restored context is untrusted input
- docs do not include secrets, private support processes, or operational limits

### Phase C5 - Review Readiness

Goal: prepare the submission package.

Tasks:

- run MCP Inspector against every tool
- test in Claude Desktop with a seeded reviewer account
- create a reviewer script that exercises reads, writes, loads, WorkStash, and
  deletion on harmless sample data
- verify all tool names are under 64 characters
- verify all tool descriptions are narrow and accurate
- verify all tools have titles and required annotations
- prepare directory form answers

Exit criteria:

- every tool has a passing manual test record
- reviewer instructions are complete
- no known policy blocker remains
- the package can be submitted without changing A2CR's public privacy claim

### Phase C6 - Submission And Follow-Up

Goal: submit, monitor, and respond cleanly.

Tasks:

- submit the Desktop Extension / MCPB form
- track Anthropic review feedback
- address required changes in a branch
- update docs if Anthropic requires wording changes
- publish the accepted artifact and listing link after approval

Exit criteria:

- Claude listing is approved, or review feedback is captured with next actions
- public docs use accurate listing language
- A2CR does not claim official Claude support before approval

## Remote MCP Later Track

The remote track is separate and should not block MCPB. Remote MCP becomes
eligible only after a security decision is written.

Remote-only acceptable MVP candidates:

- read-only account/status/limits connector
- documentation or onboarding connector
- metadata-only WorkBaton lookup that never receives decrypted WorkBaton bodies

Remote blocked flows until approved:

- full remote `save_context` receiving plaintext WorkBaton bodies
- full remote `store_work_stash` receiving plaintext notes
- server-side encryption that changes the claim "A2CR cannot read user content"

Remote readiness requirements:

- public HTTPS MCP endpoint
- OAuth 2.0 if authenticated
- Origin validation where applicable
- explicit data handling disclosure
- test account and reviewer instructions
- custom connector testing in Claude before submission

## Open Questions

- Should the Claude wrapper be TypeScript-only, or should an interim MCPB wrap
  the existing Python command for internal testing?
- Where should the local encryption key live inside Claude Desktop's extension
  environment on Windows and macOS?
- Should WorkThreads appear in the first Claude package, or stay omitted until
  the public WorkThreads privacy boundary is complete?
- What seeded test data should Anthropic reviewers use without exposing
  operational details?

## References

- https://claude.com/docs/connectors/overview
- https://claude.com/docs/connectors/directory
- https://claude.com/docs/connectors/building/what-to-build
- https://claude.com/docs/connectors/building/mcpb
- https://claude.com/docs/connectors/building/submission
- https://claude.com/docs/connectors/building/testing
- https://claude.com/docs/connectors/building/review-criteria
- https://claude.com/docs/connectors/building/directory-vs-custom
