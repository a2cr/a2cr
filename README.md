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
- server-encrypted WorkBaton mode using Fernet application-layer encryption
- client-encrypted WorkBaton mode through the local stdio MCP wrapper
- fixed Slot 1-3 support
- MCP wrapper tools: `save_context`, `resume_context`, `load_context`, `list_contexts`
- Streamlit local dashboard
- pytest coverage

Implemented Web SaaS foundation:

- Supabase/Postgres schema, RLS, and least-privileged runtime role design
- API key and Supabase JWT auth foundation
- WorkBaton Web Context API with plan limits and sanitized access logs
- server-encrypted and client-encrypted WorkBaton storage modes
- Dashboard API that returns metadata, stats, logs, and API key state without saved content bodies
- Streamable HTTP MCP `/mcp` with `save_context`, `resume_context`, `load_context`, `list_contexts`, and `get_account_limits`
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

Web SaaS Streamable HTTP example:

```json
{
  "mcpServers": {
    "a2cr": {
      "url": "https://a2cr.example/mcp",
      "headers": {
        "Authorization": "Bearer <your-a2cr-api-key>"
      }
    }
  }
}
```

Local prototype stdio example:

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

The local stdio MCP wrapper uses client-encrypted WorkBaton mode by default. It stores the client key in a local key file. You can set `A2CR_CLIENT_KEY_FILE` to choose the path, or set `A2CR_CLIENT_ENCRYPTION=0` to use legacy server-encrypted mode.

## Security Direction

A2CR is designed so human-facing dashboards do not display saved context bodies. Dashboards should show metadata only, such as slot names, timestamps, sizes, counts, status, and logs.

WorkBaton currently supports two storage modes:

- `server-encrypted`: the server stores Fernet-encrypted content and decrypts it only for authenticated MCP/API responses acting for the user. This is application-layer encryption, not zero-knowledge encryption.
- `client-encrypted`: the local stdio MCP wrapper encrypts WorkBaton content before sending it to A2CR and keeps the client key in a local key file. In this mode, A2CR stores and returns ciphertext and cannot decrypt the WorkBaton body.

Saved context bodies should not be viewable by service administrators through normal admin dashboards, support tooling, or direct database inspection. The dashboard remains metadata-only.

Important principles:

- do not log API keys or Authorization headers
- do not log saved context bodies
- do not expose decrypted content through dashboard APIs
- distinguish server-encrypted slots from client-encrypted WorkBaton slots
- use RLS and user-scoped access in the Web SaaS design
- do not put Supabase service-role keys in normal runtime environments

Do not describe A2CR as a whole as zero-knowledge. Only client-encrypted WorkBaton slots should be described that way, and users must understand that losing the local client key makes those slots unrecoverable.

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
