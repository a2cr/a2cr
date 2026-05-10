# A2CR Service Cost Estimate

Last checked: 2026-05-06

This document estimates the external service costs for running A2CR as a paid SaaS. Prices are approximate, mostly USD unless noted, and exclude tax, exchange rates, refunds, disputes, overages, and promotional credits. Confirm final pricing inside each provider account before committing.

## Summary

A2CR should use the final production architecture from the start, but avoid buying unnecessary capacity early.

| Stage | Recommended setup | Monthly estimate | Annual / one-time estimate |
| --- | --- | ---: | ---: |
| Hosted smoke test | Railway Hobby + Supabase Free + Cloudflare Free | about $5/mo | domain about $8-20/yr |
| Practical beta | Railway Hobby + Supabase Pro + Cloudflare Free | about $30/mo | domain about $8-20/yr |
| First production | Railway Pro + Supabase Pro + Cloudflare Free | about $45/mo | domain about $8-20/yr |

Recommended contract path:

1. Buy or transfer the domain in Cloudflare.
2. Create the Railway project.
3. Create the Supabase organization and project.
4. Configure Google OAuth for Supabase Auth.
5. Shortlist a virtual office/business address provider before public contact/legal pages are finalized.
6. Prepare Lemon Squeezy, but enable paid checkout only after the free WorkBaton + WorkStash preview and Core MVP smoke tests pass.

Current setup note:

- `a2cr.app` has been purchased and is active on Cloudflare Free.
- Supabase `a2cr-production` has been created on Free/Nano for testing.
- Supabase migrations have been applied and RLS was verified.
- Google OAuth has been configured and enabled in Supabase.
- Railway, Lemon Squeezy setup, and virtual office/business address selection are still pending.

## Recommended Service Stack

| Area | Service | Role in A2CR | Recommendation |
| --- | --- | --- | --- |
| App runtime | Railway | One Dockerfile service serving React/Vite, FastAPI, `/api/*`, and `/mcp` from one origin | Start Hobby, move to Pro for production |
| Database/Auth/RLS | Supabase | Postgres, Supabase Auth, Google OAuth integration, RLS, migrations | Use Pro before beta with real users |
| Domain/DNS/edge | Cloudflare | Domain registration, DNS, SSL/TLS, DNSSEC, basic edge protection | Free plan plus paid domain |
| Business address/contact | Virtual office provider | Public contact/legal display planning, mail forwarding, phone/contact option, possible corporation registration path | Shortlist before free preview; finalize before paid sales |
| Payments | Lemon Squeezy | Pro subscription billing, Merchant of Record checkout, and webhook-driven plan updates | Prepare early; enable after the free preview is stable |
| Login setup | Google Cloud OAuth | OAuth client ID/secret configured in Supabase Auth | Use minimal identity scopes only |
| Repository/CI | GitHub | Repository, issues, PRs, CI/CD, deployment source | Free is enough at the start |

## Cost Scenarios

| Stage | Railway | Supabase | Cloudflare | Lemon Squeezy | Estimated total |
| --- | ---: | ---: | ---: | ---: | ---: |
| Local only | $0 | $0 | $0 | $0 | $0 |
| Hosted smoke test | $5/mo | $0 | $0 + domain | payment fees only | about $5/mo + domain |
| Practical beta | $5/mo | about $25/mo | $0 + domain | payment fees only | about $30/mo + domain |
| First production | $20/mo | about $25/mo | $0 + domain | payment fees only | about $45/mo + domain |

## Railway

Use Railway as the only public application runtime for MVP. This keeps React, FastAPI, `/api/*`, and `/mcp` on one origin and avoids early CORS/auth complexity.

Official plan pricing checked:

- Free: $0/mo
- Hobby: $5/mo
- Pro: $20/mo
- Enterprise: custom

Recommendation:

- Use Hobby for the first hosted smoke tests and private beta.
- Move to Pro for public production if reliability, team workflows, or production posture matter.

Source: https://docs.railway.com/pricing/plans

## Supabase

Use Supabase for Postgres, Auth, RLS, and migration-backed schema. A2CR depends on Postgres RLS and `SET LOCAL app.user_id`, so Firebase/Firestore should stay out of the MVP.

Official pricing notes checked:

- Supabase bills by organization.
- Free plan exists and includes two free projects.
- Pro plan examples show $25/mo.
- Paid plans include compute credits; official examples show one Micro project commonly landing around the Pro minimum before overages.
- Additional projects, larger compute, egress, disk, read replicas, custom domains, and add-ons can increase the invoice.

Recommendation:

- Use Supabase Free only for early hosted smoke tests if needed.
- Upgrade to Supabase Pro before beta users or any serious production verification.
- Keep one project at first to avoid extra compute costs.
- Enable cost controls/spend cap where available.

Sources:

- https://supabase.com/docs/guides/platform/billing-on-supabase
- https://supabase.com/docs/guides/platform/manage-your-usage/compute
- https://supabase.com/docs/guides/platform/billing-faq

## Cloudflare

Use Cloudflare for DNS, SSL/TLS, DNSSEC, and domain registration/management. Free plan is enough at the start.

Official pricing notes checked:

- Cloudflare Registrar offers at-cost domain registration and renewal.
- Free DNS, CDN, SSL, WHOIS redaction, and DNSSEC are available for the basic setup.
- Domain price depends on the TLD and the exact domain.

Recommendation:

- Use Cloudflare Free plus a paid domain.
- Budget about $8-20/year for a normal domain, then verify the exact TLD price at purchase.
- Do not buy Cloudflare Pro or paid add-ons until a concrete production need appears.

Source: https://www.cloudflare.com/products/registrar/

## Virtual Office / Business Address

A2CR should avoid exposing a personal home address or personal phone number in
public repository metadata, support templates, screenshots, or legal/contact
pages. Shortlist a virtual office/business address provider before the free
preview, then finalize it before paid sales.

Provider requirements:

- Allows use as a public business contact/legal display address where required.
- Provides mail forwarding or scan/notification handling.
- Offers a phone number or reception option if a public phone contact is needed.
- Clearly states whether the address can be used for corporation registration.
- Can support the planned operator path: individual, sole proprietor, or
  corporation.
- Does not conflict with Lemon Squeezy onboarding, bank review, or official MCP
  listing/application materials.

Legal planning notes:

- Consumer Affairs Agency guidance says address and phone information for
  mail-order sales should function as real contact points, and virtual office
  address/phone display can satisfy the requirement when conditions are met.
- If the operator later incorporates, corporation setup and tax filings use the
  registered head office / principal office path; confirm the selected address
  supports that before formation.
- For a future Japanese corporation, the representative-address non-display
  measure can reduce public exposure in commercial registry certificates under
  conditions, but it does not remove the underlying registration obligation.

Sources:

- https://www.no-trouble.caa.go.jp/qa/advertising.html
- https://www.nta.go.jp/taxes/shiraberu/taxanswer/hojin/5100.htm
- https://www.moj.go.jp/MINJI/minji06_00210.html

## Lemon Squeezy

Lemon Squeezy is the preferred first paid-checkout provider. It should be prepared early, but paid flows should remain disabled until the free WorkBaton + WorkStash preview is stable and the remaining legal/payment checks are complete.

Provider fit:

- Lemon Squeezy positions itself as a Merchant of Record for digital products, including payments, taxes/VAT, compliance, fraud, refunds, and chargebacks.
- This is a good fit for a solo/early SaaS launch, but the final fee, payout, country, prohibited-product, and tax details must be confirmed inside the account before enabling paid checkout.
- The $8/month Pro price is intentional: it replaces the earlier $5/month idea
  so A2CR can absorb higher Merchant of Record fees while avoiding the
  operational burden of handling tax/VAT, refunds, chargebacks, and compliance
  directly during the first paid phase.

Example for an $8/mo Pro subscription:

| Item | Estimate |
| --- | ---: |
| Customer payment | $8.00 |
| Platform/payment/tax impact | Confirm in Lemon Squeezy account |
| Net before refunds/chargebacks/overages | Confirm before launch |

Recommendation:

- Create the Lemon Squeezy store early to avoid onboarding delay.
- Use hosted checkout/customer portal and signed webhooks for the first paid version.
- Set the first Pro list price to $8/month, not $5/month, because the price
  includes the cost of outsourcing tax/VAT and payment compliance through
  Lemon Squeezy's Merchant of Record model.
- Keep paid checkout disabled while WorkBaton and WorkStash are being released free to gather community feedback.

Sources:

- https://docs.lemonsqueezy.com/help/payments
- https://docs.lemonsqueezy.com/help/payments/merchant-of-record

## Google Cloud OAuth

Use Google Cloud only to create the OAuth client used by Supabase Auth.

Cost estimate:

- No direct monthly cost is expected for a basic OAuth client.
- Avoid sensitive or restricted Google API scopes.
- Time cost may appear through OAuth branding or verification review.

Sources:

- https://support.google.com/cloud/answer/6158849
- https://support.google.com/cloud/answer/13463073

## GitHub

Use GitHub for the repository, issues, PRs, and CI/CD.

Recommendation:

- GitHub Free is enough at the start.
- Revisit paid GitHub plans only when private repo CI minutes, team permissions, or compliance needs justify it.

Sources:

- https://github.com/pricing
- https://docs.github.com/en/billing/concepts/product-billing/github-actions

## Contract Priority

1. Cloudflare account and domain.
2. Railway Hobby project for hosted smoke testing.
3. Supabase project; upgrade the organization to Pro before beta.
4. Google Cloud OAuth client configured in Supabase Auth.
5. Virtual office/business address provider selection, with allowed-use terms confirmed.
6. Lemon Squeezy store preparation, with checkout disabled until the free preview is stable.

## Deployment Readiness Checklist

Before paying users can rely on A2CR:

- Supabase migrations `001_base_schema.sql` and `002_workthreads.sql` applied successfully.
- Railway deployment serves `/api/v1/health`, `/dashboard`, and `/mcp` from one origin.
- Runtime does not contain `SUPABASE_SERVICE_ROLE_KEY`.
- Google login works through Supabase Auth.
- Dashboard can issue an API key once and never reveals it again.
- MCP `resume_context` works from a fresh AI window.
- Dashboard context and WorkThreads responses are metadata-only.
- Lemon Squeezy webhook signature verification is implemented before changing `user_profiles.plan`.
- Cost controls and usage monitoring are enabled where available.

## Recommendation

For paid-SaaS intent, do not stay local. Start with a real hosted environment:

1. Contract Cloudflare domain, Railway Hobby, and Supabase Pro.
2. Apply migrations to Supabase.
3. Deploy Railway from the existing Dockerfile.
4. Run smoke tests against the public origin.
5. Add Lemon Squeezy checkout only after Core save/load/resume, WorkStash, and API key flows are stable.

Expected first serious beta budget: about $30/mo plus domain. Expected first production budget: about $45/mo plus domain and Lemon Squeezy payment fees.
