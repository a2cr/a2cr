# Security Policy

A2CR is an early prototype and is not production-ready yet.

## Reporting a Vulnerability

Please do not publish vulnerability details in public issues, discussions, or
social posts.

Preferred reporting path:

- GitHub Private Vulnerability Reporting, when enabled on the public repository

Backup reporting path:

- a2cr.mcp@gmail.com

General support and privacy requests should also go to a2cr.mcp@gmail.com.

When reporting a vulnerability, include a concise reproduction, affected
version or commit, affected surface, and sanitized logs if useful. Do not
include secrets, API keys, Authorization headers, cookies, private database
URLs, local client key files, decrypted WorkBaton or WorkStash bodies, full
chat transcripts, or other user data.

A2CR is an early public-preview project, so response times are best effort. The
target for security reports is an initial human response within 7 days.

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

WorkBaton is client-encrypted only. The local stdio MCP wrapper encrypts WorkBaton content before sending it to A2CR and keeps the client key in a local key file. A2CR stores and returns ciphertext and cannot decrypt the WorkBaton body.

A2CR APIs reject plaintext WorkBaton bodies. Direct remote HTTP MCP saving is disabled for WorkBaton because encryption must happen before upload.

Saved context bodies are not exposed through normal admin dashboards, support tooling, or direct database inspection because A2CR does not possess the local client key.

The project does not currently claim:

- production readiness
- full end-to-end encryption for the whole product
- zero-knowledge encryption for WorkThreads
- autonomous server-side AI execution

If the local client key is lost, A2CR cannot recover those WorkBaton bodies. Creating a new key works for future saves, but it cannot decrypt slots saved with the old key.

## Public Repository Hygiene

Before making this repository public, confirm that no secrets, local API keys, `.env` files, logs, local databases, private MCP configs, or local A2CR client key files are tracked.
