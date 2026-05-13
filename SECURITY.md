# Security Policy

A2CR handles AI-agent working state. Treat that state carefully even when it is
client-encrypted.

## Supported Scope

This public repository covers:

- the `a2cr-mcp` local stdio MCP wrapper
- WorkBaton and WorkStash client-side encryption behavior
- public setup examples
- AI-agent safety guidance
- documentation and tests for the public wrapper

The hosted service implementation, production database, billing, deployment,
and admin tooling are outside this public repository.

## Current Security Boundary

The local stdio MCP wrapper encrypts WorkBaton and WorkStash bodies before
upload. A2CR receives ciphertext and cannot decrypt those bodies without the
user's local client key.

The local client key remains user-owned. If it is lost, A2CR cannot recover old
client-encrypted WorkBaton or WorkStash bodies.

## Not A Secret Manager

A2CR is not a secret manager.

Do not store:

- API keys, passwords, access tokens, Authorization headers, cookies, or session IDs
- local client keys or recovery key material
- private database URLs, `.env` contents, deployment secrets, or service-role keys
- personal data, customer data, payment data, or confidential business data
- full transcripts, long logs, generated caches, git diffs, or large source-code bodies

Encryption protects against A2CR reading the body. It does not remove the risk
that a future AI window, local machine, copied resume prompt, log, issue, or PR
could expose decrypted content.

## Reporting A Vulnerability

Please do not publish vulnerability details in a public issue.

Use GitHub private vulnerability reporting or contact the repository owner
privately. Include:

- affected version or commit
- reproduction steps
- expected and observed behavior
- whether any secrets or personal data were exposed

Do not include real API keys, tokens, local client key files, or decrypted
WorkBaton / WorkStash bodies in the report.

## Public Repository Hygiene

Before publishing or accepting large changes, confirm that the repository does
not contain:

- real `.env` files
- local databases
- logs
- production credentials
- local MCP configs with real keys
- local A2CR client key files
- private service implementation code
