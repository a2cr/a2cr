# A2CR Growth and Publication Strategy

Status: Draft, internal strategy document
Date: 2026-05-06

Important: This strategy document is an internal planning document. It does not need to be committed or pushed unless the user explicitly asks.

## Purpose

This document defines how A2CR should be presented after the core product becomes stable enough to publish more broadly.

The goal is not only to announce that A2CR exists. The goal is to make A2CR look credible, technically careful, and useful to AI-agent users who care about continuity, security boundaries, and operational reliability.

## Positioning

A2CR should be positioned as:

- Agent-to-Agent Context Relay.
- A model-neutral work-continuation layer.
- A way for AI agents and AI clients to pass structured work state across windows, tools, vendors, and sessions.
- A service that does not run LLM inference in the MVP.
- A product with clear security boundaries rather than over-broad security promises.

Short positioning:

```text
A2CR is a model-neutral relay for AI work state.
WorkBaton lets an AI save a compact, client-encrypted checkpoint and resume it in another AI window or MCP-capable client.
```

## Strategic Advantage

A2CR's public credibility should come from three things:

1. Clear product concept
   - It is not another AI chat app.
   - It does not try to replace the user's AI agent.
   - It solves the handoff and resume problem.

2. Honest security posture
   - WorkBaton bodies are client-encrypted before upload.
   - Plaintext WorkBaton saves are rejected.
   - A2CR stores ciphertext and metadata.
   - Metadata and customer/account information are still normal SaaS data and must be protected.
   - A2CR does not claim that nothing can ever leak.

3. Operational seriousness
   - RLS and user-scoped access.
   - Least-privileged runtime DB role.
   - Safe logging.
   - Schema readiness checks.
   - DB timeout, lock, and concurrency planning.
   - Backup/restore and incident-response planning.
   - Clear migration and data lifecycle discipline.

This is unusually strong for a personal project and should be communicated carefully. The tone should be "serious and precise", not "enterprise theater."

## Public Security Message

Recommended README section:

```md
## Security Posture

A2CR is designed around a clear boundary:

- WorkBaton bodies are client-encrypted before upload.
- The hosted service stores and returns ciphertext only.
- Plaintext WorkBaton saves are rejected.
- The dashboard displays metadata only, not saved bodies.
- Account data, slot metadata, access logs, billing data, and operational metadata are still protected as normal SaaS data.
- Supabase RLS, least-privileged runtime DB roles, safe logging, schema readiness checks, and backup/restore planning are part of the service design.

A2CR does not claim that no data can ever leak. The security goal is narrower and more honest: keep WorkBaton plaintext out of the hosted service, protect metadata with standard SaaS controls, and fail safely under operational problems.
```

Japanese summary for posts:

```text
A2CRは「何も漏れない」とは言いません。
WorkBaton本文はローカルで暗号化してから保存し、A2CR側は暗号文だけを扱います。
一方で、アカウント情報・メタデータ・アクセスログは通常のSaaSデータとして保護します。
守れる範囲と守るべき範囲を分けて設計しているのが特徴です。
```

## Claims to Use

Use these:

- `client-encrypted WorkBaton`
- `plaintext WorkBaton saves are rejected`
- `metadata-only dashboard`
- `model-neutral`
- `MCP-first`
- `does not run server-side LLM inference in the MVP`
- `designed with RLS, least privilege, safe logging, readiness checks, and restore planning`
- `honest boundary between encrypted bodies and SaaS metadata`

Avoid these:

- `zero knowledge`
- `nothing can leak`
- `hack-proof`
- `military grade`
- `enterprise grade`
- `fully end-to-end encrypted`
- `admins can never access anything`

Reason:

A2CR's strongest message is precision. Overclaiming would reduce trust.

## Publication Phases

### Phase 0: Private Readiness

Goal:

- Make the repository and hosted service safe enough for invited testers.

Required before broader sharing:

- WorkBaton client-encrypted-only flow verified.
- Local stdio wrapper setup documented.
- Dashboard does not display saved bodies.
- Security claims reviewed.
- Schema readiness check implemented.
- DB timeout/concurrency baseline implemented.
- RLS user A/B smoke test documented.
- Restore drill run once.
- Support/contact path prepared.
- README and `SECURITY.md` reviewed for overclaims.

### Phase 1: GitHub Public Release

Goal:

- Make the repository understandable and credible.

Actions:

- Polish README around product layers: WorkBaton now, WorkThreads planned.
- Add concise security posture section.
- Keep internal planning docs clearly separated from public-facing docs.
- Add setup guide for local stdio wrapper.
- Add AI-agent guide and human guide links.
- Add `SECURITY.md` with private report path.
- Add roadmap section that clearly marks billing and WorkThreads as planned.

Success signal:

- A developer can understand what A2CR is in under 2 minutes.
- A security-conscious reader does not see obvious overclaims.
- A user can configure MCP without asking for raw API details.

### Phase 2: Small Public Posts

Goal:

- Explain the problem and get early feedback.

Suggested channels:

- GitHub repository announcement.
- X/Twitter short thread.
- Zenn or Qiita Japanese article.
- dev.to or personal blog English article.
- MCP/AI agent community spaces if relevant.

Suggested post themes:

- "AI agents need a baton, not another memory silo."
- "Why A2CR stores work state instead of chat logs."
- "Client-encrypted WorkBaton and the honest metadata boundary."
- "MCP-first context relay across Codex, Claude, Cursor, and local tools."

Avoid:

- Launching as if the product is fully production-certified.
- Promising WorkThreads before the Pro specification is final.
- Calling it zero-knowledge unless WorkThreads and all relevant paths are redesigned to support that claim.

### Phase 3: Beta Feedback Loop

Goal:

- Turn early users into product clarity.

Collect:

- Setup failures.
- Save/resume success rate.
- Confusing local client key questions.
- Whether 32KB Free is enough.
- Whether 3 slots is enough.
- What users expect from Pro.
- Whether WorkThreads solves a real workflow or needs simplification.

Metrics:

- New users who issue an API key.
- Users who successfully save at least one WorkBaton.
- Users who load/resume at least one WorkBaton.
- Save failures by reason.
- Average slot size.
- Slot deletion rate.
- Guide page visits to setup success.

Privacy:

- Do not collect or inspect WorkBaton plaintext.
- Avoid analytics that capture user content.
- Treat metadata as sensitive operational data.

### Phase 4: Pro and Billing Announcement

Goal:

- Announce Pro only after lifecycle behavior is trustworthy.

Required before Pro launch:

- Effective plan resolver.
- Stripe Checkout and webhook signature verification.
- Customer Portal.
- Cancel-at-period-end behavior.
- Downgrade behavior.
- Account deletion behavior.
- WorkThreads encryption decision.
- Public Terms, Privacy, Legal, and Contact pages.

Message:

```text
Free is for short WorkBaton checkpoints.
Pro is for larger and longer-running workflows, with WorkThreads after the Pro coordination layer is stable.
```

Do not make Pro about vague "more AI." Make it about storage, retention, coordination, and continuity.

## GitHub README Outline

Recommended README shape:

1. What is A2CR?
2. Product layers
   - WorkBaton
   - WorkThreads planned
3. Why this exists
4. Quick start
5. MCP setup
6. Security posture
7. Limits and plans
8. Roadmap
9. Development
10. Security reports

## Public Docs Checklist

Before public GitHub push:

- README explains A2CR in plain English.
- README says WorkThreads is planned or not production-ready if applicable.
- `SECURITY.md` avoids impossible guarantees.
- Human guide and AI-agent guide are split.
- Local client key guidance is visible.
- Pricing page marks Pro billing as planned until Stripe is live.
- Internal planning docs are clearly marked internal.
- No API keys, service secrets, local client keys, or private operational notes are committed.

## Outreach Content Backlog

Short posts:

- "A2CR is not an AI. It is the baton between AIs."
- "Compression summarizes a conversation. WorkBaton preserves the state needed to resume work."
- "A2CR stores ciphertext, not WorkBaton plaintext."
- "The honest boundary: WorkBaton body secrecy vs SaaS metadata protection."

Long posts:

- How WorkBaton differs from summarization.
- Why sub-agents are not enough for cross-tool continuity.
- Designing an MCP-first service without server-side LLM inference.
- Security posture for a small AI infrastructure product.
- Lessons from building client-encrypted AI work checkpoints.

Demo ideas:

- Save in Codex, resume in another client.
- Delete a slot from the dashboard.
- Show that dashboard metadata does not reveal saved body.
- Show local key path/fingerprint without revealing key material.

## Reputation Risks

Risks:

- People misunderstand A2CR as an AI memory vault.
- People expect permanent storage, not TTL relay.
- People assume "encrypted" means all metadata is invisible.
- People see WorkThreads and assume server-side AI automation.
- People challenge security claims.

Mitigations:

- Repeat the WorkBaton vs metadata boundary.
- Use "relay" and "checkpoint", not "vault".
- Mark WorkThreads as planned or separate from WorkBaton guarantees.
- Keep all security claims narrow and test-backed.
- Publish implementation details instead of slogans.

## Launch Gate

A2CR should not be promoted beyond small beta until:

- P0 security/resilience tasks are implemented.
- Hosted smoke tests pass.
- Restore drill has been performed once.
- Public docs avoid overclaims.
- Support/contact path exists.
- Free/Pro limits are clearly displayed.
- Billing is either disabled and marked planned, or fully implemented with cancellation/account lifecycle behavior.

## Japanese Summary

GitHub公開時には、セキュリティ対策と安全運用の設計は大きなプラスになる。

ただし、強く見せるポイントは「絶対安全」ではなく「責任境界を正直に定義していること」である。

A2CRは次のように見せるのがよい。

- WorkBaton本文はclient-encrypted。
- A2CRは平文WorkBatonを受け付けない。
- Dashboardは本文を表示しない。
- メタデータと顧客情報は通常のSaaSデータとして守る。
- RLS、最小権限、safe logging、readiness、DB timeout、restore drillまで設計している。
- 個人開発でも、運用事故とセキュリティ境界を真面目に扱っている。

この方向なら、広報は派手さより信頼感で伸ばすのがよい。
