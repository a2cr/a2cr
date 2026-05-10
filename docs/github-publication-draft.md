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
