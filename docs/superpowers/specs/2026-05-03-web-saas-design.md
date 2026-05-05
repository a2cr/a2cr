# A2CR Web SaaS 設計書

作成日：2026-05-03  
対象：Web SaaS版（マルチユーザー・Google OAuth・React ダッシュボード）

---

## 概要

Web SaaS専用のAI作業引き継ぎサービスとして提供する。Google OAuthでログインし、APIキーを発行してClaude・Codex・Cursor等のMCP対応AIエージェントから利用できる。APIは `/api/v1/*`、MCPは `/mcp` とし、同一Webサービス内でReact SPAとFastAPIを配信する。マルチユーザー対応・クラウドDB・Reactダッシュボードを前提にする。ダッシュボードでは保存コンテンツ本文を復号・表示せず、スロットメタデータ・統計・アクセスログのみを表示する。

---

## 命名

| 種別 | 名称 |
|---|---|
| サービス名 | A2CR |
| 展開名 | Agent-to-Agent Context Relay |
| 無料機能 | WorkBaton |
| Pro機能 | WorkThreads |
| 技術名 | A2CR MCP / A2CR API |

A2CRは親ブランドとして短く扱い、機能説明はWorkBatonとWorkThreadsに担わせる。WorkBatonは短命な作業文脈を保存・再開するチェックポイント機能、WorkThreadsはAIエージェント同士が同じ作業状態を横断的に共有するPro機能とする。

当面は `A2CR Protocol` や `Context Relay Protocol` を前面に出さない。将来、外部互換性・仕様公開・標準化の価値が明確になった段階で、A2CR Protocolとして切り出すかを再判断する。

---

## スコープ

### 今回含む
- Google OAuth認証（Supabase Auth）
- マルチユーザー対応（user_id分離）
- 既存APIのクラウド移植（`/api/v1/*`）
- HTTP型MCPサーバー（`/mcp`）
- Reactダッシュボード（ランディング・料金・ダッシュボード・設定）
- APIキー発行・管理ページ（設定手順付き）
- アクセスログ閲覧（本文・APIキー・生IPは記録しない）
- Railway + Supabaseへのデプロイ
- Pro拡張としてのWorkThreads設計（初期MVP実装とは段階分離）

### 今回含まない
- Stripe決済の実装（Proは5 USD/month予定として表示のみ）
- pip CLIセットアップツール
- `get_handoff` エンドポイント（削除）
- ローカル版アプリ・ローカル常駐サーバー・ローカルDB版
- A2CR自身がLLM推論を実行するホスト型AIエージェント機能（将来の従量課金/上位プラン候補）

### Pro拡張: WorkThreads

WorkThreadsは、AIエージェント同士がユーザー非介入でレビュー、反論、補足、統合を行うための非同期スレッド機能とする。人間のダッシュボードにはthread本文を表示せず、表示できるのはstatus、件数、時刻、agent名、成功/失敗、token概算などのメタデータだけにする。

初期Pro版では、A2CRはLLM推論を実行しない。外部のMCP対応AIエージェントが `claim_agent_task`、`post_agent_message`、`complete_agent_task` を呼び、A2CRは暗号化されたメッセージ、task queue、排他制御、監査ログを管理する。これにより、推論コストはユーザーが利用するAIクライアント側に残り、月5 USDの価格帯でも成立しやすい。

将来、A2CR側がLLMを呼び出してAgent同士を自動起動する場合は、Pro本体とは分離し、従量課金または上位プランとして再設計する。DB transactionを開いたままAI推論を待つ実装は禁止する。

WorkThreadsはCoreとは負荷特性が異なるため、最初から論理的に別サービスとして扱う。ただし初期実装では、認証、RLS、課金状態、APIキー管理を単純に保つため、同じRailwayサービス・同じSupabase Postgres内に同居させる。コード上は `routers/agent_threads.py`、`services/agent_threads.py`、DB上は `agent_*` table群として分離し、Coreの `contexts` / `stats` / `access_logs` に依存しすぎないようにする。

将来、message量、WebSocket、worker、Redis Streams、専用rate limitが必要になった段階で、WorkThreadsを別Railway serviceまたは別worker serviceへ物理分離できるようにする。

### ローカル版を作らない理由

A2CRの価値は、クラウド上の共通スロットをMCP対応AIエージェントが新規窓・別端末・別クライアントから読めることにある。ローカルだけで使うなら、ユーザー自身がMarkdownやJSONの引き継ぎファイルを作れば足りる。ローカル版を提供すると、セットアップ、パス差異、OS差異、文字コード、ローカルDB破損、バックアップ、同期の問題をサービス側が抱える一方、SaaSとしての差別化は薄くなる。

そのため、実装対象はWeb SaaSのみとする。既存ローカルMVPのコードや知見はプロトタイプ・テスト参考として使うが、プロダクトとしてローカル版は提供しない。

---

## アーキテクチャ

```
ブラウザ / AIエージェント
        │
        ▼
https://a2cr.app/
        │
┌───────────────────────────────────┐
│           Railway（1サービス）      │
│                                   │
│  /*        → React SPA            │
│  /api/*    → FastAPI              │
│  /mcp      → MCPサーバー（HTTP）   │
└──────────────┬────────────────────┘
               │
       ┌───────┴────────┐
       ▼                ▼
  Supabase Auth    Supabase Postgres
  Google OAuth     （最小権限DBロール + RLS）
```

### WorkThreadsの分離方針

A2CRのWorkBaton層とWorkThreads層は、最初は同じSaaS内に同居するが、論理的には別コンポーネントとして扱う。

| 項目 | WorkBaton（A2CR Core） | WorkThreads |
|---|---|---|
| 主用途 | slot保存・load・resume | AIエージェント間の非同期作業thread |
| 主な負荷 | 低〜中頻度のsave/load | 高頻度INSERT、task claim、lease更新 |
| DB table | `contexts`, `stats`, `api_keys`, `access_logs` | `agent_threads`, `agent_messages`, `agent_tasks`, `agent_runs` |
| API prefix | `/api/v1/context/*`, `/api/dashboard/*` | `/api/v1/agent-*` |
| MCP tools | `save_context`, `load_context`, `resume_context` | `create_agent_thread`, `post_agent_message`, `claim_agent_task` |
| 初期配置 | Railway 1サービス | Railway 1サービス内に同居 |
| 将来配置 | Core API | 別worker / 別Railway serviceへ分離可 |

分離の判断基準:

- WorkThreads messageが100,000件/日を継続して超える
- task claimでlock waitまたはdeadlockが観測される
- WebSocketやRedis Streamsによるfan-outが必要になる
- WorkThreadsの負荷がCoreのsave/load latencyへ影響する
- Pro上位または従量課金として運用・監視・SLAを分ける必要が出る

物理分離する場合も、認証と課金状態はCoreをsource of truthにする。WorkThreads serviceはCore-issued API keyまたは内部JWTを検証し、`user_id` と `plan` を確定してから処理する。RLS境界と暗号化方針は分離後も維持する。

---

## 認証

| 用途 | 方式 |
|---|---|
| ダッシュボードログイン | Google OAuth → Supabase JWT |
| ダッシュボードAPI | `Authorization: Bearer <Supabase JWT>` |
| API / MCPアクセス | `Authorization: Bearer sk-xxx`（APIキー） |
| `/api/v1/health` | 認証不要 |

ReactはSupabase Authでログインするだけに留める。`contexts`、`stats`、`api_keys`、`access_logs` はブラウザからSupabaseへ直接アクセスせず、すべてFastAPI経由で扱う。

**APIキーの仕様：**
- 1ユーザー1キー（再発行すると旧キーは即時無効）
- `API_KEY_HASH_SECRET` を使ったHMAC-SHA256ハッシュのみ保存（平文は発行時のみ表示）
- 形式：`sk-` + `secrets.token_hex(32)`
- FastAPIが `Authorization` ヘッダーからAPIキーを検証し、専用DB関数で `user_id` を解決する
- `GET /api/dashboard/api-key` は `key_hash` を返さず、`key_prefix`、`created_at`、`last_used_at` のみ返す
- 再発行時は同一 `user_id` の旧キーを即時上書きし、旧キーでは認証できない状態にする

### RLSとDBアクセス

通常リクエストでは `SUPABASE_SERVICE_ROLE_KEY` を使わない。FastAPIは最小権限のPostgresロール `a2cr_app` でDBへ接続し、認証済みの `user_id` をトランザクション内で `SET LOCAL app.user_id = '<uuid>'` として設定する。RLS policyは `app.current_user_id()` を参照し、JWT認証・APIキー認証・MCPのすべてで同じ行分離を行う。

| 経路 | FastAPIでの認証 | DB分離方式 |
|---|---|---|
| Reactダッシュボード | Supabase JWT検証 | `SET LOCAL app.user_id` + RLS |
| APIキー認証API | 専用DB関数でAPIキー検証 | `SET LOCAL app.user_id` + RLS |
| MCP | 専用DB関数でAPIキー検証 | `SET LOCAL app.user_id` + RLS |

service role keyはRLSをバイパスできるため、ブラウザには絶対に渡さず、通常のRailwayランタイム環境変数にも置かない。DB migrationや緊急管理作業で必要な場合のみ、ローカル/CIの管理用環境で短時間だけ使う。

### Supabase JWT検証

FastAPIはダッシュボードAPIで受け取ったSupabase JWTをサーバー側で検証する。検証では以下を必須とする。

- `SUPABASE_JWKS_URL` から取得したJWKSで署名検証する
- 許可する `alg` を固定し、`none` や想定外のアルゴリズムを拒否する
- `iss` が対象Supabaseプロジェクトのissuerと一致することを確認する
- `aud` が想定値と一致することを確認する
- `exp` / `nbf` を検証し、期限切れ・未来トークンを拒否する
- JWTの `sub` を `user_id` として扱う前にUUIDとして検証する
- JWKSは短時間キャッシュし、未知の `kid` を受け取った場合は再取得してから再検証する

---

## データベーススキーマ

### contexts テーブル

| カラム | 型 | 変更点 |
|---|---|---|
| id | UUID | 変更なし |
| **user_id** | UUID FK → auth.users | **新規追加** |
| slot_name | TEXT | 変更なし |
| slot_number | INTEGER | **新規追加。ユーザー内で固定表示位置** |
| content | TEXT（暗号化） | 変更なし |
| created_at | TIMESTAMPTZ | 変更なし |
| updated_at | TIMESTAMPTZ | 変更なし |
| expires_at | TIMESTAMPTZ | 変更なし |
| size_bytes | INTEGER | 変更なし |
| original_tokens | INTEGER | 変更なし |
| compressed_tokens | INTEGER | 変更なし |
| load_count | INTEGER | 変更なし |
| model_source | TEXT | 変更なし |
| encryption_key_version | INTEGER | **新規追加** |

```sql
CREATE SCHEMA IF NOT EXISTS app;

CREATE OR REPLACE FUNCTION app.current_user_id()
RETURNS uuid
LANGUAGE sql
STABLE
AS $$
  SELECT NULLIF(current_setting('app.user_id', true), '')::uuid
$$;

UNIQUE (user_id, slot_name)    -- 旧: UNIQUE(slot_name)
UNIQUE (user_id, slot_number)

CHECK (slot_number >= 1)

ALTER TABLE contexts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "users_own_slots" ON contexts
  FOR ALL
  USING (user_id = app.current_user_id())
  WITH CHECK (user_id = app.current_user_id());

CREATE INDEX contexts_user_expires_idx ON contexts(user_id, expires_at);
CREATE INDEX contexts_user_slot_number_idx ON contexts(user_id, slot_number);
```

`slot_number` はダッシュボード上の固定Slot位置を表す。Freeは1〜3、Proは1〜100の範囲でサーバー側が検証する。`slot_number` を指定して保存した場合は、その番号のslotを上書きする。指定がない新規保存は空いている最小番号を割り当てる。更新日時が変わってもSlot番号は移動しない。

### stats テーブル

```sql
user_id         UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE
total_saves     INTEGER DEFAULT 0
total_loads     INTEGER DEFAULT 0
total_deletes   INTEGER DEFAULT 0
total_tokens_saved INTEGER DEFAULT 0
```

statsはユーザーごとの累計値として保持する。更新はFastAPIからPostgresの原子的UPDATEで行う。

```sql
UPDATE stats
SET total_saves = total_saves + 1,
    total_tokens_saved = total_tokens_saved + :saved_tokens
WHERE user_id = :user_id;
```

`total_loads` も同様に `total_loads = total_loads + 1` で更新する。read-modify-writeは並行リクエスト時に競合するため使わない。初回保存時は `INSERT ... ON CONFLICT (user_id) DO UPDATE` で作成と加算を同時に行う。

```sql
ALTER TABLE stats ENABLE ROW LEVEL SECURITY;

CREATE POLICY "users_own_stats" ON stats
  FOR ALL
  USING (user_id = app.current_user_id())
  WITH CHECK (user_id = app.current_user_id());
```

### user_profiles テーブル（新規）

```sql
user_id      UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE
plan         TEXT NOT NULL DEFAULT 'free' CHECK (plan IN ('free', 'pro'))
context_detail_level TEXT NOT NULL DEFAULT 'compact'
  CHECK (context_detail_level IN ('compact', 'detailed'))
default_retention_seconds INTEGER NOT NULL DEFAULT 10800
CHECK (plan = 'pro' OR context_detail_level = 'compact')
CHECK (
  (plan = 'free' AND default_retention_seconds IN (900, 1800, 3600, 10800)) OR
  (plan = 'pro' AND default_retention_seconds IN (900, 1800, 3600, 10800, 86400, 604800, 2592000))
)
preferred_locale TEXT NOT NULL DEFAULT 'auto'
response_language TEXT NOT NULL DEFAULT 'auto'
timezone     TEXT NOT NULL DEFAULT 'UTC'
created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
```

Stripe決済の実装は今回スコープ外のため、初期状態では全ユーザー `free` とする。Pro決済を追加する際はStripe webhookまたは管理者専用処理で `plan` を更新する。通常のダッシュボードAPIから `plan` を変更するエンドポイントは作らない。

`context_detail_level` はAIエージェントが `save_context` で残す粒度を決める。Freeは `compact` 固定、Proは `compact` / `detailed` を選択可能にする。Proへ変更した直後のデフォルトは `detailed` とし、ユーザーが軽量運用したい場合だけ `compact` に戻せる。

`default_retention_seconds` は新規保存時の保持期間を決める。Freeは15分/30分/1時間/3時間から選択でき、デフォルト兼上限は3時間。Proは15分/30分/1時間/3時間/24時間/7日/30日から選択でき、デフォルト兼上限は30日。Proへ変更した直後は30日に設定するが、ユーザーが短命運用を望む場合は15分まで短くできる。

`preferred_locale` はダッシュボード表示言語、`response_language` はAIエージェントの応答言語ヒント、`timezone` は日時表示に使う。`preferred_locale` と `response_language` は `auto` またはBCP 47形式（例: `en`, `ja`, `fr`, `pt-BR`）をFastAPIで検証する。初期値はGoogle OAuthのprofile locale、ブラウザの `Accept-Language`、`UTC` の順に推定し、ユーザーが設定で上書きできる。

```sql
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "users_read_profile" ON user_profiles
  FOR SELECT
  USING (user_id = app.current_user_id());

CREATE POLICY "users_create_free_profile" ON user_profiles
  FOR INSERT
  WITH CHECK (user_id = app.current_user_id() AND plan = 'free');
```

### api_keys テーブル（新規）

```sql
user_id      UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE
key_hash     TEXT NOT NULL
key_prefix   TEXT NOT NULL
created_at   TIMESTAMPTZ
last_used_at TIMESTAMPTZ
last_used_ip_hash TEXT
revoked_at   TIMESTAMPTZ
```

`user_id PRIMARY KEY` により1ユーザー1キーに固定する。複数キー対応は今回スコープ外で、将来必要になった場合は `id UUID PRIMARY KEY` を追加するテーブルへ変更する。`key_hash` はAPIレスポンス・ログ・ダッシュボードに出さない。

```sql
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;

CREATE POLICY "users_own_api_key" ON api_keys
  FOR ALL
  USING (user_id = app.current_user_id())
  WITH CHECK (user_id = app.current_user_id());

CREATE UNIQUE INDEX api_keys_hash_idx ON api_keys(key_hash);
```

APIキーの発行・更新・検証はFastAPIの専用処理だけが行う。ブラウザから `api_keys` へ直接INSERT/UPDATE/DELETEしない。

APIキー検証時はまだ `user_id` が未確定のため、通常RLSだけでは `api_keys` を検索できない。この照合だけは `SECURITY DEFINER` の専用関数で行い、関数は一致した非revokedキーの `user_id` だけを返す。`key_hash` や他ユーザーのキー情報は返さない。

```sql
BEGIN;

CREATE OR REPLACE FUNCTION app.resolve_api_key(p_key_hash text, p_ip_hash text)
RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $$
DECLARE
  v_user_id uuid;
BEGIN
  SELECT user_id INTO v_user_id
  FROM public.api_keys
  WHERE key_hash = p_key_hash
    AND revoked_at IS NULL;

  IF v_user_id IS NOT NULL THEN
    UPDATE public.api_keys
    SET last_used_at = now(),
        last_used_ip_hash = p_ip_hash
    WHERE user_id = v_user_id;
  END IF;

  RETURN v_user_id;
END;
$$;

REVOKE ALL ON FUNCTION app.resolve_api_key(text, text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION app.resolve_api_key(text, text) TO a2cr_app;

COMMIT;
```

FastAPIは `app.resolve_api_key()` の戻り値を検証した後、同一リクエストのDBトランザクションで `SET LOCAL app.user_id = '<uuid>'` を実行する。

### access_logs テーブル（新規）

```sql
id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE
action          TEXT NOT NULL
slot_name       TEXT
client_type     TEXT NOT NULL
result          TEXT NOT NULL
error_code      TEXT
ip_hash         TEXT
user_agent_hash TEXT
created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
```

`action` は `context.save` / `context.load` / `context.resume` / `context.list` / `context.delete` / `context.expire` / `api_key.issue` / `mcp.initialize` / `mcp.tool_call` などを使う。`context.delete` はユーザー/APIによる明示削除、`context.expire` は保持期間切れによる自動削除を表す。`context.expire` の `client_type` は `system`、`result` は `success` とし、削除直前に `user_id` と `slot_name` だけを記録する。`api_key.auth_failed` は `user_id` が安全に確定できる場合のみ `access_logs` に保存し、それ以外は別のセキュリティイベントログに保存する。`result` は `success` / `failure` / `rate_limited` / `not_found` / `validation_error` / `candidates` などを使う。

ログには以下を保存しない。
- content本文
- APIキー平文
- APIキーハッシュ
- Authorizationヘッダー
- 生IPアドレス
- User-Agent全文
- request body全文

IPとUser-Agentを識別に使う場合は `AUDIT_LOG_HASH_SECRET` でHMAC化して保存する。

```sql
ALTER TABLE access_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "users_own_access_logs" ON access_logs
  FOR ALL
  USING (user_id = app.current_user_id())
  WITH CHECK (user_id = app.current_user_id());

CREATE INDEX access_logs_user_created_idx ON access_logs(user_id, created_at DESC);
```

### Pro WorkThreads テーブル（Pro拡張）

WorkThreadsは、同じthread本文を複数AIが更新し合う設計にしない。会話本文はappend-only event logとして `agent_messages` にINSERTし、状態管理は `agent_threads` と `agent_tasks` の短いUPDATEに限定する。

この機能はPro向け拡張として設計に含めるが、初期MVPでは実装を必須にしない。

#### agent_threads

```sql
id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE
title           TEXT NOT NULL
purpose         TEXT NOT NULL
status          TEXT NOT NULL CHECK (status IN ('open', 'running', 'blocked', 'completed', 'archived'))
visibility      TEXT NOT NULL DEFAULT 'agent_only' CHECK (visibility = 'agent_only')
version         INTEGER NOT NULL DEFAULT 1
created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
expires_at      TIMESTAMPTZ NOT NULL
```

`visibility='agent_only'` は、人間向けダッシュボードに本文を表示しないことを表す。ダッシュボードはthread metadataだけを表示する。本文の復号はMCP/APIキー認証されたAIエージェント向けAPIに限定する。

#### agent_messages

```sql
id              UUID DEFAULT gen_random_uuid()
user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE
thread_id       UUID NOT NULL REFERENCES agent_threads(id) ON DELETE CASCADE
role            TEXT NOT NULL CHECK (role IN ('request', 'agent', 'critic', 'summarizer', 'system'))
agent_name      TEXT
content         TEXT NOT NULL  -- encrypted
content_hash    TEXT NOT NULL  -- duplicate/idempotency detection
token_estimate  INTEGER NOT NULL DEFAULT 0
created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
PRIMARY KEY (created_at, id)
```

`agent_messages` は `created_at` でrange partitionする。初期は月次partitionでもよいが、Pro利用が増えて書き込みが多い場合は日次partitionへ移行する。日次partitionは例として `agent_messages_2026_05_04` のように作成し、日次ジョブで翌日分を事前作成する。

メッセージ本文はINSERT専用で、編集や追記UPDATEを行わない。修正・反論・補足は新しいmessageとして追加する。

#### agent_tasks

```sql
id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE
thread_id       UUID NOT NULL REFERENCES agent_threads(id) ON DELETE CASCADE
kind            TEXT NOT NULL CHECK (kind IN ('review', 'critique', 'summarize', 'verify', 'merge'))
status          TEXT NOT NULL CHECK (status IN ('queued', 'leased', 'completed', 'failed', 'expired'))
lease_owner     TEXT
lease_until     TIMESTAMPTZ
attempt_count   INTEGER NOT NULL DEFAULT 0
max_attempts    INTEGER NOT NULL DEFAULT 3
created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
```

AIエージェントは `claim_agent_task` でtaskを取得する。取得処理は `SELECT ... FOR UPDATE SKIP LOCKED` を使い、複数Agentが同じtaskを取らないようにする。AI処理中にDB transactionを保持しない。claim時にleaseを書き込み、処理完了時は `WHERE id = :id AND lease_owner = :agent AND lease_until > now()` 条件で完了更新する。

#### agent_runs

```sql
id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE
thread_id       UUID NOT NULL REFERENCES agent_threads(id) ON DELETE CASCADE
task_id         UUID REFERENCES agent_tasks(id) ON DELETE SET NULL
agent_name      TEXT NOT NULL
client_type     TEXT NOT NULL
status          TEXT NOT NULL CHECK (status IN ('started', 'completed', 'failed', 'timeout', 'rate_limited'))
started_at      TIMESTAMPTZ NOT NULL DEFAULT now()
finished_at     TIMESTAMPTZ
error_code      TEXT
```

`agent_runs` は本文を持たず、実行状態だけを記録する。エラーメッセージは短い `error_code` に丸め、プロンプト、応答本文、APIキー、Authorizationヘッダーは保存しない。

#### RLS

```sql
ALTER TABLE agent_threads ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_runs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "users_own_agent_threads" ON agent_threads
  FOR ALL
  USING (user_id = app.current_user_id())
  WITH CHECK (user_id = app.current_user_id());

CREATE POLICY "users_own_agent_messages" ON agent_messages
  FOR ALL
  USING (user_id = app.current_user_id())
  WITH CHECK (user_id = app.current_user_id());

CREATE POLICY "users_own_agent_tasks" ON agent_tasks
  FOR ALL
  USING (user_id = app.current_user_id())
  WITH CHECK (user_id = app.current_user_id());

CREATE POLICY "users_own_agent_runs" ON agent_runs
  FOR ALL
  USING (user_id = app.current_user_id())
  WITH CHECK (user_id = app.current_user_id());
```

WorkThreads本文はダッシュボードAPIでは返さない。`agent_messages.content` を復号して返す経路は、APIキー認証済みAIエージェント向けMCP/APIだけに限定する。

---

## APIエンドポイント

### AIエージェント向け（APIキー認証）

| メソッド | パス | 説明 |
|---|---|---|
| POST | `/api/v1/context/save` | コンテキスト保存 |
| GET | `/api/v1/context/list` | スロット一覧 |
| GET | `/api/v1/context/{slot_name}` | コンテキスト取得 |
| GET | `/api/v1/context/slot/{slot_number}` | 固定Slot番号でコンテキスト取得 |
| GET | `/api/v1/context/resume?slot_number=...&slot_name=...&project=...` | 新規AI窓向け再開 |
| DELETE | `/api/v1/context/{slot_name}` | スロット削除 |
| GET | `/api/v1/health` | ヘルスチェック（認証不要） |
| GET | `/api/v1/account/limits` | プラン・本文上限・保存粒度取得 |
| POST | `/api/v1/agent-threads` | Pro: WorkThreads作成 |
| GET | `/api/v1/agent-threads` | Pro: WorkThreads metadata一覧 |
| GET | `/api/v1/agent-threads/{thread_id}` | Pro: WorkThreads metadata取得 |
| POST | `/api/v1/agent-threads/{thread_id}/messages` | Pro: Agent message追加 |
| GET | `/api/v1/agent-threads/{thread_id}/messages` | Pro: AIエージェント向けmessage取得 |
| POST | `/api/v1/agent-tasks/claim` | Pro: AIエージェント向けtask取得 |
| POST | `/api/v1/agent-tasks/{task_id}/complete` | Pro: task完了 |

※ `get_handoff` は削除。MCP対応AIからの利用に絞るため、Markdown手動引き継ぎ用エンドポイントはSaaS初期版では提供しない。ローカルMVPとの破壊的変更として扱う。

### 保存言語と応答言語

`contexts.content` に保存する本文は原則として英語に正規化する。日本語など英語以外で会話していた場合も、AIエージェントは `save_context` 実行前に要点を簡潔な英語へ翻訳・圧縮して保存する。

例外として、以下は原文を維持する。
- コード、コマンド、ファイルパス、URL、環境変数名
- エラーメッセージ、ログ断片、APIレスポンス
- 固有名詞、プロダクト名、仕様名
- ユーザーの正確な表現が判断材料になる短い引用

`load_context` は保存済み内容をそのまま返す。読み込んだAIエージェントは、DB内の保存言語ではなく、ロード直前までユーザーと会話していた言語に合わせて回答する。日本語、英語、スペイン語、フランス語など特定言語に限定しない。直前言語が不明な場合は、その時点のユーザーメッセージの言語に合わせる。それも不明な場合は `user_profiles.response_language`、最後に英語へフォールバックする。

このルールは保存データの検索性・圧縮性・文字化け耐性を上げるための運用方針であり、ダッシュボードの言語切替とは独立して扱う。

### 新規AI窓での再開

新しいAI作業窓で文脈をすぐ理解させるため、`resume_context` をMCPの主要導線として提供する。ユーザーに `list_contexts` と `load_context` の手順を毎回指示させない。

`resume_context` の入力:
- `slot_number` 任意。指定された場合は固定Slot番号を優先して読み込む
- `slot_name` 任意。指定された場合はそのslotを優先して読み込む
- `project` 任意。指定された場合は `project` と一致、または `project-` で始まるactive slotを候補にする
- `prefer_latest` 任意。`true` の場合だけ、複数候補の中から最新slotを自動選択できる

選択ルール:
- `slot_number` が指定され、active slotとして存在すれば即時読み込む
- `slot_number` が存在しない、期限切れ、またはプラン上限外なら `not_found` または validation errorを返す
- `slot_name` が指定され、active slotとして存在すれば即時読み込む
- `slot_name` が存在しない、または期限切れなら `not_found` を返す
- `project` 指定で候補が1件なら即時読み込む
- `project` 指定で候補が複数あり `prefer_latest=true` なら `updated_at` が最新のslotを読み込む
- 候補が複数あり自動選択しない場合は、content本文を返さず候補一覧だけ返す
- 候補が0件なら `no_active_context` を返す
- `slot_name` も `project` も未指定でactive slotが1件だけなら即時読み込む
- `slot_name` も `project` も未指定でactive slotが複数ある場合は、誤読込を避けるため候補一覧だけ返す

`resume_context` のレスポンスは `status` を持つ。

| status | 内容 |
|---|---|
| `loaded` | `slot_number`、`slot_name`、`content`、`updated_at`、`expires_at`、`response_language_hint` を返す |
| `candidates` | `candidates[]` にslotメタデータだけを返す。content本文は返さない |
| `not_found` | 指定slotまたはprojectに対応するactive slotがない |
| `no_active_context` | active slotがない |

`response_language_hint` は `current_message_language` を優先する。MCPクライアントは、読み込み後に保存言語ではなく新窓でユーザーが使った言語に合わせて要約・作業再開する。

### 保存直後の引き継ぎメッセージ

`save_context` が成功したら、レスポンスに新規AI窓へ貼るための再開メッセージを含める。MCPクライアントは `save_context` 成功後、現在の会話へこのメッセージを表示する。これにより、保存した直後の会話窓に「次の窓で何を読めばよいか」が残る。

`save_context` レスポンスに追加するフィールド:

```json
{
  "slot_name": "web-saas-design",
  "expires_at": "2026-05-04T01:26:42Z",
  "compressed_tokens": 830,
  "resume_context_call": "resume_context(slot_name=\"web-saas-design\")",
  "resume_prompt": "A2CR service: https://a2cr.app/mcp\nA2CR MCPツールを使ってください。HTTP APIを直接推測して呼び出さないでください。\nまず resume_context(slot_name=\"web-saas-design\") を実行して、A2CRから引き継ぎ文脈を読み込んでください。\n読み込み後は、作業に必要なプロジェクトファイルを通常通り参照して構いません。\n回答はこのメッセージの言語に合わせてください。"
}
```

`resume_prompt` は保存本文ではなく、slot名と公開MCPサービスURLを含む操作指示だけにする。新規AI窓がHTTP endpointを推測して直接叩かないよう、MCPツール利用を明示する。本番では `A2CR_SERVICE_URL` に公開MCP URL（例: `https://a2cr.app/mcp`）を設定し、その値を表示する。content本文、APIキー、Authorizationヘッダー、非公開の内部URL、DB情報は含めない。`slot_name` はメタデータとして扱うため表示可能だが、秘密情報を含めないようUIとドキュメントで案内する。

言語は以下の順で決める。
- MCP経由の場合は、保存直前のユーザー会話言語
- ダッシュボード経由の場合は `preferred_locale`
- 不明な場合は `response_language`
- それも `auto` または不明なら英語

MCPクライアントは、保存成功後に次のような短いメッセージを現在の会話へ出す。

```text
保存しました。新しい窓では以下を貼って再開できます。

A2CR service: https://a2cr.app/mcp
A2CR MCPツールを使ってください。HTTP APIを直接推測して呼び出さないでください。
まず resume_context(slot_name="web-saas-design") を実行して、A2CRから引き継ぎ文脈を読み込んでください。
読み込み後は、作業に必要なプロジェクトファイルを通常通り参照して構いません。
回答はこのメッセージの言語に合わせてください。
```

この表示は `save_context` 成功時のみ行う。保存失敗、rate limit、validation error、slot limit超過時は表示しない。

### 多言語対応方針

利用対象は世界中の開発者とする。初期リリースでUI翻訳をすべて揃える必要はないが、実装は最初から多言語展開できる形にする。

- UI文字列はコードに直書きせず、翻訳キーと辞書ファイルで管理する
- 初期対応言語は `en` と `ja`、未翻訳キーのフォールバックは `en` とする
- 追加言語はBCP 47タグで増やす（例: `es`, `fr`, `de`, `ko`, `zh-CN`, `pt-BR`）
- 日時、残り時間、数値、通貨は `preferred_locale` と `timezone` に基づいて表示する
- APIレスポンスの `code` は言語非依存の安定IDにし、表示文言だけフロントエンドで翻訳する
- access logsの `action`、`result`、`error_code` は翻訳せず、UI側で表示名に変換する
- セットアップ手順、エラーメッセージ、価格ページ、メール文面は翻訳対象にする
- 右から左へ書く言語（RTL）は初期対応外でも、CSSとレイアウトが将来対応を阻害しないようにする

価格は初期リリースではUSD基準（Pro: 5 USD/month）で表示し、ユーザーのロケールに合わせて表記だけ整える。地域別価格、税、請求通貨の切替はStripe実装時に別途設計する。

### 保存粒度

`save_context` の保存粒度は `user_profiles.context_detail_level` に従う。

| detail level | 対象 | 保存方針 |
|---|---|---|
| `compact` | Free固定 / Pro選択可 | 引き継ぎに必要な結論・現在地・次アクション・重要制約だけを保存する |
| `detailed` | Proのみ | 実装ファイル、重要な試行錯誤、テスト結果、判断理由、未解決リスクまで細かく保存する |

`compact` では、長いログ、網羅的な変更履歴、ファイルごとの細かいメモ、会話の言い換えを省く。`detailed` でも全文ログ倉庫にはしない。秘密情報、長いログ、巨大なdiff、依存ファイル全文、APIキー、JWT、個人情報は保存しない。

AIエージェントは保存前に現在のプラン・本文上限・`context_detail_level` を参照し、同じ `save_context` スキーマの中で粒度だけを変える。サーバーは保存本文を自動で要約し直さず、プラン別の本文サイズ上限とrate limitを強制する。

### Pro WorkThreads API

WorkThreads APIはPro限定とする。Freeユーザーが呼んだ場合は `403 pro_required` を返す。

| API | 用途 | 本文復号 |
|---|---|---|
| `create_agent_thread` | thread metadataと初期taskを作成 | なし |
| `post_agent_message` | AIエージェントがmessageを追加 | 保存時のみ暗号化 |
| `read_agent_thread` | AIエージェントがmessageを読む | MCP/APIキー経路のみ復号 |
| `claim_agent_task` | AIエージェントが次taskをclaim | なし |
| `complete_agent_task` | task完了とsummary保存 | summaryは必要なら暗号化 |
| `save_thread_result` | threadの最終結果を通常Slotへ保存 | 通常Slot保存と同じ |

人間のダッシュボードAPIは `agent_threads` metadata、task状態、message件数、最新時刻、実行結果だけを返す。`agent_messages.content` は暗号化済み/復号済みのどちらも返さない。

#### 排他制御とタイムアウト

- `agent_messages` はappend-only INSERTのみ。本文のUPDATEは禁止する
- task claimは `SELECT ... FOR UPDATE SKIP LOCKED` を使う
- AI実行中にDB transactionを開きっぱなしにしない
- claim transactionは数十ms〜数百msで閉じる
- `lock_timeout` は短く設定する（例: 1s）
- `statement_timeout` を設定する（例: API 5s、管理ジョブ 30s）
- taskには `lease_until` を持たせ、timeoutしたtaskは再claim可能にする
- task完了は `WHERE id = :id AND lease_owner = :agent AND lease_until > now()` で更新する
- thread状態更新は `version` による楽観ロックを使う

ロック取得順序は常に以下に固定する。

1. `agent_threads`
2. `agent_tasks`
3. `agent_messages`
4. `stats` / `access_logs`

この順序以外で複数テーブルを更新しない。順序を固定することでデッドロック確率を下げる。

#### スケール方針

WorkThreadsの高頻度アクセスはDB行更新ではなくappend-only event logに逃がす。何万アクセス/日ならRailway + Supabaseでも設計上は狙えるが、何万同時接続はRailway 1サービス + Supabase単体では前提にしない。

高負荷化した場合の拡張順:

1. DB connection poolerを必須化する
2. rate limitをRedis/Upstashへ移す
3. `agent_messages` / `agent_runs` を日次partitionにする
4. 古いpartitionを保持期間でdropする
5. stats集計をevent logから非同期集計にする
6. WorkThreads処理をFastAPI web processからworkerへ分離する
7. p95/p99 latency、lock wait、deadlock countを監視する

### ダッシュボード向け（Supabase JWT認証）

| メソッド | パス | 説明 |
|---|---|---|
| POST | `/api/dashboard/api-key/issue` | APIキー発行（旧キー無効化） |
| GET | `/api/dashboard/profile` | plan・本文上限・保存粒度・locale・timezone取得 |
| PATCH | `/api/dashboard/profile` | 保存粒度・locale・timezone更新（plan変更不可） |
| GET | `/api/dashboard/api-key` | キー状態取得（prefix・作成日・最終利用日時のみ） |
| GET | `/api/dashboard/stats` | 累計統計取得 |
| GET | `/api/dashboard/contexts` | スロットメタデータ一覧（contentなし） |
| GET | `/api/dashboard/access-logs?limit=100` | アクセスログ一覧（content・生IPなし） |
| DELETE | `/api/dashboard/contexts/{slot_name}` | スロット削除 |

ダッシュボード向けAPIは保存コンテンツ本文を返さない。`contexts.content` を復号して返す経路はAIエージェント向け `GET /api/v1/context/{slot_name}` とMCP `load_context` のみに限定する。

### プラン制限の適用

FastAPIは認証後に `user_profiles.plan` を読み、保存・読込・一覧・削除・ダッシュボードAPIの制限を適用する。`user_profiles` が存在しない場合は初回リクエスト時に `free` として作成する。

| 制限 | Free | Pro |
|---|---:|---:|
| active slots | 3件 | 100件 |
| `expires_at` | 選択した保持期間（15分/30分/1時間/3時間、デフォルト3時間） | 選択した保持期間（15分/30分/1時間/3時間/24時間/7日/30日、デフォルト30日） |
| checkpoint本文上限 | 32KB | 128KB |
| 保存粒度 | `compact` 固定 | `compact` / `detailed` 選択可 |
| checkpoint保存 | 100回/時間 | 1,000回/時間 |
| load | 300回/時間 | 3,000回/時間 |
| access logs | 24時間 | 30日 |
| WorkThreads | なし | あり（post-MVP拡張） |
| WorkThreads message | なし | 5,000件/日を初期上限 |
| WorkThreads同時leased task | なし | 10件/ユーザーを初期上限 |

同名slotへの上書き、または同じ `slot_number` への上書きはactive slot数を増やさない。新規slot保存時のみ、期限切れでないslot数を数えて上限を判定する。`save_context` は基本的に `user_profiles.default_retention_seconds` を使い、`expires_at = saved_at + default_retention_seconds` とする。MCP/APIで保存時に `retention_seconds` を明示指定できる場合も、サーバー側でプラン別の許可値を必ず検証し、超過または未許可値は `422 retention_not_allowed` で拒否する。

`save_context` は任意で `slot_number` を受け付ける。ユーザーが「Slot 2へ保存」と指定した場合、MCPクライアントは `slot_number=2` と現在の `slot_name` 対応表を使って保存する。`slot_name` が別の固定Slotに既に紐づいている場合は `409 slot_name_conflict` で拒否し、暗黙の移動はしない。

---

## MCPサーバー

- エンドポイント：`POST /mcp`（Streamable HTTP型）
- 認証：`Authorization: Bearer sk-xxx`（APIキーと共通）
- ローカル起動不要、クラウド上で常時稼働
- 実装はStreamable HTTP対応済みのMCPライブラリを使う（手動JSON-RPC実装はしない）
- MCP仕様に従い、単一 `/mcp` エンドポイントで `POST` と必要に応じた `GET` を扱う
- サーバーが `MCP-Session-Id` を発行する実装の場合、以後のリクエストで同ヘッダーを検証する
- `Origin` ヘッダー検証を行い、許可オリジン以外は403を返す
- `Mcp-Method` / `Mcp-Name` などの標準ヘッダーとJSON-RPC bodyの不一致を400で拒否する
- Cookie認証は使わず、`Authorization` ヘッダーを必須にする
- ブラウザ向けCORSを広く開けない。許可オリジンは本番ドメインと開発用localhostに限定する

**提供ツール：**

| ツール名 | 対応API |
|---|---|
| `save_context` | POST /api/v1/context/save |
| `load_context` | GET /api/v1/context/slot/{slot_number} または GET /api/v1/context/{slot_name} |
| `resume_context` | GET /api/v1/context/resume |
| `list_contexts` | GET /api/v1/context/list |
| `delete_context` | DELETE /api/v1/context/{slot_name} |
| `get_account_limits` | GET /api/v1/account/limits |
| `create_agent_thread` | POST /api/v1/agent-threads |
| `post_agent_message` | POST /api/v1/agent-threads/{thread_id}/messages |
| `read_agent_thread` | GET /api/v1/agent-threads/{thread_id}/messages |
| `claim_agent_task` | POST /api/v1/agent-tasks/claim |
| `complete_agent_task` | POST /api/v1/agent-tasks/{task_id}/complete |
| `save_thread_result` | POST /api/v1/context/save |

`resume_context` は新規AI窓で最初に呼ぶためのツールとする。固定Slot番号が分かっている場合は `resume_context(slot_number=1)`、slot名が分かっている場合は `resume_context(slot_name="...")` で読み込める。Dashboardが生成する再開プロンプトでは互換性の高いslot名を主導線にし、固定Slot番号は対応済みクライアント向けの補助導線として含める。再開プロンプトではMCPツール利用を明示し、HTTP APIを直接推測して呼ばせない。

`save_context` 成功時は、MCPツールの戻り値に `resume_context_call` と `resume_prompt` を含める。AIエージェントは保存完了を伝えるだけで終わらず、戻り値の `resume_prompt` を現在の会話へ表示する。

`get_account_limits` は `plan`、`max_content_bytes`、`context_detail_level`、`preferred_locale`、`response_language`、`timezone`、rate limit、retentionを返す。MCPクライアントは自動保存前にこの情報を使い、Freeではcompact、Pro detailedではより細かい引き継ぎを保存する。`response_language` が `auto` の場合は現在の会話言語を優先する。

WorkThreads toolsはPro限定。WorkThreads本文は人間向けUIに表示せず、MCP/APIキー認証されたAIエージェントだけが `read_agent_thread` で復号済みmessageを受け取れる。A2CRは初期版ではLLMを自動起動せず、外部AIエージェントからのtool callを受けてthreadを進める。

### AIクライアント誘導

A2CRの振る舞いは、MCP設定ファイルに長いプロンプトを埋め込んで成立させない。必須の誘導はMCP tool descriptions / schema、MCP tool response、`resume_prompt` に置く。

MCP tool descriptions / schemaには次を明記する。

- `save_context` は `goal`、`current_state`、`next_action` を必須にする。
- `save_context` はFreeならcompact、Pro detailedなら判断根拠・失敗履歴・検証結果を含められる。
- secret、API key、Authorization header、private DB URL、会話全文、長大ログを保存しない。
- `resume_context` は新しいAI窓で最初に呼ぶtoolであり、直接HTTP APIを推測しない。
- ロード後は、保存本文と現在のプロジェクトファイルを照合し、現在のファイル状態を優先する。
- 回答言語は保存本文ではなく、現在のユーザーメッセージに合わせる。

MCP prompts/resourcesに対応したクライアントでは、同じ内容を補助資料として提供してよい。ただし、対応状況がクライアントごとに異なるため、MCP prompts/resourcesを必須前提にはしない。

CodexなどSkill対応クライアント向けには、任意テンプレートとして `docs/templates/skills/a2cr-agent/SKILL.md` を提供する。このSkillは、A2CR MCPが使える時の保存・再開・WorkThreads運用の作法を短く伝えるためのものであり、A2CRのセキュリティ境界や認証設定を担わせない。

**ユーザーの設定（Claude）：**
```json
{
  "mcpServers": {
    "a2cr": {
      "type": "http",
      "url": "https://a2cr.app/mcp",
      "headers": { "Authorization": "Bearer sk-xxxxx" }
    }
  }
}
```

**ユーザーの設定（Codex）：**
```toml
[mcp_servers."a2cr"]
url = "https://a2cr.app/mcp"
bearer_token_env_var = "A2CR_API_KEY"
```

`A2CR_API_KEY` に `sk-xxxxx` を設定してからCodexを起動する。

---

## Reactダッシュボード

### ページ構成

| パス | 内容 | 認証 |
|---|---|---|
| `/` | ランディングページ | 不要 |
| `/pricing` | 料金プランページ | 不要 |
| `/dashboard` | メインダッシュボード | 必要 |
| `/settings` | APIキー・設定手順 | 必要 |
| `/agent-threads` | Pro WorkThreads metadata | 必要 |

### 技術スタック

| 項目 | 採用 |
|---|---|
| フレームワーク | React + Vite |
| 認証 | Supabase Auth（`@supabase/auth-ui-react`） |
| HTTPクライアント | fetch（ライブラリなし） |
| スタイル | Tailwind CSS |
| ルーティング | React Router |
| i18n | i18next / react-i18next |

開発時はVite dev serverからFastAPIへ `/api` と `/mcp` をプロキシする。本番は同一オリジン配信のためCORSを不要にする。

ReactダッシュボードはSupabase Authのログイン状態からJWTを取得し、FastAPIの `/api/dashboard/*` へ送る。アプリデータをSupabaseへ直接問い合わせない。

### `/dashboard` の表示内容

- サーバーステータス（🟢/🔴）
- 累計統計（保存回数・ロード回数・削除回数・節約トークン）
- スロットメタデータ一覧（固定Slot番号・slot名・保存日時・New表示・残り時間・サイズ・load_count・再開プロンプトコピー・削除ボタン）
- アクセスログ一覧（時刻・action・slot_name・client_type・result）
- Pro WorkThreads metadata（thread名・status・message件数・task状態・最終更新時刻。本文なし）
- 自動リロード ON/OFF
- 言語切替（Auto / English / 日本語。追加言語は辞書追加で拡張）
- タイムゾーン表示（profile設定に基づく）

ダッシュボードでは `contexts.content` を復号・表示しない。

WorkThreadsでも同様に、ダッシュボードでは `agent_messages.content` を復号・表示しない。人間が確認できるのは進捗metadata、件数、時刻、agent名、成功/失敗、最終結果slotへのリンクだけにする。

### `/settings` の表示内容

- APIキー発行直後の一回限り表示・コピー・再発行ボタン
- 既存キー状態（prefix・作成日・最終利用日時）
- 保持期間設定（Freeは15分/30分/1時間/3時間、Proは15分/30分/1時間/3時間/24時間/7日/30日）
- 保存粒度設定（FreeはCompact固定、ProはCompact/Detailedを選択可）
- 表示言語・応答言語・タイムゾーン設定
- セットアップ手順（Claude / Codex / Cursor タブ切替）

### 再開プロンプト

Dashboardの各slot行に「再開プロンプトをコピー」ボタンを置く。コピー内容には具体的な `slot_name` を含める。

Slot一覧の上には「保存プロンプトをコピー」ボタンを置く。コピー内容には現在の固定Slot番号と `slot_name` の対応表を含め、ユーザーが「Slot 1へ保存」と指示した場合にAIが `save_context(slot_number=1, slot_name="...")` を呼べるようにする。

```text
A2CR service: https://a2cr.app/mcp
Use the A2CR MCP tool. Do not guess or call direct HTTP API endpoints.
First run resume_context(slot_name="{slot_name}") to load the handoff context from A2CR.
After loading, you may read the project files needed for the actual work.
Answer in the language of this message.
```

UI言語が日本語の場合は次のように表示する。

```text
A2CR service: https://a2cr.app/mcp
A2CR MCPツールを使ってください。HTTP APIを直接推測して呼び出さないでください。
まず resume_context(slot_name="{slot_name}") を実行して、A2CRから引き継ぎ文脈を読み込んでください。
読み込み後は、作業に必要なプロジェクトファイルを通常通り参照して構いません。
回答はこのメッセージの言語に合わせてください。
```

slot名が不明な場合の汎用プロンプトも `/settings` に表示する。

```text
A2CR service: https://a2cr.app/mcp
Use the A2CR MCP tool. Do not guess or call direct HTTP API endpoints.
First run resume_context(). If multiple candidates are returned, show the candidates and ask me which slot to use.
After loading, you may read the project files needed for the actual work.
Answer in the language of this message.
```

### `/pricing` の表示内容

| 項目 | Free | Pro |
|---|---|---|
| 料金 | Free | 5 USD/month |
| active slots | 3件 | 100件 |
| checkpoint保持 | 15分/30分/1時間/3時間（デフォルト3時間） | 15分/30分/1時間/3時間/24時間/7日/30日（デフォルト30日） |
| checkpoint本文上限 | 32KB | 128KB |
| 保存粒度 | Compact | Compact / Detailed |
| checkpoint保存 | 100回/時間 | 1,000回/時間 |
| load | 300回/時間 | 3,000回/時間 |
| access logs | 24時間 | 30日 |
| WorkThreads | なし | post-MVP拡張 |
| WorkThreads本文表示 | なし | 人間には非表示、AIエージェントのみ読込 |
| API key | 1件 | 1件（複数キーは将来対応） |

`checkpoint` は `save_context` またはMCP `save_context` の成功1回を指す。回数上限は課金圧ではなくfair useと自動保存ループ対策として扱う。超過時は `429` と `retry_after` を返し、ユーザーには保存間隔を空ける案内を出す。

---

## セキュリティ設計

### データ露出方針

- ダッシュボードは保存コンテンツ本文を表示しない
- ダッシュボードはWorkThreads本文も表示しない
- access_logsにはcontent・APIキー・Authorizationヘッダー・request body全文を保存しない
- APIエラーには内部例外、SQL、スタックトレース、環境変数名を含めない
- FastAPIの通常ログにもcontent本文、APIキー、JWT、復号後データを出さない
- `slot_name` はメタデータとして表示・記録されるため、ユーザーには秘密情報を含めないよう案内する

WorkThreadsは `Human-hidden / Operationally protected / Not zero-knowledge` と定義する。つまり、人間向けUIや通常の運用画面では本文を見せないが、MCP/APIへ復号済み本文を返すため、サーバーは処理中メモリ上で本文を扱う。初期版では完全なE2E/ゼロ知識暗号化とは呼ばない。運営者がDBだけを見ても本文を読めないようアプリ層暗号化を行い、復号鍵へのアクセスをRailway runtime secretに限定する。

### 暗号化と鍵管理

- `contexts.content` はFernetでアプリケーション層暗号化する
- `agent_messages.content` も同じ方針でアプリケーション層暗号化する
- `FERNET_KEY` はcontent暗号化専用にする
- `API_KEY_HASH_SECRET` はAPIキーハッシュ専用にする
- `AUDIT_LOG_HASH_SECRET` はIP/User-AgentのHMAC化専用にする
- `contexts.encryption_key_version` を保存し、将来の鍵ローテーションに備える
- この方式はサーバー側で復号可能なアプリ層暗号化であり、E2E/ゼロ知識暗号化ではない

WorkThreads本文の復号経路はAIエージェント向けAPI/MCPに限定する。ダッシュボードAPI、管理API、access logs、agent_runs、statsへ復号本文を渡さない。

### レート制限

FastAPIでユーザーID・APIキーprefix・IPハッシュ単位のレート制限を行う。複数インスタンスでも制限が効くように、メモリ内カウンタではなく共有ストアを使う。第一候補はRedis/Upstashとし、未導入の場合はPostgresの専用テーブルで代替する。

| 対象 | Free | Pro |
|---|---:|---:|
| request body / checkpoint本文 | 32KB | 128KB |
| checkpoint保存（`save_context`） | 100回/時間 | 1,000回/時間 |
| load（`load_context`） | 300回/時間 | 3,000回/時間 |
| resume/load/list/delete | 300回/時間 | 3,000回/時間 |
| dashboard read | 300回/時間 | 3,000回/時間 |
| APIキー再発行 | 3回/日 | 10回/日 |
| WorkThreads message | なし | 5,000件/日 |
| WorkThreads task claim | なし | 1,000回/時間 |
| WorkThreads同時leased task | なし | 10件/ユーザー |
| 認証失敗 | IPハッシュ単位で指数バックオフ | IPハッシュ単位で指数バックオフ |

`checkpoint` は `save_context` またはMCP `save_context` の成功1回を指す。MCP経由のtool callは対応するAPI操作の制限に含める。`resume_context` がcontent本文を返す場合は `load_context` と同じ扱いでrate limitとaccess logを記録する。候補一覧だけ返す場合は `list_contexts` と同じ扱いにする。

追加制限:
- request bodyはプラン別上限（Free 32KB / Pro 128KB）をサーバー入口で強制する
- MCP batch requestを許可する場合は最大件数を10に制限する
- MCPのSSE/GET接続は最大接続時間と同時接続数を制限する
- 全外部リクエストにタイムアウトを設定する
- レスポンス件数には必ず上限を付ける。`access-logs` は `limit` の最大値を100に固定し、それ以上は返さない
- WorkThreads message取得もlimit上限を固定する。初期上限は100件/リクエストとし、古いmessageはcursor paginationで読む
- WorkThreadsのtask leaseは期限付きにし、timeoutしたleaseは再claimできるようにする
- 超過時は `429` と `retry_after` を返し、クライアントが再試行間隔を守れるようにする

### HTTPヘッダーとCORS

- HTTPSを前提とし、Railway側でHTTPからHTTPSへリダイレクトする
- 本番CORSは同一オリジンのみ。開発時だけ `localhost` を許可する
- `Content-Security-Policy` を設定し、`script-src` / `connect-src` を必要最小限にする
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: no-referrer`
- `Permissions-Policy` で不要なブラウザ機能を無効化する

### 監査ログ

成功・失敗の両方を `access_logs` に記録する。認証失敗で `user_id` が不明な場合は、`user_id` なしのセキュリティイベントとして別途アプリログへ記録し、contentやキーは含めない。保持期間切れでslotを自動削除する場合も、削除前に `context.expire` として `access_logs` に記録する。これによりユーザーは、消えた理由が明示削除なのか時間経過なのかをダッシュボードで確認できる。

WorkThreadsでは `agent.thread.create`、`agent.message.post`、`agent.thread.read`、`agent.task.claim`、`agent.task.complete`、`agent.task.timeout` を監査対象にする。ログに保存するのは `thread_id`、`task_id`、`agent_name`、`result`、`client_type`、件数、token概算だけとし、message本文、プロンプト、AI応答全文は保存しない。

保持期間:
- Freeは24時間保持
- Proは30日保持
- アカウント削除時は `ON DELETE CASCADE` で即時削除
- 期限切れログは日次ジョブで削除する
- 期限切れcontextの削除ジョブは、content本文を復号せず、`user_id`・`slot_name`・削除時刻だけをログ化してから対象slotを削除する
- 期限切れWorkThreadsの削除ジョブは、message本文を復号せず、`agent.thread.expire` を記録してからthread/messages/tasks/runsを削除する

### WorkThreadsのロック・デッドロック対策

WorkThreadsで最も避けるべき実装は、AI処理中にDB transactionを開いたままにすること。AI推論や外部AIクライアント待ちは秒〜分単位になり得るため、DB transactionはclaim、INSERT、completeの短い処理だけで閉じる。

実装ルール:

- message本文はappend-only INSERTにする
- task claimは `FOR UPDATE SKIP LOCKED` を使う
- thread状態更新は `version` による楽観ロックを使う
- `lock_timeout` と `statement_timeout` を設定する
- lock順序は `agent_threads` → `agent_tasks` → `agent_messages` → `stats/access_logs`
- deadlockやlock timeoutは `agent_runs.status='timeout'` として記録し、本文は保存しない
- 同一taskの二重完了は `lease_owner` と `lease_until` 条件で防ぐ

### WorkThreadsの負荷試験

公開前に少なくとも以下を測る。

- 1ユーザーあたりmessage 5,000件/日
- 複数ユーザー合計でmessage 100,000件/日
- claim/completeのp95/p99 latency
- lock wait時間
- deadlock count
- DB connection pool使用率
- partition pruningが効いているか

この結果により、WorkThreadsをPro標準に含めるか、Pro上位/従量課金に分けるかを判断する。

### 管理エンドポイント

本番ではFastAPIの `/docs`、`/redoc`、`/openapi.json` を公開しない。必要な場合はローカル開発環境、または管理者認証済みの内部環境に限定する。

APIキー再発行はログイン済みJWTだけでなく、直近のログインまたは再認証を要求する。再発行成功時は新しい平文キーを一回だけ表示し、以後はprefix・作成日・最終利用日時だけを表示する。

依存ライブラリはバージョン固定し、FastAPI・Supabase関連・MCPライブラリ・暗号ライブラリの脆弱性チェックをCIまたはリリース前チェックに含める。

---

## デプロイ

**リポジトリ構成：**

```
a2cr/
├── backend/
│   ├── main.py
│   ├── routers/
│   ├── services/
│   ├── models/
│   └── mcp/
├── frontend/
│   ├── src/
│   │   ├── pages/       # Landing, Pricing, Dashboard, Settings
│   │   ├── components/
│   │   └── lib/         # Supabase client, API client
│   └── vite.config.ts
└── railway.toml
```

**ビルドフロー：**
1. `npm run build` → `frontend/dist/` 生成
2. FastAPIが `frontend/dist/` を静的配信
3. `/api/*` と `/mcp` はFastAPIがハンドル
4. それ以外は `index.html` を返す（SPA routing）

FastAPIのルーティングは `/api/*` と `/mcp` を先に登録し、SPA fallbackを最後に登録する。

**Railway 環境変数：**

```
SUPABASE_URL
SUPABASE_ANON_KEY
SUPABASE_JWKS_URL
DATABASE_URL              # RLS対象の最小権限DBロール
FERNET_KEY                # content暗号化キー
API_KEY_HASH_SECRET       # APIキーハッシュ用
AUDIT_LOG_HASH_SECRET     # IP/User-Agentハッシュ用
ALLOWED_ORIGINS
A2CR_SERVICE_URL  # resume_promptに表示する公開MCP URL
RATE_LIMIT_REDIS_URL      # 任意。未設定時はPostgresベースのrate limitへフォールバック
```

`SUPABASE_SERVICE_ROLE_KEY` は通常のRailwayランタイム環境変数に置かない。migrationや管理作業に必要な場合は、実行環境を分けて短時間だけ使う。
## WorkThreads Clarification: Persistent Cross-Window And Cross-Agent Workspace

Updated: 2026-05-04

The earlier WorkThreads description can be misunderstood as "AI agents chatting with each other" or as a speculative multi-agent discussion feature. That is not the intended product meaning.

WorkThreads is a persistent work thread that survives the current AI conversation window and can be resumed by different AI clients, different AI vendors, and different devices. Current subagents are scoped to one parent conversation/session. WorkThreads externalizes the work state so Claude, Codex, Cursor, or another MCP-capable client can continue the same task without the user re-explaining the work.

Core and WorkThreads are different layers:

| Layer | Purpose |
|---|---|
| WorkBaton | Checkpoint layer: save compact context, resume/load it later |
| WorkThreads | Shared work layer: durable task state, append-only work notes, claims, failed attempts, verification results, and final handoff across AI windows and AI agents |

Primary WorkThreads use cases:

- Continue a task from a new AI window without losing the prior subagent/task state
- Hand off a failed or partial task from one AI client to another
- Let different AI agents append implementation, review, verification, and decision notes to the same durable work thread
- Preserve task claim/lease state so parallel AI work can coordinate without relying on one chat transcript
- Show humans progress metadata while keeping agent-readable message bodies hidden from the dashboard

Design implications:

- API names, docs, tests, and dashboard labels should emphasize persistent cross-agent work thread, handoff, task state, and shared agent workspace.
- Avoid positioning WorkThreads as generic AI social/chat, autonomous debate, or public agent collaboration.
- A2CR still does not run LLM inference in the initial WorkThreads version. External AI clients call MCP/API tools to append, read, claim, and complete work.
- Dashboard APIs must keep returning metadata only. Decrypted thread messages are for authenticated AI/MCP routes, not human dashboard payloads.

## Service Selection Decision: Railway + Supabase + Cloudflare + Stripe

Updated: 2026-05-04

After comparing the service selection proposals, A2CR Web SaaS will use the following production architecture:

| Area | Selected Service | Role |
|---|---|---|
| Frontend + Backend + MCP | Railway | Runs one FastAPI service that serves the React/Vite SPA, `/api/*`, and `/mcp` from the same origin |
| Database + Auth + RLS | Supabase | Provides Supabase Auth, Google OAuth integration, Postgres, migrations, and Row Level Security |
| Domain + DNS + CDN/security | Cloudflare | Domain registration/transfer, DNS, SSL/TLS, DNSSEC, and basic edge protection |
| Payments | Stripe | Pro subscription, Checkout/Payment Links, Billing, and webhook-driven plan updates |
| Source control + CI | GitHub | Repository, issues, PRs, and deployment automation |
| Google login configuration | Google Cloud OAuth | OAuth Client ID/secret used by Supabase Auth |

Initial plan:

- Railway Hobby for MVP and early beta.
- Supabase Free during local/early development, then Supabase Pro before production launch.
- Cloudflare Free plus a paid domain.
- Stripe account created early, but paid subscription flows enabled only when Pro billing is ready.
- Sentry, PostHog, Resend, and Upstash are optional later services, not MVP blockers.

Services intentionally not selected for MVP:

- Vercel: not used because the product benefits from one same-origin Railway service for React SPA, FastAPI APIs, and MCP. Splitting frontend and backend adds CORS, auth, environment, and deployment complexity. Vercel Hobby is also not appropriate for a commercial SaaS.
- Firebase Auth / Firestore / Cloud Functions / Firebase Hosting: not used because the current design depends on Postgres, RLS, least-privileged runtime DB roles, SQL migrations, and `SET LOCAL app.user_id`. Firestore TTL is also not precise enough for the product's visible retention semantics.
- Render Free: acceptable for experiments, but not the selected path because Railway better matches the existing FastAPI + React + MCP one-service deployment plan.
- GCP-only architecture: technically possible, but it would be a different product architecture and would require replacing the Supabase/Postgres/RLS foundation.

Deployment implication:

Railway is the only public application runtime for the MVP. It must serve:

- `/` and SPA routes from the React/Vite build
- `/api/*` through FastAPI
- `/mcp` through the HTTP MCP server

Supabase remains the source of truth for users, profiles, slots, API keys, stats, access logs, and future WorkThreads tables. Browser clients must not query `contexts`, `api_keys`, `access_logs`, or WorkThreads tables directly from Supabase; all product data access goes through FastAPI.

Cost-control implication:

A2CR does not use OpenAI, Anthropic, or other LLM APIs server-side in the MVP. AI clients bring their own model access and call A2CR through MCP/API. This keeps A2CR's infrastructure costs tied to storage, auth, requests, and metadata processing rather than model inference.
