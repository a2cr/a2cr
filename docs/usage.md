# A2CR Usage

This guide covers development usage. The official AI-agent WorkBaton path is
the local stdio MCP wrapper targeting the A2CR SaaS API. The legacy local
SQLite `/v1/context/*` API is disabled by default.

## Local Development

Install dependencies:

```bash
pip install -r requirements.txt
```

Run verification:

```bash
python -m pytest -q
cd web
npm install
npm run build
```

Optional local services for development:

```text
API:     uvicorn main:app --host 127.0.0.1 --port 8000
Web dev: npm run dev
```

Health check:

```bash
curl http://localhost:8000/v1/health
```

Expected response:

```json
{"status":"ok"}
```

## API Key

Legacy local API routes require `X-API-Key` and
`A2CR_ENABLE_LEGACY_LOCAL_API=1`. Do not enable this for normal AI-agent work.

Example:

```bash
API_KEY="<your-local-api-key>"
```

Do not commit real API keys or local `.env` files.

## Save A WorkBaton Slot

Legacy local SQLite API example. WorkBaton bodies must be encrypted before upload. Prefer the local stdio MCP wrapper targeting A2CR SaaS. Direct local API saves must send `encrypted_content`, not plaintext `content`.

```bash
curl -X POST http://localhost:8000/v1/context/save \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "slot_name": "my-project-main",
    "encrypted_content": {
      "version": 1,
      "alg": "Fernet",
      "nonce": "embedded",
      "ciphertext": "<local-wrapper-generated-ciphertext>",
      "key_wrap": {"type": "local-key", "kid": "<key-id>"}
    },
    "original_length": 15000,
    "model_source": "codex"
  }'
```

## Load A Slot

By slot name:

```bash
curl http://localhost:8000/v1/context/my-project-main \
  -H "X-API-Key: $API_KEY"
```

By fixed slot number:

```bash
curl http://localhost:8000/v1/context/slot/1 \
  -H "X-API-Key: $API_KEY"
```

## List Slots

```bash
curl http://localhost:8000/v1/context/list \
  -H "X-API-Key: $API_KEY"
```

## Delete A Slot

```bash
curl -X DELETE http://localhost:8000/v1/context/my-project-main \
  -H "X-API-Key: $API_KEY"
```

## MCP Stdio Setup

Example only:

This is the only official AI-agent path for WorkBaton. Configure one MCP server
named `a2cr` through the local stdio wrapper. Do not configure the hosted
`/mcp` URL directly for WorkBaton, and do not use the old `AI_CLIPBOARD_*` or
`A2CR_API_STYLE` settings for normal AI-agent setup.

```json
{
  "mcpServers": {
    "a2cr": {
      "command": "python",
      "args": ["<project-root>/mcp/server.py"],
      "env": {
        "A2CR_API_KEY": "<your-api-key>",
        "A2CR_BASE_URL": "https://a2cr.app",
        "A2CR_SERVICE_URL": "https://a2cr.app/mcp"
      }
    }
  }
}
```

The local stdio MCP wrapper always uses client-encrypted WorkBaton mode.
It refuses localhost `A2CR_BASE_URL` unless `A2CR_ALLOW_LOCAL_BASE_URL=1` is
set for explicit legacy local prototype tests.

Optional environment variables:

| Variable | Purpose |
|---|---|
| `A2CR_CLIENT_KEY_FILE` | Explicit local client key file path |
| `A2CR_CONFIG_DIR` | Directory for the generated local client key file |

If the local client key is lost, A2CR cannot recover client-encrypted WorkBaton bodies.

## Connect Before Starting Work

Connect the A2CR MCP server before beginning any task session. This is the
single most important step for getting autonomous WorkBaton behavior.

### What happens when an AI connects

When an AI client connects to the A2CR MCP server, the server immediately
sends a tool list to the AI. Each tool comes with a name, a description, and
a parameter schema. The AI reads these before doing anything else.

This means the AI learns — from the server — what A2CR is for, when to save
a WorkBaton checkpoint, when not to save, and how to avoid confusing WorkBaton
with WorkThreads. No extra prompting is needed.

Some MCP clients expose tools lazily. If `save_context` is not immediately
visible after connection, the AI should search or request the exact
`save_context` tool name before concluding WorkBaton saves are unavailable.

```
AI client connects
    ↓
A2CR MCP server sends tool list
    ↓
AI reads tool names, descriptions, and parameter schemas
    ↓
AI understands: when to save, what to save, what to skip
    ↓
Work begins — AI acts autonomously at the right moments
```

### After connecting, one instruction is enough

Once the MCP server is connected, tell the AI once at the start of the session:

```
A2CR is connected. Save a WorkBaton checkpoint at each task milestone.
```

The AI will handle timing, slot naming, content distillation, and showing you
the resume prompt. You do not need to repeat this for each save.

### Without a connection

Without MCP, the AI has no instructions from A2CR. Every save requires a
manual prompt from the user, the AI cannot call `should_save_workbaton` to
check policy, and `explain_a2cr_flows` is unavailable to clarify the
Baton/Threads boundary.

### Tools the AI gains on connection

| Tool | What the AI learns to do |
|---|---|
| `explain_a2cr_flows` | Distinguish WorkBaton serial handoff from WorkThreads collaboration |
| `should_save_workbaton` | Check whether a checkpoint is appropriate before saving |
| `get_account_limits` | Check plan limits before automatic or large saves |
| `save_context` | Save a client-encrypted WorkBaton checkpoint |
| `resume_context` | Load a checkpoint in a new window |
| `list_contexts` | Find active slots |

## MCP Flow: Baton Vs Threads

AI agents interact with A2CR through MCP tools. WorkBaton and WorkThreads share
that MCP entrypoint, but their behavior after the tool call is different.

Newly connected agents should call `explain_a2cr_flows` before choosing between
WorkBaton and WorkThreads. Agents can call `should_save_workbaton` when they
are unsure whether an autonomous WorkBaton checkpoint is appropriate or whether
the current MCP surface can save it.

WorkBaton is a serial checkpoint flow: `window -> new window -> new window`.
The local stdio MCP wrapper encrypts the checkpoint before upload, and A2CR
stores ciphertext plus metadata.

WorkThreads are a collaborative coordination flow: `agent <-> agents`. A2CR
stores encrypted-at-rest append-only messages, task leases, loop guard metadata,
and progress metadata. WorkThreads must not silently create or overwrite
WorkBaton Slots.

See `docs/runbooks/mcp-baton-vs-threads-flow.md` for the detailed flow.

For autonomous checkpoint guidance, see
`docs/runbooks/workbaton-autonomous-save-spec.md`.

## Storage Mode

| Mode | Behavior |
|---|---|
| `client-encrypted` | The stdio MCP wrapper encrypts before sending; A2CR stores and returns ciphertext only |

A2CR rejects plaintext WorkBaton bodies. Direct remote HTTP MCP saving is disabled for WorkBaton because encryption must happen before upload.

## Tests

```bash
python -m pytest -q
cd web
npm run build
```
