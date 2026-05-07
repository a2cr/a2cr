# A2CR 運営・法的表示・管理者機能・Pro権限仕様書

Updated: 2026-05-06

この文書は `2026-05-06-a2cr-operations-legal-admin-design.md` を実装可能な仕様に落としたものである。

## 1. Scope

対象:

- 問い合わせメール方針。
- 公開法的ページ。
- footer navigation。
- admin認可モデル。
- admin API/UI。
- 1か月無料体験。
- 管理者によるPro付与。
- entitlement/effective plan resolver。
- セキュリティ要件とテスト要件。

対象外:

- Stripe本実装。
- support@a2cr.appからの送信設定。
- 法的文言の専門家レビュー。
- admin MFA/IP allowlistの本実装。

## 2. Success Criteria

- `/`, `/pricing`, `/contact`, `/privacy`, `/terms`, `/legal` はログインなしで閲覧できる。
- `/dashboard`, `/settings`, `/admin` はログイン必須。
- 非adminは `/admin` と `/api/admin/*` にアクセスできない。
- admin判定はサーバー側のSupabase user id allowlistで行う。
- admin UI/APIは保存本文とAPIキー全文を返さない。
- admin mutationはaudit logに記録される。
- effective planはFree、trial、admin grant、Stripe subscriptionから一貫して解決できる。
- 1か月無料体験と管理者付与Proを、ユーザー向けplan表示を複雑にせず表現できる。

## 3. Environment Variables

追加:

```text
A2CR_SUPPORT_EMAIL=support@a2cr.app
A2CR_ADMIN_USER_IDS=<comma-separated Supabase user ids>
```

将来検討:

```text
A2CR_ADMIN_REQUIRE_REASON=1
A2CR_ADMIN_IP_ALLOWLIST=
```

注意:

- `A2CR_ADMIN_USER_IDS` はemailではなくSupabase Auth user idを入れる。
- emailは変更される可能性があるため、admin権限の根拠にしない。
- service role keyをブラウザbundleに含めない。

## 4. Public Routes

追加route:

```text
/contact
/privacy
/terms
/legal
```

全てpublic routeであり、Googleログインなしで表示できる。

footer link:

```text
Contact
Privacy
Terms
Legal
Pricing
Dashboard
```

`Dashboard` は `/dashboard` に遷移し、未ログインなら既存のProtectedRouteで `/login` へ流す。

## 5. Contact Page

Route:

```text
/contact
```

表示項目:

- title: `Contact` / `お問い合わせ`
- email: `A2CR_SUPPORT_EMAIL`。未設定時は `support@a2cr.app`
- 対象:
  - product support
  - account request
  - privacy request
  - legal display request
- 個人Gmailは表示しない。

## 6. Privacy Page

Route:

```text
/privacy
```

必須セクション:

- 取得する情報。
- 利用目的。
- 保存期間。
- 第三者サービス。
- セキュリティ。
- 問い合わせ。

取得する情報:

- Account data。
- API key metadata。
- WorkBaton metadata and encrypted body。
- WorkThreads metadata and encrypted body。
- Access logs。
- Billing metadata。
- Admin audit logs。

セキュリティ表現の要件:

- 「保存本文はアプリ層で暗号化」。
- 「通常のDashboard/Admin画面では保存本文を表示しない」。
- 「ゼロ知識ではない」。

禁止表現:

- `zero-knowledge`
- `end-to-end encrypted`
- 管理者がいかなる状況でも絶対にアクセスできないという表現。

## 7. Terms Page

Route:

```text
/terms
```

必須セクション:

- サービス概要。
- アカウント。
- 利用者責任。
- 保存禁止内容。
- API/MCP利用。
- rate limit/suspension。
- Free/Pro limits。
- 免責。
- 問い合わせ。

保存禁止内容:

- secret
- API key
- Authorization header
- private database URL
- 不要な個人情報
- full transcript
- 長大なlog
- generated cache
- repositoryから読める大きなコード本文

## 8. Legal Page

Route:

```text
/legal
```

課金前の最低表示:

- title: `特定商取引法に基づく表記`
- operator: `A2CR 運営`
- contact: `support@a2cr.app`
- paid plan sales status: 未開始ならその旨

課金開始前に追加/確定する項目:

- 販売者名。
- 住所。
- 電話番号。
- 販売価格。
- 支払方法。
- 支払時期。
- サービス提供時期。
- キャンセル/返金。
- 請求時開示を使う場合の請求方法と遅滞なく提供する旨。

## 9. Database: user_entitlements

新規table:

```sql
CREATE TABLE public.user_entitlements (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  kind text NOT NULL CHECK (kind IN ('trial', 'admin_grant', 'stripe_subscription')),
  plan text NOT NULL CHECK (plan IN ('pro')),
  starts_at timestamptz NOT NULL DEFAULT now(),
  ends_at timestamptz NULL,
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'expired', 'revoked')),
  granted_by uuid NULL REFERENCES auth.users(id),
  reason text NULL,
  external_ref text NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  revoked_at timestamptz NULL
);
```

index:

```sql
CREATE INDEX ix_user_entitlements_user_status
  ON public.user_entitlements (user_id, status);

CREATE INDEX ix_user_entitlements_active_window
  ON public.user_entitlements (user_id, kind, starts_at, ends_at)
  WHERE status = 'active';

CREATE UNIQUE INDEX ux_user_entitlements_one_trial
  ON public.user_entitlements (user_id)
  WHERE kind = 'trial';
```

RLS方針:

- 通常ユーザーはwrite不可。
- 通常ユーザーは必要に応じて自分のeffective plan summaryだけ読める。
- admin mutationはserver-side API経由。

## 10. Database: admin_audit_logs

新規table:

```sql
CREATE TABLE public.admin_audit_logs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  admin_user_id uuid NOT NULL REFERENCES auth.users(id),
  target_user_id uuid NULL REFERENCES auth.users(id),
  action text NOT NULL,
  before_json jsonb NULL,
  after_json jsonb NULL,
  reason text NULL,
  request_id text NULL,
  ip_hash text NULL,
  user_agent_hash text NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
```

保存禁止:

- APIキー全文。
- Authorization header。
- raw IP。
- raw user agent。
- 保存本文。
- service role key。

## 11. Effective Plan Resolver

全てのDashboard/API/MCP/Adminで同じresolverを使う。

active entitlement条件:

```text
status = active
starts_at <= now()
revoked_at is null
ends_at is null or ends_at > now()
```

判定順:

```text
active stripe_subscription pro exists -> { plan: "pro", source: "stripe_subscription" }
active admin_grant pro exists -> { plan: "pro", source: "admin_grant" }
active trial pro exists -> { plan: "pro", source: "trial" }
else -> { plan: "free", source: "free" }
```

移行注意:

- 既存 `user_profiles.plan` と新resolverが矛盾しないようにする。
- 最終的にはplan limit判定をresolverに寄せる。

## 12. Trial API

Route:

```text
POST /api/billing/trial
```

Auth:

- Supabase JWT required。

挙動:

- 既にtrial entitlementがある場合は409。
- `kind = trial`, `plan = pro`, `starts_at = now()`, `ends_at = now() + 30 days`, `status = active` を作成。
- effective plan summaryを返す。

Response例:

```json
{
  "plan": "pro",
  "source": "trial",
  "ends_at": "2026-06-06T00:00:00Z"
}
```

## 13. Admin Auth

全admin APIで使うdependency:

```text
get_current_admin_user()
```

処理:

1. Authorization Bearer JWTを検証。
2. Supabase user_idを取得。
3. `A2CR_ADMIN_USER_IDS` をparse。
4. user_idが含まれなければ403。
5. request metadataをhash化して保持。

emailによるadmin判定は禁止。

## 14. Admin API

### GET /api/admin/users

Query:

```text
limit
cursor
email_query
plan
```

返却:

```json
{
  "items": [
    {
      "user_id": "uuid",
      "email": "user@example.com",
      "effective_plan": "pro",
      "plan_source": "admin_grant",
      "created_at": "...",
      "last_activity_at": "...",
      "active_slot_count": 1,
      "api_key_prefix": "sk-a2cr-..."
    }
  ],
  "next_cursor": null
}
```

返してはいけない:

- 保存本文。
- APIキー全文。
- Authorization header。
- raw IP。

### GET /api/admin/users/{user_id}

返却:

- user profile metadata。
- effective plan/source。
- entitlement summary。
- API key metadata。
- slot metadata。
- access log metadata。
- target userに関するrecent admin audit logs。

保存本文は返さない。

### POST /api/admin/users/{user_id}/entitlements/pro-grant

Body:

```json
{
  "ends_at": "2026-06-06T00:00:00Z",
  "reason": "beta tester"
}
```

`ends_at = null` なら無期限。

挙動:

- `admin_grant` entitlementを作成。
- admin audit logを書く。
- effective plan summaryを返す。

### DELETE /api/admin/entitlements/{entitlement_id}

Body:

```json
{
  "reason": "grant ended"
}
```

挙動:

- 初期版では `admin_grant` の失効だけ許可。
- `status = revoked`, `revoked_at = now()`。
- admin audit logを書く。
- effective plan summaryを返す。

### POST /api/admin/users/{user_id}/api-key/revoke

Body:

```json
{
  "reason": "user requested key rotation"
}
```

挙動:

- target userのactive API keyを失効。
- admin audit logを書く。
- APIキー全文は返さない。

## 15. Admin UI

Route:

```text
/admin
```

navigation:

- adminユーザーだけにAdminリンクを表示。
- hiddenでもAPI側のserver-side checkは必須。

画面:

- User list。
- User detail。
- Entitlement history。
- API key metadata。
- Access log metadata。
- Admin audit log。

操作:

- Grant Pro。
- Grant Pro until date。
- Revoke admin grant。
- Revoke API key。

全操作modal:

- target userを明示。
- reason入力必須。
- confirm button。

## 16. Test Requirements

必須テスト:

- JWTなしはadmin APIで401。
- 非admin JWTはadmin APIで403。
- `A2CR_ADMIN_USER_IDS` に含まれるuser idはadmin APIにアクセスできる。
- emailだけではadminになれない。
- admin list/detailが保存本文を含まない。
- admin list/detailがAPIキー全文を含まない。
- admin list/detailがAuthorization header、raw IP、raw user agentを含まない。
- admin grant作成でaudit logが作られる。
- admin grantでeffective planがProになる。
- admin grant失効でeffective planがFreeに戻る。ただし別Pro sourceがあればProのまま。
- trialは1ユーザー1回だけ。
- expired trialはPro判定されない。
- Stripe sourceが将来追加されてもresolverの優先順が守られる。

## 17. Rollout Plan

### Phase 1: Contact and legal public pages

1. Cloudflareで `support@a2cr.app` 転送を設定。
2. `A2CR_SUPPORT_EMAIL` を追加。
3. `/contact`, `/privacy`, `/terms`, `/legal` を追加。
4. footer linksを追加。
5. build/deploy。

verify:

- public pagesがログインなしで開ける。
- support emailが表示される。
- personal Gmailが表示されない。

### Phase 2: Read-only admin

1. `A2CR_ADMIN_USER_IDS` を追加。
2. admin auth dependencyを追加。
3. read-only admin APIを追加。
4. read-only `/admin` UIを追加。
5. redaction/auth testsを追加。

verify:

- 非adminは拒否。
- adminはuser一覧を見られる。
- 保存本文/APIキー全文は漏れない。

### Phase 3: Admin audit and safe writes

1. `admin_audit_logs` を追加。
2. API key revokeを追加。
3. audit log UIを追加。

verify:

- admin mutationが必ずaudit logを作る。

### Phase 4: Entitlements

1. `user_entitlements` を追加。
2. effective plan resolverを追加。
3. admin grant/revokeを追加。
4. trial start APIを追加。
5. Dashboard/API/MCPのlimit判定をresolverへ寄せる。

verify:

- trial/admin grantでPro limitになる。
- expiry/revokeでFreeへ戻る。

### Phase 5: Stripe source

1. Stripe subscription entitlement sourceを追加。
2. Stripe webhookを追加。
3. resolverへStripe stateを接続。

verify:

- Stripe activeでPro。
- Stripe cancel/expireでFree。ただしtrial/admin grantがあればPro。

## 18. Open Questions

- `support@a2cr.app` の転送先をどのprivate inboxにするか。
- `support@a2cr.app` から返信できるようにするか。
- 有料開始前の販売者名をどう表記するか。
- バーチャルオフィス/事業用電話を使うか。
- 1か月無料体験に支払い方法を要求するか。
- admin grantのProをユーザーに `Pro` とだけ見せるか、`Pro beta` のように見せるか。
- admin audit logの保持期間。
