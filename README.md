# A2CR

Agent-to-Agent Context Relay.

A2CR helps AI agents save and resume work context across conversation windows, tools, and clients. The current repository is an early local prototype plus design work for the planned Web SaaS version.

## Product Layers

| Layer | Purpose |
|---|---|
| WorkBaton | Save a short-lived work checkpoint and resume it in a new AI window |
| WorkThreads | Planned shared work threads for active AI-agent coordination |

A2CR does not run LLM inference on the server in the MVP. It does not think for your agents, choose models, or generate reviews. Users bring their own AI clients, and those clients call A2CR through MCP/API.

This keeps A2CR model-neutral and keeps pricing tied to storage, requests, and coordination rather than token burn.

## Current Status

Implemented locally:

- FastAPI context API
- SQLite local storage
- Fernet application-layer encryption for saved context bodies
- fixed Slot 1-3 support
- MCP wrapper tools: `save_context`, `resume_context`, `load_context`, `list_contexts`
- Streamlit local dashboard
- pytest coverage

Implemented Web SaaS foundation:

- Supabase/Postgres schema, RLS, and least-privileged runtime role design
- API key and Supabase JWT auth foundation
- WorkBaton Web Context API with plan limits and sanitized access logs
- Dashboard API that returns metadata, stats, logs, and API key state without saved content bodies
- Streamable HTTP MCP `/mcp` with `save_context`, `resume_context`, `load_context`, `list_contexts`, and `get_account_limits`
- React/Vite dashboard UI for login, WorkBaton metadata, settings, API key management, and pricing
- Railway Docker build wiring, production startup guards, same-origin guard, and deployment/security runbooks

Planned Web SaaS remaining work:

- Railway/Supabase/Cloudflare project provisioning and first hosted deployment
- Cloudflare DNS/domain
- Stripe billing after the Core MVP is stable
- WorkThreads after WorkBaton Core is solid

## Local Development

```bash
pip install -r requirements.txt
python -m pytest -q
cd web
npm install
npm run build
```

On Windows, the local prototype can be started with:

```bat
start.bat
```

Local services:

```text
API:       http://localhost:8000
Dashboard: http://localhost:8501
Web dev:   http://localhost:5173
```

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

Web SaaS Streamable HTTP example:

```json
{
  "mcpServers": {
    "a2cr": {
      "url": "https://a2cr.example/mcp",
      "headers": {
        "Authorization": "Bearer <your-a2cr-api-key>"
      }
    }
  }
}
```

Local prototype stdio example:

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

## Security Direction

A2CR is designed so human-facing dashboards do not display saved context bodies. Dashboards should show metadata only, such as slot names, timestamps, sizes, counts, status, and logs.

Saved context bodies should not be viewable by service administrators through normal admin dashboards, support tooling, or direct database inspection. Content is stored encrypted, and decrypted bodies are only returned through authenticated MCP/API paths that are acting for the user.

Important principles:

- do not log API keys or Authorization headers
- do not log saved context bodies
- do not expose decrypted content through dashboard APIs
- use application-layer encryption for content storage
- use RLS and user-scoped access in the Web SaaS design
- do not put Supabase service-role keys in normal runtime environments

The project does not currently claim full end-to-end or zero-knowledge encryption.

## Documentation

- Product spec and progress: `docs/superpowers/specs/2026-05-05-a2cr-product-spec-and-progress.md`
- WorkBaton save/load quality spec: `docs/superpowers/specs/2026-05-05-workbaton-save-load-quality-spec.md`
- Web SaaS design: `docs/superpowers/specs/2026-05-03-web-saas-design.md`
- Implementation plan: `docs/superpowers/plans/2026-05-04-web-saas-implementation-plan.md`
- Deploy runbook: `docs/runbooks/deploy.md`
- Security runbook: `docs/runbooks/security.md`
- Optional AI client Skill template: `docs/templates/skills/a2cr-agent/SKILL.md`
- GitHub publication draft: `docs/github-publication-draft.md`

## License

TBD. Keep the repository private until the license policy is decided.

---

## 概要

A2CRは、AIエージェントの作業文脈を別の会話窓、別のAIクライアント、別の端末へ引き継ぐためのサービスです。

現在のリポジトリには、ローカルプロトタイプとWeb SaaS版の設計資料が含まれています。MVP段階では、A2CRサーバー自身はLLM推論を実行しません。A2CRはAIエージェントの代わりに考えず、モデル選択やレビュー生成も行いません。Claude、Codex、CursorなどのMCP/API対応AIクライアントがA2CRを呼び出して、作業文脈を保存・読込・再開します。

これにより、A2CRはモデル中立のまま、料金をトークン消費ではなく保存・読込・連携の利用量に結びつける設計にします。

### 機能レイヤー

| レイヤー | 目的 |
|---|---|
| WorkBaton | 短命な作業チェックポイントを保存し、新しいAI窓で再開する |
| WorkThreads | 複数の作業中AIエージェントが同じ作業スレッドを見ながら連携する予定のPro機能 |

WorkBatonは「引き継ぎ箱」、WorkThreadsは「AIエージェント用の作業掲示板 / 共有作業スレッド」という位置づけです。

### 現在の状態

ローカルプロトタイプで実装済み:

- FastAPIによるcontext API
- SQLiteによるローカル保存
- Fernetによる本文のアプリ層暗号化
- Slot 1から3の固定スロット
- MCP wrapper tools: `save_context`, `resume_context`, `load_context`, `list_contexts`
- Streamlitのローカルダッシュボード
- pytestによる自動テスト

Web SaaS版の基盤で実装済み:

- Supabase/Postgres schema、RLS、最小権限runtime role設計
- API keyとSupabase JWTの認証基盤
- plan制限とsanitized access log付きのWorkBaton Web Context API
- 保存本文を返さないDashboard API
- `save_context`、`resume_context`、`load_context`、`list_contexts`、`get_account_limits` を持つStreamable HTTP MCP `/mcp`
- ログイン、WorkBatonメタデータ、設定、APIキー管理、料金表示のReact/ViteダッシュボードUI
- Railway向けDocker build、production起動ガード、same-origin guard、deploy/security runbook

Web SaaS版で今後実装するもの:

- Railway/Supabase/Cloudflare project作成と初回hosted deploy
- CloudflareによるDNS/ドメイン管理
- Core MVP安定後のStripe課金
- WorkBaton安定後のWorkThreads

### ローカル開発

```bash
pip install -r requirements.txt
python -m pytest -q
cd web
npm install
npm run build
```

Windowsのローカルプロトタイプは次で起動できます。

```bat
start.bat
```

ローカルサービス:

```text
API:       http://localhost:8000
Dashboard: http://localhost:8501
Web dev:   http://localhost:5173
```

### デプロイ

MVPの本番配置はRailwayのDockerfile serviceです。DockerfileはReact/Viteをbuildし、Python runtimeへ `web/dist` をコピーして、UvicornでFastAPIを起動します。

Railway health check:

```text
/api/v1/health
```

期限切れ削除のmaintenance command:

```bash
python -m services.maintenance expire-contexts
```

詳しくは [deploy runbook](docs/runbooks/deploy.md) と [security runbook](docs/runbooks/security.md) を参照してください。

### セキュリティ方針

A2CRはAI作業文脈という機密性の高い本文を扱うため、人間向けダッシュボードには保存本文を表示しない設計です。ダッシュボードに表示するのは、slot名、時刻、サイズ、件数、status、ログなどのメタデータに限定します。

保存本文は、通常の管理画面、サポート用ツール、DB直接参照だけではサービス管理者でも見られない設計にします。本文は暗号化して保存し、復号済み本文はユーザーのために動作する認証済みMCP/API経路だけで返します。

重要な方針:

- APIキーやAuthorization headerをログに残さない
- 保存本文をログに残さない
- ダッシュボードAPIから復号済み本文を返さない
- 本文はアプリ層暗号化して保存する
- Web SaaS版ではRLSとuser_id分離を使う
- Supabase service role keyを通常runtimeに置かない

初期版ではA2CRサーバーがAPI/MCPレスポンスを返すために本文を復号します。そのため、現時点では完全なE2E暗号化やゼロ知識暗号化とは表現しません。
