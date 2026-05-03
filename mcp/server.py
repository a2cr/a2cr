"""
MCP server wrapping the AI Clipboard HTTP API.

Registration (Claude Code):
  Add to ~/.claude/mcp.json:
  {
    "mcpServers": {
      "ai-clipboard": {
        "command": "python",
        "args": ["<project-root>/mcp/server.py"],
        "env": { "AI_CLIPBOARD_API_KEY": "<your-api-key>" }
      }
    }
  }
"""
import os
import httpx
from fastmcp import FastMCP

BASE_URL = os.environ.get("AI_CLIPBOARD_BASE_URL", "http://localhost:8000")
API_KEY = os.environ.get("AI_CLIPBOARD_API_KEY", "")

mcp = FastMCP("AI Clipboard")

_HEADERS = {"X-API-Key": API_KEY}

SAVE_DESCRIPTION = """Save conversation context to AI Clipboard.

Call this autonomously when:
- The conversation is getting long
- A task phase is complete
- Context window pressure is detected

Content schema (all keys are JSON):
  goal          (required str)  - What we're trying to achieve
  current_state (required str)  - What's done so far
  next_action   (required str)  - The concrete next step
  decisions     (list[str])     - Settled design/approach choices
  constraints   (list[str])     - Rules the next AI must not break
  problems      (list[str])     - Open issues and risks
  environment   (str)           - OS, language, framework versions
  background    (str)           - Context needed to understand decisions
  summary       (str)           - Short summary of long work
  failed_attempts (list[str])   - Approaches that didn't work
  references    (list[str])     - Spec URLs, file paths, doc links

Slot naming: {project}-{purpose}  e.g. "my-app-main", "my-app-debug"
"""


@mcp.tool(description=SAVE_DESCRIPTION)
def save_context(
    slot_name: str,
    content: dict,
    original_length: int | None = None,
    model_source: str | None = None,
) -> dict:
    """Save context to a named slot. Overwrites if slot_name already exists."""
    with httpx.Client() as client:
        r = client.post(
            f"{BASE_URL}/v1/context/save",
            json={
                "slot_name": slot_name,
                "content": content,
                "original_length": original_length,
                "model_source": model_source,
            },
            headers=_HEADERS,
            timeout=10,
        )
    r.raise_for_status()
    return r.json()


@mcp.tool(description="Load context from a named slot. Returns structured JSON ready to use.")
def load_context(slot_name: str) -> dict:
    """Retrieve saved context by slot name."""
    with httpx.Client() as client:
        r = client.get(f"{BASE_URL}/v1/context/{slot_name}", headers=_HEADERS, timeout=10)
    r.raise_for_status()
    return r.json()


@mcp.tool(description="List all active context slots with their expiry times and sizes.")
def list_contexts() -> list:
    """List all non-expired slots."""
    with httpx.Client() as client:
        r = client.get(f"{BASE_URL}/v1/context/list", headers=_HEADERS, timeout=10)
    r.raise_for_status()
    return r.json()


@mcp.tool(description="Delete a context slot manually.")
def delete_context(slot_name: str) -> dict:
    """Delete a named slot."""
    with httpx.Client() as client:
        r = client.delete(f"{BASE_URL}/v1/context/{slot_name}", headers=_HEADERS, timeout=10)
    r.raise_for_status()
    return r.json()


@mcp.tool(
    description="Get a Markdown-formatted handoff text for pasting into a new AI window. "
    "Use this when switching to a different model or starting a fresh conversation."
)
def get_handoff(slot_name: str) -> dict:
    """Return handoff Markdown text for a slot."""
    with httpx.Client() as client:
        r = client.get(f"{BASE_URL}/v1/context/{slot_name}/handoff", headers=_HEADERS, timeout=10)
    r.raise_for_status()
    return r.json()


if __name__ == "__main__":
    mcp.run()
