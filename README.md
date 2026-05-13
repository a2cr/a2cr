<p align="center">
  <img src="docs/assets/github/a2cr-logo.png" alt="A2CR logo" width="420">
</p>

<p align="center">
  <img src="docs/assets/github/a2cr-story.gif" alt="A2CR turns messy AI work context into WorkBaton and WorkStash handoff state" width="900">
</p>

# A2CR

Agent-to-Agent Context Relay.

A2CR helps AI agents hand off real work between conversation windows, models,
tools, and time. It gives an AI client a small, structured place to save where
the work stands now, then resume from that state later.

A2CR does not run an LLM on the server. It does not choose models, think for
your agent, or generate code reviews. You bring your own AI client, and that
client calls A2CR through MCP/API.

## Status

A2CR is an early public-preview project, not production-ready software.

Current focus:

- Free public preview for WorkBaton and WorkStash
- Local stdio MCP wrapper through the PyPI package `a2cr-mcp`
- Hosted account, API key, dashboard, and metadata views at `https://a2cr.app`
- OSS publication, community feedback, and official MCP listing/application work

Later work:

- Lemon Squeezy billing after the free preview and smoke checks are stable
- WorkThreads for shared AI-agent coordination
- More mature legal, support, operations, and security review processes

## What A2CR Solves

Long AI-assisted work often fails at the handoff point:

- the chat gets too long
- a model switch loses details
- a new AI window does not know what was already tried
- tests, blockers, and next steps are scattered in conversation history
- project memory files become stale or overloaded

A2CR keeps the handoff compact. A WorkBaton says: goal, current state, next
action, decisions, blockers, and validation. WorkStash can hold small temporary
supporting notes that would make the WorkBaton too bulky.

## Visual Overview

### A2CR Basics

![A2CR Basics](docs/assets/github/a2cr-basics.png)

### Save Rules and Cautions

![Save Rules and Cautions](docs/assets/github/a2cr-save-rules.png)

### Basic Workflow

![How to Use A2CR](docs/assets/github/a2cr-workflow.png)

## Product Layers

| Layer | Purpose | Status |
| --- | --- | --- |
| WorkBaton | Save a short-lived work checkpoint and resume it in a new AI window | First public-preview scope |
| WorkStash | Store temporary supporting notes referenced by WorkBaton checkpoints | First public-preview scope |
| WorkThreads | Shared work threads for active AI-agent coordination | Planned later |

## Quick Start

Install or update the local MCP wrapper:

```bash
python -m pip install --upgrade a2cr-mcp
```

Configure exactly one MCP server named `a2cr` through the local stdio wrapper.
WorkBaton requires the local stdio wrapper so content is encrypted before upload.
Do not configure the hosted `/mcp` URL directly for WorkBaton, do not guess REST
endpoints, and do not use the old `AI_CLIPBOARD_*` or `A2CR_API_STYLE` settings
for normal AI-agent setup.

Codex-style local stdio example:

```toml
[mcp_servers."a2cr"]
command = "a2cr-mcp"
args = []

[mcp_servers."a2cr".env]
A2CR_API_KEY = "<your-a2cr-api-key>"
A2CR_BASE_URL = "https://a2cr.app"
A2CR_SERVICE_URL = "https://a2cr.app/mcp"
# Optional: A2CR_CLIENT_KEY_FILE = "<path-to-workbaton.key>"
```

Generic MCP stdio example:

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

The full API key is shown only once when it is issued. If you issue a new key,
it is a different API key; update every MCP config that should keep using A2CR.

The local stdio MCP wrapper creates and stores the local client key in a local
key file during the first client-encrypted save when no key file exists. Set
`A2CR_CLIENT_KEY_FILE` to choose the path, or `A2CR_CONFIG_DIR` to choose the
directory that contains `workbaton.key`. If neither variable is set, the default
path is `%APPDATA%\A2CR\workbaton.key` on Windows, and
`$XDG_CONFIG_HOME/a2cr/workbaton.key` or `~/.config/a2cr/workbaton.key` on
macOS/Linux.

To resume the same WorkBaton from another PC, configure the A2CR API key and
securely copy the same local client key file. The API key alone can access
encrypted slot data, but it cannot decrypt the WorkBaton body.

## How Agents Should Use It

Useful WorkBaton checkpoints are small:

- goal
- current state
- next action
- decisions
- blockers
- validation status
- references to any needed WorkStash `entry_key` values

Avoid saving:

- secrets
- API keys
- Authorization headers
- private database URLs
- local client key files
- full chat transcripts
- long logs
- generated caches
- large source files

## Project Memory Files vs A2CR

`CLAUDE.md`, `AGENTS.md`, and similar project memory files are not a replacement
for WorkBaton. They have different jobs:

| Surface | Best for | Avoid using it for |
| --- | --- | --- |
| `CLAUDE.md` / `AGENTS.md` | Durable project rules, setup notes, coding conventions, and instructions the AI should read at the start of every session | Constantly changing task state, latest validation status, and "where we stopped just now" |
| WorkBaton | Current handoff state: goal, `current_state`, `next_action`, recent decisions, blockers, and validation needed by the next AI window | Permanent documentation, full chat transcripts, long logs, secrets, or large source files |
| WorkStash | Temporary supporting notes that would bloat the WorkBaton, such as confirmed file paths, API findings, failed approaches, and concise validation notes | Durable knowledge base content, secrets, full transcripts, or generated caches |

Short version: project memory files describe how the AI should work in a
repository. WorkBaton describes where the work is right now.

## MCP / A2A / A2CR Positioning

A2CR is complementary to MCP and A2A, not a replacement for either protocol.

| Surface | Primary role | A2CR relationship |
| --- | --- | --- |
| MCP | Connects an AI agent to tools, APIs, and external data | A2CR is exposed to agents through MCP, but MCP itself is not the handoff memory |
| A2A | Connects AI agents to other AI agents for delegation, communication, and collaboration | A2CR is not an agent-to-agent protocol; WorkBaton preserves the work state that a configured agent can resume |
| A2CR | Carries compact work state across AI windows, models, tools, and time | Complements MCP and A2A by handing off `goal`, `current_state`, `next_action`, validation, and blockers across sessions |

## Security Boundaries

A2CR's hosted service uses Supabase/Postgres for the data layer and Railway for
the app runtime. User-owned rows are separated with Supabase Row Level Security
(RLS) and a least-privileged `a2cr_app` runtime role. Official WorkBaton saves
are encrypted locally before upload, so the service stores ciphertext for
WorkBaton bodies rather than plaintext.

A2CR is designed so human-facing dashboards do not display saved context bodies.
Dashboards should show metadata only, such as slot names, timestamps, sizes,
counts, status, and logs.

WorkBaton is client-encrypted only. The local stdio MCP wrapper encrypts
WorkBaton content before sending it to A2CR and keeps the client key in a local
key file. A2CR stores and returns ciphertext and cannot decrypt the WorkBaton
body.

Important principles:

- do not log API keys or Authorization headers
- do not log saved context bodies
- do not expose decrypted content through dashboard APIs
- reject plaintext WorkBaton bodies on A2CR APIs
- use RLS and user-scoped access in the Web SaaS design
- do not put Supabase service-role keys in normal runtime environments

Users must understand that losing the local client key makes those WorkBaton
slots unrecoverable. Creating a new key works for future saves, but it cannot
decrypt slots saved with the old key.

Supabase and Railway publish SOC 2 / compliance information for their platforms.
That helps with vendor risk, but it does not make A2CR itself SOC 2 certified
and does not replace A2CR's own RLS, client encryption, key hygiene, and smoke
tests.

## Current Implementation

Implemented Web SaaS foundation:

- Supabase/Postgres schema, RLS, and least-privileged runtime role design
- API key and Supabase JWT auth foundation
- WorkBaton Web Context API with plan limits and sanitized access logs
- client-encrypted-only WorkBaton storage
- Dashboard API that returns metadata, stats, logs, and API key state without saved content bodies
- Streamable HTTP MCP `/mcp` as a service surface; the official AI-agent path for WorkBaton is the local stdio MCP wrapper so client encryption happens before upload
- React/Vite dashboard UI for login, WorkBaton metadata, settings, API key management, and pricing
- Railway Docker build wiring, production startup guards, same-origin guard, and deployment/security runbooks

Legacy local prototype retained for development reference:

- FastAPI context API
- SQLite local storage
- fixed Slot 1-5 support
- Streamlit local dashboard
- pytest coverage

The legacy local SQLite WorkBaton API is disabled by default. It must not be
used as the official AI-agent save path.

## Local Development

```bash
pip install -r requirements.txt
python -m pytest -q
cd web
npm install
npm run build
```

Optional local services for development:

```text
API:     uvicorn main:app --host 127.0.0.1 --port 8000
Web dev: npm run dev
```

## Deployment

The MVP deployment target is one Railway Dockerfile service. The Dockerfile
builds the React/Vite app, installs the Python runtime, copies `web/dist`, and
starts FastAPI with Uvicorn.

Railway health check:

```text
/api/v1/health
```

Maintenance cleanup command:

```bash
python -m services.maintenance expire-contexts
```

See [deploy runbook](docs/runbooks/deploy.md) and
[security runbook](docs/runbooks/security.md).

## Contributing

A2CR is an early public-preview project, and community feedback is very welcome.

Useful contributions include:

- trying the MCP wrapper in real AI coding workflows
- reporting confusing setup steps or documentation gaps
- filing bugs with clear reproduction steps
- suggesting safer defaults for WorkBaton and WorkStash
- improving docs, examples, onboarding, and compatibility notes
- reviewing security boundaries and privacy wording

Please do not include secrets, API keys, Authorization headers, private database
URLs, local client key files, decrypted WorkBaton or WorkStash bodies, full chat
transcripts, or other user data in public issues.

A2CR is being built in the open because AI-assisted development has a real
context handoff problem, and solving it well will take more than one person's
workflow.

## Support And Security

- General support: a2cr.mcp@gmail.com
- Security reports: a2cr.mcp@gmail.com, or GitHub Private Vulnerability Reporting
  when enabled on the public repository
- Privacy requests: a2cr.mcp@gmail.com
- X: @A2CR_MCP
- Discord: a2cr.mcp (reserved; public community/support use is pending a
  moderation policy)

## Documentation

- Usage guide: `docs/usage.md`
- Public contact email setup: `docs/runbooks/public-contact-email-setup.md`
- MCP Baton vs Threads flow: `docs/runbooks/mcp-baton-vs-threads-flow.md`
- WorkBaton autonomous save spec: `docs/runbooks/workbaton-autonomous-save-spec.md`
- Deploy runbook: `docs/runbooks/deploy.md`
- Disaster recovery runbook: `docs/runbooks/disaster-recovery.md`
- Security runbook: `docs/runbooks/security.md`
- Data lifecycle runbook: `docs/runbooks/data-lifecycle.md`
- WorkThreads runbook: `docs/runbooks/workthreads.md`
- Security/resilience baseline: `docs/superpowers/specs/2026-05-06-a2cr-security-resilience-plan.md`
- Optional AI client Skill template: `docs/templates/skills/a2cr-agent/SKILL.md`
- Service cost estimate: `docs/a2cr-service-cost-estimate.md`
- GitHub publication draft: `docs/github-publication-draft.md`

## Project Note

A2CR started as an AI-assisted project by a solo builder without a traditional
software engineering background. GPT and Claude were used heavily for
implementation, review, documentation, and iteration.

That origin is part of why A2CR focuses on durable AI work handoff: when AI
tools help build real software, losing context between sessions becomes a
practical engineering problem.

## License

TBD before OSS publication. Choose and add an open-source license before making
the repository public.

---

## 日本語概要

A2CR は、AI エージェントの作業状態を次の会話窓、別のモデル、別の MCP 対応クライアントへ引き継ぐためのコンテキスト中継レイヤーです。

たとえば、長い実装作業の途中でチャットが長くなったり、モデルを切り替えたり、新しい AI 窓へ移ったりすると、「何をやっていたか」「何が検証済みか」「次に何をするべきか」が失われがちです。A2CR はその引き継ぎ状態を WorkBaton として短く保存し、必要に応じて WorkStash に補助メモを分けて残します。

### 主な考え方

- WorkBaton は、次の AI が作業を再開するための短い引き継ぎです。
- WorkStash は、WorkBaton に入れると大きくなりすぎる補助メモを一時的に置く場所です。
- A2CR はサーバー側で LLM 推論を行いません。
- 公式の WorkBaton 保存経路では、ローカル stdio MCP wrapper がアップロード前に本文を暗号化します。
- A2CR のダッシュボードは、保存本文ではなくメタデータを扱う設計です。
- Free public preview では WorkBaton と WorkStash を中心に進め、課金や WorkThreads は後続フェーズです。

### OSSとして協力してほしいこと

A2CR はまだ初期の public-preview project です。実際の AI コーディング作業で試した結果、セットアップで詰まった点、ドキュメントの分かりにくい箇所、安全境界の表現、MCP クライアントごとの互換性メモなどを歓迎します。

Issue には、API キー、Authorization header、private database URL、ローカル client key、復号済みの WorkBaton / WorkStash 本文、全文チャットログなどの機密情報を含めないでください。

### プロジェクトの背景

A2CR は、従来の開発経験がない個人が GPT と Claude を活用して作り始めた AI-assisted project です。

この背景があるからこそ、A2CR は「AI と一緒に実際のソフトウェアを作るとき、作業文脈をどう安全に次へ渡すか」を実用上の問題として扱っています。完璧な完成品としてではなく、同じ課題を持つ人たちと育てていく OSS として公開準備を進めています。
