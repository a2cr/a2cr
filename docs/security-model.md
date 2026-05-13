# Security Model

A2CR's public wrapper encrypts WorkBaton and WorkStash bodies locally before
upload. A2CR stores ciphertext and cannot decrypt the body without the user's
local client key.

## What This Protects

- A2CR does not receive plaintext WorkBaton or WorkStash bodies.
- Hosted metadata can exist without exposing saved body content.
- A lost server-side copy of encrypted content is not enough to read the body.

## What This Does Not Protect

- A future AI window can read decrypted content after loading.
- A compromised local machine or local client key can expose content.
- A user can accidentally paste decrypted content into an issue, PR, log, or chat.
- A2CR is not a password manager or secret vault.

## Do Not Store

- API keys, passwords, access tokens, Authorization headers, cookies, or session IDs
- local client keys or recovery key material
- private database URLs, `.env` contents, deployment secrets, or service-role keys
- personal data, customer data, payment data, or confidential business data
- full transcripts, long logs, generated caches, git diffs, or large source-code bodies

Use A2CR for work state, not credentials.
