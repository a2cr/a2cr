# A2CR GitHub Publication Draft

Updated: 2026-05-05

この文書は、A2CRをGitHubで公開する時にREADME、リポジトリ説明、公開前チェックリストへ転用するための下書きである。実際に公開する前に、秘密情報、ローカル設定、古い名称、未確定の契約情報が含まれていないか必ず確認する。

## 1. Repository概要案

Repository name:

```text
a2cr
```

Short description:

```text
Agent-to-Agent Context Relay: save and resume AI agent work context across windows, tools, and clients.
```

Topics:

```text
ai-agents, mcp, fastapi, context-management, agent-workflow, python, saas
```

Website:

```text
未定。ドメイン取得後に a2cr.app などを設定する。
```

## 2. README構成案

### Title

```markdown
# A2CR

Agent-to-Agent Context Relay
```

### One-liner

```markdown
A2CR helps AI agents save, resume, and share work context across conversation windows, AI clients, and devices.
```

### What is A2CR?

A2CR is a context relay service for AI-agent workflows. It lets MCP-capable AI clients such as Claude, Codex, Cursor, and similar tools save structured work context and resume it later from another AI window.

The project is designed around two product layers:

| Layer | Purpose |
|---|---|
| WorkBaton | Save a short-lived work checkpoint and resume it in a new AI window |
| WorkThreads | Let multiple active AI agents coordinate through a shared work thread |

In the initial version, A2CR does not run LLM inference on the server. Users bring their own AI clients, and those clients call A2CR through MCP/API.

### Why?

AI agents are useful, but their work state is usually trapped inside one conversation window. When a session gets long, a subagent finishes, or a user switches tools, important context is often lost.

A2CR externalizes that work state:

- save the goal, current state, next action, decisions, constraints, and references
- reopen the work from a fresh AI window
- keep dashboard views focused on metadata, not private context bodies
- prepare for future cross-agent work coordination through WorkThreads

### Current status

```text
Status: early prototype / active design
```

Implemented locally:

- FastAPI local API
- SQLite local storage
- Fernet application-layer encryption for saved context bodies
- fixed Slot 1-3 support
- MCP wrapper tools such as `save_context`, `resume_context`, `load_context`, and `list_contexts`
- optional AI client Skill template at `docs/templates/skills/a2cr-agent/SKILL.md`
- Streamlit local dashboard
- automated pytest coverage

Planned Web SaaS:

- Railway runtime for React/Vite + FastAPI + HTTP MCP
- Supabase Auth + Postgres + RLS
- Cloudflare DNS/domain
- Stripe billing after the Core MVP is stable
- WorkThreads as a Pro feature after WorkBaton Core is solid

### Core concepts

#### WorkBaton

WorkBaton is the free/core checkpoint feature. An AI agent saves a compact structured context object, and a later AI agent resumes from that checkpoint.

Example saved fields:

- `goal`
- `current_state`
- `next_action`
- `decisions`
- `constraints`
- `problems`
- `environment`
- `background`
- `summary`
- `failed_attempts`
- `references`

#### WorkThreads

WorkThreads is the planned Pro shared work layer. It is not a generic AI chat room. It is closer to an AI-agent work board where active agents can append notes, review results, track failures, and notice updates while they are working.

The initial WorkThreads design favors:

- append-only messages
- unread cursors
- update checks
- optional long polling such as `wait_workthread_updates`
- no server-side LLM inference
- no attempt to wake sleeping or stopped AI windows

### Security and privacy direction

A2CR is designed so human-facing dashboards do not display saved context bodies. Dashboards should show metadata only: slot names, timestamps, sizes, counts, status, and logs.

Saved context bodies should not be viewable by service administrators through normal admin dashboards, support tooling, or direct database inspection. This should be presented as an operational visibility control, not as a zero-knowledge guarantee.

Important principles:

- do not log API keys or Authorization headers
- do not log saved context bodies
- do not expose decrypted content through dashboard APIs
- use application-layer encryption for content storage
- use RLS and user-scoped access in the Web SaaS design
- do not put Supabase service-role keys in normal runtime environments

This project is not currently claiming full end-to-end or zero-knowledge encryption.

### Local development

Draft only. Update before publishing:

```bash
pip install -r requirements.txt
python -m pytest -q
```

On Windows local prototype:

```bat
start.bat
```

Local services:

```text
API:       http://localhost:8000
Dashboard: http://localhost:8501
```

### MCP usage

Draft only. Do not include real keys.

```json
{
  "mcpServers": {
    "a2cr": {
      "command": "python",
      "args": ["<project-root>/mcp/server.py"],
      "env": {
        "A2CR_API_KEY": "<your-api-key>"
      }
    }
  }
}
```

Typical resume prompt:

```text
A2CR service: http://localhost:8000
A2CR MCPツールを使ってください。HTTP APIを直接推測して呼び出さないでください。
まず resume_context(slot_name="your-slot") を実行して、A2CRから引き継ぎ文脈を読み込んでください。
```

The optional `docs/templates/skills/a2cr-agent/SKILL.md` template can be used by Skill-capable clients such as Codex. A2CR should still work without it because the required guidance lives in MCP tool descriptions, tool responses, and generated resume prompts.

### Roadmap

Near term:

- finalize the Web SaaS Core specification
- migrate from local SQLite prototype to Supabase Postgres
- implement Web SaaS authentication and API-key management
- implement HTTP MCP endpoint
- build React/Vite dashboard

Later:

- WorkThreads message/unread/update-check MVP
- WorkThreads long polling
- Stripe billing for Pro
- production deployment and monitoring
- optional Redis/Sentry/PostHog only when needed

### License

```text
TBD
```

Choose a license before public release. If undecided, keep the repository private until the license policy is clear.

### Additional README section

The public README should be English-first. Add the localized summary after the full English README content, not before it.

Suggested section title:

```markdown
## 概要
```

Suggested summary:

```markdown
A2CRは、AIエージェントの作業文脈を別の会話窓、別のAIクライアント、別の端末へ引き継ぐためのサービスです。

WorkBatonは短命な作業チェックポイントを保存して新しいAI窓で再開するための機能です。WorkThreadsは、複数の作業中AIエージェントが同じ作業スレッドを見ながら連携する予定のPro機能です。

MVP段階では、A2CRサーバー自身はLLM推論を実行しません。Claude、Codex、CursorなどのMCP/API対応AIクライアントがA2CRを呼び出して、作業文脈を保存・読込・再開します。
```

Keep this section short enough that the README still feels primarily aimed at English-speaking users.

## 3. GitHub公開前チェックリスト

### Must fix before public

- Remove or ignore `.env` files.
- Do not publish real API keys, Fernet keys, Supabase keys, Stripe keys, Google OAuth secrets, or Railway tokens.
- Do not publish `.claude/mcp.json` if it contains local API keys.
- Do not publish local SQLite DB files.
- Do not publish `logs/`.
- Do not publish `__pycache__/` or `.pytest_cache/`.
- Check whether old `AIClipboard` naming should be removed, renamed, or kept only as migration history.
- Add or confirm `.gitignore`.
- Add a top-level `README.md`.
- Add a `LICENSE` file or keep the repository private.
- Run tests before publishing.

### Recommended cleanup

- Move internal planning docs under `docs/internal/` if they are not meant for public readers.
- Keep public docs focused on A2CR, WorkBaton, WorkThreads, setup, and roadmap.
- Add `SECURITY.md` with a short responsible disclosure policy before public beta.
- Add `.env.example` with placeholder values only.
- Consider adding screenshots only after the UI is stable and does not expose private data.

## 4. Public messaging boundaries

Say:

- A2CR helps AI agents save and resume work context.
- WorkBaton is for context checkpoints.
- WorkThreads is planned for active cross-agent work coordination.
- A2CR does not run LLM inference in the MVP.
- The dashboard is designed to show metadata, not saved context bodies.

Do not overclaim:

- Do not call it a protocol yet.
- Do not claim zero-knowledge encryption.
- Do not claim autonomous AI orchestration.
- Do not claim production readiness until Web SaaS auth, RLS, logs, rate limits, and deployment are verified.
- Do not claim integrations with specific AI products beyond general MCP/API compatibility unless tested.

## 5. Possible GitHub release note for first public push

```markdown
## Initial public preview

This is an early prototype of A2CR, Agent-to-Agent Context Relay.

Included:

- local FastAPI context API
- local encrypted context storage
- MCP wrapper tools for save/resume/load/list
- fixed Slot 1-3 support
- design docs for the planned Web SaaS architecture
- early WorkThreads specification

Not production-ready yet:

- Web SaaS authentication is not implemented
- Supabase/RLS integration is design-stage
- HTTP MCP endpoint is not implemented
- WorkThreads is specification-stage
- billing is not implemented
```
