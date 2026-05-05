# A2CR Security Runbook

This runbook covers operational security for the Web SaaS MVP.

## Runtime Secret Rules

Never put these in the browser bundle, logs, GitHub, or support tools:

- `DATABASE_URL`
- `FERNET_KEY`
- `API_KEY_HASH_SECRET`
- `AUDIT_HASH_SECRET`
- `SUPABASE_JWT_SECRET`
- `SUPABASE_SERVICE_ROLE_KEY`
- Stripe and Google OAuth secrets

`SUPABASE_SERVICE_ROLE_KEY` must not exist in the normal Railway runtime. It is only for migrations or emergency admin work in a separate, short-lived environment.

## Content Visibility

Dashboards and ordinary admin/support views must not display:

- WorkBaton saved bodies
- WorkThreads message bodies
- AI prompts or AI response bodies
- full API keys
- Authorization headers

Saved bodies are encrypted in the application layer. A service administrator should not be able to read bodies through normal dashboards, support tools, or direct DB inspection. This is not a zero-knowledge claim because the A2CR server decrypts content in memory when returning authenticated MCP/API responses for the user.

## Startup Guards

Production startup must fail when:

- `SUPABASE_SERVICE_ROLE_KEY` is present
- required Web SaaS env values are missing
- `FERNET_KEY` is not a valid Fernet key
- production `A2CR_SERVICE_URL` is not HTTPS
- production hash/audit secrets are too short

## Same-Origin Policy

Production is same-origin by default. React, FastAPI, and `/mcp` are served from the same public origin.

Unexpected browser `Origin` values are rejected with 403 and no `Access-Control-Allow-Origin` header. MCP/API clients that do not send `Origin` are unaffected.

## Logging Rules

Access logs may contain:

- action
- result
- error code
- request id
- slot name
- size
- timestamp
- hashed IP / hashed user agent when needed

Access logs must not contain:

- saved body content
- API key or Authorization header
- raw IP address
- full User-Agent
- database URLs or secrets

## Monitoring Signals

Track these metrics/events:

- auth failure count
- rate-limit responses
- save/load/delete counts
- cleanup job failures
- DB connection errors
- unexpected origin rejections
- API key issue/revoke events

Initial alert paths:

- cleanup job failure: check Railway job logs, then run `python -m services.maintenance expire-contexts` manually
- auth anomaly: check rate-limited/auth failure counts and rotate affected API keys if needed
- DB errors: confirm Supabase availability, connection limit, and `a2cr_app` role permissions

## Incident Steps

1. Stop or roll back the affected Railway deploy.
2. Preserve logs without exporting secrets or request bodies.
3. Revoke exposed API keys.
4. Rotate runtime secrets if exposure is plausible.
5. Re-run smoke checks before reopening traffic.

---

## 概要

このrunbookはA2CR Web SaaS MVPの運用セキュリティ手順です。

## runtime secretの扱い

`DATABASE_URL`、`FERNET_KEY`、`API_KEY_HASH_SECRET`、`AUDIT_HASH_SECRET`、`SUPABASE_JWT_SECRET`、Stripe/Google OAuth secretは、ブラウザbundle、ログ、GitHub、通常のサポート画面に出しません。

`SUPABASE_SERVICE_ROLE_KEY` は通常Railway runtimeに置きません。migrationや緊急管理作業だけ、通常runtimeと分けた短時間の環境で使います。

## 本文の見え方

人間向けダッシュボード、通常管理画面、サポート画面ではWorkBaton本文、WorkThreads本文、AIプロンプト本文、AI応答本文、APIキー全文、Authorization headerを表示しません。

保存本文はアプリ層暗号化します。DBを直接見てもサービス管理者が本文を読めない設計にします。ただし、A2CRサーバーはユーザーのためにMCP/APIレスポンスを返す際、処理中メモリ上で本文を復号するため、ゼロ知識とは表現しません。

## 起動時ガード

本番起動時には、service role key混入、必須env不足、不正なFernet key、HTTPの `A2CR_SERVICE_URL`、短すぎるhash/audit secretを拒否します。

## CORS / same-origin

本番は同一origin前提です。想定外の `Origin` は403で拒否します。通常のMCP/APIクライアントのように `Origin` を送らない通信は影響を受けません。

## 監視

auth失敗、rate limit、save/load/delete数、cleanup失敗、DBエラー、想定外Origin拒否、API key発行/失効を追います。cleanup失敗時はRailway job logを確認し、必要なら `python -m services.maintenance expire-contexts` を手動実行します。
