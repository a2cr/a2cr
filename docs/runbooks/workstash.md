# WorkStash Runbook

WorkStash は A2CR の一時作業記憶 DB サービス。AI エージェントがセッション内・セッション間で作業メモを保存・取得するために使う。WorkBaton（直列引き継ぎ）・WorkThreads（並列協業）とは独立した DB・暗号化方針を持つ。

## 暗号化設計

WorkStash は WorkBaton と同じ**クライアント側 Fernet 暗号化**を採用する。

WorkStash は WorkBaton と同じ前提（同一ユーザーが同一ローカル環境から使う）が成立するため、ローカル stdio ラッパーによるクライアント側暗号化が適用できる。WorkThreads はサーバー側 Fernet（複数エージェントがローカルキーを共有できないため）を採用しており、暗号化方針が異なる。

セキュリティの主張：

- エントリはローカル stdio ラッパーで暗号化されてからアップロードされる
- A2CR は暗号文のみを保存し、復号できない
- ローカルクライアントキーを失うと保存済みエントリは復号不可能になる
- テナント分離は RLS と `user_id` 述語で保証する

## コンテンツ境界

- ダッシュボードはキー名・サイズ・タグ・有効期限・作成日時のみ返す
- ダッシュボードと React ペイロードは `encrypted_value` の復号内容を含んではならない
- WorkStash は WorkBaton Slot や WorkThreads のメッセージストアに書き込まない

## MCP ツール

- `store_work_stash` — キー・バリューを保存（同一キーは upsert）
- `get_work_stash` — キーを指定して値を取得
- `list_work_stash` — エントリ一覧を返す（値は含まない）
- `delete_work_stash` — 指定キーを削除
- `should_use_work_stash` — 保存すべきかを判断するアドバイザリーツール

MCP ツールは AI クライアントから直接使う。HTTP エンドポイントを直接推測・呼び出しすることは禁止。

## WorkBaton との連携

WorkStash のキー名を WorkBaton の `references` または `next_action` に記録することで、次のセッションのエージェントがデータを再取得できる。

```
WorkBaton: next_action に "WorkStash key: api_spec_v1 を参照" と記録
次セッション: WorkBaton ロード → get_work_stash(key="api_spec_v1")
```

WorkBaton にデータ本体を格納しない。キー名だけを引き継ぐことで WorkBaton のコンパクト設計を維持する。

## プラン別制限

| 項目 | 無料 | PRO |
|------|------|------|
| 合計容量 | 256 KB | 2 MB |
| TTL | 7日 | 30日 |
| 公開上のエントリ数上限 | なし | なし |
| 1エントリ最大サイズ | 8 KB | 32 KB |

容量超過時は新規書き込みを拒否する。既存エントリの強制削除は行わない。

## TTL と削除ジョブ

- `expires_at` を過ぎたエントリはメンテナンスジョブが定期削除する
- 実装は WorkBaton の `expire-contexts` と同じパターン
- バッチサイズを制限し、大量削除をリクエストパスに含めない
- 手動削除は `delete_work_stash` または `delete_all_work_stash` で実行

## セキュリティ境界

保存禁止コンテンツ（ツールレベルで拒否）：

- APIキー・Authorizationヘッダー・DB URL
- パスワード・シークレット類
- 個人情報・決済情報
- 大きなソースコード本体・フルログ

アクセスログに含めてはならないもの：

- value の内容
- APIキー・Authorizationヘッダー
- 生のIPアドレス

## 分離境界

Core は user_id・プラン・APIキー・課金状態の信頼できる情報源として残る。WorkStash は Core の `routers.workstash` をマウントしないことで無効化できる。WorkBaton の save/load/resume と WorkThreads は独立して動作する。

## インシデント対応

- ローカルクライアントキーが漏洩した疑いがある場合は新しいキーで再保存を促す（A2CR は復号できないため旧エントリの内容は確認不可）
- テナント分離バイパスの疑いがある場合は影響ユーザーに通知し該当エントリを削除する
- 削除ジョブ失敗時は Railway ジョブログを確認し、手動で `expire-work-stash` を実行する
- DB エラー時は WorkBaton と同じ障害マトリクスに従う
