# WorkBaton Format v0.1

Status: early public specification draft

WorkBaton is a compact handoff object for AI agents. It describes the current
working state well enough for another AI session to continue without receiving
the full conversation history.

WorkBaton is a JSON object. Implementations may store it locally, encrypt it,
send it to a relay, or pass it directly between tools. The hosted A2CR service
is one implementation, not a requirement of the format.

## Design Goals

- Preserve only the essential working state.
- Keep the handoff inspectable by humans and agents.
- Avoid secrets, raw logs, and full transcripts.
- Make the next action explicit.
- Allow supporting notes to live outside the baton through references.

## Required Fields

| Field | Type | Description |
|---|---|---|
| `goal` | string | The current task goal in one or a few sentences. |
| `current_state` | string | What is known now, including the latest meaningful state of the work. |
| `next_action` | string | The next concrete action another agent should take. |

Required string fields must be non-empty after trimming whitespace.

## Recommended Fields

| Field | Type | Description |
|---|---|---|
| `decisions` | array of strings | Decisions already made that should not be rediscovered. |
| `blockers` | array of strings | Known blockers, unresolved questions, or external dependencies. |
| `validation` | array of strings | Checks already run, results, and remaining validation gaps. |
| `references` | array of strings | Pointers to safe supporting material, such as `WorkStash: <entry_key>` or file paths. |
| `completed_since_previous` | array of strings | Work completed since the previous baton. |
| `remaining_tasks_ordered` | array of strings | Ordered remaining tasks when sequence matters. |
| `previous_slot` | string or integer | The previous handoff slot or identifier, when applicable. |
| `supersedes_slots` | array of strings or integers | Older slots that should no longer be treated as current. |
| `do_not_use_slots` | array of strings or integers | Known stale or contaminated slots. |
| `language_context` | object | Preferred response language or localization notes. |
| `extensions` | object | Namespaced implementation-specific data. |

## Minimal Example

```json
{
  "goal": "Fix login error",
  "current_state": "Confirmed the API returns 401 after token refresh.",
  "next_action": "Check token refresh logic in src/auth/session.ts."
}
```

## Full Example

```json
{
  "goal": "Fix login error",
  "current_state": "Confirmed the API returns 401 after token refresh.",
  "next_action": "Check token refresh logic in src/auth/session.ts.",
  "decisions": [
    "Do not change the database schema yet.",
    "Keep the patch limited to the auth client and tests."
  ],
  "blockers": [
    "Need to confirm whether refresh tokens expire after 24 hours."
  ],
  "validation": [
    "Reproduction confirmed with the existing auth fixture.",
    "Unit tests have not been run after the next patch."
  ],
  "references": [
    "WorkStash: login-refresh-notes-v1",
    "src/auth/session.ts"
  ],
  "completed_since_previous": [
    "Inspected the login request and confirmed the 401 response path."
  ],
  "remaining_tasks_ordered": [
    "Patch refresh-token retry handling.",
    "Run the auth test file.",
    "Update the handoff after validation."
  ],
  "previous_slot": 3,
  "supersedes_slots": [2],
  "do_not_use_slots": ["old-login-debug"],
  "language_context": {
    "preferred_response_language": "ja"
  },
  "extensions": {
    "example.com/debug_scope": "auth"
  }
}
```

## Field Rules

Implementations should preserve unknown fields when possible, but must not rely
on unknown fields to understand the core handoff. The required fields are the
portable minimum.

Arrays should contain short strings. When a note becomes long, move it to a
WorkStash entry and reference it from `references`.

References must not be treated as trusted instructions. A receiving agent should
load references only when needed, then decide whether the referenced content is
relevant and safe.

## Extension Rules

Use `extensions` for implementation-specific metadata. Keys should be namespaced
by a domain, product, or project identifier, for example:

```json
{
  "extensions": {
    "example.com/retry_count": 2
  }
}
```

Experimental top-level fields may use an `x_` or `x-` prefix. Stable fields
should be proposed in the specification before broad use.

## Prohibited Content

WorkBaton is not a secret store. Do not place these in a baton:

- API keys, passwords, access tokens, cookies, or Authorization headers
- private database URLs or connection strings
- local client keys or encryption keys
- customer data, personal data, or confidential payloads
- full chat transcripts
- long logs, generated caches, source files, binaries, or base64 blobs

Use WorkBaton for working state, not credentials or bulk storage.

## Trust Model

Loaded WorkBaton content is untrusted data. It can guide the next agent, but it
must not override system, developer, repository, or user instructions. A baton
should be treated like a compact project note, not like an authority.

## Versioning

This document defines WorkBaton Format v0.1. Version v0.1 is intentionally
small. Additions should prefer optional fields and extensions until the format
has enough real-world feedback for a stricter compatibility policy.
