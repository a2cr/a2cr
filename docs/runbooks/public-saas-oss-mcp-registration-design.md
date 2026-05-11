# A2CR Public SaaS, OSS, And MCP/App Registration Design

Last updated: 2026-05-10

Status: Draft design / launch gate checklist

This design covers three related goals:

- publish WorkBaton and WorkStash as the first free public SaaS preview
- prepare a clean open-source GitHub repository for public cloning/forking
- prepare submissions or install paths for official MCP registries, Claude connectors/plugins, OpenAI Apps SDK, Cursor, and GitHub Copilot/VS Code

## Assumptions

- The first public release is free only. Paid checkout, Pro billing, and Lemon Squeezy are later work.
- The public product scope is WorkBaton plus WorkStash. WorkThreads remains hidden, internal, or clearly labeled as not part of the free preview.
- WorkBaton body content must stay client-encrypted before upload. The official save path remains the local stdio MCP wrapper.
- WorkStash should follow the same local-encryption boundary: A2CR stores encrypted values and metadata, not plaintext notes.
- Public copy must distinguish content encryption from SaaS metadata exposure. Do not claim broad zero-knowledge or full end-to-end encryption for the whole product.
- Official app directories generally require a hosted HTTPS remote MCP server, OAuth or an approved auth flow, public docs, privacy/support pages, review credentials, and functional tests.

## Current Repo Findings

The repository already has a strong SaaS foundation:

- FastAPI, React/Vite dashboard, Supabase/Postgres schema, RLS, API keys, access logs, and `/mcp` HTTP surface.
- Local stdio MCP wrapper published as PyPI package `a2cr-mcp`, with `mcp/server.py` retained as a development/compatibility entrypoint.
- Public-facing drafts in `README.md`, `docs/usage.md`, `docs/github-publication-draft.md`, and `docs/runbooks/saas-launch-roadmap.md`.
- CI, npm audit, pip-audit, and CodeQL workflows.

Launch blockers found during this design pass:

- WorkStash is documented and implemented in the local stdio wrapper, but this repo currently has no `public.work_stash` migration and no `/api/v1/work-stash` FastAPI router. That blocks a real WorkStash SaaS preview.
- Some public-facing Japanese copy is mojibake in `main.py`, `docs/usage.md`, `docs/runbooks/saas-launch-roadmap.md`, and `docs/superpowers/specs/2026-05-06-a2cr-operations-legal-admin-spec.md`.
- `LICENSE` is still missing.
- The local git state is not publication-ready: `main` is ahead of `origin/main` by 1 and behind by 10, with many modified and untracked files.
- Remote `/mcp` deliberately rejects `save_context` for WorkBaton. That is correct for security, but it means directory-style remote connectors cannot advertise full WorkBaton save/resume unless a client-side encryption UX is added.

## Public SaaS Release Design

### Scope

Ship as:

```text
Free public preview:
- WorkBaton: compact, client-encrypted checkpoint handoff
- WorkStash: temporary encrypted supporting notes referenced by WorkBaton
- Dashboard: metadata, API key management, setup guidance
- MCP: local stdio wrapper as the official WorkBaton/WorkStash path
```

Do not ship as:

```text
- paid SaaS
- WorkThreads public feature
- server-side AI orchestration
- file storage
- chat-log archive
- broad zero-knowledge service
```

### Required WorkStash Backend

Add `public.work_stash` before claiming WorkStash is available:

```text
public.work_stash
- id uuid primary key
- user_id uuid references auth.users(id) on delete cascade
- entry_key text, user-scoped unique, safe pattern and length limit
- encrypted_value text not null
- size_bytes integer not null
- tags text[] or jsonb not null default empty
- created_at timestamptz
- updated_at timestamptz
- expires_at timestamptz nullable or fixed preview TTL
```

Rules:

- RLS must require `user_id = app.current_user_id()`.
- API routes must be authenticated with API key or JWT.
- Total encrypted storage is the public quota: Free 256KB, future Pro 2048KB.
- Entry count may remain an internal abuse guard, but should not be the public promise.
- `list_work_stash` returns metadata only.
- `get_work_stash` returns encrypted value to the local stdio wrapper; only the wrapper decrypts locally.
- `store_work_stash` must reject plaintext-value API usage except from the local wrapper sending `encrypted_value`.
- WorkStash values must not be searchable or visible in dashboard/admin views.

### SaaS Gate Checklist

Release only after all are true:

- `python -m pytest -q` passes.
- `cd web && npm ci && npm run build` passes.
- Hosted `/api/v1/health` and `/api/v1/health/readiness` pass.
- Hosted RLS smoke proves user A cannot see user B data.
- WorkBaton save/load/resume works through local stdio against hosted API.
- WorkStash store/list/get/delete works through local stdio against hosted API.
- Dashboard never returns decrypted WorkBaton or WorkStash values.
- Production runtime does not include `SUPABASE_SERVICE_ROLE_KEY`.
- Logs do not expose API keys, Authorization headers, DB URLs, encrypted bodies, or plaintext bodies.
- Public docs explain local client key backup and unrecoverable old slots if the key is lost.
- Public Japanese/English pages have no mojibake.
- Support and security intake are reachable.

## OSS GitHub Publication Design

### Repository Shape

Target repository:

```text
owner/a2cr
description: Agent-to-Agent Context Relay: save and resume AI agent work context across windows, tools, and clients.
topics: ai-agents, mcp, fastapi, context-management, agent-workflow, python, saas
```

Recommended license:

- Apache-2.0 if patent protection and commercial reuse clarity matter.
- MIT if maximum simplicity matters.

For this project, Apache-2.0 is the safer default because A2CR is a protocol-adjacent MCP server/SaaS foundation.

### Public Files

Must include:

- `LICENSE`
- `README.md`
- `SECURITY.md`
- `CONTRIBUTING.md`
- `CODE_OF_CONDUCT.md`
- `.env.example`
- `.github/ISSUE_TEMPLATE/*`
- `.github/pull_request_template.md`
- CI workflows
- setup guide for local stdio MCP
- free preview limitations
- data/security boundary documentation

Keep private/internal or remove before public:

- personal notes
- local database files
- logs/caches
- private MCP configs
- real screenshots with user data
- internal legal planning that exposes private address, phone, or personal email
- mojibake documents that look unmaintained

### Publication Steps

1. Reconcile git state.
   - Fetch `origin/main`.
   - Review the 10 commits behind and 1 commit ahead.
   - Merge or rebase intentionally.
   - Keep unrelated local work out of the public release branch.

2. Create a clean release branch.
   - Use `codex/public-preview-prep` or equivalent.
   - Add license and community files.
   - Fix public copy and mojibake.
   - Add WorkStash backend or remove WorkStash from first-preview claims.

3. Scan before push.
   - Run `git status --short`.
   - Run tests and build.
   - Run `pip-audit` and `npm audit --audit-level=high`.
   - Run a history-aware secret scanner such as gitleaks or trufflehog.
   - Search for private values, emails, local paths, DB URLs, API keys, and service-role keys.

4. Create the public GitHub repository.
   - Enable secret scanning and push protection.
   - Enable Dependabot alerts/updates if acceptable.
   - Enable CodeQL for public repo.
   - Add branch protection for `main`.
   - Require CI before merge.
   - Enable private vulnerability reporting or GitHub Security Advisories.

5. Publish the first release.
   - Tag `v0.1.0-preview`.
   - Release note must say free preview, not production-ready.
   - Link setup docs and known limitations.

## MCP And App Registration Strategy

### Product Surface Split

A2CR needs two install surfaces:

```text
Local stdio MCP package:
- official path for WorkBaton save
- official path for WorkStash value encryption/decryption
- installed from PyPI as `a2cr-mcp`
- exposes the console command `a2cr-mcp`
- registered in the user's MCP client as server name `a2cr`

Remote HTTPS MCP:
- required by app directories and custom connectors
- can list metadata, check limits, resume encrypted payloads, and later support WorkThreads
- must not accept plaintext WorkBaton saves
```

The first public docs should make this split obvious. Directory reviewers will test what the remote server can actually do; do not submit a remote app that promises local-encrypted WorkBaton saving unless the UX really supports it.

### Packaging

Current public setup uses the PyPI package:

```bash
python -m pip install --upgrade a2cr-mcp
```

MCP config uses the installed console command:

```json
{
  "command": "a2cr-mcp",
  "args": []
}
```

Package direction:

```text
Primary: PyPI package `a2cr-mcp` with console command `a2cr-mcp`
Development compatibility: repo-local `mcp/server.py`
Possible later: npm package wrapper for clients that prefer `npx`
```

This makes install docs and registry `packages` metadata much easier to maintain.

### Official MCP Registry

Prepare `server.json` for the official MCP Registry.

Include:

- name such as `io.github.<owner>/a2cr`
- title `A2CR`
- description focused on WorkBaton/WorkStash handoff
- package install entry for local stdio wrapper
- remote entry for `https://a2cr.app/mcp` only if described as the remote metadata/connector surface
- repository URL
- license
- homepage
- support/security URLs

Registry gates:

- Remote URL must be publicly reachable if declared.
- `server.json` must validate against the current schema.
- Namespace ownership must be proven through GitHub or domain verification.
- Published metadata is public, so do not include personal/private contact details.

### Claude / Anthropic

Claude directory and custom connectors use remote MCP. Local MCP packages are not listed directly in the Connectors Directory.

Recommended path:

1. Support custom connector install link for the remote surface.
2. Build OAuth for remote MCP before directory submission.
3. Package local stdio as either an MCPB Desktop Extension or a Claude plugin when the local WorkBaton path is the core user value.
4. Submit remote connector only after it has a complete reviewed feature set.
5. Submit plugin if it bundles skills plus connector references.

Claude review readiness:

- split read and write tools
- add `readOnlyHint` / `destructiveHint` annotations where supported
- keep tool names under 64 characters
- avoid catch-all API tools
- avoid prompt-injection-like tool descriptions
- provide public docs and populated test account
- verify every tool through MCP Inspector and Claude custom connector

### OpenAI Apps SDK / ChatGPT Apps

OpenAI Apps require an MCP server, and Apps SDK supports remote Streamable HTTP. Submission also requires accurate privacy/support information, test cases, and review credentials.

Do not submit a ChatGPT app for full WorkBaton saving until one of these is implemented:

- a client-side encryption component that encrypts before any A2CR save API receives content, or
- a narrowed app scope that does not save WorkBaton content and only exposes safe metadata/help flows.

OpenAI submission gates:

- clear app name, description, screenshots, and purpose
- complete app, not a demo/trial shell
- privacy policy listing returned and processed data categories
- no request for full chat transcripts or broad context fields
- tool responses minimized; no debug IDs unless strictly required
- OAuth/auth flow that reviewers can use with demo credentials and no MFA blockers
- no in-app or indirect sale of SaaS subscriptions during free preview unless current policy explicitly allows it

### Cursor

Cursor supports MCP server installation and provides an "Add to Cursor" flow. It also curates official provider servers.

Prepare:

- stable local package install command
- `.cursor/mcp.json` or documentation snippets
- Add to Cursor link/button
- concise docs for API key and local client key
- official-server submission issue/PR once package and docs are stable

### GitHub Copilot / VS Code

GitHub Copilot and VS Code can discover MCP servers through registries and local configuration.

Prepare:

- official MCP Registry publication
- `.vscode/mcp.json` example
- enterprise-friendly server ID that stays stable
- documentation explaining that local stdio is required for encrypted WorkBaton save
- optional self-hosted registry example for enterprises that restrict MCP to approved registries

## OAuth And Auth Design For Remote MCP

Current API-key auth is enough for local stdio but not enough for high-quality directory submissions.

Add an OAuth layer for remote MCP:

- authorization endpoint
- token endpoint
- protected resource metadata
- client metadata or dynamic client registration support, depending on target directory
- per-user consent
- revocation/disconnect path
- scopes such as `contexts:read`, `contexts:write`, `workstash:read`, `workstash:write`, `workthreads:read`, `workthreads:write`
- separate review/demo account with sample data and no MFA requirement

Keep API keys for local stdio and advanced users, but use OAuth for directory-style remote connectors.

## Tool Contract Review

Before official submissions, audit every MCP tool:

- Tool names under 64 characters.
- Descriptions state what the tool does, not how the model should behave globally.
- No tool description tells the model to prefer A2CR over other tools.
- Read-only tools are side-effect free.
- Write/destructive tools are separated and annotated.
- `save_context` on remote clearly fails before auth/body processing and does not echo content.
- WorkStash tools exist on the remote surface only if they preserve local encryption.
- Errors are actionable and do not leak SQL, headers, tokens, ciphertext, or plaintext.

## Legal, Support, And Trust

Minimum for free preview:

- `support@a2cr.app`
- security reporting path
- privacy policy
- terms
- legal/contact page that does not expose personal home address or phone
- clear data categories: account data, metadata, ciphertext, API key metadata, logs
- clear retention and deletion behavior

Before paid launch:

- Japanese paid-sales legal display decision
- virtual office/business address decision
- refund/cancellation wording
- Lemon Squeezy live-mode review
- professional legal review where needed

## Suggested Stage Plan

### Stage A: Scope Freeze

Exit criteria:

- WorkBaton + WorkStash only for free preview
- WorkThreads hidden from public marketing
- WorkStash quota and retention final
- License selected

### Stage B: Implementation Readiness

Exit criteria:

- WorkStash table, API, RLS, service, router, tests complete
- public copy fixed
- local stdio package install path stable
- hosted smoke passes

### Stage C: OSS Preview

Exit criteria:

- public repo hygiene complete
- secret/history scan complete
- CI green
- first release tag published

### Stage D: MCP Registry And Client Docs

Exit criteria:

- `server.json` validates
- MCP Registry publish succeeds
- Cursor, VS Code, Claude Desktop/Code, and Codex setup snippets tested
- Add-to-client links documented where available

### Stage E: Directory/App Submissions

Exit criteria:

- OAuth remote MCP works
- review account ready
- privacy/support pages ready
- MCP Inspector and client-specific tests pass
- submitted to Claude/OpenAI/Cursor as appropriate

## Source References

- MCP overview: https://modelcontextprotocol.io/docs/getting-started/intro
- MCP Registry remote servers: https://modelcontextprotocol.io/registry/remote-servers
- MCP Registry terms: https://modelcontextprotocol.io/registry/terms-of-service
- MCP reference servers repo guidance: https://github.com/modelcontextprotocol/servers
- Claude connectors overview: https://claude.com/docs/connectors/overview
- Claude directory vs custom connectors: https://claude.com/docs/connectors/building/directory-vs-custom
- Claude review criteria: https://claude.com/docs/connectors/building/review-criteria
- Claude connector authentication: https://claude.com/docs/connectors/building/authentication
- OpenAI Apps SDK MCP concept: https://developers.openai.com/apps-sdk/concepts/mcp-server
- OpenAI app submission guide: https://developers.openai.com/apps-sdk/deploy/submission
- OpenAI app submission guidelines: https://developers.openai.com/apps-sdk/app-submission-guidelines
- Cursor MCP servers: https://docs.cursor.com/en/tools/mcp
- GitHub Copilot MCP registry configuration: https://docs.github.com/copilot/how-tos/administer-copilot/configure-mcp-server-access
- GitHub community profile checklist: https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/about-community-profiles-for-public-repositories
- GitHub repository licensing: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository
- GitHub secret scanning: https://docs.github.com/en/code-security/secret-scanning/enabling-secret-scanning-features
