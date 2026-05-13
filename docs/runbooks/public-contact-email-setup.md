# Public Contact Email Setup

Status: Dedicated Gmail, GitHub Organization, and social accounts configured on 2026-05-13

This checklist records the public contact addresses A2CR should use before OSS
publication and free public preview.

## Addresses

Use the dedicated project Gmail account for the first public preview. Do not use
or expose a personal/private inbox in public docs, GitHub metadata, app pages,
issue templates, support pages, registry submissions, or screenshots.

| Address | Purpose | Public use |
| --- | --- | --- |
| a2cr.mcp@gmail.com | General support, setup questions, preview feedback, privacy requests, and security backup intake | README, SECURITY.md, app contact page, registry support URL |

## Social Accounts

| Account | Purpose | Public use |
| --- | --- | --- |
| GitHub Organization: a2cr | OSS publication owner and repository home | Public repository owner, package/project identity |
| X: @A2CR_MCP | Product updates and public announcements | README, repository metadata, launch posts |
| Discord: a2cr.mcp | Community/support identity reservation | README or community page after moderation policy is ready |

## Mail Provider Requirements

- Receive public-preview mail at the dedicated project Gmail account.
- Send replies from the same dedicated project Gmail account during the free
  preview.
- Keep access protected with strong authentication.
- Avoid exposing personal home address, personal phone number, or personal
  inboxes in public-facing templates.

Cloudflare Email Routing is acceptable for temporary forwarding, but it is
forward-only. Use a domain mail provider such as Google Workspace, Fastmail,
Proton, Zoho, or another equivalent service when replies must come from
`@a2cr.app`.

## Current Status

Dedicated public-preview contact accounts are available:

- Email: `a2cr.mcp@gmail.com`
- GitHub Organization: `a2cr`
- X: `@A2CR_MCP`
- Discord: `a2cr.mcp`

Cloudflare Email Routing was previously enabled for `a2cr.app`.

- `support@a2cr.app` forwards to the verified operator mailbox.
- `security@a2cr.app` forwards to the verified operator mailbox.
- `privacy@a2cr.app` forwards to the verified operator mailbox.
- MX records point to Cloudflare Email Routing.
- SPF is configured with `include:_spf.mx.cloudflare.net`.
- Cloudflare DKIM TXT is present at `cf2024-1._domainkey.a2cr.app`.
- DMARC is configured at `_dmarc.a2cr.app` with `v=DMARC1; p=none`.

The free public preview should use `a2cr.mcp@gmail.com` for both receiving and
replying. Domain-branded `@a2cr.app` mail remains a later upgrade before paid
sales or a more formal launch.

## Setup Checklist

- [x] Choose the preview mailbox: `a2cr.mcp@gmail.com`.
- [x] Create GitHub Organization: `a2cr`.
- [x] Reserve X account: `@A2CR_MCP`.
- [x] Reserve Discord account: `a2cr.mcp`.
- [x] Choose the receive provider for `a2cr.app`: Cloudflare Email Routing.
- [x] Create or alias `support@a2cr.app`.
- [x] Create or alias `security@a2cr.app`.
- [x] Create or alias `privacy@a2cr.app`.
- [x] Configure MX records.
- [x] Configure SPF.
- [x] Configure DKIM.
- [x] Configure DMARC.
- [ ] Confirm `a2cr.mcp@gmail.com` can receive public test mail.
- [ ] Confirm replies visibly come from `a2cr.mcp@gmail.com`.
- [ ] Confirm no personal/private inbox address appears in public headers or
  signatures.
- [ ] Decide whether `@a2cr.app` mail should be upgraded before paid sales.
- [ ] Enable GitHub Private Vulnerability Reporting after the public repository
  exists.

## Publication Gates

Before OSS publication:

- SECURITY.md lists `a2cr.mcp@gmail.com` as the backup security intake.
- README lists support, security, privacy, X, and notes Discord as reserved
  until a moderation policy is ready.
- GitHub Organization `a2cr` is the public repository owner.
- GitHub repository metadata does not expose a personal/private email address.

Before paid sales:

- Decide whether public mail should move to `@a2cr.app` addresses.
- Legal/contact pages are complete.
- The business address and phone/contact policy is finalized.
- Any virtual office provider is approved for the intended public legal/contact
  display use.
