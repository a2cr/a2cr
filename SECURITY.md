# Security Policy

A2CR is an early prototype and is not production-ready yet.

## Reporting a Vulnerability

Until a public contact channel is decided, please do not publish vulnerability details publicly. Use a private GitHub security advisory or contact the repository owner directly.

## Security Scope

Sensitive areas include:

- API key generation, storage, and verification
- encrypted WorkBaton context bodies
- planned WorkThreads message bodies
- dashboard APIs that must not return saved content bodies
- logs and audit events
- Supabase RLS and user isolation in the planned Web SaaS
- deployment secrets such as Fernet keys, DB URLs, Supabase keys, Stripe keys, and OAuth secrets

## Current Guarantees

The current local prototype uses application-layer encryption for saved context bodies and API-key based local access.

The project does not currently claim:

- production readiness
- full end-to-end encryption
- zero-knowledge encryption
- autonomous server-side AI execution

## Public Repository Hygiene

Before making this repository public, confirm that no secrets, local API keys, `.env` files, logs, local databases, or private MCP configs are tracked.

---

## 日本語圏向けセキュリティ方針

A2CRはまだ初期プロトタイプであり、本番運用できる状態ではありません。

### 脆弱性の報告

公開用の連絡先が決まるまでは、脆弱性の詳細を公開issueなどに書かないでください。GitHubのprivate security advisory、またはリポジトリ所有者への非公開連絡を使ってください。

### セキュリティ上重要な範囲

- APIキーの生成、保存、検証
- 暗号化されたWorkBaton本文
- 今後実装予定のWorkThreads message本文
- 保存本文を返してはいけないdashboard API
- access logと監査イベント
- Web SaaS版で予定しているSupabase RLSとユーザー分離
- Fernet key、DB URL、Supabase key、Stripe key、OAuth secretなどのdeployment secret

### 現時点で保証しないこと

このプロジェクトは現時点では、次のものを保証しません。

- 本番運用可能であること
- 完全なE2E暗号化
- ゼロ知識暗号化
- サーバー側での自律AI実行

GitHubで公開する前に、secret、ローカルAPIキー、`.env`、ログ、ローカルDB、private MCP設定がtrackされていないことを必ず確認してください。
