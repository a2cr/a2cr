# A2CR Web SaaS Implementation Plan

> **For agentic workers:** この計画はWeb SaaS版だけを対象にする。既存ローカルMVPは参照実装であり、製品スコープには含めない。各Taskはチェックボックス単位で進め、検証が通るまで次のTaskへ進まない。

**Goal:** Railway + Supabase + FastAPI + React/Vite + HTTP MCPで、AI作業文脈を安全にクラウド保存し、新しいAI窓からすぐ再開できるWeb SaaSを実装する。

**Core value:** ローカルファイルではなく、クラウド上の共通slotをMCP対応AIエージェントが別窓・別端末・別クライアントから読めること。

**Naming:** サービス名は **A2CR**、展開名は **Agent-to-Agent Context Relay**。無料機能は **WorkBaton**、Pro機能は **WorkThreads**、技術名は **A2CR MCP / A2CR API** とする。`A2CR Protocol` は将来の成否を見て判断し、MVPでは前面に出さない。

**Primary success criteria:**

- Google OAuthでログインできる
- ダッシュボードからAPIキーを発行できる
- MCP/APIキー経由で `save_context` / `resume_context` / `load_context` / `list_contexts` が動く
- `save_context` 成功時に新窓へ貼る再開プロンプトが返る
- ダッシュボードはslot本文を復号・表示せず、metadata / stats / access logsだけを表示する
- Freeプランの制限が強制される
- 通常Runtimeに `SUPABASE_SERVICE_ROLE_KEY` を置かない
- RLSで全経路のユーザー分離を検証できる

---

## Assumptions

- 初期リリースでは全ユーザーを `free` として作成する。
- Proは5 USD/month予定としてUIとDB設計だけ入れる。Stripe課金実装は今回含めない。
- Supabase AuthのGoogle OAuth設定はSupabase側で行う。
- RailwayはFastAPIがReact build済みSPAも配信する1サービス構成にする。
- ローカルMVPのSQLite/Streamlit実装は移植元ではなく、UXとAPI挙動の参考として扱う。

## Non-goals

- ローカルアプリ、常駐ローカルサーバー、ローカルDB版
- Stripe決済、請求ポータル、税計算
- チーム機能、組織管理
- 複数APIキー
- ダッシュボードでの保存本文閲覧
- 管理者が任意ユーザーの本文を読む機能

---

## Target File Map

最小構成で始める。必要になるまでmonorepo風の分割はしない。

```text
(project root)
├── main.py
├── routers/
│   ├── context.py              # /api/v1/context/*
│   ├── dashboard.py            # /api/dashboard/*
│   ├── auth.py                 # API key issue/revoke, current user helpers
│   └── health.py
├── services/
│   ├── config.py
│   ├── db.py                   # Postgres connection and transaction scope
│   ├── auth.py                 # Supabase JWT + API key auth
│   ├── crypto.py               # content encryption/decryption
│   ├── limits.py               # plan limits and rate limiting
│   ├── logs.py                 # sanitized access log writes
│   ├── context.py              # save/load/list/resume/delete logic
│   └── prompts.py              # save/resume prompt generation
├── mcp/
│   └── server.py               # Streamable HTTP MCP tools
├── web/
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
├── supabase/
│   └── migrations/
├── tests/
│   ├── test_rls.py
│   ├── test_auth.py
│   ├── test_context_api.py
│   ├── test_limits.py
│   └── test_dashboard_api.py
└── docs/
```

---

## Task 1: Supabase Schema, RLS, And DB Functions

**Goal:** 先にデータ境界を完成させる。ここが通るまでAPIやUIへ進まない。

**Files:**

- Create: `supabase/migrations/001_base_schema.sql`
- Create: `tests/test_rls.py`

- [ ] **Step 1: Create least-privileged runtime role**

`a2cr_app` を作成し、Runtimeからはこのroleだけで接続する。`SUPABASE_SERVICE_ROLE_KEY` は通常のRailway環境変数に置かない。

Verify:

- `a2cr_app` は必要なschema/table/function以外へアクセスできない
- service roleなしで通常操作が動く
- service roleがない状態をCI/起動時チェックで検出できる

- [ ] **Step 2: Add `app.current_user_id()`**

`SET LOCAL app.user_id = '<uuid>'` を参照するDB関数を作る。未設定時はNULLを返し、RLSは通さない。

Verify:

- `SET LOCAL app.user_id` 未設定では `contexts` / `stats` / `user_profiles` / `api_keys` / `access_logs` が読めない
- user Aのtransactionではuser Bの行が読めない

- [ ] **Step 3: Create tables**

Create:

- `contexts`
- `stats`
- `user_profiles`
- `api_keys`
- `access_logs`

Important constraints:

- `contexts.content` は暗号化済み本文だけを保存する
- `contexts.slot_number` はユーザー内固定の表示位置として保存する
- `user_profiles.plan` は `free` / `pro`
- Free retention: `900, 1800, 3600, 10800, 21600, 43200, 86400`
- Pro retention: `900, 1800, 3600, 10800, 21600, 43200, 86400, 259200, 604800, 864000, 1209600, 2592000`
- Free detail: `compact` only
- API keyは1 user 1 key

Verify:

- 不正なretentionがDB constraintで拒否される
- Freeで `detailed` を設定できない
- 同一user内で同名active slotは一意
- 同一user内で同じ `slot_number` のactive slotは一意

- [ ] **Step 4: Add API key verification function**

APIキー照合だけは `SECURITY DEFINER` 関数で行い、一致した `user_id` だけを返す。`key_hash`、plaintext、他ユーザー情報は返さない。

Verify:

- 正しいHMAC hashだけが一致する
- revoked keyは通らない
- 関数戻り値にsecretやkey metadataが含まれない

- [ ] **Step 5: Add stats and expiration functions**

Stats更新はDB側の関数/triggerで原子的に行う。期限切れ削除は本文を復号せず、削除直前に `context.expire` を `client_type=system` で記録する。

Verify:

- save成功で累計保存回数が増える
- load/resume成功で累計ロード回数が増える
- 期限切れ削除で `context.expire` が残る
- `context.delete` と `context.expire` をログ上で区別できる

- [ ] **Step 6: Add RLS policies**

All user tables enable RLS and use `app.current_user_id()` for separation.

Verify:

- dashboard JWT path, API key path, MCP pathのすべてで同じRLS境界を使える
- cross-user select/update/deleteが失敗する
- dashboard APIが本文を返せないことをテストで確認する

---

## Task 2: FastAPI Security Foundation

**Goal:** HTTP層の認証、DB transaction、ログsanitizeを先に実装する。

**Files:**

- Update: `services/config.py`
- Update/Create: `services/db.py`
- Create: `services/auth.py`
- Create: `services/logs.py`
- Create: `tests/test_auth.py`

- [ ] **Step 1: Configuration**

Required env:

- `DATABASE_URL`
- `FERNET_KEY`
- `API_KEY_HASH_SECRET`
- `SUPABASE_JWT_SECRET` or JWKS settings
- `A2CR_SERVICE_URL`
- `APP_ENV`

Reject startup when runtime contains `SUPABASE_SERVICE_ROLE_KEY`.

Verify:

- Missing required env fails fast
- Service role env present in runtime fails fast

- [ ] **Step 2: Supabase JWT auth**

Dashboard APIs accept Supabase JWT and extract user id after signature/audience/expiry verification.

Verify:

- expired JWT rejected
- wrong audience rejected
- unsigned or malformed JWT rejected

- [ ] **Step 3: API key auth**

API/MCP use `Authorization: Bearer sk-...` and verify with HMAC-SHA256 + DB function.

Verify:

- plaintext key is never persisted
- bad key returns 401 with generic error
- `Authorization` header is never logged

- [ ] **Step 4: Transaction user context**

Every authenticated request opens a DB transaction and sets `SET LOCAL app.user_id`.

Verify:

- user id cannot leak across pooled connections
- request without authenticated user cannot access user rows

- [ ] **Step 5: Sanitized logging helper**

Access logs can store action, result, slot_name, plan, client_type, approximate size, request id, hashed IP prefix, and coarse user agent. They must not store content, API keys, Authorization headers, full request bodies, raw IP, or full UA.

Verify:

- log rows contain no content fragments
- log rows contain no `sk-`
- log rows contain no `Bearer`

---

## Task 3: Context API And Plan Limits

**Goal:** AIエージェント向けAPIを安全な制限付きで完成させる。

**Files:**

- Update: `routers/context.py`
- Update: `models/schemas.py`
- Create: `services/limits.py`
- Update: `services/context.py`
- Create: `services/prompts.py`
- Create: `tests/test_context_api.py`
- Create: `tests/test_limits.py`

- [ ] **Step 1: Implement plan limits**

Free:

- active slots: 3
- retention: 15m / 30m / 1h / 3h / 6h / 12h / 24h, default 24h
- max body: 32KB
- detail: compact only
- saves: 100/hour
- loads: 300/hour
- access logs: 24h
- API keys: 1

Pro:

- active slots: 100
- retention: 15m / 30m / 1h / 3h / 6h / 12h / 24h / 3d / 7d / 10d / 14d / 30d, default 30d
- max body: 128KB
- detail: compact / detailed
- saves: 1000/hour
- loads: 3000/hour
- access logs: 30d
- API keys: 1

Verify:

- over-limit save returns 429 + `retry_after`
- invalid retention returns 422 `retention_not_allowed`
- oversized body returns 413 or 422 without logging body

- [ ] **Step 2: Save context**

`POST /api/v1/context` encrypts content, applies retention, writes logs, updates stats, and returns `resume_context_call` + `resume_prompt`.

Verify:

- same slot overwrite does not increase active slot count
- same `slot_number` overwrite does not move other slots
- new slot over Free limit is rejected
- response prompt contains service URL and slot name only
- response prompt explicitly says to use the A2CR MCP tool and not guessed direct HTTP endpoints
- response prompt contains no content/API key/private URL

- [ ] **Step 3: List context metadata**

`GET /api/v1/contexts` returns active slot metadata only.

Verify:

- content is not returned
- expired slots are not listed
- cross-user rows are not listed

- [ ] **Step 4: Load context**

`GET /api/v1/context/{slot_name}` decrypts content only for API/MCP path.

Verify:

- expired slot returns not_found
- dashboard path cannot call this without API key
- load count and access log are updated

- [ ] **Step 5: Resume context**

`GET /api/v1/context/resume` supports `slot_name`, `project`, and `prefer_latest`.

Verify:

- exact slot loads immediately
- one project candidate loads immediately
- multiple candidates without `prefer_latest` returns metadata only
- candidates-only response does not count as content load

- [ ] **Step 6: Delete context**

Explicit delete logs `context.delete` and does not produce `context.expire`.

Verify:

- user can delete own slot
- user cannot delete another user's slot
- explicit and automatic deletion are distinguishable in logs

---

## Task 4: Dashboard API

**Goal:** React dashboardが必要な情報だけを取得できるAPIを作る。本文は返さない。

**Files:**

- Create: `routers/dashboard.py`
- Update: `routers/auth.py`
- Create: `tests/test_dashboard_api.py`

- [ ] **Step 1: Current profile and settings**

Endpoints:

- `GET /api/dashboard/profile`
- `PATCH /api/dashboard/profile`

Editable:

- `default_retention_seconds`
- `context_detail_level` where allowed
- `preferred_locale`
- `response_language`
- `timezone`

Verify:

- plan cannot be changed via dashboard API
- Free cannot set `detailed`
- invalid locale/timezone rejected

- [ ] **Step 2: Slot metadata**

`GET /api/dashboard/contexts` returns slot name, created/updated/expires, size, token estimate, source metadata, and generated resume prompt.

Verify:

- response does not include encrypted content
- response does not include decrypted content

- [ ] **Step 3: Stats and access logs**

Endpoints:

- `GET /api/dashboard/stats`
- `GET /api/dashboard/access-logs?limit=100`

Verify:

- access logs are scoped to current user
- logs contain no secret/content fields
- log retention pruning follows plan

- [ ] **Step 4: API key management**

Endpoints:

- `POST /api/dashboard/api-key`
- `DELETE /api/dashboard/api-key`

Verify:

- plaintext key is shown only once
- issuing a new key revokes/replaces previous key
- key hash uses HMAC secret, not raw SHA-256 alone

---

## Task 5: Streamable HTTP MCP

**Goal:** 新規AI窓で `resume_context(slot_name="...")` からすぐ再開できる。

**Files:**

- Update: `mcp/server.py`
- Create: `tests/test_mcp.py`

- [ ] **Step 1: Choose MCP library**

Streamable HTTP対応済みライブラリを使う。手動JSON-RPC実装はしない。実装前に利用ライブラリの現在仕様を確認する。

Verify:

- `/mcp` single endpointでPOSTと必要なGETが動く
- `MCP-Session-Id` を使う実装ならsession検証が動く
- method/nameヘッダーとbody不一致を拒否できる

- [ ] **Step 2: Implement tools**

Tools:

- `save_context`
- `resume_context`
- `load_context`
- `list_contexts`
- `get_account_limits`

Verify:

- MCP save returns `resume_prompt`
- `resume_prompt` uses `slot_name` as the primary resume path and `slot_number` only as an optional compatible path
- `resume_prompt` explicitly says to use the MCP tool and not guessed direct HTTP endpoints
- MCP resume loads exact slot by `slot_number` or `slot_name`
- MCP load accepts `slot_number` or `slot_name`
- MCP ambiguous resume returns candidates only
- auth failure does not leak whether slot exists

- [ ] **Step 3: Client compatibility checks**

Verify with at least:

- Codex MCP config
- Claude Desktop compatible config if available
- plain HTTP integration test

Expected:

- API key is sent as Authorization header
- Japanese prompt produces Japanese continuation
- English prompt produces English continuation

- [ ] **Step 4: AI client guidance artifacts**

Implement and publish the guidance surfaces that help AI agents use A2CR correctly.

Required:

- MCP tool descriptions and JSON schemas contain required fields, compact/detailed guidance, secret prohibitions, and the "do not guess direct HTTP API" rule
- `save_context` responses include `resume_context_call` and `resume_prompt`
- dashboard setup text explains that `SKILL.md` is optional and client-specific
- public template exists at `docs/templates/skills/a2cr-agent/SKILL.md`

Verify:

- WorkBaton save/load/resume works without installing any Skill
- Codex with the optional Skill follows `resume_context` first and avoids direct HTTP guesses
- Skill text does not contain API keys, private URLs, or user-specific secrets
- MCP config examples only contain URL/auth configuration, not long embedded prompts

---

## Task 6: React/Vite Dashboard

**Goal:** 本文を見せないSaaS dashboardを作る。ローカルStreamlitで固めたUXは参考にするが、実装はReactで作る。

**Files:**

- Create: `web/package.json`
- Create: `web/vite.config.ts`
- Create: `web/src/*`

- [ ] **Step 1: App shell**

Pages:

- `/login`
- `/dashboard`
- `/settings`
- `/pricing`

Verify:

- unauthenticated user is redirected to login
- authenticated user can reload routes directly
- FastAPI serves SPA fallback for non-API paths

- [ ] **Step 2: Dashboard**

Show:

- slot cards
- fixed slot numbers
- active slot count
- cumulative saves/loads/token estimate
- copy save prompt
- copy resume prompt per slot
- access log summary

Do not show:

- saved context body
- decrypted content
- API key after initial issue

Verify:

- network response for dashboard contains no content field
- copy prompts wrap correctly on desktop/mobile
- empty state works

- [ ] **Step 3: Settings**

Settings:

- default retention
- context detail level
- locale
- response language
- timezone
- API key issue/revoke

Verify:

- Free retention options capped at 24h
- Pro options appear only when `plan=pro`
- language setting persists after reload

- [ ] **Step 4: i18n**

Use `i18next` / `react-i18next`. Initial locales: `en`, `ja`; fallback: `en`.

Verify:

- switching language does not reset theme/settings
- date/time respects timezone
- unsupported locale falls back cleanly

- [ ] **Step 5: Frontend security**

Add CSP-compatible implementation, avoid inline secret exposure, and keep Supabase anon key only on client.

Verify:

- no secret env is embedded in JS bundle
- access token is not printed in console/logs
- API errors do not expose internals

---

## Task 7: Deployment And Operations

**Goal:** Railway本番に安全に出せる状態にする。

**Files:**

- Create/Update: `Dockerfile`
- Create/Update: `railway.json`
- Update: `README.md`
- Create: `docs/runbooks/security.md`
- Create: `docs/runbooks/deploy.md`

- [ ] **Step 1: Build pipeline**

Build React, then serve static assets from FastAPI.

Verify:

- production image starts without dev server
- `/api/v1/health` works
- `/dashboard` direct access returns SPA

- [ ] **Step 2: Environment hardening**

Railway env:

- no service role key
- generated Fernet key
- generated API key hash secret
- public `A2CR_SERVICE_URL`
- production CORS disabled or same-origin only

Verify:

- startup fails on unsafe env
- CORS rejects unexpected origins

- [ ] **Step 3: Cleanup scheduler**

Use a narrow maintenance DB function or protected scheduled job. It must only expire due contexts and write sanitized `context.expire` logs.

Verify:

- job cannot read/decrypt content
- job cannot delete non-expired rows
- job is idempotent

- [ ] **Step 4: Monitoring**

Track:

- auth failures
- rate-limit spikes
- save/load counts
- cleanup failures
- DB errors

Verify:

- security events do not contain secrets
- alerting path exists for cleanup failure and auth anomaly

---

## Task 8: Pro WorkThreads

**Goal:** Pro向けに、AIエージェント同士が人間非表示の非同期threadでレビュー・反論・統合できる基盤を追加する。これはpost-MVP拡張であり、Slot保存/ロードの公開beta後に着手する。

**Boundary:** WorkThreadsはCoreと論理的に別サービスとして設計する。初期実装では同じRailway serviceと同じSupabase Postgresに同居させるが、API、service module、DB table、rate limit、monitoringを分け、将来worker/Redis/別Railway serviceへ分離できるようにする。

**Files:**

- Create: `supabase/migrations/00x_agent_threads.sql`
- Create: `routers/agent_threads.py`
- Create: `services/agent_threads.py`
- Create: `tests/test_agent_threads.py`
- Update: `mcp/server.py`
- Update: `web/src/*`

- [ ] **Step 1: Schema**

Create:

- `agent_threads`
- `agent_messages`
- `agent_tasks`
- `agent_runs`

Rules:

- `agent_messages` is append-only
- `agent_messages.content` is encrypted
- dashboard APIs never return `agent_messages.content`
- message table is range-partition ready by `created_at`
- high volume mode uses daily partitions

Verify:

- cross-user RLS isolation
- dashboard metadata response contains no content
- AI/MCP read path can decrypt messages
- WorkThreads tables do not require writes to Core `contexts`

- [ ] **Step 2: Task claim and leases**

Implement `claim_agent_task` with `SELECT ... FOR UPDATE SKIP LOCKED`.

Verify:

- two agents cannot claim the same task
- expired leases can be reclaimed
- task complete requires matching `lease_owner`
- DB transaction is closed before any AI work begins
- claim/lease code can move to a worker service without changing Core context APIs

- [ ] **Step 3: Agent message flow**

Tools/APIs:

- `create_agent_thread`
- `post_agent_message`
- `read_agent_thread`
- `claim_agent_task`
- `complete_agent_task`
- `save_thread_result`

Verify:

- messages are inserted, not updated
- idempotency key/content hash prevents accidental duplicate post
- final result can be saved to a normal Slot
- WorkThreads APIs remain under `/api/v1/agent-*`

- [ ] **Step 4: Human-hidden dashboard**

Dashboard shows only:

- thread title/purpose/status
- message count
- task count/status
- agent names
- last activity time
- final result Slot link

Dashboard does not show:

- message content
- encrypted message body
- prompts
- full AI responses

Verify:

- browser network payload contains no message content
- search/indexing cannot expose message content

- [ ] **Step 5: Lock, timeout, and load tests**

Test:

- 5,000 messages/day/user
- 100,000 total messages/day
- concurrent task claim
- p95/p99 latency
- lock wait
- deadlock count

Verify:

- p95/p99 remain within chosen SLA
- deadlocks are zero or extremely rare and safely retried
- lock timeout records sanitized `agent_runs.status='timeout'`

- [ ] **Step 6: Physical separation readiness**

Document and test the split boundary.

Verify:

- WorkThreads can run with its own router/service module disabled without breaking Core
- Core remains the source of truth for user id, plan, API key, and billing state
- WorkThreads uses explicit interfaces to check `user_id` and `plan`
- Redis/Upstash can be added for rate limit or fan-out without schema changes to Core
- load tests identify whether separation is needed before public Pro rollout

---

## Security Gates

These gates must pass before public beta. WorkThreads gates apply before WorkThreads is enabled for Pro users.

- [ ] **Gate A: No runtime service role**

Railway runtime does not contain `SUPABASE_SERVICE_ROLE_KEY`; app startup rejects it.

- [ ] **Gate B: RLS tenant isolation**

Automated tests prove user A cannot read/update/delete/list user B data across dashboard/API/MCP paths.

- [ ] **Gate C: Dashboard content blindness**

Dashboard API and React network payloads never include encrypted or decrypted context body.

- [ ] **Gate D: Secret-safe logging**

Access logs and app logs contain no content, API keys, Authorization headers, raw IPs, or full UAs.

- [ ] **Gate E: Abuse controls**

Free and Pro limits enforce active slots, retention, save rate, load rate, body size, and API key count.

- [ ] **Gate F: MCP compatibility**

`resume_context` works from a fresh AI window without requiring `list_contexts` first when slot name is known.

- [ ] **Gate G: Expiration auditability**

Automatic expiration writes `context.expire`; explicit delete writes `context.delete`.

- [ ] **Gate H: Multilingual behavior**

Stored context can be English-first, but loaded/resumed answer language follows the user's current message language.

- [ ] **Gate I: WorkThreads human-hidden content**

Pro WorkThreads message content is never returned by dashboard APIs or React payloads. Only MCP/API-key agent routes can read decrypted messages.

- [ ] **Gate J: WorkThreads lock safety**

WorkThreads implementation uses append-only messages, short transactions, leases, `FOR UPDATE SKIP LOCKED`, lock timeout, and load tests before public availability.

- [ ] **Gate K: WorkThreads separation boundary**

WorkThreads can be disabled or moved to a worker/service without breaking Core save/load/resume, auth, billing state, or dashboard context metadata.

---

## Recommended Implementation Order

1. Task 1: Supabase schema/RLS/functions
2. Task 2: FastAPI auth/DB/logging foundation
3. Task 3: Context API and limits
4. Task 5: MCP tools
5. Task 4: Dashboard API
6. Task 6: React dashboard
7. Task 7: Deployment/ops
8. Task 8: Pro WorkThreads

MCP can start before the final dashboard because the product's core value is AI-window resume. The dashboard API should still be implemented before the React UI so the UI never has to reach into unsafe data directly.

## First Concrete Next Step

Start with `supabase/migrations/001_base_schema.sql` and `tests/test_rls.py`.

Minimum first milestone:

- `contexts`, `user_profiles`, `api_keys`, `access_logs`, `stats`
- `app.current_user_id()`
- API key verification DB function
- RLS policies
- cross-user isolation tests
- runtime role permission tests

When this milestone passes, the rest of the SaaS can be built on a secure base instead of patching isolation later.

## WorkThreads Clarification Addendum

Updated: 2026-05-04

Task 8 should be read with this corrected product meaning:

WorkThreads is a persistent cross-window and cross-agent work thread. It exists because current subagents are scoped to a single parent conversation/session. The feature should let a task survive across AI windows, AI clients, AI vendors, and devices. Claude, Codex, Cursor, or any MCP-capable client should be able to append to and resume the same work thread without the user manually re-explaining the task.

Do not frame Task 8 as generic AI-agent debate or social collaboration. The implementation target is durable handoff and coordination:

- append-only work notes
- failed attempts
- task claims and leases
- verification results
- final result links
- shared thread state that does not depend on the original chat window remaining alive

Additional Task 8 verification:

- A thread can be created by one API/MCP client and read or continued by another client for the same user.
- Thread state remains available after the original AI chat window is gone.
- Tests and docs use cross-window/cross-agent handoff language, not "agents chatting" language.
- Dashboard exposes only progress metadata while AI/MCP routes can read decrypted thread messages.
- The final result can be saved back to a normal A2CR Slot for Core resume flows.

## Service Selection Addendum

Updated: 2026-05-04

Use this service stack for the Web SaaS implementation:

| Area | Service | Implementation impact |
|---|---|---|
| Frontend + Backend + MCP | Railway | One FastAPI runtime serves React/Vite build, `/api/*`, and `/mcp` |
| DB/Auth/RLS | Supabase | Use Supabase Auth, Postgres, migrations, RLS, runtime role `a2cr_app` |
| Domain/DNS/CDN | Cloudflare | Manage domain, DNS, SSL/TLS, DNSSEC, and basic edge protection |
| Payment | Stripe | Add after Core MVP; webhook updates paid plan state |
| Source/CI | GitHub | Repository, PRs, Actions/deploy automation |
| Google Login | Google Cloud OAuth | OAuth Client ID/secret configured in Supabase Auth |

Do not add Vercel for MVP. The app should remain same-origin on Railway so auth, cookies/headers, CORS, public service URL, `/api`, and `/mcp` stay simple. Do not move the frontend to Vercel unless a later production requirement clearly justifies the split and Vercel Pro cost.

Do not switch Core to Firebase/Firestore. The implementation plan depends on Postgres RLS, SQL migrations, `SET LOCAL app.user_id`, and least-privileged runtime DB roles. Switching to Firestore would invalidate Task 1 and most security verification gates.

MVP contract/setup order:

1. GitHub repository
2. Cloudflare account and domain
3. Railway Hobby project
4. Supabase project on Free for development, Pro before production
5. Google Cloud OAuth client for Supabase Auth
6. Stripe account, with billing flows enabled after Core is stable

Later services:

- Sentry before public beta for error monitoring
- PostHog after MVP if product analytics are needed
- Resend when transactional email is added
- Upstash Redis when Postgres-backed rate limiting or queues become insufficient

Verification updates:

- Deployment tests must confirm one public Railway origin serves SPA, `/api/v1/health`, and `/mcp`.
- Runtime startup must reject `SUPABASE_SERVICE_ROLE_KEY`.
- Browser bundle must contain only public Supabase anon config, never DB URLs, API key hash secrets, audit secrets, or service role keys.
- Stripe webhooks must verify signatures before changing `user_profiles.plan`.
