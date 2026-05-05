# A2CR 使用説明書

AIエージェント（Claude・GPT・Gemini等）が会話コンテキストを30分間保存・復元できるローカルサービスです。

---

## 目次

1. [セットアップ](#セットアップ)
2. [起動方法](#起動方法)
3. [基本的な使い方（curl）](#基本的な使い方curl)
4. [APIリファレンス](#apiリファレンス)
5. [ダッシュボード](#ダッシュボード)
6. [MCPサーバー（Claude Code連携）](#mcpサーバーclaude-code連携)
7. [仕様・制約](#仕様制約)
8. [トラブルシューティング](#トラブルシューティング)

---

## セットアップ

### 前提条件
- Python 3.13
- Windows 11

### インストール

```bash
cd <project-root>
pip install -r requirements.txt
```

### APIキーの確認

初回 `start.bat` 実行時に自動生成されます。

```
%APPDATA%\a2cr\.env
```

内容例：
```
API_KEY=sk-xxxxxxxxxxxxxxxx...
FERNET_KEY=xxxxxxxxxxxx...
DB_PATH=%APPDATA%\a2cr\a2cr.db
```

---

## 起動方法

### `start.bat` で一発起動（推奨）

```bat
start.bat
```

- FastAPI サーバーがバックグラウンドで起動（ポート 8000）
- Streamlit ダッシュボードがフォアグラウンドで起動（ポート 8501）
- `.env` がない場合、APIキーとFernetキーを自動生成

### 手動起動

ターミナルを2つ開いて：

```bash
# ターミナル1：APIサーバー
uvicorn main:app --host 127.0.0.1 --port 8000

# ターミナル2：ダッシュボード
streamlit run dashboard/app.py --server.port 8501
```

### 動作確認

```bash
curl http://localhost:8000/v1/health
# → {"status": "ok"}
```

---

## 基本的な使い方（curl）

### APIキーを変数にセット

```bash
API_KEY="sk-xxxxxxxx..."   # .envファイルの値をコピー
```

### 1. コンテキストを保存する

```bash
curl -X POST http://localhost:8000/v1/context/save \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "slot_name": "my-project-main",
    "content": {
      "goal": "FastAPIアプリのバグを修正する",
      "current_state": "認証エラーの原因を特定済み。routers/auth.pyの42行目が問題",
      "next_action": "routers/auth.pyを修正してテストを実行する",
      "decisions": ["JWTトークンを使う", "有効期限は24時間"],
      "constraints": ["後方互換性を維持すること"],
      "environment": "Python 3.13, FastAPI 0.115"
    },
    "original_length": 15000,
    "model_source": "claude"
  }'
```

レスポンス例：
```json
{
  "slot_name": "my-project-main",
  "expires_at": "2026-05-03T21:00:00",
  "compressed_tokens": 87,
  "saved_tokens": 4913
}
```

### 2. コンテキストを読み込む

```bash
curl http://localhost:8000/v1/context/my-project-main \
  -H "X-API-Key: $API_KEY"
```

### 3. スロット一覧を見る

```bash
curl http://localhost:8000/v1/context/list \
  -H "X-API-Key: $API_KEY"
```

### 4. ハンドオフテキストを取得する（新しいAIウィンドウへの引き継ぎ）

```bash
curl http://localhost:8000/v1/context/my-project-main/handoff \
  -H "X-API-Key: $API_KEY"
```

レスポンスの `handoff_text` をそのまま新しいAIウィンドウに貼り付けると引き継ぎができます。

### 5. スロットを削除する

```bash
curl -X DELETE http://localhost:8000/v1/context/my-project-main \
  -H "X-API-Key: $API_KEY"
```

---

## APIリファレンス

すべてのエンドポイントに `X-API-Key` ヘッダーが必要です。

### `POST /v1/context/save`

コンテキストを保存します。同じ `slot_name` が存在する場合は上書きし、TTLをリセットします。

**リクエストボディ：**

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `slot_name` | string | ✅ | スロット名。`[a-zA-Z0-9_-]{1,64}` |
| `content` | object | ✅ | コンテキスト内容（下記参照） |
| `original_length` | int | - | 元のトークン数換算のための文字数（節約トークン計算に使用） |
| `model_source` | string | - | `"claude"` / `"gpt"` / `"gemini"` / `"other"` |

**`content` オブジェクト：**

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `goal` | string | ✅ | 達成したいこと |
| `current_state` | string | ✅ | 現在の状況・完了済みの作業 |
| `next_action` | string | ✅ | 次にやるべき具体的なステップ |
| `decisions` | list[string] | - | 決定済みの設計・方針 |
| `constraints` | list[string] | - | 次のAIが守るべきルール |
| `problems` | list[string] | - | 未解決の問題・リスク |
| `environment` | string | - | OS・言語・フレームワークのバージョン |
| `background` | string | - | 判断の背景・文脈 |
| `summary` | string | - | 長い作業の要約 |
| `failed_attempts` | list[string] | - | 試みて失敗したアプローチ |
| `references` | list[string] | - | 仕様URL・ファイルパス・ドキュメントリンク |

**レスポンス（201）：**

```json
{
  "slot_name": "my-project-main",
  "expires_at": "2026-05-03T21:00:00",
  "compressed_tokens": 87,
  "saved_tokens": 4913
}
```

---

### `GET /v1/context/{slot_name}`

保存済みコンテキストを読み込みます。読み込むたびに `load_count` が増加します。

**レスポンス（200）：**

```json
{
  "slot_name": "my-project-main",
  "content": { ... },
  "expires_at": "2026-05-03T21:00:00",
  "compressed_tokens": 87,
  "model_source": "claude",
  "load_count": 3
}
```

---

### `GET /v1/context/list`

有効期限内のすべてのスロット一覧を返します。

**レスポンス（200）：** スロット情報の配列

---

### `GET /v1/context/{slot_name}/handoff`

指定スロットの内容をMarkdown形式のハンドオフテキストに変換して返します。

**レスポンス（200）：**

```json
{
  "slot_name": "my-project-main",
  "handoff_text": "# GOAL\n...\n\n# CURRENT_STATE\n..."
}
```

---

### `DELETE /v1/context/{slot_name}`

スロットを削除します。

**レスポンス（200）：** `{"message": "deleted"}`

---

### `GET /v1/health`

サーバーの死活確認。認証不要。

**レスポンス（200）：** `{"status": "ok"}`

---

### エラーレスポンス形式

```json
{
  "code": "slot_limit_exceeded",
  "message": "Maximum slot count (3) reached"
}
```

| コード | HTTP | 説明 |
|---|---|---|
| `slot_limit_exceeded` | 400 | スロット上限（3件）に達した |
| `content_too_large` | 400 | コンテンツが10KBを超えている |
| `slot_not_found` | 404 | スロットが存在しないか期限切れ |
| `invalid_api_key` | 401 | APIキーが不正 |

---

## ダッシュボード

ブラウザで `http://localhost:8501` を開くと、Streamlit製のダッシュボードが表示されます。

### 画面の見方

```
┌─────────────────────────────────────────────────────┐
│ A2CR                                        │
│                                                     │
│  累計保存回数   累計ロード回数   累計節約トークン      │
│      3              1              4500             │
│─────────────────────────────────────────────────────│
│ 現在のスロット（2/3 件使用中）                        │
│                                                     │
│ ▶ my-project  — 残り 🟢28分                          │
│ ▶ test-slot   — 残り 🟠8分  ← 10分未満でオレンジ     │
└─────────────────────────────────────────────────────┘
```

スロット行をクリックすると展開して詳細が表示されます：

```
▼ my-project  — 残り 28分
  モデル: claude   サイズ: 982B   圧縮後: 353tok   節約: 4913tok   ロード: 1回

  goal: A2CR ローカルMVPの実装
  current_state: 全12タスク実装済み...
  next_action: 実際の作業でMCPを活用...

  { "goal": "...", "decisions": [...], ... }   ← JSON全体

  [ 削除 ]  ← クリックでそのスロットを削除
```

### 使い方

| やりたいこと | 操作 |
|---|---|
| スロットの内容を確認する | スロット行をクリックして展開 |
| 期限切れそうなスロットを見つける | オレンジ色の残り時間が目印 |
| 不要なスロットを消す | 展開して「削除」ボタンをクリック |
| 最新状態に更新する | ブラウザをリロード（30秒で自動更新） |

---

## Swagger UI（APIデバッグ用）

`http://localhost:8000/docs` を開くと Swagger UI が表示されます。**普段は不要**ですが、APIが正しく動いているか確認したいときに使います。

### 画面の見方

```
┌─────────────────────────────────────────────────────┐
│ A2CR  0.1.0                  [ Authorize 🔒]│  ← APIキー入力ボタン
│─────────────────────────────────────────────────────│
│ GET   /v1/health        ▼                           │
│ POST  /v1/context/save  ▼                           │  ← クリックで展開
│ GET   /v1/context/list  ▼                           │
│ GET   /v1/context/{slot_name}/handoff ▼             │
│ GET   /v1/context/{slot_name}  ▼                    │
│ DELETE /v1/context/{slot_name} ▼                    │
└─────────────────────────────────────────────────────┘
```

### 使い方

**① Authorize でAPIキーを登録**

1. 右上の **Authorize 🔒** をクリック
2. `API_KEY` の値（`sk-xxxx...`）を入力して **Authorize**
3. **Close** で閉じる（以降すべての操作に自動で適用される）

**② エンドポイントを試す**

1. 使いたいエンドポイント（例: `POST /v1/context/save`）をクリックして展開
2. **Try it out** をクリック
3. Request body を編集して **Execute**
4. 下に `Response body` が表示される

**いつ使うか**

- `start.bat` 起動後に API が動いているか確認したい
- curl コマンドを書く前に手軽に動作確認したい
- エラーが出たときにリクエスト/レスポンスの詳細を見たい

---

## MCPサーバー（Claude Code連携）

Claude Code から直接 A2CR を操作できます。

### 登録方法

`~/.claude/mcp.json` に以下を追加：

```json
{
  "mcpServers": {
    "a2cr": {
      "command": "python",
      "args": ["<project-root>/mcp/server.py"],
      "env": {
        "A2CR_API_KEY": "<.envファイルのAPI_KEYの値>"
      }
    }
  }
}
```

APIキーは `.env` ファイルから確認：
```
%APPDATA%\a2cr\.env
```

### 利用可能なMCPツール

| ツール名 | 説明 |
|---|---|
| `save_context` | コンテキストを保存 |
| `load_context` | コンテキストを読み込み |
| `list_contexts` | スロット一覧を表示 |
| `delete_context` | スロットを削除 |
| `get_handoff` | ハンドオフテキストを取得 |

### Claude Codeでの使い方例

Claude に対してこのように指示するだけで動作します：

```
今の作業内容を a2cr の "my-project-main" スロットに保存してください
```

```
a2cr の "my-project-main" を読み込んで、作業を再開してください
```

---

## 仕様・制約

| 項目 | 値 |
|---|---|
| スロット上限 | 3件 |
| コンテンツ上限 | 10KB |
| TTL（有効期限） | 30分（保存・上書きのたびにリセット） |
| 暗号化 | Fernet（AES-128-CBC）アプリ層暗号化 |
| DBエンジン | SQLite（ORM経由、生SQLなし） |
| APIキー認証 | `hmac.compare_digest`（タイミング攻撃対策済み） |
| スロット名 | 正規表現 `[a-zA-Z0-9_-]{1,64}` |
| 期限切れクリーンアップ | APIサーバー起動中に10分ごと自動実行 |

### スロット名の命名規則

`{プロジェクト名}-{用途}` の形式を推奨：

```
my-app-main       # メインの作業
my-app-debug      # デバッグ中の分岐
my-app-review     # レビュー対応
```

---

## テスト

```bash
python -m pytest -v
```

43テストがすべてパスすることを確認できます。

---

## トラブルシューティング

### APIサーバーが起動しない

```bash
# ポート8000が使用中か確認
netstat -ano | findstr :8000

# 別のポートで起動
uvicorn main:app --port 8001
```

### 「slot_limit_exceeded」エラーが出る

スロットが3件埋まっています。

```bash
# 一覧を確認して不要なものを削除
curl http://localhost:8000/v1/context/list -H "X-API-Key: $API_KEY"
curl -X DELETE http://localhost:8000/v1/context/{slot_name} -H "X-API-Key: $API_KEY"
```

または期限切れを待つか、ダッシュボードの削除ボタンを使います。

### APIキーがわからない

```
%APPDATA%\a2cr\.env
```

を開いて `API_KEY=` の値を確認してください。

### MCP サーバーが動かない

MCPサーバーは **スクリプトとして実行** する必要があります（`import mcp.server` は不可）。

```bash
# 正しい起動方法
python mcp/server.py
```

`~/.claude/mcp.json` の `args` に `mcp/server.py` のフルパスを指定していることを確認してください。

### Swagger UI でAPIを試す

`http://localhost:8000/docs` をブラウザで開くと、GUI でAPIをテストできます。

「Authorize」ボタンをクリックして APIキーを入力してから各エンドポイントを試してください。
