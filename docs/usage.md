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
named `a2cr` through the local stdio wrapper. Install the wrapper from PyPI as
`a2cr-mcp`; the repository-local `mcp/server.py` entrypoint is for development
and compatibility only. Do not configure the hosted `/mcp` URL directly for
WorkBaton, and do not use the old `AI_CLIPBOARD_*` or `A2CR_API_STYLE` settings
for normal AI-agent setup.

Install or update the wrapper:

```bash
python -m pip install --upgrade a2cr-mcp
```

```json
{
  "mcpServers": {
    "a2cr": {
      "command": "a2cr-mcp",
      "args": [],
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

The full API key is shown only once when it is issued. If you issue a new key,
it is a different API key; update every MCP config that should keep using
A2CR.

The local client key file is created by the `a2cr-mcp` wrapper during the first
client-encrypted save when no key file exists. Set `A2CR_CLIENT_KEY_FILE` to
choose the exact file path, or set `A2CR_CONFIG_DIR` to choose the directory
that contains `workbaton.key`. If neither variable is set, the default path is
`%APPDATA%\A2CR\workbaton.key` on Windows, and
`$XDG_CONFIG_HOME/a2cr/workbaton.key` or `~/.config/a2cr/workbaton.key` on
macOS/Linux.

To resume the same WorkBaton from another PC, configure the A2CR API key and
securely copy the same local client key file. The API key alone can access
encrypted slot data, but it cannot decrypt the WorkBaton body.

If the local client key is lost, A2CR cannot recover client-encrypted WorkBaton bodies.

## Connect Before Starting Work

Connect the A2CR MCP server before beginning any task session. This is the
single most important step for getting autonomous WorkBaton and WorkStash
behavior.

### What happens when an AI connects

When an AI client connects to the A2CR MCP server, the server immediately
sends a tool list to the AI. Each tool comes with a name, a description, and
a parameter schema. The AI reads these before doing anything else.

This means the AI learns — from the server — what A2CR is for, when to save
a WorkBaton checkpoint, when to put supporting details in WorkStash, when not
to save, and how to avoid confusing WorkBaton with WorkThreads. No extra
prompting is needed.

Primary WorkBaton save tool: `save_context`. When the user asks to save,
overwrite, or put work into a fixed Slot, the AI should call `save_context`
with `slot_number` when available. Some MCP clients expose tools lazily. If
`save_context` is not immediately visible after connection, the AI should
search or request the exact `save_context` tool name before concluding
WorkBaton saves are unavailable.

```
AI client connects
    ↓
A2CR MCP server sends tool list
    ↓
AI reads tool names, descriptions, and parameter schemas
    ↓
AI understands: when to save, when to stash, what to skip
    ↓
Work begins — AI acts autonomously at the right moments
```

### After connecting, one instruction is enough

Once the MCP server is connected, tell the AI once at the start of the session:

```
A2CR is connected. Save a WorkBaton checkpoint at each task milestone.
```

The AI will handle timing, slot naming, WorkStash entry keys, content
distillation, and showing you the resume prompt. You do not need to repeat this
for each save.

### Without a connection

Without MCP, the AI has no instructions from A2CR. Every save or stash requires
a manual prompt from the user, the AI cannot call `should_save_workbaton` or
`should_use_work_stash` to check policy, and `explain_a2cr_flows` is unavailable
to clarify the Baton/Stash/Threads boundary.

### Tools the AI gains on connection

| Tool | What the AI learns to do |
|---|---|
| `explain_a2cr_flows` | Distinguish WorkBaton handoff, WorkStash temporary memory, and WorkThreads collaboration |
| `should_save_workbaton` | Check whether a checkpoint is appropriate before saving |
| `get_account_limits` | Check plan limits, WorkBaton size budget, and WorkStash quota before automatic or large saves |
| `save_context` | Save a client-encrypted WorkBaton checkpoint |
| `resume_context` | Load a checkpoint in a new window |
| `list_contexts` | Find active slots |
| `should_use_work_stash` | Check whether intermediate information belongs in WorkStash |
| `store_work_stash` | Store client-encrypted temporary work memory |
| `get_work_stash` | Retrieve a WorkStash note referenced by a WorkBaton |
| `list_work_stash` | Inspect WorkStash metadata and quota |
| `delete_work_stash` | Remove temporary WorkStash entries |

## MCP Flow: Baton Vs Threads

AI agents interact with A2CR through MCP tools. WorkBaton, WorkStash, and
WorkThreads share that MCP entrypoint, but their behavior after the tool call is
different.

Newly connected agents should call `explain_a2cr_flows` before choosing between
WorkBaton, WorkStash, and WorkThreads. Agents can call `should_save_workbaton`
when they are unsure whether an autonomous WorkBaton checkpoint is appropriate
or whether the current MCP surface can save it. Agents can call
`should_use_work_stash` when they are unsure whether safe intermediate
information belongs in WorkStash.

Use this decision table:

| Situation | Use |
|---|---|
| A future AI window needs focused resume-critical state | WorkBaton |
| A future AI window may need a small supporting note that would bloat WorkBaton | WorkStash |
| The task is short and no intermediate state needs to survive | No save |
| Multiple active agents need to coordinate, answer, wait, claim, or complete tasks | WorkThreads |

WorkBaton is a serial checkpoint flow: `window -> new window -> new window`.
The local stdio MCP wrapper encrypts the checkpoint before upload, and A2CR
stores ciphertext plus metadata. Agents should call `get_account_limits` before
automatic or large saves and use the returned WorkBaton size budget
intelligently. Free has a smaller body budget; Pro has a larger one, so Pro can
carry a richer handoff without changing the same safety rules.

WorkStash is temporary work memory for safe supporting notes. It is useful when
details would bloat the WorkBaton body or are optional support notes that a
future AI window may need.
The agent stores the note with `store_work_stash`, records the retained
`entry_key` in WorkBaton `references` or `next_action`, and later retrieves it
with `get_work_stash` after `resume_context` or `load_context`.

Planned WorkStash quotas for the first public preview are intentionally based on
total encrypted storage size, not number of notes: Free gets 256KB total, and
Pro gets 1024KB total. Pro is exactly four times Free for richer safe handoff
notes. WorkStash is not file storage; store concise notes and delete entries
when a task phase is complete.

Good WorkStash entries:

- confirmed file paths
- API behavior notes
- reproduction details
- small decision summaries
- concise validation summaries

Bad WorkStash entries:

- secrets, API keys, Authorization headers, cookies, or private database URLs
- personal data, full transcripts, long logs, generated caches, or git diffs
- large source-code bodies or file-like payloads that can be read from the repo

WorkThreads are a collaborative coordination flow: `agent <-> agents`. A2CR
stores locally encrypted append-only message ciphertext, task leases, loop guard
metadata, and progress metadata. Only agent windows that know the WorkThread key
can decrypt or post readable message bodies. WorkThreads must not silently create
or overwrite WorkBaton Slots.

## Context Freshness

Agents should treat context freshness as a heuristic. If the current conversation
is getting noisy, contradictory, stale, or polluted by old task state, the agent
should call `should_save_workbaton`, save a focused WorkBaton within the current
size budget when recommended, and suggest continuing in a fresh AI window.

Warning signs include newer user instructions conflicting with older decisions,
completed work being treated as unfinished, stale assumptions competing with
current tool results, uncertainty about the active file/spec/branch/goal, or the
WorkBaton summary no longer matching the workspace state.

Routine saves should report `user_facing_summary` by default. Show the full
`resume_prompt` when the user is actually switching windows or asks for it.

See `docs/runbooks/mcp-baton-vs-threads-flow.md` for the detailed flow.

For autonomous checkpoint guidance, see
`docs/runbooks/workbaton-autonomous-save-spec.md`.

## WorkStash

WorkStash is a temporary key-value store for AI agents. It is separate from
WorkBaton checkpoints and WorkThreads messages. Use it to persist intermediate
work data — parsed specs, API responses, scratchpad notes — that would be too
large or too volatile to carry inside a WorkBaton body.

WorkStash uses the same client-side Fernet encryption as WorkBaton: the local
stdio wrapper encrypts the value before upload, and A2CR stores and returns
ciphertext only.

### When to use WorkStash

Call `should_use_work_stash` when unsure. Typical cases:

- Storing a parsed API spec that multiple steps in the same session will read
- Caching an intermediate artifact that is too large for a WorkBaton body
- Sharing a computed result across separate sub-tasks in the same session

Do not use WorkStash as a permanent store. Entries expire automatically (7 days
on Free, 30 days on Pro) and are deleted when the agent explicitly removes them
or when the quota is reached.

### Entry key format

Keys must match `^[A-Za-z0-9_.:-]{1,256}`. Use a descriptive namespaced key
such as `myapp_api_spec_v1` or `session:2026-05-08:parsed_schema`.

### Plan limits

| | Free | Pro |
|---|---|---|
| Quota | 256 KB | 1,024 KB |
| TTL | 7 days | 30 days |
| Public entry-count limit | none | none |
| Max per entry | 8 KB | 32 KB |
| Writes / hour | 200 | 400 |
| Reads / hour | 300 | 800 |

Check limits with `get_account_limits` before large or frequent writes.

### WorkStash is not WorkBaton

WorkBaton carries session handoff context between AI windows. WorkStash carries
temporary work data within or across tasks. Do not store WorkBaton slot names
or resume prompts inside WorkStash entries.

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
