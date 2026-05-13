# A2CR WorkStash 設計仕様書

Status: Draft  
Date: 2026-05-08  
Author: Working document — internal planning only

---

## 1. 概要

WorkStash は A2CR の第三のサービスであり、AI エージェントがセッション内およびセッション間で利用する**一時的な作業記憶 DB** を提供する。

WorkBaton（直列引き継ぎ）・WorkThreads（並列協業）とは独立した DB・暗号化方針を持つ。

### 設計哲学

- WorkBaton が「次のエージェントへの引き継ぎ書」なら、WorkStash は「今のプロジェクトの作業デスク」
- エージェントがコンテキストウィンドウに抱えていた作業メモを外部に出し、ウィンドウを軽量に保つ
- WorkBaton と連携して「地図（WorkBaton）＋データ（WorkStash）」という分離を実現する
- 7日または30日で自動削除される一時領域であることを明示する

---

## 2. 他サービスとの位置づけ

**このドキュメントは WorkBaton 用の一時保管 DB（WorkStash）の設計書である。**

| サービス | 役割 | 一時保管DB | 暗号化 | プラン |
|------|------|------|------|------|
| WorkBaton | セッション間の直列引き継ぎ | **WorkStash（本書）** | クライアント側 Fernet | 無料・PRO |
| WorkThreads | エージェント間の並列協業 | **WorkStash（別設計書）** | サーバー側 Fernet | PRO のみ |

WorkThreads にも一時保管 DB（WorkStash）が存在するが、WorkThreads は複数エージェントがローカルキーを共有できないためサーバー側 Fernet を採用しており、暗号化の仕組みが根本的に異なる。そのため WorkStash とは完全に別の DB を使用する。WorkStash の設計は別ドキュメントで定義する。

### WorkBaton との連携パターン

```
エージェントA（セッション1）
  ├─ WorkStash に作業メモを保存
  │    store_work_stash(key="api_spec_v2", value="...")
  │
  └─ WorkBaton 保存時にキー情報だけを記録
       next_action: "WorkStash key: api_spec_v2 を参照してAPIの仕様を確認する"

エージェントB（セッション2）
  ├─ WorkBaton をロード → WorkStashキーを把握
  └─ get_work_stash(key="api_spec_v2") → データ取得
```

WorkBaton にデータ本体を詰め込まず、キー情報だけを引き継ぐ。WorkBaton のコンパクト哲学と完全に一致する。

---

## 3. 暗号化方針

### クライアント側 Fernet（WorkBaton と同方針）

WorkStash は WorkBaton と同じ**クライアント側 Fernet 暗号化**を採用する。

- ローカル stdio ラッパーがアップロード前にコンテンツを暗号化する
- A2CR サーバーは暗号文のみを受け取り、復号できない
- ローカルクライアントキーはユーザーのローカル環境に留まる

### なぜクライアント側で統一できるか

WorkStash は WorkBaton と同じ前提に立つ。**同一ユーザーが同一ローカル環境から使う。**

WorkThreads がサーバー側 Fernet を必要とした理由は「複数の独立したエージェントウィンドウがローカルキーを共有できない」という構造上の制約だった。WorkStash はこの制約が発生しないため、WorkBaton と同じクライアント側暗号化が成立する。

### セキュリティ上の位置づけ

- WorkBaton と同様に「A2CR は WorkStash の値を復号できない」という保証が成立する
- ローカルクライアントキーを失うと、保存済みエントリは復号不可能になる
- WorkBaton・WorkStash の暗号化保証と WorkThreads の保証は明確に異なる

### 別 DB とする理由

WorkBaton（クライアント暗号化）・WorkThreads（サーバー側 Fernet）・WorkStash（クライアント暗号化）は、データライフサイクル・アクセスパターン・TTL 管理が異なる。テナント分離・マイグレーション・バックアップ・削除ジョブを独立して管理できるよう、別 DB テーブルグループとして設計する。

---

## 4. データ構造

### テーブル: `work_stash_entries`

| カラム | 型 | 説明 |
|------|------|------|
| `id` | UUID (PK) | エントリID |
| `user_id` | UUID (FK) | テナント分離キー |
| `entry_key` | VARCHAR(256) | エージェントが指定するキー名 |
| `encrypted_value` | TEXT | サーバー側 Fernet で暗号化された値 |
| `size_bytes` | INTEGER | 値のバイト数（プラン容量管理用） |
| `created_at` | TIMESTAMPTZ | 作成日時（UTC） |
| `expires_at` | TIMESTAMPTZ | 有効期限（UTC） |
| `last_accessed_at` | TIMESTAMPTZ | 最終アクセス日時 |
| `tags` | TEXT[] | 任意のタグ（検索・整理用） |

### ユニーク制約

```sql
UNIQUE (user_id, entry_key)
```

同一ユーザーの同一キーへの書き込みは上書き（upsert）とする。

### RLS ポリシー

```sql
CREATE POLICY work_stash_tenant_isolation ON work_stash_entries
  USING (user_id = app.current_user_id());
```

---

## 5. プラン別制限

| 制限項目 | 無料 | PRO |
|------|------|------|
| 合計容量 | 256 KB | 1,024 KB |
| TTL | 7日 | 30日 |
| 公開上のエントリ数上限 | なし | なし |
| 1エントリの最大サイズ | 8 KB | 32 KB |
| 1時間あたり書き込み上限 | 200回 | 400回 |
| 1時間あたり読み取り上限 | 300回 | 800回 |

### 容量超過時の動作

- 新規書き込み時にユーザーの合計使用量を確認する
- 容量超過の場合は書き込みを拒否し、エラーメッセージで現在の使用量と上限を返す
- 自動削除（古いエントリの強制削除）は行わない

### プランダウングレード時

- 既存エントリは読み取り・削除を許可する
- 新規書き込みは Free 制限に戻るまでブロックする
- 強制削除は行わない

---

## 6. TTL と削除ポリシー

### 自動削除

- `expires_at` を過ぎたエントリはメンテナンスジョブが定期削除する
- 削除ジョブは WorkBaton の expire-contexts と同じパターンで実装する
- バッチサイズを制限し、リクエストパスで大量削除しない

### 手動削除

エージェント・ユーザーは明示的に削除できる。

```
delete_work_stash(key="api_spec_v2")
delete_all_work_stash()  # 全件削除
```

### 不要と判断した場合の削除

エージェントがタスク完了時に「このデータはもう不要」と判断した場合、明示的に削除することを推奨する。MCP ツールの description でこの動作を促す。

---

## 7. MCP ツール定義

### `store_work_stash`

作業メモを WorkStash に保存する。同一キーが存在する場合は上書きする。

```json
{
  "key": "api_spec_v2",
  "value": "GET /users returns {id, name, email}",
  "tags": ["api", "spec"],
  "ttl_override_seconds": null
}
```

**description に含めるべき内容：**
- APIレスポンス仕様・確認結果・中間メモなど、コンテキストに抱えるには重いが捨てると困る情報を保存する
- WorkBaton にキー名だけ記録しておけば、次のセッションで取り出せる
- タスク完了後は削除して容量を解放することを推奨する

### `get_work_stash`

キーを指定して値を取得する。

```json
{
  "key": "api_spec_v2"
}
```

### `list_work_stash`

保存中のエントリ一覧を返す（値は含まない）。

```json
{
  "tag_filter": ["api"],
  "include_expired": false
}
```

レスポンス例：

```json
{
  "entries": [
    {
      "key": "api_spec_v2",
      "size_bytes": 128,
      "tags": ["api", "spec"],
      "expires_at": "2026-05-15T10:00:00Z",
      "created_at": "2026-05-08T10:00:00Z"
    }
  ],
  "total_size_bytes": 128,
  "quota_bytes": 262144,
  "entry_count": 1,
  "entry_limit": null
}
```

### `delete_work_stash`

指定キーのエントリを削除する。

```json
{
  "key": "api_spec_v2"
}
```

### `should_use_work_stash`（アドバイザリー）

WorkBaton の `should_save_workbaton` に相当するアドバイザリーツール。エージェントが「これを WorkStash に保存すべきか」を判断する際に使う。

**入力：**

```json
{
  "reason": "API仕様確認結果を後で参照したい",
  "estimated_size_bytes": 512,
  "already_in_context": true
}
```

**出力：**

```json
{
  "should_store": true,
  "reason": "セッションをまたいで参照する可能性があり、コンテキスト軽量化に有効",
  "recommended_key_pattern": "プロジェクト名_内容_バージョン",
  "workbaton_hint": "WorkBatonのnext_actionにキー名を記録することで次セッションで再利用できる",
  "quota_status": {
    "used_bytes": 128,
    "quota_bytes": 262144,
    "entry_count": 1,
    "entry_limit": null
  }
}
```

---

## 8. WorkBaton との統合ガイド

### WorkBaton への記録パターン

WorkStash に保存した情報は、WorkBaton の以下のフィールドに**キー名のみ**記録する。

```json
{
  "goal": "ECサイトのAPIリファクタリング",
  "current_state": "エンドポイント一覧の確認完了",
  "next_action": "WorkStash key: endpoint_list_v1 を参照してリファクタリング対象を特定する",
  "references": [
    "WorkStash: endpoint_list_v1 (APIエンドポイント一覧)",
    "WorkStash: db_schema_notes (DBスキーマメモ)"
  ]
}
```

### 次セッションでの再開フロー

```
1. resume_context() → WorkBatonロード
2. next_actionにWorkStashキーを発見
3. get_work_stash(key="endpoint_list_v1") → データ取得
4. 作業再開
```

---

## 9. セキュリティ要件

### 保存禁止コンテンツ（ツールレベルで拒否）

- APIキー・Authorizationヘッダー・DBのURL
- パスワード・シークレット類
- 個人情報・決済情報
- 大きなソースコード本体・フルログ

### ロギングルール

アクセスログに含めて良いもの：

- action（store/get/list/delete）
- result（success/error code）
- key名（ハッシュ化推奨）
- size_bytes
- timestamp
- user_id（ハッシュ化）

アクセスログに含めてはならないもの：

- 保存した value の内容
- APIキー・Authorizationヘッダー
- 生のIPアドレス

### ダッシュボード表示ルール

- キー名・サイズ・タグ・有効期限・作成日時は表示可
- value の内容はダッシュボードに表示しない
- ダッシュボードは value を復号して返してはならない

### テナント分離

WorkBaton・WorkThreads と同じ `web_transaction(user_id)` パターンを使い、すべてのクエリに `user_id` 述語を付ける。RLS ポリシーを第二の防衛線として設定する。

---

## 10. 非目標（WorkStash がやらないこと）

- WorkBaton の代替・拡張にはならない（用途が異なる）
- WorkThreads のメッセージストレージにはならない
- ファイル・バイナリのアップロードストレージにはならない
- 永続的なプロジェクト知識ベースにはならない（TTL を超えたら消える）
- サーバー側でのAI実行・処理は行わない

---

## 11. 受け入れ基準

実装完了の判定基準：

- `store_work_stash` が同一キーへの upsert を正しく処理する
- `get_work_stash` が期限切れエントリを返さない
- 容量超過時に新規書き込みを拒否し、安全なエラーを返す
- RLS ユーザーA/Bの分離テストが通過する
- ダッシュボードが value を表示しない
- メンテナンスジョブが期限切れエントリを正しく削除する
- `should_use_work_stash` が quota 情報を返す
- WorkBaton の `references` フィールドにキー名を記録する手順が agent guide に記載される
- 保存禁止コンテンツパターンがツールレベルで拒否される
