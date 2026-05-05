# A2CR WorkBaton Save/Load Quality Specification

Updated: 2026-05-05

この文書は、WorkBatonの保存・ロード・新窓再開の品質を固定するための仕様書である。APIが動くだけでは不十分で、AIエージェントが何を保存し、何を捨て、ロード後にどう作業を再開するかまでを仕様として扱う。

## 1. 目的

WorkBatonの価値は、新しいAI窓が短時間で作業を再開できることにある。保存された内容が薄すぎると再説明が必要になり、厚すぎると新しいAIが重要情報を見失う。

この仕様の成功条件:

- 新しいAIが `goal`、`current_state`、`next_action` をすぐ把握できる。
- 直近の重要判断、制約、未解決リスクを見落とさない。
- 既に失敗した方法を繰り返しにくい。
- 必要なファイル、コマンド、テスト結果への参照がある。
- 保存本文にsecret、長大ログ、会話全文、不要な雑談が入らない。
- FreeとProで保存粒度の違いが明確である。

## 2. 用語

| 用語 | 意味 |
|---|---|
| checkpoint | WorkBatonに保存された作業文脈 |
| `save_context` | checkpointを保存するMCP/API操作 |
| `resume_prompt` | 新しいAI窓へ貼るための再開指示文 |
| `resume_context` | 新しいAI窓で最初に呼ぶ再開用MCP tool |
| `load_context` | slot名またはslot番号を指定して本文を読む操作 |
| compact | Free固定、Proでも選択可能な短い保存粒度 |
| detailed | Proのみ。判断根拠や失敗履歴まで含める保存粒度 |

## 3. 保存タイミング

AIエージェントは、次のタイミングで `save_context` を検討する。

| タイミング | 保存すべき理由 |
|---|---|
| ユーザーが保存を明示した時 | 明示指示を優先する |
| 作業フェーズが完了した時 | 次のAIが区切りから再開できる |
| 会話が長くなり文脈圧迫を感じた時 | 文脈消失を防ぐ |
| 重要な設計判断をした時 | 判断理由と制約を失わない |
| 失敗した試行から学びがあった時 | 次のAIが同じ失敗を繰り返さない |
| 新しいAI窓、別モデル、別クライアントへ移る前 | 再開品質に直結する |
| 大きな変更や危険な操作の前 | 戻れる作業状態を残す |

保存しすぎはrate limitとノイズの原因になる。小さな進捗ごとに保存するのではなく、作業の意味が変わる節目で保存する。

## 4. 保存スキーマ

現在のMVP互換スキーマは次の通り。

必須:

- `goal`
- `current_state`
- `next_action`

任意:

- `decisions`
- `constraints`
- `problems`
- `environment`
- `background`
- `summary`
- `failed_attempts`
- `references`

Pro detailedで必要になるファイル単位の作業、テスト結果、コマンド、判断理由は、当面はこの既存スキーマ内に圧縮して保存する。将来、互換性を保てる段階で `files_changed`、`tests_run`、`commands_run`、`open_questions` などの明示フィールド追加を検討する。

## 5. FreeとProの保存粒度

### 5.1 プラン差分

| 項目 | Free / compact | Pro / compact | Pro / detailed |
|---|---|---|---|
| 主目的 | 短時間の作業再開 | 軽量運用の作業再開 | 高品質な作業再開 |
| 保存方針 | 必要最小限 | Free相当だが保持期間・slot数に余裕 | 判断根拠、失敗履歴、検証結果まで保存 |
| 保存サイズ | 32KB予定 | 128KB内でcompact | 128KB内でdetailed |
| 保持期間 | 最大24時間予定 | 最大30日予定 | 最大30日予定 |
| slot数 | 3 | 100 | 100 |
| 保存対象 | 現在地と次アクション中心 | 同左 | ファイル、テスト、リスク、背景まで |
| 捨てるもの | 詳細な試行錯誤、長いログ、古い話題 | 同左 | 会話全文、secret、大量ログ、再取得可能な本文 |

Proだから何でも保存するわけではない。Pro detailedは「再開に必要な判断情報を多めに残す」だけであり、会話ログ倉庫ではない。

### 5.2 Free / compactで残すもの

Freeでは、新しいAIが次の一手を間違えないための最小情報を残す。

必ず残す:

- 最終目標
- 現在完了していること
- 次にやる具体的な作業
- 守るべき重要制約
- 直近の重要な決定
- 未解決のブロッカーまたはリスク
- 必要なファイルパス、URL、仕様書リンク
- 実行すべきコマンドがある場合はその最小形

原則として捨てる:

- 会話全文
- 長い議論の経緯
- 既に完了して今後影響しない作業
- 再度ファイルを読めば分かるコード本文
- 長大なログ
- 感想、雑談、重複した説明
- 古い仮説や破棄済み案
- secret、API key、token、個人情報

Freeでは「次に何をすればよいか」が最優先であり、「なぜそうなったか」は重要な判断に限って短く残す。

### 5.3 Pro / detailedで残すもの

Pro detailedでは、新しいAIがより深い作業文脈を再構築できるようにする。

Freeに加えて残す:

- 触ったファイルと責務
- 主要な差分の意図
- 実行したテストと結果
- 失敗した試行と失敗理由
- 重要な設計判断の理由
- 未解決リスクと検証計画
- 次に読むべき仕様書、issue、PR、関連ファイル
- DB migration、API contract、security ruleなどの注意点
- ユーザーが強くこだわった判断や表現
- 途中で見つけたが未対応の関連問題

Pro detailedでも捨てる:

- 会話全文
- secretや認証情報
- 大量のビルドログやテストログ全文
- 生成物や依存キャッシュ
- リポジトリから容易に再取得できる長いコード本文
- 結論に影響しない雑談や古い迷い

Pro detailedの目的は「次のAIが設計意図を失わないこと」であり、「すべてを保存すること」ではない。

## 6. 取捨選択ルール

AIエージェントは保存前に次の順で情報を選別する。

1. 新しいAIが作業を再開するために必要な事実を列挙する。
2. ファイルを読めば分かることは、本文ではなくファイルパスや行き先だけ残す。
3. 決定、制約、失敗、未解決リスクは優先して残す。
4. 再開直後に実行すべき作業を `next_action` に1つ以上具体化する。
5. Freeでは詳細を削り、Pro detailedでは判断理由と検証結果を追加する。
6. secret、API key、Authorization header、DB URL、OAuth secretが混ざっていないか確認する。
7. 保存本文がプラン別サイズ上限を超えないように圧縮する。

判断基準:

| 情報 | 保存判断 |
|---|---|
| 次のAIが知らないと間違える | 保存する |
| ファイルを読めば正確に分かる | パスだけ保存する |
| 過去の失敗を繰り返す防止になる | 保存する |
| 意思決定の根拠になる | Freeは短く、Pro detailedは理由も保存 |
| ただの会話経緯 | 原則捨てる |
| secretまたは個人情報 | 絶対に保存しない |

## 7. 保存本文の言語

保存本文は、原則として簡潔な英語に正規化する。理由は、AIクライアントやモデルをまたいだ時に解釈が安定しやすいためである。

例外として、次のものは原文を保持してよい。

- ユーザーの短い重要表現
- UI文言やブランド名
- エラーメッセージ
- コマンド
- ファイルパス
- URL
- コード識別子
- 日本語でなければ意味が変わる仕様文言

ロード後の回答言語は保存言語では決めない。新しいAIは、ロード直前または現在のユーザーメッセージの言語に合わせて回答する。

## 8. `resume_prompt` 仕様

`save_context` 成功時は、レスポンスに `resume_context_call` と `resume_prompt` を含める。AIエージェントは保存完了後、この `resume_prompt` を現在の会話へ表示する。

### 8.1 必須要素

`resume_prompt` には次を含める。

- A2CR service URL
- A2CR MCP toolを使う指示
- HTTP APIを直接推測して呼ばない指示
- 最初に実行すべき `resume_context(slot_name="...")`
- slot番号対応済みなら `resume_context(slot_number=N)` の補助導線
- 読み込み後は必要なプロジェクトファイルを参照してよいこと
- 回答言語は現在のユーザーメッセージに合わせること

### 8.2 含めてはいけないもの

- 保存本文
- API key
- Authorization header
- private DB URL
- 内部管理URL
- secret
- 長い説明
- 「ローカルファイルを読むな」という制限

新しいAIは、保存本文を読んだ後に必要なプロジェクトファイルを通常通り参照できる必要がある。

### 8.3 日本語例

```text
A2CR service: https://a2cr.app/mcp
A2CR MCPツールを使ってください。HTTP APIを直接推測して呼び出さないでください。
まず resume_context(slot_name="web-saas-next-steps") を実行して、A2CRから引き継ぎ文脈を読み込んでください。
Slot番号対応済みなら resume_context(slot_number=1) でも読み込めます。
読み込み後は、作業に必要なプロジェクトファイルを通常通り参照して構いません。
回答はこのメッセージの言語に合わせてください。
```

### 8.4 英語例

```text
A2CR service: https://a2cr.app/mcp
Use the A2CR MCP tool. Do not guess or call direct HTTP API endpoints.
First run resume_context(slot_name="web-saas-next-steps") to load the handoff context from A2CR.
If your client supports Slot numbers, resume_context(slot_number=1) can also be used.
After loading, you may inspect the project files normally as needed.
Respond in the language of this message.
```

### 8.5 AIクライアント誘導アーティファクト

A2CRはMCP-firstで設計する。AIエージェントへの誘導は、特定クライアントだけに依存させず、次の複数面に分ける。

| アーティファクト | 位置づけ | 必須度 |
|---|---|---|
| MCP tool descriptions / schema | `save_context`、`resume_context`、`load_context`などの使い方、必須項目、禁止事項をAIへ伝える主導線 | 必須 |
| MCP tool response | `resume_context_call`、`resume_prompt`、validation error、rate limitなどの実行時結果を伝える | 必須 |
| `resume_prompt` | 新しいAI窓に貼るslot固有の再開指示 | 必須 |
| MCP prompts/resources | MCPクライアントが対応している場合の補助説明 | 任意 |
| `SKILL.md` template | CodexなどSkill対応クライアント向けのプロジェクト/ユーザー導入ガイド | 任意 |
| MCP設定ファイル | server URLと認証設定を置く場所。プロンプト注入の主導線にはしない | 設定上必要 |

MCP tool descriptions / schemaには少なくとも次を入れる。

- `save_context` は `goal`、`current_state`、`next_action` を必須にする。
- Freeではcompact、Pro detailedでは判断根拠・失敗履歴・検証結果を追加できることを示す。
- secret、API key、Authorization header、private DB URL、長大ログ、会話全文を保存してはいけないことを明記する。
- `resume_context` は新窓の最初に呼ぶtoolであり、HTTP APIを直接推測しないことを明記する。
- ロード後は、保存本文だけでなく必要なプロジェクトファイルを参照してよいことを明記する。
- 回答言語は保存本文ではなく、現在のユーザーメッセージに合わせることを明記する。

`SKILL.md` は有効だが、A2CRの成立条件にはしない。理由は、すべてのAIクライアントがSkillを読むわけではなく、MCP tool call前にプロジェクトファイルを読まないクライアントもあるためである。公開テンプレートは `docs/templates/skills/a2cr-agent/SKILL.md` に置き、Codexなどの利用者が自分の環境へコピーして使える補助資料とする。

MCP設定ファイルに長いプロンプトを埋め込む設計は避ける。設定ファイルはsecret管理や接続先管理の責務が強く、クライアントごとの差も大きい。入れてよいのはserver URL、認証設定、短い表示名程度とし、A2CR固有の行動規則はMCP tool descriptions / schema、`resume_prompt`、任意の `SKILL.md` に分離する。

## 9. ロード仕様

### 9.1 `resume_context`

`resume_context` は新しいAI窓の入口である。

| 入力 | 挙動 |
|---|---|
| `slot_name` 指定 | そのslotを直接ロードする |
| `slot_number` 指定 | その固定Slotを直接ロードする |
| `project` 指定、候補1件 | そのslotをロードする |
| `project` 指定、候補複数 | `prefer_latest=true` でない限り候補metadataだけ返す |
| 入力なし、候補複数 | 候補metadataだけ返す |
| 見つからない/期限切れ | `not_found` を返し、本文を推測しない |

候補metadataだけ返す場合は、本文ロードとして扱わない。`load_count` とload rate limitは、本文を返す時だけ加算する。

### 9.2 `load_context`

`load_context` は、slot名またはslot番号が既に分かっている場合の直接ロードである。本文を返すため、成功時はload count、access log、rate limitの対象にする。

### 9.3 ロード後のAIの振る舞い

ロード後のAIは次を行う。

1. 保存文脈を読んだことを短く認識する。
2. `goal`、`current_state`、`next_action` を内部的に確認する。
3. 必要なら保存文脈に書かれたファイルや仕様書を読む。
4. コーディング作業なら `git status` などで現在の作業ツリーを確認する。
5. 保存文脈と現在のファイル状態が食い違う場合は、現在のファイル状態を優先し、差分を説明する。
6. ユーザーに再説明を求める前に、保存文脈とリポジトリから分かる範囲を使って作業を再開する。
7. 回答は現在のユーザーメッセージの言語に合わせる。

ロード後のAIがしてはいけないこと:

- 保存文脈にない事実を作る。
- 候補が複数あるのに勝手に無関係なslotを読む。
- 期限切れやnot_foundを無視して作業を続ける。
- 保存本文に含まれるsecretらしき情報を表示する。
- 保存文脈だけを信じ、現在のファイル状態を確認せず大きな変更をする。

## 10. 保存レスポンス仕様

`save_context` 成功時のレスポンスは次を含める。

| フィールド | 内容 |
|---|---|
| `slot_name` | 保存先slot名 |
| `slot_number` | 固定Slot番号。対応していない場合はnull可 |
| `expires_at` | 有効期限 |
| `compressed_tokens` | 保存後の概算token数 |
| `saved_tokens` | 推定節約token数。計算不能ならnull |
| `resume_context_call` | 新窓で実行する最小tool call |
| `resume_prompt` | 新窓に貼る再開指示文 |

保存失敗、validation error、rate limit、slot limit超過、認証失敗の場合は `resume_prompt` を返さない。

## 11. セキュリティとプライバシー

- 保存本文は人間向けdashboardに表示しない。
- サービス管理者向けの通常管理画面、サポート画面、監査ログにも本文を表示しない。
- 保存本文はアプリ層暗号化する。
- A2CRサーバーはMCP/APIレスポンス生成時に本文を復号するため、ゼロ知識暗号化とは呼ばない。
- `resume_prompt` には本文、API key、secret、private URLを含めない。
- `slot_name` は表示されるmetadataなので、ユーザーにsecretを含めないよう案内する。

## 12. 検証項目

### 12.1 自動テスト

- `save_context` は必須フィールドなしを拒否する。
- `save_context` 成功時に `resume_context_call` と `resume_prompt` を返す。
- `resume_prompt` はservice URL、MCP tool指示、slot名、必要ならslot番号を含む。
- `resume_prompt` はAPI key、Authorization header、保存本文を含まない。
- Freeは `detailed` を設定できない。
- Proは `compact` / `detailed` を選択できる。
- `resume_context` の候補metadata返却はload countを増やさない。
- 本文ロード成功時だけload countを増やす。

### 12.2 手動品質テスト

新しいAI窓に `resume_prompt` を貼り、次を確認する。

- AIが最初に `resume_context` を呼ぶ。
- AIが直接HTTP APIを推測して呼ばない。
- AIがgoal/current_state/next_actionを把握している。
- AIが必要なプロジェクトファイルを読みに行ける。
- AIがユーザーの現在メッセージの言語で回答する。
- Free保存では簡潔に再開できる。
- Pro detailed保存では判断理由、失敗履歴、検証結果まで再開できる。

## 13. 現行実装との差分

ローカルMVPはFree compact相当として扱う。現行実装は次を満たしている。

- `goal` / `current_state` / `next_action` 必須
- slot 1〜3
- `save_context` / `load_context` / `resume_context`
- `resume_prompt` 生成
- Fernetによる本文暗号化
- load count

Web SaaS実装は次を満たしている。

- Supabase Auth/JWTとA2CR API key認証
- Postgres RLS/access log連携
- Free/Pro planによるretention/body size/detail level制限
- Dashboard APIからの保存粒度、retention、locale/language/timezone設定
- HTTP MCP `/mcp` の `save_context` / `resume_context` / `load_context` / `list_contexts` / `get_account_limits`
- `slot_name` と `slot_number` のload/resume

未実装または今後のUI/運用で対応するもの:

- React dashboard UI
- 本番公開URLでの外部AIクライアント接続検証
