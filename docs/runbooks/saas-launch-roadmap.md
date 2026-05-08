# A2CR SaaS Launch Roadmap

Last updated: 2026-05-07

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
- Stripe setup is pending
- Public legal pages and support flow are not fully launch-ready
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
- Do not enable paid checkout until Core WorkBaton save/load/resume and API key
  flows are stable.
- Do not market WorkThreads as having the same secrecy boundary as WorkBaton
  unless its encryption design is explicitly finished and verified.
- Do not put production data or production secrets into STG.
- Do not claim zero-knowledge. Say that WorkBaton bodies are client-encrypted
  and not normally viewable by A2CR; account data and metadata remain SaaS data.
- Legal pages can be drafted internally, but paid public launch should have
  professional review where required.

## Stage 0: Product Scope Freeze

Goal: decide what the first SaaS release actually includes.

Status: Not started

Work:

- Freeze Core WorkBaton MVP scope
- Freeze first Pro plan limits and user-facing promises
- Decide whether WorkThreads is included in beta, included as limited Pro beta,
  or hidden behind a feature gate
- Decide whether paid launch starts with subscriptions or starts with manual
  beta grants/trials only
- Define support scope and response expectations for early users

Deliverables:

- Core MVP scope note
- Pro plan limits and entitlement rules
- WorkThreads release scope decision
- Paid launch decision: disabled, private beta only, or public checkout

Exit criteria:

- There is no ambiguity about which features are public, beta-only, Pro-only, or
  hidden
- Pricing page copy matches the actual launch scope
- README and public docs do not overclaim production readiness

## Stage 1: STG Foundation

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

## Stage 2: Core SaaS Hardening

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

## Stage 3: Pro Plan And Entitlements

Goal: make the Pro plan real before charging for it.

Status: Spec exists, implementation status must be confirmed before launch

Work:

- Finalize Free vs Pro limits
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

## Stage 4: WorkThreads Release Decision

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
- Decide whether WorkThreads needs client-side encryption parity with WorkBaton
  before public marketing

Deliverables:

- WorkThreads release decision
- WorkThreads MVP implementation plan
- WorkThreads user-facing copy
- WorkThreads smoke test record
- WorkThreads security review record

Exit criteria:

- WorkThreads is not described as server-side AI execution
- WorkThreads is not described as zero-knowledge
- Dashboard does not expose message content
- Loop guard and task leases have regression tests
- Any disabled features are hidden or clearly unavailable

## Stage 5: Payment And Billing

Goal: prepare paid SaaS flows without letting billing mutate plans unsafely.

Status: Pending

Work:

- Create Stripe account
- Decide first paid price and currency
- Decide trial and coupon policy
- Implement Stripe Checkout or Billing portal
- Implement Stripe webhook signature verification
- Map Stripe subscription state into `user_entitlements`
- Add customer portal link for plan management
- Add failure/retry/cancel behavior
- Test with Stripe test mode first

Deliverables:

- Stripe account and test mode configuration
- Checkout/customer portal flow
- Webhook endpoint
- Billing tests
- Refund/cancellation support note

Exit criteria:

- Webhook signatures are verified before plan changes
- Stripe active subscription grants Pro
- Stripe canceled/expired subscription returns to Free unless another Pro source
  is active
- Billing errors do not expose secrets or raw webhook payloads
- Paid checkout remains disabled until Core and STG smoke are green

## Stage 6: Legal, Support, And Public Trust

Goal: have the minimum public-facing legal and support surface before real users.

Status: Spec exists, final content and review pending

Work:

- Configure `support@a2cr.app`
- Add or confirm `/contact`
- Add or confirm `/privacy`
- Add or confirm `/terms`
- Add or confirm `/legal`
- Confirm Japanese 特定商取引法 display requirements before paid sales
- Confirm refund/cancellation wording
- Confirm privacy wording for account data, metadata, ciphertext, access logs,
  and billing metadata
- Define security issue intake path

Deliverables:

- Public contact page
- Privacy policy
- Terms of service
- Legal display page
- Support handling checklist
- Security contact/intake process

Exit criteria:

- Public legal/support pages are reachable without login
- Personal email is not exposed as the public support contact
- Paid sales page does not launch before required legal fields are accurate
- Security claims distinguish WorkBaton body secrecy from metadata exposure
- Legal pages have been professionally reviewed where needed for paid launch

## Stage 7: Backup, Restore, Monitoring, And Operations

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

## Stage 8: Private Beta

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

## Stage 9: Public Beta

Goal: make A2CR discoverable, but still avoid claiming final production maturity.

Status: Not started

Work:

- Update README and public docs
- Publish public pricing and limitations
- Confirm public legal/support pages
- Confirm backup/restore and monitoring are active
- Confirm Stripe is either disabled with clear messaging or fully tested
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

## Stage 10: Paid SaaS Launch

Goal: open paid SaaS access with billing, legal, and operations in place.

Status: Not started

Work:

- Enable Stripe live mode
- Enable paid checkout
- Confirm tax, invoice, cancellation, and refund handling
- Confirm 特定商取引法 display is complete for paid sales
- Confirm production provider plans are appropriate
- Move Railway to Pro if required by reliability/team needs
- Keep Supabase Pro or equivalent backup/restore posture
- Run final STG then production smoke

Deliverables:

- Paid launch approval checklist
- Stripe live-mode verification
- Final legal/support review
- Final production smoke record

Exit criteria:

- Payment success grants Pro
- Payment cancel/expire removes Stripe Pro source safely
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
- Should public launch start with Stripe enabled, or with manual beta grants
  first?
- Which inbox receives `support@a2cr.app`?
- Which legal entity/name/address/phone are used for paid sales display?
- Who performs final legal review before paid public launch?
- Which monitoring provider or Railway/Supabase-native alert path is used first?
- Is `stg.a2cr.app` needed, or is a restricted Railway generated URL enough for
  early STG?
