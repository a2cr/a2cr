# AI Clipboard Web SaaS 設計書

作成日：2026-05-03  
対象：Web SaaS版（マルチユーザー・Google OAuth・React ダッシュボード）

---

## 概要

ローカルMVPをSaaSとして公開する。Google OAuthでログインし、APIキーを発行してClaude・Codex・Cursor等のMCP対応AIエージェントから利用できる。ローカル版で検証済みのAPI仕様をそのまま維持し、マルチユーザー対応・クラウドDB・Reactダッシュボードへ移行する。

---

## スコープ

### 今回含む
- Google OAuth認証（Supabase Auth）
- マルチユーザー対応（user_id分離）
- 既存APIのクラウド移植（`/api/v1/*`）
- HTTP型MCPサーバー（`/mcp`）
- Reactダッシュボード（ランディング・料金・ダッシュボード・設定）
- APIキー発行・管理ページ（設定手順付き）
- Railway + Supabaseへのデプロイ

### 今回含まない
- Proプラン・Stripe決済（Coming Soon表示のみ）
- pip CLIセットアップツール
- `get_handoff` エンドポイント（削除）
- ローカル版（テスト用として残すが開発対象外）

---

## アーキテクチャ

```
ブラウザ / AIエージェント
        │
        ▼
https://ai-clipboard.up.railway.app/
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
  Google OAuth     （RLS有効）
```

---

## 認証

| 用途 | 方式 |
|---|---|
| ダッシュボードログイン | Google OAuth → Supabase JWT |
| API / MCPアクセス | `Authorization: Bearer sk-xxx`（APIキー） |
| `/api/v1/health` | 認証不要 |

**APIキーの仕様：**
- 1ユーザー1キー（再発行すると旧キーは即時無効）
- サーバー側にSHA-256ハッシュのみ保存（平文は発行時のみ表示）
- 形式：`sk-` + `secrets.token_hex(32)`

---

## データベーススキーマ

### contexts テーブル

| カラム | 型 | 変更点 |
|---|---|---|
| id | UUID | 変更なし |
| **user_id** | UUID FK → auth.users | **新規追加** |
| slot_name | TEXT | 変更なし |
| content | TEXT（暗号化） | 変更なし |
| created_at | TIMESTAMPTZ | 変更なし |
| updated_at | TIMESTAMPTZ | 変更なし |
| expires_at | TIMESTAMPTZ | 変更なし |
| size_bytes | INTEGER | 変更なし |
| original_tokens | INTEGER | 変更なし |
| compressed_tokens | INTEGER | 変更なし |
| load_count | INTEGER | 変更なし |
| model_source | TEXT | 変更なし |

```sql
UNIQUE (user_id, slot_name)  -- 旧: UNIQUE(slot_name)

CREATE POLICY "users_own_slots" ON contexts
  USING (user_id = auth.uid());
```

### stats テーブル

```sql
user_id         UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE
total_saves     INTEGER DEFAULT 0
total_loads     INTEGER DEFAULT 0
total_tokens_saved INTEGER DEFAULT 0
```

### api_keys テーブル（新規）

```sql
user_id      UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE
key_hash     TEXT NOT NULL
created_at   TIMESTAMPTZ
last_used_at TIMESTAMPTZ
```

---

## APIエンドポイント

### AIエージェント向け（APIキー認証）

| メソッド | パス | 説明 |
|---|---|---|
| POST | `/api/v1/context/save` | コンテキスト保存 |
| GET | `/api/v1/context/list` | スロット一覧 |
| GET | `/api/v1/context/{slot_name}` | コンテキスト取得 |
| DELETE | `/api/v1/context/{slot_name}` | スロット削除 |
| GET | `/api/v1/health` | ヘルスチェック（認証不要） |

※ `get_handoff` は削除

### ダッシュボード向け（Supabase JWT認証）

| メソッド | パス | 説明 |
|---|---|---|
| POST | `/api/dashboard/api-key/issue` | APIキー発行（旧キー無効化） |
| GET | `/api/dashboard/api-key` | キー情報取得（ハッシュのみ） |
| GET | `/api/dashboard/stats` | 累計統計取得 |

---

## MCPサーバー

- エンドポイント：`POST /mcp`（Streamable HTTP型）
- 認証：`Authorization: Bearer sk-xxx`（APIキーと共通）
- ローカル起動不要、クラウド上で常時稼働

**提供ツール：**

| ツール名 | 対応API |
|---|---|
| `save_context` | POST /api/v1/context/save |
| `load_context` | GET /api/v1/context/{slot_name} |
| `list_contexts` | GET /api/v1/context/list |
| `delete_context` | DELETE /api/v1/context/{slot_name} |

**ユーザーの設定（Claude）：**
```json
{
  "mcpServers": {
    "ai-clipboard": {
      "type": "http",
      "url": "https://ai-clipboard.up.railway.app/mcp",
      "headers": { "Authorization": "Bearer sk-xxxxx" }
    }
  }
}
```

**ユーザーの設定（Codex）：**
```toml
[mcp_servers."ai-clipboard"]
url = "https://ai-clipboard.up.railway.app/mcp"
api_key = "sk-xxxxx"
```

---

## Reactダッシュボード

### ページ構成

| パス | 内容 | 認証 |
|---|---|---|
| `/` | ランディングページ | 不要 |
| `/pricing` | 料金プランページ | 不要 |
| `/dashboard` | メインダッシュボード | 必要 |
| `/settings` | APIキー・設定手順 | 必要 |

### 技術スタック

| 項目 | 採用 |
|---|---|
| フレームワーク | React + Vite |
| 認証 | Supabase Auth（`@supabase/auth-ui-react`） |
| HTTPクライアント | fetch（ライブラリなし） |
| スタイル | Tailwind CSS |
| ルーティング | React Router |

### `/dashboard` の表示内容

- サーバーステータス（🟢/🔴）
- 累計統計（保存回数・ロード回数・節約トークン）
- スロット一覧（残り時間・サイズ・削除ボタン・コンテンツプレビュー）
- 自動リロード ON/OFF
- 言語切替（日本語/英語）

### `/settings` の表示内容

- APIキー表示・コピー・再発行ボタン
- セットアップ手順（Claude / Codex / Cursor タブ切替）

### `/pricing` の表示内容

| Free | Pro |
|---|---|
| スロット3件 | スロット無制限 |
| TTL 30分 | 無期限保存 |
| 無料 | Coming Soon |

---

## デプロイ

**リポジトリ構成：**

```
ai_clipboard/
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

**Railway 環境変数：**

```
SUPABASE_URL
SUPABASE_ANON_KEY
SUPABASE_SERVICE_ROLE_KEY
FERNET_KEY       # コンテンツ暗号化キー（ローカル版の.envから移行）
```
