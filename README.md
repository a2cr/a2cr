# A2CR

Agent-to-Agent Context Relay.

A2CR helps AI agents save and resume work context across conversation windows, tools, and clients. The current repository is a Web SaaS foundation with a legacy local prototype kept only for development reference.

## Product Layers

| Layer | Purpose |
|---|---|
| WorkBaton | Save a short-lived work checkpoint and resume it in a new AI window |
| WorkThreads | Planned shared work threads for active AI-agent coordination |

A2CR does not run LLM inference on the server in the MVP. It does not think for your agents, choose models, or generate reviews. Users bring their own AI clients, and those clients call A2CR through MCP/API.

This keeps A2CR model-neutral and keeps pricing tied to storage, requests, and coordination rather than token burn.

## Current Status

Legacy local prototype retained for development reference:

- FastAPI context API
- SQLite local storage
- client-encrypted WorkBaton mode through the local stdio MCP wrapper
- fixed Slot 1-3 support
- MCP wrapper tools: `explain_a2cr_flows`, `should_save_workbaton`, `save_context`, `resume_context`, `load_context`, `list_contexts`
- Streamlit local dashboard
- pytest coverage

The legacy local SQLite WorkBaton API is disabled by default. It must not be used as the official AI-agent save path.

Implemented Web SaaS foundation:

- Supabase/Postgres schema, RLS, and least-privileged runtime role design
- API key and Supabase JWT auth foundation
- WorkBaton Web Context API with plan limits and sanitized access logs
- client-encrypted-only WorkBaton storage
- Dashboard API that returns metadata, stats, logs, and API key state without saved content bodies
- Streamable HTTP MCP `/mcp` as a service surface; the official AI-agent path for WorkBaton is the local stdio MCP wrapper so client encryption happens before upload
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

Optional local services for development:

```text
API:     uvicorn main:app --host 127.0.0.1 --port 8000
Web dev: npm run dev
```

The old one-click local SQLite prototype launcher is not part of the active
SaaS path.

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

WorkBaton requires the local stdio wrapper so content is encrypted before upload. Configure exactly one MCP server named `a2cr` through this stdio wrapper for AI-agent work. Do not configure the remote `/mcp` URL directly for WorkBaton, do not guess REST endpoints, and do not use the old `AI_CLIPBOARD_*` or `A2CR_API_STYLE` settings for normal AI-agent setup.

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

- Usage guide: `docs/usage.md`
- MCP Baton vs Threads flow: `docs/runbooks/mcp-baton-vs-threads-flow.md`
- WorkBaton autonomous save spec: `docs/runbooks/workbaton-autonomous-save-spec.md`
- Deploy runbook: `docs/runbooks/deploy.md`
- Disaster recovery runbook: `docs/runbooks/disaster-recovery.md`
- Security runbook: `docs/runbooks/security.md`
- Data lifecycle runbook: `docs/runbooks/data-lifecycle.md`
- WorkThreads runbook: `docs/runbooks/workthreads.md`
- Security/resilience baseline: `docs/superpowers/specs/2026-05-06-a2cr-security-resilience-plan.md`
- Optional AI client Skill template: `docs/templates/skills/a2cr-agent/SKILL.md`
- Service cost estimate: `docs/a2cr-service-cost-estimate.md`
- GitHub publication draft: `docs/github-publication-draft.md`

## License

TBD. Keep the repository private until the license policy is decided.
