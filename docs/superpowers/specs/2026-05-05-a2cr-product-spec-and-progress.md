# A2CR Product Specification And Progress

Updated: 2026-05-05

この文書はA2CRの基準仕様書と進捗表を兼ねる。詳細なWeb SaaS設計は
`2026-05-03-web-saas-design.md`、実装順序は
`2026-05-04-web-saas-implementation-plan.md` に分ける。

## 1. 確定した命名

| 種別 | 名称 |
|---|---|
| サービス名 | A2CR |
| 展開名 | Agent-to-Agent Context Relay |
| 無料機能 | WorkBaton |
| Pro機能 | WorkThreads |
| 技術名 | A2CR MCP / A2CR API |

当面は `A2CR Protocol` や `Context Relay Protocol` を前面に出さない。プロダクトが使われ、外部互換仕様として切り出す価値が明確になってから判断する。

## 2. プロダクト定義

A2CRは、AIエージェントが作業文脈を別の会話窓、別のAIクライアント、別の端末へ引き継げるようにするサービスである。

A2CR自身はMVP段階ではLLM推論を実行しない。Claude、Codex、Cursorなどの外部AIエージェントがA2CR MCP/APIを呼び出して、作業文脈や作業スレッドを保存・読込・更新する。

設計原則:

- A2CRはAIエージェントの代わりに考えない。保存、読込、共有、状態管理、監査に徹する。
- サーバー側LLMは原則使わない。モデル選択、レビュー生成、要約生成、相談仲裁をA2CRサーバーの責務にしない。
- ループ防止、rate limit、重複検知、未解決question制限は、LLM判定ではなく説明可能なルールで行う。
- 料金はトークン消費ではなく、保存容量、リクエスト数、保持期間、WorkThreadsのmessage/metadata処理に紐づける。
- 将来LLMを使う拡張を作る場合も、A2CR Core / WorkBaton / WorkThreads Pro本体とは分離し、別サービスまたは上位/従量課金として再設計する。

## 3. 機能レイヤー

| レイヤー | 目的 | プラン | 状態 |
|---|---|---|---|
| WorkBaton | 短命な作業文脈をslotへ保存し、新しいAI窓で再開する | Free中心 | ローカルMVP実装済み、Web SaaSは設計中 |
| WorkThreads | AIエージェント同士が同じ作業スレッドを見ながら継続作業する | Pro | 仕様策定中、未実装 |

WorkBatonは「引き継ぎ箱」、WorkThreadsは「AIエージェント用の作業掲示板 / 共有作業スレッド」として扱う。

## 4. WorkBaton仕様

### 4.1 目的

WorkBatonは、現在のAI作業状態を構造化JSONとして保存し、新しいAI窓で `resume_context` から再開できるようにする。

保存・ロード・新窓再開の品質仕様は `2026-05-05-workbaton-save-load-quality-spec.md` を基準にする。特に、Freeはcompactな取捨選択、Proはdetailedな判断根拠・失敗履歴・検証結果まで含める差分を明確に扱う。

### 4.2 基本操作

| 操作 | MCPツール | API |
|---|---|---|
| 保存 | `save_context` | `POST /v1/context/save` |
| 読込 | `load_context` | `GET /v1/context/{slot_name}` |
| 再開 | `resume_context` | MCP側でlist/loadを組み合わせる |
| 一覧 | `list_contexts` | `GET /v1/context/list` |
| 削除 | `delete_context` | `DELETE /v1/context/{slot_name}` |

### 4.3 保存内容

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

### 4.4 Free仕様

| 項目 | ローカルMVP | Web SaaS予定 |
|---|---:|---:|
| slot数 | 3 | 3 |
| 保存サイズ | 10KB | 32KB |
| 保持時間 | 30分 | 15分 / 30分 / 1時間 / 3時間 / 6時間 / 12時間 / 24時間 |
| APIキー | ローカル固定1件 | ユーザーごと1件 |
| 本文暗号化 | Fernet | アプリ層暗号化 |

ローカルMVPは検証用の参照実装であり、製品として提供する主対象はWeb SaaS版とする。

### 4.5 セキュリティ方針

- ダッシュボードは保存本文を表示しない。
- ダッシュボードが扱うのはslot名、slot番号、有効期限、サイズ、統計、アクセスログなどのメタデータのみ。
- 本文読込はAPIキー認証済みのA2CR API/MCP経路に限定する。
- APIキー、Authorizationヘッダー、生IP、本文、リクエスト全文はログに保存しない。

詳細なセキュリティ仕様は `8. セキュリティ仕様` にまとめる。

### 4.6 AIクライアント誘導

A2CRの標準誘導面はMCP tool descriptions / schema、MCP tool response、`resume_prompt` とする。ここに保存粒度、禁止情報、ロード後の振る舞い、回答言語、直接HTTP APIを推測しない方針を入れる。

`SKILL.md` はCodexなどSkill対応クライアント向けの任意テンプレートとして提供する。A2CR本体はSkillに依存しない。Skill非対応クライアントでも、MCP tool descriptions / schemaと `resume_prompt` だけで保存・ロード・再開品質を維持できることを必須条件にする。

公開テンプレート:

- `docs/templates/skills/a2cr-agent/SKILL.md`

## 5. WorkThreads仕様

### 5.1 目的

WorkThreadsは、AIエージェント同士が同じ作業スレッドを見ながら作業するためのPro機能である。人間向けチャットやAI同士の雑談ではなく、継続作業、レビュー、検証、失敗記録、担当宣言、最終成果物リンクを共有するための作業掲示板として設計する。

### 5.2 WorkBatonとの違い

| 項目 | WorkBaton | WorkThreads |
|---|---|---|
| 主目的 | 一回の引き継ぎ | 継続的な共同作業 |
| データ単位 | slot | thread |
| 更新方式 | 上書き保存 | append-only message中心 |
| AI間連携 | 新窓で読込 | 複数AIが同じthreadを確認 |
| 状態管理 | slot metadata | unread、version、task lease、run status |

### 5.3 重要な前提

WorkThreadsは、停止中または寝ているAIエージェントを勝手に起こす通知システムではない。作業中のAIエージェントがMCP/APIツールを呼んだタイミングで新着を確認する。

そのため、MVPではプラグインやOS通知は不要とする。プラグインや常駐クライアントが必要になるのは、AI窓がツール確認していない時でも人間向け通知を出したい場合、または停止中の作業窓を起こしたい場合である。

### 5.4 更新確認

作業中のAIエージェント同士が相手の書き込みに気づく方法は次の2つとする。

| 方式 | 使いどころ | 備考 |
|---|---|---|
| 通常ポーリング | 作業中に定期確認する | 60秒間隔などで `check_workthread_updates` を呼ぶ |
| long polling | 相手の返答待ち | `wait_workthread_updates(timeout_seconds=60)` が新着まで待つ |

推奨は、通常作業中は要所で確認し、相手待ちの時だけlong pollingを使う方式である。AIが長い処理中でツール呼び出しをしていない間は新着に気づけない。

### 5.5 MCP/APIツール案

| ツール | 目的 |
|---|---|
| `create_workthread` | 作業スレッドを作成する |
| `post_workthread_message` | スレッドに作業メモ、レビュー、結果を書き込む |
| `read_workthread` | 指定cursor以降のメッセージを読む |
| `check_workthread_updates` | 新着有無と未読数を短く確認する |
| `wait_workthread_updates` | 最大60秒程度、新着を待つ |
| `mark_workthread_seen` | 自分の既読位置を更新する |
| `claim_workthread_task` | 作業タスクをlease付きで確保する |
| `complete_workthread_task` | 確保したタスクを完了にする |
| `save_workthread_result` | 最終結果をWorkBaton slotへ保存する |

外部公開名、MCP tool名、API path、DB table名は `workthread` / `work_thread_*` 系に統一する。古いagent系表現は過去案として扱い、実装名には使わない。

### 5.6 データモデル案

| テーブル | 用途 |
|---|---|
| `work_threads` | thread本体、title、status、version、last_message_id |
| `work_thread_messages` | append-onlyの本文。contentは暗号化 |
| `work_thread_read_marks` | agentごとのlast_seen_message_id |
| `work_thread_tasks` | task、lease_owner、lease_until、status |
| `work_thread_runs` | claim、complete、timeout、failureなどの監査 |

ダッシュボードにはmessage本文を返さない。表示するのはtitle、status、件数、agent名、最終更新、成功/失敗、最終slotリンクなどのメタデータだけにする。

### 5.7 DB負荷とロック方針

- AI処理中にDB transactionを開いたままにしない。
- messageはappend-only INSERTにする。
- 既読管理は `thread_id + agent_id` の1行更新にする。
- 更新確認は `thread_id`、`last_message_id`、`version`、`updated_at` にindexを張る。
- long pollingはDB transactionを保持せず、短いSELECTを1〜2秒間隔で繰り返す。
- task claimは `FOR UPDATE SKIP LOCKED` とlease timeoutで競合を抑える。
- 将来、負荷が増えたらPostgres `LISTEN/NOTIFY`、Redis、別worker、別Railway serviceへ分離する。

### 5.8 相談とループ防止

WorkThreadsは、AIエージェント同士が作業について相談できる。ただし、自由な雑談や終わらない議論を目的にしない。相談は必ず作業成果へ収束させる。

message種別は次を基本にする。

| 種別 | 用途 |
|---|---|
| `note` | 作業メモ |
| `question` | 他Agentへの作業相談 |
| `answer` | 相談への回答 |
| `decision` | 決定事項 |
| `review` | レビュー結果 |
| `failure` | 失敗・原因 |
| `handoff` | 引き継ぎ |
| `result` | 最終結果 |
| `blocked` | 人間判断または外部条件待ち |

相談messageは `consultation_id` と `parent_message_id` で束ねる。`question` は目的、回答してほしい論点、任意の `target_agent_name`、返信期限を持つ。`answer` は推奨アクションまたは判断材料を含め、次のmessageは原則 `decision`、`handoff`、`result`、または1回だけの追加質問へ収束させる。

初期のループ防止ルール:

- 1つの `consultation_id` で最大6message、または質問/回答3往復まで。
- 未解決の `question` はthreadあたり最大3件まで。
- 同じAgentが同じ相談で連続して `question` を2回以上投げない。
- `content_hash` と `idempotency_key` で重複投稿を拒否する。
- `wait_workthread_updates` は最大60秒、同じ待機理由で最大3回まで。
- 上限に近い時は `loop_warning` を返す。
- 上限を超えた場合は、新しい `question` / `answer` を拒否し、`decision`、`handoff`、`blocked`、`result` のいずれかを要求する。

ループガードが発火しても、A2CRはAIを勝手に停止・起動しない。MCP/APIレスポンスで `loop_guard_triggered` を返し、AIクライアントに「結論へ畳む」「人間へ確認する」「WorkBatonへ最終状態を保存する」のいずれかを促す。

## 6. Web SaaS構成

| 領域 | 採用サービス | 用途 |
|---|---|---|
| Frontend + Backend + MCP | Railway | React/Vite SPA、FastAPI、`/mcp`を同一originで配信 |
| DB + Auth + RLS | Supabase | Google OAuth、Postgres、RLS、migration |
| Domain/DNS/CDN | Cloudflare | ドメイン、DNS、SSL/TLS、DNSSEC |
| Payment | Stripe | Pro課金。Core安定後に有効化 |
| Source/CI | GitHub | リポジトリ、PR、Actions |

MVPではA2CRサーバー側でOpenAI/Anthropic等のLLM APIを呼ばない。AI推論コストはユーザーが使うAIクライアント側に残す。

## 7. サービス・ツール契約状況

契約状況は、A2CRプロジェクト内で確認できる範囲を基準に記載する。実際の外部アカウントの契約状態はこのリポジトリからは確認できないため、未確認のものは `未確認` とする。

### 7.1 外部サービス

| サービス | 用途 | 採用判断 | 契約状況 | 次の確認/作業 |
|---|---|---|---|---|
| Cloudflare | ドメイン取得、DNS、SSL/TLS、DNSSEC、基本的なedge保護 | MVPで採用 | 未確認 | A2CR用ドメインを取得し、DNS管理先をCloudflareにする |
| Railway | FastAPI、React/Vite build、HTTP MCP `/mcp` の本番runtime | MVPで採用 | 未確認 | Railway Hobby以上でproject作成。本番originを1つに統一する |
| Supabase | Postgres、Supabase Auth、Google OAuth連携、RLS、migration | MVPで採用 | 未確認 | 開発はFreeで開始可。本番前にPro化するか判断する |
| Google Cloud OAuth | Googleログイン用OAuth client | MVPで採用 | 未確認 | Supabase Authに設定するOAuth Client ID/secretを作成する |
| GitHub | リポジトリ、issue、PR、CI/CD | MVPで採用 | 未確認 | remote repositoryとActions方針を確認する |
| Stripe | Pro課金、Checkout/Billing、webhookでplan更新 | Core安定後に採用 | 未確認 | 先にアカウント準備だけ行い、課金flowはMVP後に有効化する |

### 7.2 開発・実装ツール

| ツール | 用途 | 状態 | メモ |
|---|---|---|---|
| Python 3.13 | FastAPI backend、local MVP、tests | 使用中 | 現行ローカル実装で利用中 |
| FastAPI | API server、Web SaaS backend | 使用中 | ローカルMVPで稼働中。Web SaaSでも継続採用 |
| React / Vite | Web SaaS dashboard | 採用予定 | 未実装。Streamlit dashboardは参照用に留める |
| Supabase CLI | migration適用、ローカル/remote DB管理 | 採用予定 | 導入状況は未確認 |
| PostgreSQL / SQL | Web SaaS DB、RLS、least-privileged role | 採用予定 | `supabase/migrations/001_base_schema.sql` は作成済み |
| SQLite | ローカルMVP DB | 使用中 | 製品版の主DBではなく参照実装用 |
| FastMCP | MCP tool server wrapper | 使用中 | ローカルMCP wrapperとWeb SaaS HTTP MCP `/mcp` で利用中 |
| pytest | 自動テスト | 使用中 | 2026-05-05時点で `103 passed` |
| ripgrep (`rg`) | 高速検索 | 使用中 | `winget`で `ripgrep 15.1.0` を導入済み |
| winget | Windows package install | 使用中 | `rg`導入に使用済み |
| Docker | Railway build、将来の本番image | 採用予定 | 導入状況は未確認 |

### 7.3 現時点では採用しないサービス

| サービス/方式 | 判断 | 理由 |
|---|---|---|
| Vercel | MVPでは不採用 | React SPA、FastAPI、MCPを同一originのRailway 1サービスに寄せるため |
| Firebase / Firestore | 不採用 | Postgres RLS、SQL migration、`SET LOCAL app.user_id` 方針と合わないため |
| Render Free | 不採用 | 実験には可だが、選定済み構成はRailway |
| OpenAI/Anthropic APIのサーバー側契約 | MVPでは不要 | A2CRはLLM推論を実行せず、ユーザー側AIクライアントがMCP/APIを呼ぶため |
| Upstash Redis | 後回し | rate limitやWorkThreads fan-outがPostgresだけで不足した段階で追加 |
| Sentry | 後回し | public beta前に導入検討 |
| PostHog | 後回し | プロダクト分析が必要になった段階で導入 |
| Resend | 後回し | transactional emailを実装する段階で導入 |

### 7.4 契約優先順位

1. CloudflareでA2CR用ドメインを取得する。
2. GitHub repositoryを確定する。
3. Railway projectを作成し、public originを決める。
4. Supabase projectを作成し、Auth/Postgres/RLS migrationを適用する。
5. Google Cloud OAuth clientを作成し、Supabase Authに設定する。
6. Stripe accountを準備する。ただし課金flowの実装と有効化はCore MVP安定後に回す。
7. Sentry、Upstash、PostHog、Resendは必要性が出た段階で追加する。

## 8. セキュリティ仕様

### 8.1 基本方針

A2CRは、AI作業文脈という機密性の高い本文を扱う。MVPのセキュリティ方針は「本文を人間向けUIやログに出さない」「認証済みAI/MCP/API経路だけが本文を読める」「DBだけを見ても本文を読めないようアプリ層暗号化する」とする。

保存本文は、通常の管理画面、サポート用ツール、DB直接参照だけではサービス管理者でも見られない設計にする。サービス管理者が確認できるのは、原則としてslot名、thread title、時刻、サイズ、件数、status、agent名、監査ログなどのメタデータだけとする。

ただし、A2CRサーバーはAPI/MCPレスポンスを返すために処理中メモリ上で本文を復号する。したがって、初期版では完全なE2E暗号化またはゼロ知識暗号化とは呼ばない。

### 8.2 データ分類

| 分類 | 例 | 保存/表示方針 |
|---|---|---|
| Secret | APIキー、Fernet key、DB URL、Supabase secret、Stripe secret、Google OAuth secret | リポジトリ、ログ、ブラウザbundle、ダッシュボードに出さない |
| Sensitive content | WorkBaton本文、WorkThreads message本文、AIプロンプト、AI応答本文 | 暗号化保存。ダッシュボード表示禁止。MCP/API-key経路のみ復号して返す |
| Sensitive metadata | slot名、thread title、agent名、status、件数、timestamp、size、token概算 | ダッシュボード表示可。ただしユーザー分離とログ方針を守る |
| Audit metadata | action、result、error_code、request_id、IP hash、UA hash | 本文とsecretを含めず保存。保持期間をplan別に制限する |
| Public data | README、公開仕様、料金表示、公開ロードマップ | GitHubやWebサイトで公開可 |

### 8.3 認証と認可

| 経路 | 認証方式 | 認可方針 |
|---|---|---|
| Local MVP API | `X-API-Key` | シングルユーザー前提。固定APIキー一致のみ |
| Web SaaS dashboard | Supabase AuthのJWT | JWT検証後、`user_id` で全データを分離する |
| Web SaaS API/MCP | A2CR API key | API key hashから `user_id` を解決し、RLS user contextを設定する |
| Admin/maintenance | 専用の管理環境 | 通常runtimeと分離し、必要最小限の時間だけsecretを使う |

Web SaaSでは、ブラウザから `contexts`、`api_keys`、`access_logs`、WorkThreads本文tableへ直接アクセスしない。すべてFastAPI経由で扱う。

### 8.4 APIキー管理

- 平文APIキーは発行時に一度だけ表示する。
- DBには平文APIキーを保存しない。
- Web SaaSでは `API_KEY_HASH_SECRET` を使ったHMAC-SHA256 hashだけを保存する。
- APIキーの照合はタイミング攻撃に配慮した比較を使う。
- APIキーのprefix、作成日時、最終利用日時は表示可とする。
- APIキー再発行時は旧キーを即時失効する。
- ログ、例外、テスト出力、GitHub公開物に `sk-` 形式の実キーを残さない。

### 8.5 暗号化と鍵管理

- WorkBaton本文はアプリ層で暗号化して保存する。
- WorkThreads message本文も同じ方針で暗号化して保存する。
- ローカルMVPではFernet keyをローカル `.env` に保存する。
- Web SaaSではFernet keyまたは後継の暗号鍵をRailway runtime secretとして管理する。
- `encryption_key_version` を保存し、将来の鍵ローテーションに備える。
- 暗号鍵を失うと本文は復号できないため、鍵のバックアップとローテーション手順を本番前に決める。
- 初期版では運営者がruntime secretへアクセスできる前提のため、ゼロ知識とは表現しない。

### 8.6 ダッシュボード本文非表示

ダッシュボードは人間が運用状況を確認するための画面であり、本文閲覧画面ではない。

ダッシュボードに表示してよいもの:

- slot名、slot番号、有効期限、作成日時、更新日時
- 保存サイズ、token概算、load count
- thread title、status、message count、task count、agent名、last activity
- access logのaction、result、時刻、client_type

ダッシュボードに表示してはいけないもの:

- WorkBaton本文
- WorkThreads message本文
- AIプロンプト本文
- AI応答本文
- APIキー全文
- Authorization header
- 復号済み本文を含むエラー詳細

この制限は一般ユーザー向けdashboardだけでなく、サービス管理者向けの通常管理画面、サポート画面、監査ログにも適用する。

### 8.7 ログと監査

- access logには本文、APIキー、Authorization header、request body全文、生IP、full User-Agentを保存しない。
- IPとUser-Agentは必要な場合のみHMAC hashまたは粗い分類として保存する。
- 失敗ログもsecret-safeにする。
- 自動期限切れ削除は `context.expire`、明示削除は `context.delete` として区別する。
- WorkThreadsでは `workthread.create`、`workthread.message.post`、`workthread.read`、`workthread.update.check`、`workthread.task.claim`、`workthread.task.complete`、`workthread.task.timeout` を監査対象にする。

### 8.8 RLSとDB接続

Web SaaSではSupabase PostgresのRLSを必須とする。

- 通常runtimeは `a2cr_app` のような最小権限DB roleで接続する。
- `SUPABASE_SERVICE_ROLE_KEY` を通常Railway runtimeに置かない。
- 認証済みrequestごとにtransaction内で `SET LOCAL app.user_id = '<uuid>'` を設定する。
- RLS policyは `app.current_user_id()` を参照する。
- cross-user select/update/deleteが失敗することを自動テストで確認する。
- service role keyが必要なmigrationや緊急作業は、通常runtimeとは分けて短時間だけ実行する。

### 8.9 入力制限と悪用対策

- request body sizeをplan別に制限する。
- slot数、retention、save回数、load回数、APIキー数をplan別に制限する。
- MCP batch requestを許可する場合は最大件数を制限する。
- 一覧系APIは `limit` 上限を固定し、必要ならcursor paginationにする。
- WorkThreads message取得はcursor paginationを必須にする。
- 429では `retry_after` を返し、AIクライアントが無駄に再試行し続けないようにする。

### 8.10 WorkThreads固有の安全策

- message本文はappend-onlyにする。
- AI処理中にDB transactionを開いたままにしない。
- long pollingはDB transactionを保持せず、短いSELECTを繰り返す。
- 既読管理はagentごとのcursor更新に限定する。
- task claimはlease付きにし、`FOR UPDATE SKIP LOCKED` を使う。
- ダッシュボードはWorkThreads本文を返さない。
- thread metadataだけでも機密になり得るため、user_id分離とログ方針をWorkBatonと同じ強さで扱う。

### 8.11 Web公開とGitHub公開の注意

- `.env`、DBファイル、log、`.claude/mcp.json`、`__pycache__`、`.pytest_cache` を公開しない。
- `.env.example` にはplaceholderだけを置く。
- GitHub公開前に古い `AIClipboard` 名やローカルAPIキーが残っていないか確認する。
- licenseを決めるまでpublic repositoryにしない。
- `SECURITY.md` を追加し、脆弱性報告先を明記する。

### 8.12 公開前セキュリティゲート

| Gate | 内容 | 状態 |
|---|---|---|
| Secret scan | GitHub公開前にsecret、API key、DB URL、OAuth secretがないことを確認 | 未実施 |
| Runtime secret separation | 通常Railway runtimeにservice role keyを置かない | 設計済み、未実装 |
| RLS isolation | user Aがuser Bのdataを読めないことをテスト | 静的テスト + ローカルPostgres実DB検証済み。API key routeとDashboard JWT routeのDB smoke test済み。MCP統合は未実装 |
| Dashboard blindness | dashboard API/React payloadに本文が含まれないことをテスト | Dashboard APIは実装/テスト済み。React payload検証は未実装 |
| Safe logging | logに本文、secret、Authorization、生IPが含まれないことをテスト | helperとContext API success logは実装済み。app log全体の検証は未実施 |
| Rate limit | Free/Pro制限と429が効くことをテスト | plan limit unit testあり。実DBでの超過ケース検証は未実施 |
| MCP auth | API keyなし/不正keyでslot存在有無を漏らさないことをテスト | 一部ローカル実装済み |
| Dependency check | FastAPI、MCP、暗号、Supabase関連依存の脆弱性確認 | 未実施 |
| Key backup/rotation | 暗号鍵のバックアップとローテーション手順を作る | 未実施 |

## 9. 非対象

- MVPでのAI自動起動、AIホスティング、LLM推論実行
- サーバー側LLMによる要約、レビュー、相談仲裁、ループ判定
- 停止中のAI窓を起こす通知機能
- WorkThreads本文の人間向けダッシュボード表示
- チーム、組織、複数APIキー
- Stripe課金の初期実装
- ローカル版の製品提供

## 10. 進捗サマリー

| 領域 | 状態 | メモ |
|---|---|---|
| サービス名変更 | 完了 | A2CR / WorkBaton / WorkThreadsへ設計・ローカル表示を更新済み |
| ローカルWorkBaton API | 完了 | save/load/list/delete、slot番号、TTL、Fernet暗号化 |
| ローカルMCP wrapper | 完了 | `save_context`、`resume_context`、`load_context`、`list_contexts`等 |
| ローカルStreamlit dashboard | 完了 | A2CR名へ更新済み。ただし製品主対象ではない |
| Supabase schema/RLS案 | 一部完了 | migration、静的テスト、ローカルPostgres実DB検証済み。remote Supabase projectへの適用は未実施 |
| Web SaaS詳細設計 | 一部完了 | Railway + Supabase + Cloudflare + Stripe構成で確定寄り |
| Web SaaS実装 | 一部着手 | FastAPI security foundation、WorkBaton Web Context API、Dashboard API、HTTP MCP `/mcp` を追加済み。React dashboardは未実装 |
| HTTP MCP `/mcp` | 完了 | FastMCP Streamable HTTPで実装。`save_context`、`resume_context`、`load_context`、`list_contexts`、`get_account_limits` をTask 3のWeb Context serviceへ接続済み |
| AIクライアント誘導 | 一部完了 | MCP tool descriptions / schemaを必須誘導面にし、任意の `SKILL.md` templateを追加 |
| WorkThreads仕様 | 一部完了 | 目的、更新確認、負荷方針、相談ループ防止方針を本書に確定仕様として追加 |
| WorkThreads実装 | 未着手 | DB、API、MCP tools、long polling、load testが未実装 |
| Stripe課金 | 未着手 | Core安定後に着手 |
| 本番デプロイ | 未着手 | Railway/Supabase/Cloudflare接続が未完了 |
| サービス契約管理 | 一部完了 | 採用サービスと契約状況欄を本書に追加。実契約状態は要確認 |
| セキュリティ仕様 | 一部完了 | データ分類、認証、暗号化、ログ、RLS、公開前ゲートを本書に追加 |

## 11. 次に固める項目

1. WorkThreads MVPにtask/leaseまで含めるか、まずはmessage + unread + long pollingだけで始めるか。
2. 次の実装単位としてReact/Vite dashboardを作る。Dashboard APIは本文非表示のまま、slot metadata、stats、access logs、API key管理を表示する。
3. ダッシュボード上でWorkThreadsをどこまで見せるか。本文非表示は確定、metadataの粒度を決める。

現時点の推奨は、WorkThreads MVPを `message + unread + check_updates + wait_updates` までに絞り、task/leaseは第2段階に回すこと。これなら「作業中のAI同士が気づく」価値を最小実装で検証できる。
