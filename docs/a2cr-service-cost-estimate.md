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
5. Prepare Stripe, but enable paid checkout only after Core MVP smoke tests pass.

Current setup note:

- `a2cr.app` has been purchased and is active on Cloudflare Free.
- Supabase `a2cr-production` has been created on Free/Nano for testing.
- Supabase migrations have been applied and RLS was verified.
- Google OAuth has been configured and enabled in Supabase.
- Railway and Stripe are still pending.

## Recommended Service Stack

| Area | Service | Role in A2CR | Recommendation |
| --- | --- | --- | --- |
| App runtime | Railway | One Dockerfile service serving React/Vite, FastAPI, `/api/*`, and `/mcp` from one origin | Start Hobby, move to Pro for production |
| Database/Auth/RLS | Supabase | Postgres, Supabase Auth, Google OAuth integration, RLS, migrations | Use Pro before beta with real users |
| Domain/DNS/edge | Cloudflare | Domain registration, DNS, SSL/TLS, DNSSEC, basic edge protection | Free plan plus paid domain |
| Payments | Stripe | Pro subscription billing and webhook-driven plan updates | Prepare early; enable after Core is stable |
| Login setup | Google Cloud OAuth | OAuth client ID/secret configured in Supabase Auth | Use minimal identity scopes only |
| Repository/CI | GitHub | Repository, issues, PRs, CI/CD, deployment source | Free is enough at the start |

## Cost Scenarios

| Stage | Railway | Supabase | Cloudflare | Stripe | Estimated total |
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

## Stripe

Stripe should be prepared early, but paid flows should remain disabled until Core MVP is stable.

Japan pricing note:

- Stripe Japan pricing currently advertises 3.6% for domestic card transactions on the standard pricing page.
- Other payment methods, international cards, Billing, Tax, disputes, refunds, and currency conversion can change the effective fee.

Example for a $5/mo Pro subscription:

| Item | Estimate |
| --- | ---: |
| Customer payment | $5.00 |
| Card processing at 3.6% | about $0.18 |
| Net before other fees/tax/refunds | about $4.82 |

Recommendation:

- Create the Stripe account early to avoid onboarding delay.
- Use Checkout/Billing/Customer Portal for the first paid version.
- Reconsider the $5/mo price before launch because payment fees, support, tax, and chargebacks make very low subscription prices fragile.

Source: https://stripe.com/jp/pricing

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
5. Stripe account preparation, with checkout disabled until Core MVP is stable.

## Deployment Readiness Checklist

Before paying users can rely on A2CR:

- Supabase migrations `001_base_schema.sql` and `002_workthreads.sql` applied successfully.
- Railway deployment serves `/api/v1/health`, `/dashboard`, and `/mcp` from one origin.
- Runtime does not contain `SUPABASE_SERVICE_ROLE_KEY`.
- Google login works through Supabase Auth.
- Dashboard can issue an API key once and never reveals it again.
- MCP `resume_context` works from a fresh AI window.
- Dashboard context and WorkThreads responses are metadata-only.
- Stripe webhook signature verification is implemented before changing `user_profiles.plan`.
- Cost controls and usage monitoring are enabled where available.

## Recommendation

For paid-SaaS intent, do not stay local. Start with a real hosted environment:

1. Contract Cloudflare domain, Railway Hobby, and Supabase Pro.
2. Apply migrations to Supabase.
3. Deploy Railway from the existing Dockerfile.
4. Run smoke tests against the public origin.
5. Add Stripe checkout only after Core save/load/resume and API key flows are stable.

Expected first serious beta budget: about $30/mo plus domain. Expected first production budget: about $45/mo plus domain and Stripe payment fees.
