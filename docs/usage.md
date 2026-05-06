# A2CR Usage

This guide covers the local prototype usage path.

## Start Local Services

Install dependencies:

```bash
pip install -r requirements.txt
```

On Windows:

```bat
start.bat
```

Local services:

```text
API:       http://localhost:8000
Dashboard: http://localhost:8501
Web dev:   http://localhost:5173
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

Local API routes require `X-API-Key`.

Example:

```bash
API_KEY="<your-local-api-key>"
```

Do not commit real API keys or local `.env` files.

## Save A WorkBaton Slot

```bash
curl -X POST http://localhost:8000/v1/context/save \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "slot_name": "my-project-main",
    "content": {
      "goal": "Fix the current bug",
      "current_state": "The failing route has been identified",
      "next_action": "Patch the handler and run tests",
      "decisions": ["Keep the change minimal"],
      "constraints": ["Do not commit secrets"],
      "environment": "Python 3.13, FastAPI"
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

```json
{
  "mcpServers": {
    "a2cr": {
      "command": "python",
      "args": ["<project-root>/mcp/server.py"],
      "env": {
        "A2CR_API_KEY": "<your-api-key>"
      }
    }
  }
}
```

The local stdio MCP wrapper uses client-encrypted WorkBaton mode by default.

Optional environment variables:

| Variable | Purpose |
|---|---|
| `A2CR_CLIENT_KEY_FILE` | Explicit local client key file path |
| `A2CR_CONFIG_DIR` | Directory for the generated local client key file |
| `A2CR_CLIENT_ENCRYPTION=0` | Disable client-encrypted mode and use legacy server-encrypted mode |

If the local client key is lost, A2CR cannot recover client-encrypted WorkBaton bodies.

## Storage Modes

| Mode | Behavior |
|---|---|
| `server-encrypted` | A2CR stores Fernet-encrypted content and can decrypt it for authenticated MCP/API responses |
| `client-encrypted` | The stdio MCP wrapper encrypts before sending; A2CR stores and returns ciphertext only |

Do not describe A2CR as a whole as zero-knowledge. Only client-encrypted WorkBaton slots should be described that way.

## Tests

```bash
python -m pytest -q
cd web
npm run build
```
