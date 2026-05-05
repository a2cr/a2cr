# A2CR

Agent-to-Agent Context Relay.

A2CR helps AI agents save and resume work context across conversation windows, tools, and clients. The current repository is an early local prototype plus design work for the planned Web SaaS version.

## Product Layers

| Layer | Purpose |
|---|---|
| WorkBaton | Save a short-lived work checkpoint and resume it in a new AI window |
| WorkThreads | Planned shared work threads for active AI-agent coordination |

In the MVP, A2CR does not run LLM inference on the server. Users bring their own AI clients, and those clients call A2CR through MCP/API.

## Current Status

Implemented locally:

- FastAPI context API
- SQLite local storage
- Fernet application-layer encryption for saved context bodies
- fixed Slot 1-3 support
- MCP wrapper tools: `save_context`, `resume_context`, `load_context`, `list_contexts`
- Streamlit local dashboard
- pytest coverage

Planned Web SaaS:

- Railway runtime for React/Vite + FastAPI + HTTP MCP
- Supabase Auth + Postgres + RLS
- Cloudflare DNS/domain
- Stripe billing after the Core MVP is stable
- WorkThreads after WorkBaton Core is solid

## Local Development

```bash
pip install -r requirements.txt
python -m pytest -q
```

On Windows, the local prototype can be started with:

```bat
start.bat
```

Local services:

```text
API:       http://localhost:8000
Dashboard: http://localhost:8501
```

## MCP Configuration

Example only. Do not commit real API keys.

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

## Security Direction

A2CR is designed so human-facing dashboards do not display saved context bodies. Dashboards should show metadata only, such as slot names, timestamps, sizes, counts, status, and logs.

Important principles:

- do not log API keys or Authorization headers
- do not log saved context bodies
- do not expose decrypted content through dashboard APIs
- use application-layer encryption for content storage
- use RLS and user-scoped access in the Web SaaS design
- do not put Supabase service-role keys in normal runtime environments

The project does not currently claim full end-to-end or zero-knowledge encryption.

## Documentation

- Product spec and progress: `docs/superpowers/specs/2026-05-05-a2cr-product-spec-and-progress.md`
- Web SaaS design: `docs/superpowers/specs/2026-05-03-web-saas-design.md`
- Implementation plan: `docs/superpowers/plans/2026-05-04-web-saas-implementation-plan.md`
- GitHub publication draft: `docs/github-publication-draft.md`

## License

TBD. Keep the repository private until the license policy is decided.
