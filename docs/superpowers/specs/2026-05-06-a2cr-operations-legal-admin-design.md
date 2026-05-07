# A2CR 運営・法的表示・管理者機能・Pro権限設計書

Updated: 2026-05-06

この文書は、A2CRを個人開発のWeb SaaSとして運営するための設計方針をまとめる。
対象は、問い合わせメール、公開ページ、プライバシーポリシー、利用規約、特定商取引法に基づく表記、管理者専用画面、1か月無料体験、管理者によるPro権限付与である。

この文書はプロダクト/技術設計であり、法的助言ではない。有料プラン開始前には、最新の公的情報と必要に応じて専門家確認を行う。

## 1. 前提

- A2CRは法人ではなく、個人開発プロダクトとして開始する。
- 公開ドメインは `https://a2cr.app`。
- TOPページ、料金表、問い合わせ、法的ページはGoogleログインなしで閲覧できる。
- Dashboard、Settings、AdminはGoogleログイン必須。
- A2CRはGoogleログイン情報、APIキー、アクセスログ、WorkBaton/WorkThreadsの暗号化本文を扱う。
- 保存本文はアプリ層で暗号化する。
- 通常のDashboard/Admin画面では保存本文を表示しない。
- A2CRサーバーは認証済みAPI/MCP応答時に本文をメモリ上で復号するため、ゼロ知識とは表現しない。
- Stripe課金はまだ本番稼働していないが、将来のStripe Pro、1か月無料体験、管理者付与Proが併存できるように設計する。

## 2. 問い合わせメール設計

公開ページには個人Gmailを出さず、独自ドメインの問い合わせ先を表示する。

推奨:

```text
support@a2cr.app
```

初期運用:

```text
support@a2cr.app -> 個人Gmailへ転送
```

Cloudflare Email Routingは受信メール転送に使える。ただし送信用SMTPは提供しないため、`support@a2cr.app` から返信したい場合は、別途以下のいずれかを使う。

- Gmailの送信エイリアスとSMTP設定
- Google Workspace
- Resend、Postmarkなどのメール送信サービス

公開ページ上の運営者表記は当面以下とする。

```text
A2CR 運営
```

有料プラン開始前に、特定商取引法に基づく表記で必要になる氏名、住所、電話番号の扱いを決める。

## 3. 公開ページ構成

以下のページをログインなしで閲覧可能にする。

```text
/contact
/privacy
/terms
/legal
```

意味:

- `/contact`: 問い合わせ先、問い合わせ対象、返信目安。
- `/privacy`: プライバシーポリシー。
- `/terms`: 利用規約。
- `/legal`: 特定商取引法に基づく表記。

TOPページ、料金表、ログインページ、フッターから到達できるようにする。

## 4. プライバシーポリシー設計

A2CRはGoogleログイン、APIキー、作業文脈、アクセスログを扱うため、Privacy Policyは早めに用意する。

最低限記載するデータ種別:

- アカウント情報: Supabase user id、メールアドレス、Google OAuthで必要なメタデータ。
- APIキー情報: key hash、key prefix、作成日時、最終利用日時、失効日時。
- WorkBaton情報: 暗号化された保存本文、slot名、slot番号、有効期限、サイズ、推定トークン、load count。
- WorkThreads情報: 有効化時の暗号化message本文、thread/task/run metadata。
- アクセスログ: action、result、client type、request id、概算サイズ、hash化IP、hash化user agent、日時。
- 課金情報: Stripe customer/subscription id。カード番号はStripe側で扱い、A2CRでは保持しない。
- 管理者監査ログ: admin操作、対象user、理由、before/after metadata。

記載する利用目的:

- ログインと本人認証。
- WorkBaton/WorkThreadsの提供。
- API/MCPの認証。
- 不正利用防止、rate limit、セキュリティ監査。
- 問い合わせ対応。
- 課金管理。

セキュリティ表現:

- 「保存本文はアプリ層で暗号化されます」は可。
- 「通常のDashboard/Admin画面では保存本文を表示しません」は可。
- 「管理者が通常閲覧できない設計」は可。
- 「ゼロ知識」「完全なE2E暗号化」「管理者が絶対にアクセスできない」は不可。

## 5. 利用規約設計

MVPでは短く、行動規範と禁止事項を明確にする。

最低限記載する内容:

- A2CRはAI作業文脈の保存、読込、再開、共有補助を行うサービスである。
- A2CR自身はMVP段階ではLLM推論を行わない。
- ユーザーは保存する内容に責任を持つ。
- 以下を保存しない:
  - secret
  - APIキー
  - Authorization header
  - private database URL
  - 不要な個人情報
  - full transcript
  - 長大なlog
  - 生成cache
  - repositoryから読める大きなコード本文
- 不正利用、過負荷、規約違反に対してrate limit、停止、APIキー失効を行える。
- Free/Proの上限はMVP中に変更される可能性がある。
- 有料課金はStripe導入後に別途表示する条件に従う。
- 問い合わせ先は `support@a2cr.app`。

## 6. 特定商取引法に基づく表記の設計

有料Proを販売する段階では、通信販売として特定商取引法の表示事項が問題になる。

課金前の暫定方針:

- `/legal` を先に作る。
- 運営者は `A2CR 運営` と表示する。
- 問い合わせ先は `support@a2cr.app`。
- 有料プラン販売がまだ開始していない場合は、その旨を明記する。

課金開始前に決めること:

- 法的な販売者名の表示。
- 住所の扱い。
- 電話番号の扱い。
- バーチャルオフィスや事業用電話の利用有無。
- 請求があった場合に住所/電話番号等を遅滞なく提供する表示にできるか。
- Proの価格、支払時期、支払方法、提供時期、キャンセル、返金条件。

公開上の注意:

- 自宅住所や個人電話をTOPページに直接出す必要はない。
- ただし有料販売開始後に必要表示を曖昧にしない。
- 「会社情報」ではなく「運営者情報」または「特定商取引法に基づく表記」とする。

## 7. 管理者画面の設計

管理者画面は必要だが、初期版では「読める情報」と「できる操作」を絞る。

管理者画面:

```text
/admin
```

管理者判定は必ずサーバー側で行う。メールアドレスやフロントエンドだけで判定しない。

推奨設定:

```text
A2CR_ADMIN_USER_IDS=<comma-separated Supabase user ids>
```

全 `/api/admin/*` は以下を満たす。

- Supabase JWT必須。
- JWTからuser_idを解決。
- user_idが `A2CR_ADMIN_USER_IDS` に含まれるかサーバー側で確認。
- 非adminは403。
- 重要な読み取り/変更はadmin audit logに残す。

初期Adminで見せる情報:

- ユーザー一覧。
- ユーザー詳細。
- effective plan。
- plan source。
- 作成日時、更新日時、最終利用日時。
- active slot数。
- API key prefix、作成日時、最終利用日時、失効日時。
- access log metadata。
- entitlement履歴。

初期Adminで見せない情報:

- 保存本文。
- WorkThreads message本文。
- APIキー全文。
- Authorization header。
- raw IP。
- raw user agent。
- Supabase service role key。

初期Adminで許可する操作:

- APIキー失効。
- Pro付与。
- 期限付きPro付与。
- admin grant失効。

全ての変更操作にはreason入力を必須にする。

## 8. Pro権限の設計

ユーザー向け表示は単純に `Free` / `Pro` とする。一方、内部ではProになっている理由を分けて持つ。

Proの発生源:

- Stripe subscription
- 1か月無料体験
- 管理者によるPro付与

概念モデル:

```text
user_entitlements
- id
- user_id
- kind: trial | admin_grant | stripe_subscription
- plan: pro
- starts_at
- ends_at
- status: active | expired | revoked
- granted_by
- reason
- external_ref
- created_at
- updated_at
- revoked_at
```

effective plan判定:

```text
activeなstripe_subscription proがある -> Pro
activeなadmin_grant proがある -> Pro
activeなtrial proがある -> Pro
それ以外 -> Free
```

Dashboardではシンプルに表示する。

```text
Plan: Pro
```

Adminでは理由も表示する。

```text
Plan: Pro
Source: admin grant
Ends: no expiry
```

## 9. 1か月無料体験

無料体験は `trial` entitlementとして扱う。

条件:

- 1ユーザー1回。
- Supabase user_id単位で判定。
- MVPではカード登録なしで開始する方がシンプル。
- 将来Stripe trialへ移行する余地を残す。

作成内容:

```text
kind = trial
plan = pro
starts_at = now()
ends_at = now() + 30 days
status = active
```

未決定:

- 将来、同一メールhash、Google provider id、Stripe customer idでの再試行防止を追加するか。
- Trial終了前に通知メールを送るか。

## 10. 管理者によるPro付与

用途:

- beta tester
- 協力者
- support対応
- 返金/障害補填
- デモ用account

付与方法:

- 無期限: `ends_at = null`
- 期限付き: `ends_at = 指定日時`

必須入力:

- target user
- grant type
- end dateまたは無期限
- reason

失効:

- `status = revoked`
- `revoked_at = now()`
- admin audit logにreason付きで記録

## 11. 管理者監査ログ

Admin操作はuser-facing access logsとは別に保存する。

概念モデル:

```text
admin_audit_logs
- id
- admin_user_id
- target_user_id
- action
- before_json
- after_json
- reason
- request_id
- ip_hash
- user_agent_hash
- created_at
```

保存しないもの:

- APIキー全文
- Authorization header
- raw IP
- raw user agent
- 保存本文
- Supabase service role key

## 12. Adminセキュリティ基準

必須:

- server-side admin allowlist。
- service role keyをブラウザに出さない。
- admin APIはsame-origin前提。
- 全mutationにreason必須。
- 全list APIにpagination必須。
- admin操作はaudit log必須。
- 保存本文やfull keyを返さないテスト。
- 非admin拒否テスト。
- rate limit。

後で検討:

- admin操作時の再認証。
- MFA必須。
- IP allowlist。
- admin grant/revoke時の通知メール。
- break-glass admin account。

## 13. 実装順序

1. `support@a2cr.app` の転送設定。
2. `/contact`, `/privacy`, `/terms`, `/legal` の追加。
3. footer linksの追加。
4. `A2CR_ADMIN_USER_IDS` とadmin auth dependency。
5. read-only admin API。
6. read-only `/admin` UI。
7. `admin_audit_logs`。
8. adminによるAPI key revoke。
9. `user_entitlements` とeffective plan resolver。
10. 1か月無料体験。
11. admin Pro grant/revoke。
12. Stripe subscription source。

## 14. 参考

- Cloudflare Email Routing:
  https://developers.cloudflare.com/email-routing/get-started/
- Cloudflare Email Routing addresses:
  https://developers.cloudflare.com/email-routing/setup/email-routing-addresses/
- 消費者庁 特定商取引法ガイド 通信販売:
  https://www.no-trouble.caa.go.jp/what/mailorder/
- 消費者庁 通信販売広告について:
  https://www.no-trouble.caa.go.jp/what/mailorder/advertising.html
- 個人情報保護委員会 個人情報の保護に関する基本方針:
  https://www.ppc.go.jp/personalinfo/legal/fundamental_policy/
