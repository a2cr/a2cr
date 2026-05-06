# Security Policy

A2CR is an early prototype and is not production-ready yet.

## Reporting a Vulnerability

Until a public contact channel is decided, please do not publish vulnerability details publicly. Use a private GitHub security advisory or contact the repository owner directly.

## Security Scope

Sensitive areas include:

- API key generation, storage, and verification
- WorkBaton context bodies
- planned WorkThreads message bodies
- dashboard APIs that must not return saved content bodies
- logs and audit events
- Supabase RLS and user isolation in the planned Web SaaS
- deployment secrets such as Fernet keys, DB URLs, Supabase keys, Stripe keys, and OAuth secrets
- local client-encryption key files used by the stdio MCP wrapper

## Current Guarantees

The current local prototype supports two WorkBaton storage modes:

- `server-encrypted`: the server stores Fernet-encrypted content and decrypts it only for authenticated MCP/API responses acting for the user. This is application-layer encryption, not a zero-knowledge guarantee.
- `client-encrypted`: the local stdio MCP wrapper encrypts WorkBaton content before sending it to A2CR and keeps the client key in a local key file. In this mode, A2CR stores and returns ciphertext and cannot decrypt the WorkBaton body.

Saved context bodies should not be viewable by service administrators through normal admin dashboards, support tooling, or direct database inspection. This is an operational visibility control.

The project does not currently claim:

- production readiness
- full end-to-end encryption for the whole product
- zero-knowledge encryption for A2CR as a whole
- zero-knowledge encryption for WorkThreads
- autonomous server-side AI execution

Only client-encrypted WorkBaton slots should be described as zero-knowledge-style or client-encrypted. If the local client key is lost, A2CR cannot recover those slot bodies.

## Public Repository Hygiene

Before making this repository public, confirm that no secrets, local API keys, `.env` files, logs, local databases, private MCP configs, or local A2CR client key files are tracked.
