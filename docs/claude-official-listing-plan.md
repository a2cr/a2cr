# Claude Official Listing Plan

Current as of 2026-06-24.

This document defines the A2CR path toward official Claude distribution through
Anthropic's Connectors Directory. It is public-safe planning only: it must not
include reviewer credentials, private support runbooks, secrets, customer data,
or unpublished backend details.

## Decision

A2CR should target Claude with a local Desktop Extension / MCPB distributed from
GitHub Releases and, after approval, the Anthropic Connectors Directory.

The submitted artifact should be named and described as A2CR, not as a separate
"A2CR Local" product. The product boundary is local-only:

- no A2CR account;
- no API key;
- no hosted base URL;
- no SaaS dashboard;
- no remote MCP connector;
- no upload of saved WorkBaton or WorkStash content.

The earlier SaaS/hosted relay path is being retired from the public
distribution and should not appear in reviewer setup instructions.

## Requirements That Matter

Anthropic's current MCPB path expects a local MCP server packaged as a `.mcpb`
archive with a valid `manifest.json`.

Requirements relevant to A2CR:

- The MCPB runs locally and communicates with Claude Desktop over stdio.
- Node.js is the preferred runtime because Claude Desktop supplies it on macOS
  and Windows.
- Every submitted tool must have a title and accurate annotations.
- Local tools that do not call external services should set `openWorldHint:
  false`.
- Read, write, and destructive behavior should be separated into clear tools.
- The manifest should include support, repository, icon, and privacy-policy
  metadata.
- Reviewers must be able to exercise every tool with harmless sample data and no
  credentials.

## Target User Experience

The desired install flow:

1. User downloads `a2cr-<version>.mcpb` from a GitHub Release or installs it
   from the Directory after approval.
2. Claude Desktop shows the A2CR extension install screen.
3. User reviews permissions and completes the install.
4. Claude Desktop starts the local A2CR MCP server.
5. Claude can call A2CR tools without hand-editing MCP JSON.
6. WorkBaton data is validated, encrypted, saved, listed, loaded, and decrypted
   locally.

No reviewer test account is required for the local-only MCPB. Reviewer
instructions should provide a disposable Slot name and harmless WorkBaton JSON.

## Architecture

Recommended target architecture:

```text
Claude Desktop
  -> stdio MCP
A2CR Claude MCPB local Node.js wrapper
  -> local validation, guardrails, encryption, decryption
  -> local MCPB store file
```

The Node.js wrapper should be a thin sibling of the Python `a2cr-mcp` wrapper,
not a separate product. It should mirror the public tool contract while
optimizing for Claude Desktop extension distribution.

Distribution before approval:

- package the Node wrapper as `.mcpb`;
- publish the `.mcpb` as a GitHub Release asset for manual Claude Desktop
  installation;
- include a SHA-256 checksum for the asset;
- keep the npm package private; end users install the `.mcpb`, not an npm
  package;
- describe this as "Claude Desktop Extension / MCPB" before approval, not as an
  approved or listed Anthropic connector.

## Tool Surface For Claude MCPB

Initial submission inventory:

| Tool | Class | Claude annotation | Notes |
|---|---|---|---|
| `get_account_limits` | read | `readOnlyHint: true`, `openWorldHint: false` | Returns local storage metadata and limits. |
| `list_contexts` | read | `readOnlyHint: true`, `openWorldHint: false` | Lists Slot metadata only. |
| `save_context` | write | `readOnlyHint: false`, `destructiveHint: true`, `openWorldHint: false` | Creates or overwrites a WorkBaton Slot after local validation and encryption. |
| `load_context` | read | `readOnlyHint: true`, `openWorldHint: false` | Loads a Slot by name or number and decrypts locally. |
| `store_work_stash` | write | `readOnlyHint: false`, `destructiveHint: true`, `openWorldHint: false` | Encrypts and stores a temporary supporting note in the local store. It can overwrite an existing entry key. |
| `get_work_stash` | read | `readOnlyHint: true`, `openWorldHint: false` | Loads one referenced WorkStash entry and decrypts locally. |
| `list_work_stash` | read | `readOnlyHint: true`, `openWorldHint: false` | Lists WorkStash metadata only. Stored values are not returned. |
| `delete_work_stash` | destructive | `readOnlyHint: false`, `destructiveHint: true`, `openWorldHint: false` | Deletes one local WorkStash entry. |

Future parity work can add advisory, resume, handoff, WorkThreads, and
WorkBaton delete tools, but each tool must preserve the local-only storage
boundary unless a new public design decision changes it.

## Manifest And Submission Metadata

The MCPB `manifest.json` should include:

- name: `a2cr`
- display name: `A2CR`
- description: local AI-agent handoff checkpoints and temporary work memory
- supported platforms: `darwin`, `win32`
- runtime: Node.js-compatible MCP server entrypoint
- user configuration: none required for the local-only submission
- icon metadata, with at least a 512x512 transparent PNG
- privacy-policy URL through `privacy_policies`
- tool metadata with titles and annotations
- public repository and support links

Initial manifest:

- `packages/claude-extension/manifest.json`
- icon: `packages/claude-extension/assets/icon.png`
- extension/package version: aligned with the public Python `a2cr-mcp`
  compatibility version for the current submission, currently `0.1.7`

Packaging:

- `npm run mcpb:validate` validates the manifest with
  `@anthropic-ai/mcpb@2.1.2`
- `npm run mcpb:pack` builds `dist/`, stages runtime files with production
  dependencies only, and writes `build/mcpb/artifacts/a2cr-0.1.7.mcpb` plus
  `build/mcpb/artifacts/SHA256SUMS.txt`
- the staged artifact excludes TypeScript sources, tests, and dev dependencies
- GitHub Release is the manual distribution point for `a2cr-0.1.7.mcpb` until
  Anthropic Directory approval; npm is not an end-user distribution channel for
  this package

Manual verification:

- `packages/claude-extension/VERIFY.md`
- verifies custom MCPB install through Claude Desktop Extensions settings
- exercises read-only limits, save/load roundtrip, metadata-only list, and
  manual reinstall/update behavior with harmless local data

## Release And Review Checklist

Before submission:

- run `npm test`
- run `npm run typecheck`
- run `npm run mcpb:validate`
- run `npm run mcpb:pack`
- inspect the packaged `manifest.json`, `README.md`, and `dist/tools.js`
- confirm no API key or hosted URL configuration appears in install flow
- confirm all tools set `openWorldHint: false`
- confirm reviewer instructions require no seeded account or secret

When publishing:

- publish the matching Python package to PyPI if the version changes;
- publish/update MCP Registry metadata after the PyPI package exists;
- attach `a2cr-<version>.mcpb` and `SHA256SUMS.txt` to the same GitHub Release;
- send Anthropic the owner/repo, release tag pattern, artifact filename, and
  maintainer contact requested for automated release pickup.

Automated pickup details for the `0.1.7` submission:

- `owner/repo`: `a2cr/a2cr`
- tag pattern: `v*` (example: `v0.1.7`)
- asset filename: `a2cr-<version>.mcpb`
- checksum filename: `SHA256SUMS.txt`
- maintainer contact: fill in the human contact before sending to Anthropic

This submission uses one cross-platform Node MCPB bundle rather than separate
per-platform assets.

## Remote MCP Later Track

Remote MCP is not part of this submission. A future remote connector would need
a new public privacy and storage decision. Until that exists, the Directory path
is the local MCPB only.

## Open Questions

- Should WorkThreads appear in the Claude package before Python/Node tool parity
  is complete?
- Should the MCPB eventually share the Python SQLite database directly, or keep
  its local JSON store until the Claude package has full parity?
- What public privacy-policy URL should replace any legacy SaaS-oriented page if
  `a2cr.app` is fully retired?

## References

- https://claude.com/docs/connectors/overview
- https://claude.com/docs/connectors/directory
- https://claude.com/docs/connectors/building/what-to-build
- https://claude.com/docs/connectors/building/mcpb
- https://claude.com/docs/connectors/building/submission
- https://claude.com/docs/connectors/building/testing
- https://claude.com/docs/connectors/building/review-criteria
- https://claude.com/docs/connectors/building/directory-vs-custom
