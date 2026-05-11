# A2CR GitHub Publication Draft

Updated: 2026-05-10

This document is a public-release checklist and messaging draft for publishing A2CR on GitHub.

## Repository Metadata

Repository name:

```text
a2cr
```

Short description:

```text
Agent-to-Agent Context Relay: save and resume AI agent work context across windows, tools, and clients.
```

Suggested topics:

```text
ai-agents, mcp, fastapi, context-management, agent-workflow, python, saas
```

## Public GitHub Content Package

Use this section as the near-final content set for the public repository page.
Keep the public repository mostly English-first. Add a short Japanese summary
only after the English content is stable.

### Visual Asset Plan

Use the refreshed logo and the generated story GIF as the first visual signals.
Keep the text-heavy explainer images static so readers can scan them at their
own pace.

Repository asset paths:

```text
docs/assets/github/a2cr-logo.png
docs/assets/github/a2cr-logo-dark.png
docs/assets/github/a2cr-story.gif
docs/assets/github/a2cr-basics.png
docs/assets/github/a2cr-save-rules.png
docs/assets/github/a2cr-workflow.png
```

README order:

```text
1. Refreshed A2CR logo
2. Story GIF: messy context -> WorkBaton / WorkStash -> handoff complete
3. Short product explanation
4. Static explainer images: basics, save rules, workflow
5. Product layers, current status, setup, security, docs
```

Do not GIF-animate the explainer images for the README. They contain dense text
and are better as static documentation panels. A separate slow carousel GIF can
be created later for social posts or a landing page if needed.

### GitHub About Sidebar

Description:

```text
Agent-to-Agent Context Relay: save and resume AI agent work context across windows, tools, and clients.
```

Website:

```text
https://a2cr.app
```

Topics:

```text
ai-agents
mcp
model-context-protocol
context-management
agent-workflow
fastapi
react
supabase
developer-tools
```

### README Opening Copy

```markdown
<p align="center">
  <img src="docs/assets/github/a2cr-logo.png" alt="A2CR logo" width="420">
</p>

<p align="center">
  <img src="docs/assets/github/a2cr-story.gif" alt="A2CR turns messy AI work context into WorkBaton and WorkStash handoff state" width="900">
</p>

# A2CR

Agent-to-Agent Context Relay.

A2CR is an MCP-first context relay for AI-agent workflows. It helps an AI agent
save a compact work checkpoint, then lets another AI window, model, or MCP-capable
client resume from the useful state instead of carrying a full chat history.

A2CR is not an AI runtime and does not run LLM inference on the server. Users
bring their own AI clients. A2CR provides the handoff layer those clients can
call through MCP/API.
```

### Public Status Banner

Use this near the top of `README.md` until hosted preview is verified:

```markdown
> Status: early public-preview preparation. The Web SaaS foundation and local
> stdio MCP wrapper are under active development. Do not treat this repository
> as production-ready until hosted deployment, auth, RLS, logging hygiene,
> backup/restore, and smoke checks are verified.
```

After hosted preview is verified, replace it with:

```markdown
> Status: free public preview. WorkBaton is available through the local stdio MCP
> wrapper and A2CR SaaS API. Paid billing and WorkThreads are not part of the
> first public preview.
```

If the WorkStash SaaS backend is not complete by publication time, do not say
WorkStash is included. Use:

```markdown
> WorkStash is documented as the next companion feature for WorkBaton, but the
> public preview currently focuses on WorkBaton until the hosted WorkStash API,
> RLS, quota, and smoke tests are complete.
```

If WorkStash is complete and tested, use:

```markdown
> The first public preview includes WorkBaton for compact checkpoints and
> WorkStash for small encrypted supporting notes referenced by WorkBaton.
```

### README Feature Summary

```markdown
## What It Does

- Saves compact AI work-state checkpoints as WorkBaton slots.
- Resumes work from another AI window or MCP-capable client.
- Keeps the official WorkBaton save path client-encrypted through the local
  stdio MCP wrapper.
- Shows dashboard metadata without exposing saved context bodies.
- Provides a Web SaaS foundation for API keys, plan limits, sanitized logs,
  Supabase/Postgres RLS, and Streamable HTTP MCP.
```

### Product Layer Table

```markdown
## Product Layers

| Layer | Status | Purpose |
| --- | --- | --- |
| WorkBaton | First preview scope | Save a short-lived work checkpoint and resume it in a new AI window |
| WorkStash | Include only after backend smoke passes | Store temporary supporting notes referenced by WorkBaton checkpoints |
| WorkThreads | Planned later | Shared work threads for active multi-agent coordination |
```

### Security Boundary Copy

```markdown
## Security Model

WorkBaton is client-encrypted only. The local stdio MCP wrapper encrypts a
checkpoint before sending it to A2CR. A2CR stores ciphertext and metadata, and
does not have the local client key needed to decrypt WorkBaton bodies.

The dashboard is designed to show metadata only, such as slot names, timestamps,
sizes, counts, status, and access-log summaries. It must not display saved
WorkBaton bodies.

This does not mean the whole service is zero-knowledge. Account data, metadata,
API key metadata, access logs, billing metadata when billing exists, and
operational records remain normal SaaS data that A2CR must protect.
```

### What A2CR Is Not

```markdown
## What A2CR Is Not

- Not an LLM or server-side AI agent.
- Not a chat-history archive.
- Not file storage.
- Not an autonomous orchestration platform.
- Not a replacement for model-native summarization or context compaction.
- Not a broad zero-knowledge product claim for every piece of SaaS metadata.
```

### Quick Start Shape

````markdown
## Quick Start

Install the local stdio MCP wrapper from PyPI:

```bash
python -m pip install --upgrade a2cr-mcp
```

Configure the local stdio MCP wrapper in your AI client. Example:

```json
{
  "mcpServers": {
    "a2cr": {
      "command": "a2cr-mcp",
      "args": [],
      "env": {
        "A2CR_API_KEY": "<your-a2cr-api-key>",
        "A2CR_BASE_URL": "https://a2cr.app",
        "A2CR_SERVICE_URL": "https://a2cr.app/mcp"
      }
    }
  }
}
```

Do not commit real API keys or local client key files.
````

### First Public Release Note

```markdown
## v0.1.0-preview

This is the first public preview preparation release for A2CR, Agent-to-Agent
Context Relay.

Included:

- PyPI package `a2cr-mcp` with the `a2cr-mcp` console command
- local stdio MCP wrapper for client-encrypted WorkBaton save/load/resume
- WorkBaton Web Context API that accepts encrypted content only
- Supabase/Postgres schema, RLS, API key auth, and sanitized access-log foundation
- React/Vite dashboard for metadata, settings, pricing, and API key management
- Streamable HTTP MCP surface for hosted metadata and future connector work
- deployment, security, and data-lifecycle runbooks

Not included yet:

- paid checkout
- public WorkThreads launch
- server-side AI execution
- production SLA

Known limitations:

- WorkBaton saves require the local stdio wrapper so encryption happens before upload.
- Losing the local client key makes old client-encrypted WorkBaton slots unrecoverable.
- Hosted deployment, backup/restore, monitoring, and official MCP directory submissions
  must be verified before claiming production readiness.
```

### Issue Templates

Suggested issue templates:

```text
Bug report
- What happened?
- What did you expect?
- Which client did you use? Codex / Claude / Cursor / VS Code / other
- Local stdio or hosted remote MCP?
- A2CR version / commit
- Sanitized error message
- Confirmation: no secrets, API keys, Authorization headers, DB URLs, or saved context bodies are included

Feature request
- Problem
- Desired behavior
- Why this belongs in A2CR
- WorkBaton / WorkStash / WorkThreads / Dashboard / Docs

MCP client compatibility
- Client name and version
- OS
- MCP configuration shape, with secrets removed
- Which tool failed or behaved unexpectedly
- Sanitized logs or screenshots
```

### Pull Request Template

```markdown
## Summary

## Scope

- [ ] WorkBaton
- [ ] WorkStash
- [ ] WorkThreads
- [ ] Dashboard
- [ ] Docs
- [ ] Deployment/security

## Verification

- [ ] `python -m pytest -q`
- [ ] `cd web && npm run build`
- [ ] MCP/manual smoke, if relevant:

## Security checklist

- [ ] No secrets, API keys, Authorization headers, DB URLs, local client keys, or saved context bodies are included.
- [ ] Dashboard/API/MCP responses do not expose decrypted WorkBaton or WorkStash values.
- [ ] Public copy does not overclaim zero-knowledge, production readiness, or AI orchestration.
```

### Short Japanese Summary For README Bottom

Add this only after the English README is stable:

```markdown
## Japanese Summary

A2CR は、AI エージェントの作業状態を WorkBaton として保存し、別の AI 窓や MCP 対応クライアントで再開するためのコンテキスト中継レイヤーです。

サーバー側で LLM 推論は行いません。WorkBaton 本文はローカル stdio MCP wrapper でアップロード前に暗号化され、A2CR は ciphertext とメタデータを保存します。

初回公開は無料プレビューとして扱い、課金・WorkThreads・本番 SLA は後続フェーズです。
```

## README Messaging

A2CR is a context relay service for AI-agent workflows. It lets MCP-capable AI clients such as Claude, Codex, Cursor, and similar tools save structured work context and resume it later from another AI window.

Product layers:

| Layer | Purpose |
|---|---|
| WorkBaton | Save a short-lived work checkpoint and resume it in a new AI window |
| WorkStash | Store temporary supporting notes referenced by WorkBaton checkpoints |
| WorkThreads | Planned shared work threads for active AI-agent coordination |

In the MVP, A2CR does not run LLM inference on the server. Users bring their own AI clients, and those clients call A2CR through MCP/API.

## Current Status Copy

Implemented locally:

- FastAPI local API
- SQLite local storage
- client-encrypted WorkBaton mode through the local stdio MCP wrapper
- fixed Slot 1-5 support
- MCP wrapper tools such as `save_context`, `resume_context`, `load_context`, `list_contexts`, and WorkStash tools
- optional AI client Skill template at `docs/templates/skills/a2cr-agent/SKILL.md`
- Streamlit local dashboard
- automated pytest coverage

Implemented Web SaaS foundation:

- Railway runtime wiring for React/Vite + FastAPI + HTTP MCP
- Supabase Auth + Postgres + RLS foundation
- API-key management foundation
- WorkBaton Web Context API with plan limits and sanitized access logs
- client-encrypted-only WorkBaton storage
- dashboard APIs that return metadata, not saved context bodies
- React/Vite dashboard

Planned:

- first hosted Railway/Supabase deployment for a free WorkBaton + WorkStash preview
- Cloudflare DNS/domain
- GitHub OSS publication and community feedback loop
- official MCP listing/application work after the public setup docs are stable
- Lemon Squeezy billing after the free preview and Core smoke tests are stable
- WorkThreads after WorkBaton/WorkStash adoption, billing, and remaining legal work are under control

## Security And Privacy Copy

A2CR is designed so human-facing dashboards do not display saved context bodies. Dashboards should show metadata only: slot names, timestamps, sizes, counts, status, and logs.

WorkBaton is client-encrypted only. The local stdio MCP wrapper encrypts WorkBaton content before sending it to A2CR and keeps the client key in a local key file. A2CR stores and returns ciphertext and cannot decrypt the WorkBaton body.

A2CR rejects plaintext WorkBaton bodies. Direct remote HTTP MCP saving is disabled for WorkBaton because encryption must happen before upload. Users must understand that losing the local client key makes those slots unrecoverable.

## Must Fix Before Public

- Remove or ignore `.env` files.
- Do not publish real API keys, Fernet keys, Supabase keys, Lemon Squeezy keys, Google OAuth secrets, Railway tokens, or local A2CR client key files.
- Do not publish private MCP configs.
- Do not publish local SQLite DB files.
- Do not publish logs, `__pycache__/`, `.pytest_cache/`, or generated caches.
- Add or confirm `.gitignore`.
- Add a `LICENSE` file before OSS publication.
- Confirm public docs, repository metadata, support templates, and screenshots
  do not expose a personal home address, personal phone number, or personal
  Gmail address.
- Decide the public contact path for the free preview: `support@a2cr.app` plus
  virtual office/business address planning for later paid legal display.
- Run `python -m pytest -q`.
- Run `cd web && npm run build`.
- Confirm public-facing Markdown does not contain mojibake or private planning notes.

## Recommended Cleanup

- Keep public docs focused on A2CR, WorkBaton, WorkThreads, setup, and roadmap.
- Move internal planning docs under a clearly internal path if they are not meant for public readers.
- Keep `SECURITY.md` short and accurate.
- Keep `.env.example` placeholder-only.
- Add screenshots only after the UI is stable and does not expose private data.
- Prepare a concise MCP server submission/listing package after the public setup path is tested.
- Keep paid legal-display details out of public preview copy until the virtual
  office/business address and phone/contact handling decision is recorded.

## Public Messaging Boundaries

Say:

- A2CR helps AI agents save and resume work context.
- WorkBaton is for context checkpoints.
- WorkThreads is planned for active cross-agent work coordination.
- A2CR does not run LLM inference in the MVP.
- A2CR should remain model-neutral.
- Dashboards are designed to show metadata, not saved context bodies.
- Client-encrypted WorkBaton slots are encrypted before reaching A2CR.
- A2CR cannot decrypt WorkBaton bodies.
- WorkBaton and WorkStash are the first public free preview scope.
- Pro is planned at $8/month to account for Merchant of Record payment/tax
  handling, but paid checkout is not part of the first free preview.

Do not overclaim:

- Do not call it a protocol yet.
- Do not claim full end-to-end encryption for the whole product.
- Do not claim zero-knowledge encryption for WorkThreads.
- Do not claim autonomous AI orchestration.
- Do not claim production readiness until hosted deployment, auth, RLS, logs, rate limits, and backup/restore are verified.
- Do not claim integrations with specific AI products beyond general MCP/API compatibility unless tested.

## Possible Release Note For First Public Push

```markdown
## Initial public preview

This is an early prototype of A2CR, Agent-to-Agent Context Relay.

Included:

- local FastAPI context API
- local encrypted context storage
- client-encrypted WorkBaton mode through the stdio MCP wrapper
- MCP wrapper tools for save/resume/load/list
- fixed Slot 1-5 support
- Web SaaS foundation for Supabase/Postgres, HTTP MCP, and React dashboard
- design docs for the planned WorkThreads layer

Not production-ready yet:

- first hosted deployment is not complete
- billing is not implemented
- WorkThreads is not production-ready
- public support/security contact is not finalized
```
