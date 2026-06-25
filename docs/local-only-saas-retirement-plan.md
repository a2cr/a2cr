# A2CR Local-Only Transition And SaaS Retirement Plan

Status: active transition plan
Repository scope: `public-release/`
Decision date: 2026-06-24

## Product Decision

A2CR's public product is the local MCP workspace.

The public wrapper must work without:

- an A2CR account
- an A2CR API key
- `https://a2cr.app` as a save/load dependency
- hosted relay storage
- cloud sync

WorkBaton, WorkStash, WorkThreads, actors, and event history belong in the
user's local A2CR workspace database by default.

## Public Distribution Boundary

Public distribution should describe A2CR simply as `A2CR`, not as a separate
`A2CR Local` product. Local storage is the normal A2CR behavior.

The words `local-only` are useful in transition notes and reviewer explanations,
but should not become the product name.

## SaaS Retirement Scope

The public package must no longer steer new users to the SaaS path.

Retired public paths:

- API-key-required quickstarts
- `A2CR_BASE_URL=https://a2cr.app` setup examples
- `a2cr-cloud-mcp` as a new public console script
- MCP Registry metadata that requires `A2CR_API_KEY`
- Claude MCPB manifest settings for A2CR API key or base URL

Legacy/private hosted surfaces can remain outside `public-release/` during the
retirement window, but they are not part of the public A2CR install story.

## Anthropic Directory Position

The Anthropic Directory artifact should be the normal `A2CR` MCPB distributed
from GitHub Releases.

Reviewer-facing boundary:

- the MCPB stores saved WorkBaton content locally
- no A2CR hosted service is required for save/load/list
- no reviewer API key is required
- `openWorldHint` should be false for local tools that do not call external
  services

After the local MCPB is verified, send Anthropic:

- `owner/repo`: `a2cr/a2cr`
- tag pattern: `v*` (example: `v0.1.7`)
- asset filename pattern: `a2cr-<version>.mcpb`
- checksum filename: `SHA256SUMS.txt`
- maintainer contact, filled in immediately before sending to Anthropic

## Implementation Phases

1. Public Python wrapper defaults to local storage and exposes local setup only.
2. MCP Registry metadata no longer asks for API keys or hosted base URLs.
3. Claude MCPB no longer calls the hosted API and no longer requests sensitive
   hosted-service configuration.
4. Public README, setup docs, usage docs, security docs, and examples describe
   A2CR as local by default.
5. Legacy hosted/SaaS operational shutdown is handled from the private
   production repository, with no private-only material copied into
   `public-release/`.

## Verification Gates

- `a2cr doctor --target local` reports ready.
- Python local save/load/stash/search/thread tests pass without opening HTTP.
- MCP Registry metadata validates with only local environment variables.
- MCPB tests pass with a temporary local store file and no mock hosted API.
- Public docs contain no API-key-required setup path for new users.
