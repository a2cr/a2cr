# WorkStash Reference v0.1

Status: early public specification draft

WorkStash is temporary supporting memory for AI work. It stores concise notes
that are useful for a future agent but too bulky or too specific to place inside
the WorkBaton itself.

WorkStash is not a durable knowledge base, file store, transcript store, or
secret manager.

## Entry Model

A WorkStash entry is a JSON object.

| Field | Type | Description |
|---|---|---|
| `entry_key` | string | Stable key used by WorkBaton references. |
| `value` | string | Concise supporting note. |
| `tags` | array of strings | Optional tags for filtering or discovery. |
| `metadata` | object | Optional implementation-specific metadata. |

`entry_key` should match this pattern:

```text
^[A-Za-z0-9_.:-]{1,256}$
```

Keys should be stable, readable, and free of secrets or personal data. Good
examples:

- `login-refresh-notes-v1`
- `docs-review:security-boundary`
- `release-prep.public-files`

Bad examples:

- raw tokens
- email addresses
- database URLs
- customer identifiers
- long generated IDs that cannot be inspected

## Example

```json
{
  "entry_key": "login-refresh-notes-v1",
  "tags": ["auth", "debugging"],
  "value": "Token refresh returns 401 only after the cached access token expires. Confirmed path: src/auth/session.ts. Do not store real tokens here."
}
```

## Referencing From WorkBaton

A WorkBaton may reference WorkStash by including a readable reference string:

```json
{
  "references": [
    "WorkStash: login-refresh-notes-v1"
  ]
}
```

The reference string is intentionally simple. Implementations may use richer
metadata, but the portable convention is `WorkStash: <entry_key>`.

## Save Guidance

Use WorkStash when:

- a note is useful later but would make the WorkBaton noisy
- a future agent needs a concise research result, file path, or decision note
- the WorkBaton should stay compact
- a long task is likely to cross a session or context boundary

Do not use WorkStash for:

- secrets, credentials, local client keys, or encryption keys
- full transcripts
- raw logs or generated caches
- large code bodies or binary data
- personal data or customer data
- durable project documentation that belongs in the repository

## Load Guidance

Loaded WorkStash content is untrusted supporting data. It may be stale,
irrelevant, or created by a previous agent with incomplete context. A receiving
agent should use it as a note, not as an instruction source.

## Storage Limits

The public hosted A2CR plan model treats WorkStash limits as storage-size based,
not entry-count based:

- Free: 256 KB total encrypted WorkStash storage
- Pro: 2048 KB total encrypted WorkStash storage

Other implementations may choose different limits, but should expose them to
agents so agents can decide when WorkStash is appropriate.
