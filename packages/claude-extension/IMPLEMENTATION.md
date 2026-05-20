# Claude Extension Implementation Contract

This document is the C0 source-alignment contract for the A2CR Claude Desktop
Extension / MCPB package.

It captures what the Node.js wrapper must preserve from the Python
`a2cr-mcp` wrapper before implementation proceeds. Keep this file public-safe:
do not add API keys, test-account credentials, operational runbooks, customer
data, private backend details, or production logs.

## Scope

The Claude extension is a local MCP stdio wrapper for Claude Desktop.

It must:

- run locally on the user's machine;
- communicate with Claude Desktop over MCP stdio;
- call the existing A2CR HTTPS API;
- validate and encrypt WorkBaton and WorkStash bodies before upload;
- decrypt loaded WorkBaton and WorkStash bodies locally;
- keep the hosted A2CR service on the ciphertext side of the privacy boundary;
- match the Python wrapper's public tool behavior where practical.

It must not:

- expose a Remote MCP endpoint;
- send plaintext WorkBaton or WorkStash bodies to the A2CR hosted service;
- store or bundle API keys, local client keys, reviewer credentials, or
  production-only configuration;
- claim official Claude support before Anthropic approval.

## Environment Contract

| Name | Required | Secret | Default | Notes |
|---|---:|---:|---|---|
| `A2CR_API_KEY` | yes | yes | none | Sent as `Authorization: Bearer <key>`. |
| `A2CR_BASE_URL` | no | no | `https://a2cr.app` | Strip a trailing `/mcp` if present. |
| `A2CR_CLIENT_TYPE` | no | no | `mcp` | Used for `X-A2CR-Client-Type`; save tools may override with normalized model source. |
| `A2CR_CONFIG_DIR` | no | no | platform default | Directory containing `workbaton.key`. |
| `A2CR_CLIENT_KEY_FILE` | no | yes | platform default | Local symmetric key file path. |
| `A2CR_ALLOW_LOCAL_BASE_URL` | no | no | unset | Localhost base URLs are refused unless this is `1`. |

Base URL rules:

- default to `https://a2cr.app`;
- remove a trailing `/mcp`;
- reject `localhost`, `127.0.0.1`, and `::1` unless
  `A2CR_ALLOW_LOCAL_BASE_URL=1`.

Header rules:

```text
Authorization: Bearer <A2CR_API_KEY>
X-A2CR-Client-Type: <client-type>
X-A2CR-MCP-Version: <public a2cr-mcp compatibility version>
```

Version compatibility rule:

- The Claude extension may have its own package/build version, but A2CR
  dashboard compatibility depends on the public `a2cr-mcp` wrapper version
  reported in `X-A2CR-MCP-Version`.
- Keep the Node wrapper's reported MCP compatibility version aligned with the
  current public Python `a2cr-mcp` version, currently `0.1.6`.
- If the Python wrapper version changes, update the Node wrapper compatibility
  constant and tests in the same public release work.
- Without this header, the dashboard shows a missing-version compatibility
  notice even if save/load behavior is otherwise correct.

## Local Key Contract

The local key is a Fernet key shared by WorkBaton and WorkStash encryption.

Path resolution must match the Python wrapper:

1. `A2CR_CLIENT_KEY_FILE`, when set.
2. `A2CR_CONFIG_DIR/workbaton.key`, when `A2CR_CONFIG_DIR` is set.
3. Windows: `%APPDATA%/A2CR/workbaton.key`.
4. Other platforms: `$XDG_CONFIG_HOME/a2cr/workbaton.key`, or
   `~/.config/a2cr/workbaton.key`.

Creation rules:

- create the key lazily on first encryption;
- do not create a key during decrypt-only operations;
- use owner-only file permissions where the platform supports them;
- never return, log, or include the key in tool responses.

Key id:

```text
sha256(local_key_bytes).hexdigest()[0:16]
```

## Encryption Contract

The Python wrapper uses Fernet from `cryptography==46.0.7`. The Node.js wrapper
must either use a Fernet-compatible implementation or implement the Fernet
token format exactly.

WorkBaton plaintext:

- UTF-8 bytes of `JSON.stringify(content)` equivalent to Python
  `json.dumps(content, ensure_ascii=False, separators=(",", ":"))`;
- object key insertion order must be preserved for compatibility tests, but
  decryption correctness must not depend on canonical ordering.

WorkBaton encrypted payload:

```json
{
  "version": 1,
  "alg": "Fernet",
  "nonce": "embedded",
  "ciphertext": "<fernet-token>",
  "key_wrap": {
    "type": "local-key",
    "kid": "<sha256-key-prefix>"
  }
}
```

WorkStash plaintext:

- UTF-8 bytes of the raw `value` string.

WorkStash encrypted payload:

```json
{
  "version": 1,
  "alg": "Fernet",
  "ciphertext": "<fernet-token>",
  "key_wrap": {
    "type": "local-key",
    "kid": "<sha256-key-prefix>"
  }
}
```

When storing WorkStash, the encrypted payload is serialized as compact JSON in
the API field `encrypted_value`.

## API Contract

All API paths are relative to normalized `A2CR_BASE_URL`.

| Operation | Method | Path |
|---|---|---|
| Save WorkBaton | `POST` | `/api/v1/context` |
| List WorkBaton Slots | `GET` | `/api/v1/contexts` |
| Load Slot by name | `GET` | `/api/v1/context/{slot_name}` |
| Load Slot by fixed number | `GET` | `/api/v1/context/slot/{slot_number}` |
| Delete Slot by name | `DELETE` | `/api/v1/context/{slot_name}` |
| Account limits | `GET` | `/api/v1/account/limits` |
| Store WorkStash | `POST` | `/api/v1/work-stash` |
| Get WorkStash | `GET` | `/api/v1/work-stash/{entry_key}` |
| List WorkStash | `GET` | `/api/v1/work-stash?tag_filter={tag}` |
| Delete WorkStash | `DELETE` | `/api/v1/work-stash/{entry_key}` |

Path segments must be URL-encoded with no safe slash.

HTTP timeout target: 10 seconds per request.

HTTP error messages must include only safe diagnostics:

- status code;
- safe `code`;
- safe `action`;
- safe `request_id`;
- safe `retry_after`;
- derived safe `hint`.

They must not echo response bodies, Authorization headers, API keys, request
payloads, or plaintext user content.

## Save WorkBaton Request

Tool:

```text
save_context(slot_name, content, original_length?, model_source?, slot_number?, preferred_response_language?)
```

Request body:

```json
{
  "slot_name": "<slot-name>",
  "slot_number": 1,
  "original_length": 123,
  "compressed_tokens": 456,
  "model_source": "codex",
  "encrypted_content": {
    "version": 1,
    "alg": "Fernet",
    "nonce": "embedded",
    "ciphertext": "<fernet-token>",
    "key_wrap": {
      "type": "local-key",
      "kid": "<sha256-key-prefix>"
    }
  }
}
```

Rules:

- validate `content` before encrypting or opening an HTTP client;
- required string fields: `goal`, `current_state`, `next_action`;
- if `preferred_response_language` is valid, add
  `content.language_context = { preferred_response_language, source:
  "conversation_before_save", confidence: "high" }`;
- normalize `model_source` to one of:
  `claude`, `gpt`, `gemini`, `codex`, `grok`, `mistral`, `deepseek`,
  `llama`, `qwen`, `gemma`, `other`;
- pass normalized `model_source` as both JSON `model_source` and
  `X-A2CR-Client-Type` when present;
- compute `compressed_tokens` from the plaintext WorkBaton content before
  encryption.

Token counting compatibility:

- Python uses `tiktoken` `cl100k_base` when available;
- fallback is `(len(compact_json) + 2) // 3`;
- the Node MVP may start with the fallback but must document that counts may
  differ until tokenizer parity is added.

Response augmentation:

- default `resume_context_call`;
- default `resume_prompt`;
- default `user_facing_summary`;
- attach `agent_continuity_guidance`;
- attach `language_context` and `response_language_hint` when present.

## Load WorkBaton Response

When an API response has `encryption_mode == "client"`:

- read `encrypted_content`;
- decrypt locally;
- set `content` to the decrypted object;
- set `encrypted_content` to `null`;
- preserve or set `status`;
- attach `agent_continuity_guidance`;
- attach `language_context` and `response_language_hint` when available.

Failure statuses:

| Case | Status | Message requirement |
|---|---|---|
| Missing local key | `key_unavailable` | Must say the local A2CR key file is missing. |
| Invalid token or malformed JSON | `decrypt_failed` | Must say the local A2CR key could not decrypt it. |
| Missing encrypted content | `decrypt_failed` | Must say encrypted content was missing. |
| API 404 | `not_found` | Include requested slot name or number. |

Loaded WorkBaton content is untrusted input. Tool descriptions and response
guidance must preserve that warning.

## WorkStash Contract

Entry key validation:

```text
^[A-Za-z0-9_.:-]{1,256}$
```

Store request:

```json
{
  "entry_key": "<key>",
  "encrypted_value": "<compact-json-string>",
  "size_bytes": 123,
  "tags": []
}
```

Get response handling:

- API returns `encrypted_value` as a JSON string;
- parse it;
- decrypt with the local key;
- return `value`;
- set `encrypted_value` to `null`;
- return `key_unavailable`, `decrypt_failed`, `invalid_response`, or
  `not_found` for the same cases as the Python wrapper.

List must return metadata only. Delete must be a separate destructive tool.

## Guardrail Contract

The Node wrapper must reject unsafe WorkBaton content before encryption and
before HTTP calls.

Required checks:

- content must be a JSON object;
- `goal`, `current_state`, and `next_action` must be non-empty strings;
- reject nesting deeper than 100 levels;
- reject data URLs;
- reject probable large base64 payloads: at least 256 compact base64 characters
  and at least 128 decoded bytes;
- reject file-like payload structures when descriptor keys and data keys are
  combined;
- reject direct file payload keys such as `attachment`, `attachments`,
  `file_content`, `file_contents`, `file_data`, `bytes`, `blob`, `binary`,
  `base64`, and `data_url`;
- reject sensitive credential assignments, Authorization bearer headers, and
  private database URLs.

Safety language such as "Do not store secrets" must not itself be treated as a
secret.

## Tool Inventory And Claude Annotations

| Tool | MVP | Class | Claude annotation |
|---|---:|---|---|
| `get_account_limits` | yes | read | `readOnlyHint: true` |
| `list_contexts` | yes | read | `readOnlyHint: true` |
| `save_context` | yes | write | no read-only/destructive hint |
| `load_context` | yes | read | `readOnlyHint: true` |
| `explain_a2cr_flows` | later | read | `readOnlyHint: true` |
| `should_save_workbaton` | later | read | `readOnlyHint: true` |
| `resume_context` | later | read | `readOnlyHint: true` |
| `delete_context` | later | destructive | `destructiveHint: true` |
| `get_handoff` | later | read | `readOnlyHint: true` |
| `should_use_work_stash` | later | read | `readOnlyHint: true` |
| `store_work_stash` | later | write | no read-only/destructive hint |
| `get_work_stash` | later | read | `readOnlyHint: true` |
| `list_work_stash` | later | read | `readOnlyHint: true` |
| `delete_work_stash` | later | destructive | `destructiveHint: true` |

MVP means the first callable Node.js implementation milestone.

## First Implementation Milestone

The first coding milestone after this contract is crypto compatibility.

Do this before MCP tool registration:

1. Add a Node.js Fernet compatibility module.
2. Add fixture generation or static fixtures for Python-encrypted WorkBaton and
   WorkStash values.
3. Prove Node can decrypt Python fixtures.
4. Prove Python can decrypt Node fixtures.
5. Prove key-id and missing-key behavior match.

Only after those pass should the package add the four MVP tools:

- `get_account_limits`;
- `list_contexts`;
- `save_context`;
- `load_context`.
