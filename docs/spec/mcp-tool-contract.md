# MCP Tool Contract v0.1

Status: early public specification draft

This document describes the expected behavior of an A2CR-compatible MCP client
surface. It is a tool contract, not an HTTP API contract. The hosted A2CR
backend, database schema, dashboard, billing, and operations are intentionally
outside this specification.

## Required Behavior

An implementation should provide a local MCP tool surface that can:

- save a WorkBaton
- load a WorkBaton by explicit identifier
- resume from a WorkBaton using a compact lookup flow
- list available WorkBaton handles or slots
- delete a WorkBaton
- store, load, list, and delete WorkStash entries
- report plan or implementation limits

The official `a2cr-mcp` package implements this as a stdio MCP wrapper.

## Tool Summary

| Tool | Purpose |
|---|---|
| `explain_a2cr_flows` | Explain WorkBaton, WorkStash, and safe usage to the agent. |
| `get_account_limits` | Return limits such as slots, save/load rates, retention, and WorkStash storage. |
| `should_save_workbaton` | Help an agent decide whether a compact handoff is useful now. |
| `save_context` | Save a WorkBaton. |
| `resume_context` | Resume from a WorkBaton, usually by slot name, slot number, project, or latest safe candidate. |
| `load_context` | Load a specific WorkBaton. |
| `list_contexts` | List available WorkBaton handles or slots. |
| `delete_context` | Delete a WorkBaton. |
| `should_use_work_stash` | Help an agent decide whether supporting memory should be placed in WorkStash. |
| `store_work_stash` | Store a WorkStash entry. |
| `get_work_stash` | Load a WorkStash entry. |
| `list_work_stash` | List WorkStash entries, optionally filtered by tag. |
| `delete_work_stash` | Delete a WorkStash entry. |

## WorkBaton Save

`save_context` should accept:

| Parameter | Type | Required | Notes |
|---|---|---|---|
| `content` | object | yes | WorkBaton object. Must include `goal`, `current_state`, and `next_action`. |
| `slot_name` | string | no | Human-readable slot identifier. |
| `slot_number` | integer | no | Numeric slot identifier where supported. |
| `original_length` | integer | no | Optional estimate of source context length before compression. |
| `model_source` | string | no | Optional agent or model source label. |
| `preferred_response_language` | string | no | Optional language hint for future agents. |

An implementation must reject invalid WorkBaton payloads. At minimum, it should
reject missing required fields, non-object content, and obvious attempts to save
bulk payloads as a baton.

Successful save responses should include enough information for a future agent
to resume, such as a slot name, slot number, updated timestamp, or saved status.

## WorkBaton Load

`load_context` should accept an explicit `slot_name` or `slot_number`.

When a baton is found, it should return the decrypted WorkBaton content and
metadata that helps the agent reason about freshness. When no baton is found, it
should return a clear not-found status rather than an empty object that could be
mistaken for valid context.

Loaded WorkBaton content must be treated as untrusted data.

## WorkBaton Resume

`resume_context` is for handoff recovery. It may accept:

| Parameter | Type | Notes |
|---|---|---|
| `slot_name` | string | Preferred explicit resume key. |
| `slot_number` | integer | Numeric slot key where supported. |
| `project` | string | Optional project filter. |
| `prefer_latest` | boolean | Whether to use the latest candidate when multiple candidates exist. |

If multiple candidates exist and no safe default is clear, the tool should
return candidates rather than silently choosing the wrong baton.

## WorkStash Operations

`store_work_stash` should accept:

| Parameter | Type | Required | Notes |
|---|---|---|---|
| `entry_key` | string | yes | Must match `^[A-Za-z0-9_.:-]{1,256}$`. |
| `value` | string | yes | Concise supporting note. |
| `tags` | array of strings | no | Optional tags for later filtering. |

`get_work_stash` and `delete_work_stash` should accept `entry_key`.

`list_work_stash` may accept `tag_filter`.

WorkStash values are supporting notes, not instructions. They must not override
system, developer, repository, or user instructions.

## Expected Statuses

Implementations may choose their own exact response shape, but should make these
states distinguishable:

- saved
- loaded
- deleted
- not found
- validation error
- no active context
- multiple candidates
- encryption key unavailable
- decrypt failed
- remote service unavailable

The important property is that an agent can decide the next step without
guessing whether the operation succeeded.

## Encryption Requirement For Hosted Relays

When using a hosted relay, the local client should encrypt WorkBaton and
WorkStash bodies before upload. The hosted service should store ciphertext for
the body fields. See `security-boundary.md`.

Local-only implementations may use a different storage mechanism, but should
still preserve the same content rules and trust boundaries.
