# MCP Setup

Install the wrapper:

```bash
python -m pip install --upgrade a2cr-mcp
```

Register the MCP server as `a2cr`.

## Codex-Style TOML

```toml
[mcp_servers."a2cr"]
command = "a2cr-mcp"
args = []

[mcp_servers."a2cr".env]
A2CR_API_KEY = "YOUR_A2CR_API_KEY"
A2CR_BASE_URL = "https://a2cr.app"
A2CR_SERVICE_URL = "https://a2cr.app/mcp"
```

## JSON MCP Config

```json
{
  "mcpServers": {
    "a2cr": {
      "command": "a2cr-mcp",
      "args": [],
      "env": {
        "A2CR_API_KEY": "YOUR_A2CR_API_KEY",
        "A2CR_BASE_URL": "https://a2cr.app",
        "A2CR_SERVICE_URL": "https://a2cr.app/mcp"
      }
    }
  }
}
```

## Notes

- Configure exactly one A2CR MCP server named `a2cr`.
- Use the local stdio wrapper for WorkBaton saves.
- Do not paste real API keys into public issues, PRs, or screenshots.
- If `save_context` is not visible in a lazy MCP client, search for the exact
  tool name `save_context`.
