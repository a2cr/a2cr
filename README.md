# A2CR

Agent-to-Agent Context Relay.

A2CR helps AI agents save and resume work context across conversation windows, tools, and clients. The current repository is an early local prototype plus Web SaaS foundation work.

## Product Layers

| Layer | Purpose |
|---|---|
| WorkBaton | Save a short-lived work checkpoint and resume it in a new AI window |
| WorkThreads | Planned shared work threads for active AI-agent coordination |

A2CR does not run LLM inference on the server in the MVP. It does not think for your agents, choose models, or generate reviews. Users bring their own AI clients, and those clients call A2CR through MCP/API.

This keeps A2CR model-neutral and keeps pricing tied to storage, requests, and coordination rather than token burn.

## Current Status

Implemented locally:

- FastAPI context API
- SQLite local storage
- client-encrypted WorkBaton mode through the local stdio MCP wrapper
- fixed Slot 1-3 support
- MCP wrapper tools: `save_context`, `resume_context`, `load_context`, `list_contexts`
- Streamlit local dashboard
- pytest coverage

Implemented Web SaaS foundation:

- Supabase/Postgres schema, RLS, and least-privileged runtime role design
- API key and Supabase JWT auth foundation
- WorkBaton Web Context API with plan limits and sanitized access logs
- client-encrypted-only WorkBaton storage
- Dashboard API that returns metadata, stats, logs, and API key state without saved content bodies
- Streamable HTTP MCP `/mcp` for metadata, account limits, and WorkThreads tools; WorkBaton saving uses the local stdio wrapper for client encryption
- React/Vite dashboard UI for login, WorkBaton metadata, settings, API key management, and pricing
- Railway Docker build wiring, production startup guards, same-origin guard, and deployment/security runbooks

Planned Web SaaS remaining work:

- Railway/Supabase/Cloudflare project provisioning and first hosted deployment
- Cloudflare DNS/domain
- Stripe billing after the Core MVP is stable
- WorkThreads after WorkBaton Core is solid

## Local Development

```bash
pip install -r requirements.txt
python -m pytest -q
cd web
npm install
npm run build
```

On Windows, the local prototype can be started with:

```bat
start.bat
```

Local services:

```text
API:       http://localhost:8000
Dashboard: http://localhost:8501
Web dev:   http://localhost:5173
```

## Deployment

The MVP deployment target is one Railway Dockerfile service. The Dockerfile builds the React/Vite app, installs the Python runtime, copies `web/dist`, and starts FastAPI with Uvicorn.

Railway health check:

```text
/api/v1/health
```

Maintenance cleanup command:

```bash
python -m services.maintenance expire-contexts
```

See [deploy runbook](docs/runbooks/deploy.md) and [security runbook](docs/runbooks/security.md).

## MCP Configuration

Example only. Do not commit real API keys.

WorkBaton requires the local stdio wrapper so content is encrypted before upload. Direct remote HTTP MCP saving is disabled for WorkBaton.

Codex-style local stdio example:

```toml
[mcp_servers."a2cr"]
command = "python"
args = ["<project-root>/mcp/server.py"]

[mcp_servers."a2cr".env]
A2CR_API_KEY = "<your-a2cr-api-key>"
A2CR_BASE_URL = "https://a2cr.app"
A2CR_SERVICE_URL = "https://a2cr.app/mcp"
# Optional: A2CR_CLIENT_KEY_FILE = "<path-to-workbaton.key>"
```

Generic MCP stdio example:

```json
{
  "mcpServers": {
    "a2cr": {
      "command": "python",
      "args": ["<project-root>/mcp/server.py"],
      "env": {
        "A2CR_API_KEY": "<your-a2cr-api-key>",
        "A2CR_BASE_URL": "https://a2cr.app",
        "A2CR_SERVICE_URL": "https://a2cr.app/mcp"
      }
    }
  }
}
```

The local stdio MCP wrapper creates and stores the local client key in a local key file. Set `A2CR_CLIENT_KEY_FILE` to choose the path, or `A2CR_CONFIG_DIR` to choose the directory that contains `workbaton.key`.

## Security Direction

A2CR is designed so human-facing dashboards do not display saved context bodies. Dashboards should show metadata only, such as slot names, timestamps, sizes, counts, status, and logs.

WorkBaton is client-encrypted only. The local stdio MCP wrapper encrypts WorkBaton content before sending it to A2CR and keeps the client key in a local key file. A2CR stores and returns ciphertext and cannot decrypt the WorkBaton body.

Saved context bodies should not be viewable by service administrators through normal admin dashboards, support tooling, or direct database inspection. The dashboard remains metadata-only.

Important principles:

- do not log API keys or Authorization headers
- do not log saved context bodies
- do not expose decrypted content through dashboard APIs
- reject plaintext WorkBaton bodies on A2CR APIs
- use RLS and user-scoped access in the Web SaaS design
- do not put Supabase service-role keys in normal runtime environments

Users must understand that losing the local client key makes those WorkBaton slots unrecoverable. Creating a new key works for future saves, but it cannot decrypt slots saved with the old key.

## Documentation

- Product spec and progress: `docs/superpowers/specs/2026-05-05-a2cr-product-spec-and-progress.md`
- WorkBaton save/load quality spec: `docs/superpowers/specs/2026-05-05-workbaton-save-load-quality-spec.md`
- Web SaaS design: `docs/superpowers/specs/2026-05-03-web-saas-design.md`
- Implementation plan: `docs/superpowers/plans/2026-05-04-web-saas-implementation-plan.md`
- Deploy runbook: `docs/runbooks/deploy.md`
- Security runbook: `docs/runbooks/security.md`
- Optional AI client Skill template: `docs/templates/skills/a2cr-agent/SKILL.md`
- GitHub publication draft: `docs/github-publication-draft.md`

## License

TBD. Keep the repository private until the license policy is decided.
