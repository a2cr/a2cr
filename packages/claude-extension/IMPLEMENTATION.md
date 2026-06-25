# Claude Extension Implementation Contract

This document is the implementation contract for the A2CR Claude Desktop
Extension / MCPB package.

Keep this file public-safe: do not add API keys, reviewer credentials, private
operations notes, customer data, or production logs.

## Scope

The Claude extension is a local MCP stdio wrapper for Claude Desktop.

It must:

- run locally on the user's machine;
- communicate with Claude Desktop over MCP stdio;
- store WorkBaton and WorkStash records in a local file managed by the
  extension;
- validate and encrypt WorkBaton bodies and WorkStash values before writing
  them to the local store;
- decrypt loaded WorkBaton bodies and WorkStash values locally;
- avoid requiring an A2CR account, API key, hosted base URL, SaaS dashboard, or
  remote MCP endpoint;
- match the Python wrapper's public WorkBaton tool behavior where practical.

It must not:

- expose a Remote MCP endpoint;
- upload saved WorkBaton bodies to A2CR infrastructure;
- store or bundle API keys, local client keys, reviewer credentials, or
  production-only configuration;
- claim official Claude support before Anthropic approval.

## Environment Contract

| Name | Required | Secret | Default | Notes |
|---|---:|---:|---|---|
| `A2CR_CLIENT_TYPE` | no | no | `mcp` | Used for local metadata and compatibility reporting. |
| `A2CR_LOCAL_STORE_FILE` | no | no | platform default | Optional local JSON store path for the MCPB. |
| `A2CR_LOCAL_DB` | no | no | unset | If set, the MCPB stores beside this path as `<A2CR_LOCAL_DB>.claude-extension.json`. |
| `A2CR_CONFIG_DIR` | no | no | platform default | Directory containing `workbaton.key`. |
| `A2CR_CLIENT_KEY_FILE` | no | yes | platform default | Local symmetric key file path. |

Legacy cloud compatibility environment variables may still exist in tests or
transitional helpers, but the public MCPB does not request or require them.

Default local store paths:

- Windows: `%LOCALAPPDATA%/A2CR/claude-extension-store.json`
- macOS: `~/Library/Application Support/A2CR/claude-extension-store.json`
- Linux: `$XDG_DATA_HOME/a2cr/claude-extension-store.json` or
  `~/.local/share/a2cr/claude-extension-store.json`

## Version Compatibility Rule

- The Claude extension may have its own package/build version, but A2CR MCP
  compatibility should stay aligned with the public Python `a2cr-mcp` version,
  currently `0.1.7`.
- If the Python wrapper version changes, update the Node wrapper compatibility
  constant, MCPB manifest version, tests, and docs in the same public release.

## Local Key Contract

The local key is a Fernet key shared by local WorkBaton and WorkStash
encryption.

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
must use a Fernet-compatible implementation.

WorkBaton plaintext:

- UTF-8 bytes of compact JSON equivalent to Python
  `json.dumps(content, ensure_ascii=False, separators=(",", ":"))`;
- object key insertion order must be preserved for compatibility tests, but
  decryption correctness must not depend on canonical ordering.

Stored WorkBaton payload:

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

The encrypted payload is written to the local MCPB store. It is not uploaded by
the public MCPB.

## Local Store Contract

The MCPB local store is JSON for the initial Claude Desktop package. For
WorkBaton records, it stores:

- Slot name and optional fixed Slot number;
- original length and estimated compressed token count;
- normalized model source;
- encrypted WorkBaton payload;
- creation and update timestamps.

The store returns metadata-only results for `list_contexts`. `load_context`
decrypts locally, sets `encrypted_content` to `null` in the returned object, and
preserves the warning that loaded WorkBaton content is untrusted input.

For WorkStash records, it stores:

- entry key;
- optional project and tag metadata;
- encrypted WorkStash value;
- value size and timestamps.

The store returns metadata-only results for `list_work_stash`. `get_work_stash`
decrypts locally, sets `encrypted_value` to `null` in the returned object, and
preserves the warning that loaded WorkStash content is untrusted supporting
data.

## Save WorkBaton Contract

Tool:

```text
save_context(slot_name, content, original_length?, model_source?, slot_number?, preferred_response_language?)
```

Rules:

- validate `content` before encrypting or writing to the local store;
- required string fields: `goal`, `current_state`, `next_action`;
- if `preferred_response_language` is valid, add
  `content.language_context = { preferred_response_language, source:
  "conversation_before_save", confidence: "high" }`;
- normalize `model_source` to one of:
  `claude`, `gpt`, `gemini`, `codex`, `grok`, `mistral`, `deepseek`,
  `llama`, `qwen`, `gemma`, `other`;
- compute `compressed_tokens` from plaintext WorkBaton content before
  encryption.

Response augmentation:

- default `resume_context_call`;
- default `resume_prompt`;
- default `user_facing_summary`;
- attach `agent_continuity_guidance`;
- attach `language_context` and `response_language_hint` when present.

## Load WorkBaton Contract

When a local store record has encrypted content:

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
| Missing Slot | `not_found` | Include requested slot name or number. |

Loaded WorkBaton content is untrusted input. Tool descriptions and response
guidance must preserve that warning.

## Guardrail Contract

The Node wrapper must reject unsafe WorkBaton content before encryption and
before local writes.

Required checks:

- content must be a JSON object;
- `goal`, `current_state`, and `next_action` must be non-empty strings;
- reject nesting deeper than 100 levels;
- reject data URLs;
- reject probable large base64 payloads;
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

| Tool | Submission | Class | Claude annotation |
|---|---:|---|---|
| `get_account_limits` | yes | read | `readOnlyHint: true`, `openWorldHint: false` |
| `list_contexts` | yes | read | `readOnlyHint: true`, `openWorldHint: false` |
| `save_context` | yes | write | `readOnlyHint: false`, `destructiveHint: true`, `openWorldHint: false` |
| `load_context` | yes | read | `readOnlyHint: true`, `openWorldHint: false` |
| `store_work_stash` | yes | write | `readOnlyHint: false`, `destructiveHint: true`, `openWorldHint: false` |
| `get_work_stash` | yes | read | `readOnlyHint: true`, `openWorldHint: false` |
| `list_work_stash` | yes | read | `readOnlyHint: true`, `openWorldHint: false` |
| `delete_work_stash` | yes | destructive | `readOnlyHint: false`, `destructiveHint: true`, `openWorldHint: false` |

The submission scope is local WorkBaton plus local WorkStash. Additional
Python-wrapper tools can be added later, but they must keep the same local-only
storage boundary unless a separate public design decision changes it.

## Verification

Before publishing a GitHub Release MCPB asset, run:

```powershell
npm test
npm run typecheck
npm run mcpb:validate
npm run mcpb:pack
```

The packaged artifact should be named `a2cr-<version>.mcpb`, accompanied by a
matching `SHA256SUMS.txt`, and install without requesting API key or hosted URL
configuration.
