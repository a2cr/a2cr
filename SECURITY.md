# Security Policy

A2CR is an early prototype and is not production-ready yet.

## Reporting a Vulnerability

Until a public contact channel is decided, please do not publish vulnerability details publicly. Use a private GitHub security advisory or contact the repository owner directly.

## Security Scope

Sensitive areas include:

- API key generation, storage, and verification
- encrypted WorkBaton context bodies
- planned WorkThreads message bodies
- dashboard APIs that must not return saved content bodies
- logs and audit events
- Supabase RLS and user isolation in the planned Web SaaS
- deployment secrets such as Fernet keys, DB URLs, Supabase keys, Stripe keys, and OAuth secrets

## Current Guarantees

The current local prototype uses application-layer encryption for saved context bodies and API-key based local access.

The project does not currently claim:

- production readiness
- full end-to-end encryption
- zero-knowledge encryption
- autonomous server-side AI execution

## Public Repository Hygiene

Before making this repository public, confirm that no secrets, local API keys, `.env` files, logs, local databases, or private MCP configs are tracked.
