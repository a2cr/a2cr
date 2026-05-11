# A2CR SaaS Launch Roadmap

Last updated: 2026-05-10

Status: Draft / not started as a unified launch program

This roadmap connects the work required to move A2CR from the current hosted
prototype state to a public SaaS release. It is intentionally gate-based: do not
advance to the next stage until the exit criteria for the current stage are
verified.

## Japanese Summary

この文書は、STG構築、Pro版仕様、WorkThreads仕様、決済、法的対策、
運用/セキュリティ検証を含めた、SaaS公開までの全体ロードマップです。

現時点では、各分野の仕様書・runbook はありますが、公開までの一本化された
進行計画は未着手でした。このロードマップでは、まず仕様を確定し、次にSTGで
検証し、private beta、public beta、paid SaaS公開へ進めます。

## Current Position

Known current state:

- Domain `a2cr.app` exists in Cloudflare
- Supabase production-like project `a2cr-production` exists
- Google OAuth is configured for Supabase Auth
- Railway production candidate exists, but canonical production service still
  needs confirmation
- STG infrastructure is not created yet
- Supabase backups or scheduled exports are not confirmed
- Lemon Squeezy setup is pending
- Public legal pages and support flow are not fully launch-ready
- Virtual office / business address provider is not selected yet
- WorkThreads exists as a Pro-only concept, but final production scope must be
  frozen before marketing or paid release

Primary references:

- `docs/runbooks/staging-design.md`
- `docs/runbooks/staging-implementation-plan.md`
- `docs/runbooks/deploy.md`
- `docs/runbooks/disaster-recovery.md`
- `docs/runbooks/security.md`
- `docs/runbooks/workthreads.md`
- `docs/runbooks/workthreads-mvp-plan.md`
- `docs/a2cr-service-cost-estimate.md`
- `docs/superpowers/specs/2026-05-06-a2cr-operations-legal-admin-spec.md`
- `docs/superpowers/specs/2026-05-06-a2cr-security-resilience-plan.md`

## Guiding Rules

- Do not publish A2CR as production-ready until hosted deployment, auth, RLS,
  logging hygiene, backup/restore, and smoke checks are verified.
- Release WorkBaton and WorkStash first as a free public preview, then use
  GitHub OSS publication, community feedback, and official MCP listing/application
  work to form the initial user community.
- Do not enable paid checkout until the free WorkBaton/WorkStash preview, Core
  save/load/resume, WorkStash flows, and API key flows are stable.
- The first planned Pro price is $8/month, not $5/month, because the price
  needs to absorb Lemon Squeezy Merchant of Record fees and the value of
  outsourced tax/VAT, refund, chargeback, and compliance handling.
- Use Lemon Squeezy as the preferred first checkout provider, with signed
  webhooks as the only path that can mutate paid entitlement state.
- Select a virtual office/business address before public contact/legal pages
  are finalized, so personal home address and personal phone details do not
  become part of the public product surface.
- Do not market WorkThreads message-body encryption until its local thread-key
  design is implemented and verified.
- Do not put production data or production secrets into STG.
- Do not make broad zero-knowledge claims. Say that WorkBaton bodies and planned
  WorkThreads message bodies are client-encrypted; account data, metadata, task
  state, and access logs remain SaaS data.
- Legal pages can be drafted internally, but paid public launch should have
  professional review where required.

## Stage 0: Product Scope Freeze

Goal: decide the free preview, OSS, and later paid scope before changing public copy.

Status: Not started

Work:

- Freeze Core WorkBaton MVP scope
- Freeze WorkStash free-preview scope: Free starts at 256KB total encrypted
  storage and Pro starts at 2048KB total encrypted storage because Pro WorkStash
  also supports Threads-related stash use. Public plan limits should be based on
  total encrypted storage size, not entry count. Entry count can remain an
  internal abuse guard if needed.
- Freeze first Pro plan limits and user-facing promises
- Confirm the first Pro list price is $8/month and record that the increase
  from the earlier $5 idea is intentional to support the Lemon Squeezy
  Merchant of Record cost structure.
- Decide whether WorkThreads is included in beta, included as limited Pro beta,
  or hidden behind a feature gate
- Decide the GitHub OSS license and publication checklist
- Decide official MCP listing/application owner and submission package
- Decide whether the first public operator identity is individual, sole
  proprietor, or corporation, and select a virtual office path that can support
  that path.
- Confirm paid launch starts after the free preview rather than at first public
  release
- Define support scope and response expectations for early users

Deliverables:

- Core MVP scope note
- WorkStash free-preview scope note, including Free 256KB total encrypted
  storage and Pro 2048KB total encrypted storage, with no public entry-count
  limit
- Pro plan limits and entitlement rules
- OSS license/publication decision
- Official MCP listing/application checklist
- Business address decision: provider shortlist, allowed uses, mail forwarding,
  phone/contact handling, and later corporation migration path
- WorkThreads release scope decision
- Paid launch decision: disabled for first free preview, Lemon Squeezy later

Exit criteria:

- There is no ambiguity about which features are public, beta-only, Pro-only, or
  hidden
- Pricing page copy matches the actual launch scope
- README and public docs do not overclaim production readiness
- Public copy says WorkBaton and WorkStash are free-preview first, with
  WorkThreads, payment, and remaining legal work following later
- Public contact/legal planning does not require exposing a personal home
  address or personal phone number.

## Stage 1: Free Preview Publication

Goal: release WorkBaton and WorkStash first, free, and start forming a community.

Status: Not started

Work:

- Publish the GitHub repository as OSS after license and secret checks pass
- Keep the public README focused on WorkBaton, WorkStash, MCP setup, and known
  limitations
- Confirm `python -m pip install --upgrade a2cr-mcp` works from a clean user environment
- Publish a free-preview guide for WorkBaton and WorkStash
- Keep public legal/contact copy minimal and non-paid while the virtual
  office/business address decision is being finalized.
- Prepare and submit the official MCP listing/application package once setup
  docs are stable
- Route feedback through GitHub issues/discussions or another visible community
  surface
- Keep paid checkout disabled and WorkThreads hidden/internal-only

Deliverables:

- OSS repository with LICENSE and SECURITY guidance
- Free-preview release note
- WorkBaton + WorkStash onboarding guide
- Official MCP listing/application package
- Community feedback intake path

Exit criteria:

- No secrets, local DBs, or private MCP configs are published
- `python -m pytest -q` and `cd web && npm run build` pass before the public push
- A clean PyPI install can configure the MCP wrapper and use WorkBaton/WorkStash
- Public docs say billing and WorkThreads are not part of the first free preview
- Public docs do not expose a personal home address, personal phone number, or
  personal Gmail address.
- Feedback/community intake is visible from the repository

## Stage 2: STG Foundation

Goal: create a non-public environment for safe validation.

Status: Not started

Work:

- Create Supabase STG project
- Apply all migrations to STG
- Create STG test users
- Create Railway STG service
- Configure STG-only runtime and browser variables
- Configure STG Auth redirect URLs
- Keep STG non-public, preferably behind Cloudflare Access if `stg.a2cr.app`
  is introduced

Deliverables:

- STG Supabase project
- STG Railway service
- STG origin
- STG test users
- STG smoke record

Exit criteria:

- `/api/v1/health` passes on STG
- `/api/v1/health/readiness` passes on STG
- `python scripts/check_migrations.py` passes against STG
- `python scripts/smoke_rls_pooler.py` passes against STG
- STG dashboard login works
- STG API key issue/revoke works
- STG MCP smoke works with test-only data
- Production secrets and production data are not used in STG

## Stage 3: Core SaaS Hardening

Goal: make the base service dependable before inviting real beta users.

Status: Partially implemented, not fully verified in hosted environment

Work:

- Confirm canonical Railway production service
- Confirm Cloudflare DNS points `a2cr.app` to the intended Railway service
- Apply pending Supabase production migrations
- Confirm Supabase Auth URL configuration for production
- Verify same-origin guard and security headers in hosted production candidate
- Verify dashboard/API/MCP metadata-only behavior
- Confirm rate limits and error hygiene
- Run hosted smoke for health, readiness, dashboard, API key, MCP, and
  WorkBaton save/resume

Deliverables:

- Production deploy record
- Hosted smoke record
- Migration check record
- Security header/origin check record

Exit criteria:

- Production candidate readiness passes
- Unexpected `Origin` is rejected
- Runtime does not contain `SUPABASE_SERVICE_ROLE_KEY`
- Dashboard does not return WorkBaton body content
- API and logs do not expose DB URLs, tokens, Authorization headers, or API keys

## Stage 4: Pro Plan And Entitlements

Goal: make the Pro plan real before charging for it.

Status: Spec exists, implementation status must be confirmed before launch

Work:

- Finalize Free vs Pro limits
- Set Pro list price to $8/month in public copy and entitlement docs, with the
  internal rationale that MoR/tax/compliance outsourcing is part of the price.
- Implement or confirm `user_entitlements`
- Implement or confirm effective plan resolver
- Implement trial entitlement rules
- Implement admin grant and revoke path
- Ensure Dashboard/API/MCP all use the same effective plan resolver
- Add downgrade behavior for over-limit users returning to Free

Deliverables:

- Pro limits table
- Entitlement migration
- Effective plan resolver tests
- Trial/admin grant tests
- User-facing plan display

Exit criteria:

- Trial can grant Pro temporarily
- Admin grant can grant and revoke Pro
- Expired/revoked entitlements return users to Free unless another Pro source is
  active
- Plan limits are enforced consistently
- Users do not lose existing data automatically on downgrade

## Stage 5: WorkThreads Release Decision

Goal: avoid shipping an ambiguous or overclaimed collaboration feature.

Status: Runbook exists, final release scope still needs confirmation

Work:

- Decide release mode:
  - hidden
  - internal only
  - Pro beta
  - public Pro feature
- Confirm WorkThreads content boundary
- Confirm Dashboard metadata-only behavior
- Confirm loop guard and task lease behavior
- Decide whether final-result saving remains disabled
- Confirm WorkThreads local thread-key encryption is implemented before public
  marketing

Deliverables:

- WorkThreads release decision
- WorkThreads MVP implementation plan
- WorkThreads user-facing copy
- WorkThreads smoke test record
- WorkThreads security review record

Exit criteria:

- WorkThreads is not described as server-side AI execution
- WorkThreads makes no broad zero-knowledge claim beyond local message-body
  encryption
- Dashboard does not expose message content
- Loop guard and task leases have regression tests
- Any disabled features are hidden or clearly unavailable

## Stage 6: Payment And Billing

Goal: prepare paid SaaS flows without letting billing mutate plans unsafely.

Status: Pending, after the free WorkBaton/WorkStash preview

Work:

- Create Lemon Squeezy store
- Confirm first paid price is $8/month and decide billing currency; do not
  reduce the price back to $5 unless the payment/tax/compliance model changes.
- Decide trial and coupon policy
- Implement Lemon Squeezy hosted checkout or customer portal
- Implement Lemon Squeezy webhook signature verification
- Map Lemon Squeezy subscription state into `user_entitlements`
- Add customer portal link for plan management
- Add failure/retry/cancel behavior
- Test with Lemon Squeezy test mode first

Deliverables:

- Lemon Squeezy store and test mode configuration
- Checkout/customer portal flow
- Webhook endpoint
- Billing tests
- Refund/cancellation support note

Exit criteria:

- Webhook signatures are verified before plan changes
- Lemon Squeezy active subscription grants Pro
- Lemon Squeezy canceled/expired subscription returns to Free unless another Pro source
  is active
- Billing errors do not expose secrets or raw webhook payloads
- Paid checkout remains disabled until Core and STG smoke are green

## Stage 7: Legal, Support, And Public Trust

Goal: have the minimum public-facing legal and support surface before real users.

Status: Spec exists, final content and review pending

Work:

- Configure `support@a2cr.app`
- Select a virtual office/business address provider, or explicitly decide not
  to use one, before paid sales.
- Confirm the provider permits the required uses: public contact/legal display,
  mail forwarding, business phone/phone reception if needed, and future
  corporation registration if that path is chosen.
- Confirm Lemon Squeezy onboarding, bank/account review, and any official MCP
  listing/application materials can use the selected operator identity and
  business address without conflicting claims.
- Add or confirm `/contact`
- Add or confirm `/privacy`
- Add or confirm `/terms`
- Add or confirm `/legal`
- Confirm Japanese 特定商取引法 display requirements before paid sales
- Decide whether paid legal display uses full address/phone display or a
  request-disclosure flow where legally appropriate.
- Confirm refund/cancellation wording
- Confirm privacy wording for account data, metadata, ciphertext, access logs,
  and billing metadata
- Define security issue intake path

Deliverables:

- Public contact page
- Privacy policy
- Terms of service
- Legal display page
- Virtual office/business address decision record
- Paid legal-display readiness note
- Support handling checklist
- Security contact/intake process

Exit criteria:

- Public legal/support pages are reachable without login
- Personal email is not exposed as the public support contact
- Personal home address and personal phone number are not exposed in public
  docs, dashboard pages, public repository metadata, or support templates unless
  explicitly approved.
- Any virtual office address/phone shown publicly has a written service
  agreement or plan that allows use as the relevant contact point.
- Paid sales page does not launch before required legal fields are accurate
- Security claims distinguish WorkBaton body secrecy from metadata exposure
- Legal pages have been professionally reviewed where needed for paid launch

## Stage 8: Backup, Restore, Monitoring, And Operations

Goal: make the service recoverable and operable before beta users rely on it.

Status: Partially specified, not fully executed

Work:

- Upgrade Supabase or add scheduled exports before beta with real users
- Confirm backup retention and restore target
- Run first restore drill into non-production
- Configure cleanup jobs
- Configure access log pruning
- Run global orphan/data lifecycle scan
- Add monitoring/alerts for health/readiness, elevated 5xx, cleanup failures,
  DB connection errors, and auth anomalies
- Run Railway redeploy/rollback drill
- Run runtime secret rotation dry run

Deliverables:

- Backup/export configuration record
- Restore drill record
- Cleanup job configuration
- Monitoring/alert checklist
- Rollback drill record
- Secret rotation drill record

Exit criteria:

- Production data is not treated as recoverable until backup/export is verified
- Restore drill succeeds into non-production
- Readiness catches schema drift
- Operators can rotate secrets without pasting them into chat/docs/Git
- Incident and rollback runbooks are usable without exposing secrets

## Stage 9: Private Beta

Goal: invite a small number of trusted users while preserving manual control.

Status: Not started

Work:

- Select beta users
- Use admin grants or trial entitlements instead of public paid checkout if
  billing is not fully ready
- Provide setup guide for official MCP path
- Verify users understand local client key backup responsibility
- Monitor support issues, auth failures, rate limits, and unexpected errors
- Keep WorkThreads hidden or clearly labeled beta if included

Deliverables:

- Private beta invite checklist
- Beta onboarding guide
- Known limitations list
- Support and incident log

Exit criteria:

- Core save/load/resume works for beta users
- Support process works in practice
- No critical privacy/security issue remains open
- Pricing, Pro limits, and WorkThreads scope are still accurate after feedback

## Stage 10: Public Beta

Goal: make A2CR discoverable, but still avoid claiming final production maturity.

Status: Not started

Work:

- Update README and public docs
- Publish public pricing and limitations
- Confirm public legal/support pages
- Confirm backup/restore and monitoring are active
- Confirm Lemon Squeezy is either disabled with clear messaging or fully tested
- Confirm abuse/rate limits are active
- Confirm public onboarding path

Deliverables:

- Public beta release checklist
- Public docs update
- Public pricing page
- Support process

Exit criteria:

- Public docs do not overclaim security or production readiness
- New users can onboard without operator help for the core flow
- Paid checkout is either intentionally disabled or fully verified
- Alerts and rollback path are live

## Stage 11: Paid SaaS Launch

Goal: open paid SaaS access with billing, legal, and operations in place.

Status: Not started

Work:

- Enable Lemon Squeezy live mode
- Enable paid checkout
- Confirm tax, invoice, cancellation, and refund handling
- Confirm 特定商取引法 display is complete for paid sales
- Confirm production provider plans are appropriate
- Move Railway to Pro if required by reliability/team needs
- Keep Supabase Pro or equivalent backup/restore posture
- Run final STG then production smoke

Deliverables:

- Paid launch approval checklist
- Lemon Squeezy live-mode verification
- Final legal/support review
- Final production smoke record

Exit criteria:

- Payment success grants Pro
- Payment cancel/expire removes Lemon Squeezy Pro source safely
- Legal display is complete
- Backup/restore and incident process are tested
- Production deploy and rollback path are verified
- No P0/P1 launch blocker remains open

## Cross-Stage Decision Log

Record decisions here as they are made:

| Date | Decision | Owner | Notes |
| --- | --- | --- | --- |
| 2026-05-07 | STG should be non-public and separated from production | TBD | Implement through separate Supabase/Railway and access restrictions where practical |
| 2026-05-08 | WorkThreads local implementation can proceed before STG, but STG must exist before external beta, public beta, paid checkout, or hosted usability claims | TBD | See `docs/runbooks/workthreads-mvp-plan.md` |

## Open Questions

- What are the exact Free and Pro limits for the first paid version?
- Is WorkThreads included in the first beta, or hidden until after Core launch?
- Does WorkThreads need client-side encryption parity with WorkBaton before any
  public Pro marketing?
- What is the first paid price and currency?
- Should public launch start as a free preview with Lemon Squeezy disabled, or
  should any private paid beta happen before public checkout?
- Which inbox receives `support@a2cr.app`?
- Which legal entity/name/address/phone are used for paid sales display?
- Which virtual office provider is used, and does it support public display,
  mail forwarding, phone handling, payment review, and possible corporation
  registration?
- Who performs final legal review before paid public launch?
- Which monitoring provider or Railway/Supabase-native alert path is used first?
- Is `stg.a2cr.app` needed, or is a restricted Railway generated URL enough for
  early STG?
