<p align="center">
  <img src="docs/assets/github/a2cr-logo.png" alt="A2CR logo" width="420">
</p>

<p align="center">
  <img src="docs/assets/github/a2cr-story.gif" alt="A2CR turns messy AI work context into WorkBaton and WorkStash handoff state" width="900">
</p>

# A2CR

Agent-to-Agent Context Relay.

A2CR helps AI agents save and resume work context across conversation windows, tools, and clients. The current repository is a Web SaaS foundation with a legacy local prototype kept only for development reference.

## Visual Overview

### A2CR Basics

![A2CR Basics](docs/assets/github/a2cr-basics.png)

### Save Rules and Cautions

![Save Rules and Cautions](docs/assets/github/a2cr-save-rules.png)

### Basic Workflow

![How to Use A2CR](docs/assets/github/a2cr-workflow.png)

## Product Layers

| Layer | Purpose |
|---|---|
| WorkBaton | Save a short-lived work checkpoint and resume it in a new AI window |
| WorkStash | Store temporary supporting notes referenced by WorkBaton checkpoints |
| WorkThreads | Planned shared work threads for active AI-agent coordination |

## Project Memory Files vs A2CR

`CLAUDE.md`, `AGENTS.md`, and similar project memory files are not a replacement for WorkBaton. They have different jobs:

| Surface | Best for | Avoid using it for |
|---|---|---|
| `CLAUDE.md` / `AGENTS.md` | Durable project rules, setup notes, coding conventions, and instructions the AI should read at the start of every session | Constantly changing task state, latest validation status, and "where we stopped just now" |
| WorkBaton | Current handoff state: goal, `current_state`, `next_action`, recent decisions, blockers, and validation needed by the next AI window | Permanent documentation, full chat transcripts, long logs, secrets, or large source files |
| WorkStash | Temporary supporting notes that would bloat the WorkBaton, such as confirmed file paths, API findings, failed approaches, and concise validation notes | Durable knowledge base content, secrets, full transcripts, or generated caches |

Short version: project memory files describe how the AI should work in this repository. WorkBaton describes where the work is right now.

A2CR does not run LLM inference on the server in the MVP. It does not think for your agents, choose models, or generate reviews. Users bring their own AI clients, and those clients call A2CR through MCP/API.

This keeps A2CR model-neutral and keeps pricing tied to storage, requests, and coordination rather than token burn.

## MCP / A2A / A2CR Positioning

A2CR is complementary to MCP and A2A, not a replacement for either protocol.

| Surface | Primary role | A2CR relationship |
|---|---|---|
| MCP | Connects an AI agent to tools, APIs, and external data | A2CR is exposed to agents through MCP, but MCP itself is not the handoff memory |
| A2A | Connects AI agents to other AI agents for delegation, communication, and collaboration | A2CR is not an agent-to-agent protocol; WorkBaton preserves the work state that a configured agent can resume |
| A2CR | Carries compact work state across AI windows, models, tools, and time | Complements MCP and A2A by handing off `goal`, `current_state`, `next_action`, validation, and blockers across sessions |

## Current Status

Legacy local prototype retained for development reference:

- FastAPI context API
- SQLite local storage
- client-encrypted WorkBaton mode through the local stdio MCP wrapper
- fixed Slot 1-5 support
- MCP wrapper tools: `explain_a2cr_flows`, `should_save_workbaton`, `save_context`, `resume_context`, `load_context`, `list_contexts`, and WorkStash tools
- Streamlit local dashboard
- pytest coverage

The legacy local SQLite WorkBaton API is disabled by default. It must not be used as the official AI-agent save path.

Implemented Web SaaS foundation:

- Supabase/Postgres schema, RLS, and least-privileged runtime role design
- API key and Supabase JWT auth foundation
- WorkBaton Web Context API with plan limits and sanitized access logs
- client-encrypted-only WorkBaton storage
- Dashboard API that returns metadata, stats, logs, and API key state without saved content bodies
- Streamable HTTP MCP `/mcp` as a service surface; the official AI-agent path for WorkBaton is the local stdio MCP wrapper so client encryption happens before upload
- React/Vite dashboard UI for login, WorkBaton metadata, settings, API key management, and pricing
- Railway Docker build wiring, production startup guards, same-origin guard, and deployment/security runbooks

Planned Web SaaS remaining work:

- Railway/Supabase/Cloudflare project provisioning and first hosted deployment
- Cloudflare DNS/domain
- Free public preview for WorkBaton and WorkStash before paid checkout
- GitHub OSS publication, community feedback, and official MCP listing/application work
- Lemon Squeezy billing after the free preview, community loop, and Core smoke tests are stable
- WorkThreads after WorkBaton/WorkStash adoption, billing, and remaining legal work are under control

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

The old one-click local SQLite prototype launcher is not part of the active
SaaS path.

## Deployment

The MVP deployment target is one Railway Dockerfile service. The Dockerfile builds the React/Vite app, installs the Python runtime, copies `web/dist`, and starts FastAPI with Uvicorn.

Railway health check:

```text
/api/v1/health
```

Maintenance cleanup command:

```bash
python -m services.maintenance expire-contexts
```

See [deploy runbook](docs/runbooks/deploy.md) and [security runbook](docs/runbooks/security.md).

## MCP Configuration

Example only. Do not commit real API keys.

WorkBaton requires the local stdio wrapper so content is encrypted before upload. The official user-facing distribution path is the PyPI package `a2cr-mcp`, which provides the `a2cr-mcp` command. Configure exactly one MCP server named `a2cr` through this stdio wrapper for AI-agent work. Do not configure the remote `/mcp` URL directly for WorkBaton, do not guess REST endpoints, and do not use the old `AI_CLIPBOARD_*` or `A2CR_API_STYLE` settings for normal AI-agent setup.

Install or update the wrapper:

```bash
python -m pip install --upgrade a2cr-mcp
```

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
directory that contains `workbaton.key`. If neither variable is set, the default path is
`%APPDATA%\A2CR\workbaton.key` on Windows, and
`$XDG_CONFIG_HOME/a2cr/workbaton.key` or `~/.config/a2cr/workbaton.key` on
macOS/Linux.

To resume the same WorkBaton from another PC, configure the A2CR API key and
securely copy the same local client key file. The API key alone can access
encrypted slot data, but it cannot decrypt the WorkBaton body.

## Security Direction

A2CR's hosted service uses Supabase/Postgres for the data layer and Railway for
the app runtime. User-owned rows are separated with Supabase Row Level Security
(RLS) and a least-privileged `a2cr_app` runtime role. Official WorkBaton saves
are encrypted locally before upload, so the service stores ciphertext for
WorkBaton bodies rather than plaintext. Supabase and Railway publish SOC 2 /
compliance information for their platforms; that helps with vendor risk, but it
does not make A2CR itself SOC 2 certified and does not replace A2CR's own RLS,
client encryption, key hygiene, and smoke tests.

A2CR is designed so human-facing dashboards do not display saved context bodies. Dashboards should show metadata only, such as slot names, timestamps, sizes, counts, status, and logs.

WorkBaton is client-encrypted only. The local stdio MCP wrapper encrypts WorkBaton content before sending it to A2CR and keeps the client key in a local key file. A2CR stores and returns ciphertext and cannot decrypt the WorkBaton body.

Saved context bodies should not be viewable by service administrators through normal admin dashboards, support tooling, or direct database inspection. The dashboard remains metadata-only.

Important principles:

- do not log API keys or Authorization headers
- do not log saved context bodies
- do not expose decrypted content through dashboard APIs
- reject plaintext WorkBaton bodies on A2CR APIs
- use RLS and user-scoped access in the Web SaaS design
- do not put Supabase service-role keys in normal runtime environments

Users must understand that losing the local client key makes those WorkBaton slots unrecoverable. Creating a new key works for future saves, but it cannot decrypt slots saved with the old key.

## Support And Security

- General support: a2cr.mcp@gmail.com
- Security reports: a2cr.mcp@gmail.com, or GitHub Private Vulnerability Reporting
  when enabled on the public repository
- Privacy requests: a2cr.mcp@gmail.com
- X: @A2CR_MCP
- Discord: a2cr.mcp (reserved; public community/support use is pending a
  moderation policy)

Do not include secrets, API keys, Authorization headers, private database URLs,
local client key files, decrypted WorkBaton or WorkStash bodies, full chat
transcripts, or other user data in public issues.

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

## 日本語概要

A2CR は、AI エージェントの作業状態を別の会話窓・別のモデル・別の MCP 対応クライアントへ引き継ぐためのコンテキスト中継レイヤーです。

WorkBaton は、次の AI が作業を再開するために必要な最小限の状態を保存するための仕組みです。WorkStash は、ファイルパス、調査メモ、判断理由などの補助情報を WorkBaton から参照できる形で分けて扱うためのレイヤーです。

CLAUDE.md / AGENTS.md などは、プロジェクトの永続的なルールやセットアップ手順を書く場所です。WorkBaton は、今この瞬間の作業状態、検証結果、ブロッカー、次のアクションを次の AI に渡す一時的な引き継ぎです。役割が違います。

A2CR はサーバー側で LLM 推論を行いません。ユーザーは自分の AI クライアントを使い、それらのクライアントが MCP/API 経由で A2CR を呼び出します。

MCP は AI エージェントをツール、API、外部データへ接続する仕組みです。A2A は AI エージェント同士が委任・通信・協調するための仕組みです。A2CR は、AI 窓・モデル・ツール・時間をまたいで、次のセッションが再開できる作業状態を引き継ぐ仕組みです。これらは競合ではなく補完関係です。

WorkBaton 本文は、ローカル stdio MCP wrapper でアップロード前に暗号化されます。A2CR は暗号化済み本文とメタデータを保存しますが、ダッシュボードでは本文ではなくスロット名、時刻、サイズ、状態などのメタデータのみを扱う設計です。

ホスト版 A2CR は、データ層に Supabase/Postgres、アプリ層に Railway を使います。ユーザーごとのデータ分離は Supabase RLS と least-privileged `a2cr_app` runtime role で行い、公式 WorkBaton 経路では送信前に端末側で暗号化するため、A2CR は WorkBaton 本文の暗号文を保存します。Supabase と Railway は SOC 2 / compliance 情報を公開していますが、それは A2CR 自体が SOC 2 認証済みという意味ではなく、A2CR 側の RLS、クライアント暗号化、鍵管理、スモークテストの代わりにはなりません。

初回公開は無料プレビューとして進め、課金、WorkThreads、本番 SLA は後続フェーズで扱う予定です。

## License

TBD before OSS publication. Choose and add an open-source license before making the repository public.
