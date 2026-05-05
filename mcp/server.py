"""
MCP server wrapping the A2CR HTTP API.

Registration (Claude Code):
  Add to ~/.claude/mcp.json:
  {
    "mcpServers": {
      "a2cr": {
        "command": "python",
        "args": ["<project-root>/mcp/server.py"],
        "env": { "A2CR_API_KEY": "<your-api-key>" }
      }
    }
  }
"""
import os
import httpx
from fastmcp import FastMCP

BASE_URL = os.environ.get(
    "A2CR_BASE_URL",
    os.environ.get("AI_CLIPBOARD_BASE_URL", "http://localhost:8000"),
)
SERVICE_URL = os.environ.get(
    "A2CR_SERVICE_URL",
    os.environ.get("AI_CLIPBOARD_SERVICE_URL", BASE_URL),
)
API_KEY = os.environ.get("A2CR_API_KEY", os.environ.get("AI_CLIPBOARD_API_KEY", ""))

mcp = FastMCP("A2CR")

_HEADERS = {"X-API-Key": API_KEY}


def _resume_context_call(slot_name: str, slot_number: int | None = None) -> str:
    return f'resume_context(slot_name="{slot_name}")'


def _resume_prompt(slot_name: str, slot_number: int | None = None) -> str:
    slot_number_hint = (
        f"Slot番号対応済みなら resume_context(slot_number={slot_number}) "
        "でも読み込めます。\n"
        if slot_number is not None
        else ""
    )
    return (
        f"A2CR service: {SERVICE_URL}\n"
        "A2CR MCPツールを使ってください。HTTP APIを直接推測して呼び出さないでください。\n"
        f"まず {_resume_context_call(slot_name, slot_number)} "
        "を実行して、A2CRから引き継ぎ文脈を読み込んでください。\n"
        f"{slot_number_hint}"
        "読み込み後は、作業に必要なプロジェクトファイルを通常通り参照して構いません。\n"
        "回答はこのメッセージの言語に合わせてください。"
    )


def _load_slot(client: httpx.Client, slot_name: str) -> dict:
    r = client.get(f"{BASE_URL}/v1/context/{slot_name}", headers=_HEADERS, timeout=10)
    if r.status_code == 404:
        return {"status": "not_found", "slot_name": slot_name}
    r.raise_for_status()
    data = r.json()
    data["status"] = "loaded"
    data["response_language_hint"] = "current_message_language"
    return data


def _load_slot_number(client: httpx.Client, slot_number: int) -> dict:
    r = client.get(f"{BASE_URL}/v1/context/slot/{slot_number}", headers=_HEADERS, timeout=10)
    if r.status_code == 404:
        return {"status": "not_found", "slot_number": slot_number}
    r.raise_for_status()
    data = r.json()
    data["status"] = "loaded"
    data["response_language_hint"] = "current_message_language"
    return data

SAVE_DESCRIPTION = """Save conversation context to A2CR.

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

Storage language:
  Write content in concise English by default, even if the conversation is in
  another language. Preserve code, commands, file paths, URLs, env vars, error
  messages, logs, API responses, product names, and short exact user quotes when
  the original wording matters.

Response language:
  After load_context, answer in the language used immediately before the load.
  Do not assume only English or Japanese; support the user's active language.

After saving:
  The tool returns a resume_prompt. Show it in the current conversation so the
  user can paste it into a new AI window later.

Fixed Slot numbers:
  If the user asks to save to Slot 1, Slot 2, or Slot 3, pass slot_number with
  the matching integer. Use the slot_name provided by the dashboard's Slot map
  when available.

Slot naming: {project}-{purpose}  e.g. "my-app-main", "my-app-debug"
"""


@mcp.tool(description=SAVE_DESCRIPTION)
def save_context(
    slot_name: str,
    content: dict,
    original_length: int | None = None,
    model_source: str | None = None,
    slot_number: int | None = None,
) -> dict:
    """Save context to a named slot. Optionally overwrite a fixed Slot number."""
    with httpx.Client() as client:
        r = client.post(
            f"{BASE_URL}/v1/context/save",
            json={
                "slot_name": slot_name,
                "slot_number": slot_number,
                "content": content,
                "original_length": original_length,
                "model_source": model_source,
            },
            headers=_HEADERS,
            timeout=10,
        )
    r.raise_for_status()
    result = r.json()
    saved_slot_number = result.get("slot_number")
    result.setdefault("resume_context_call", _resume_context_call(slot_name, saved_slot_number))
    result.setdefault("resume_prompt", _resume_prompt(slot_name, saved_slot_number))
    return result


@mcp.tool(
    description=(
        "Resume work from A2CR. If slot_number or slot_name is "
        "provided, load that slot directly. If multiple candidates are found, "
        "return metadata only unless prefer_latest is true. After loading, "
        "answer in the user's active language."
    )
)
def resume_context(
    slot_name: str | None = None,
    slot_number: int | None = None,
    project: str | None = None,
    prefer_latest: bool = False,
) -> dict:
    """Find and load the right context for a new AI window."""
    with httpx.Client() as client:
        if slot_number is not None:
            return _load_slot_number(client, slot_number)
        if slot_name:
            return _load_slot(client, slot_name)

        r = client.get(f"{BASE_URL}/v1/context/list", headers=_HEADERS, timeout=10)
        r.raise_for_status()
        candidates = r.json()

        if project:
            prefix = f"{project}-"
            candidates = [
                item for item in candidates
                if item["slot_name"] == project or item["slot_name"].startswith(prefix)
            ]

        if not candidates:
            return {"status": "not_found" if project else "no_active_context"}

        candidates = sorted(candidates, key=lambda item: item["updated_at"], reverse=True)
        if len(candidates) == 1 or prefer_latest:
            return _load_slot(client, candidates[0]["slot_name"])

        return {"status": "candidates", "candidates": candidates}


@mcp.tool(
    description=(
        "Load context from a fixed Slot number or named slot. Returns "
        "structured JSON ready to use. After loading, answer the user in the "
        "language used immediately before the load, not necessarily the storage "
        "language. Support any active conversation language, not only English "
        "or Japanese."
    )
)
def load_context(slot_name: str | None = None, slot_number: int | None = None) -> dict:
    """Retrieve saved context by slot number or slot name."""
    if slot_number is None and not slot_name:
        return {
            "status": "validation_error",
            "message": "slot_number or slot_name is required",
        }
    with httpx.Client() as client:
        if slot_number is not None:
            r = client.get(f"{BASE_URL}/v1/context/slot/{slot_number}", headers=_HEADERS, timeout=10)
        else:
            r = client.get(f"{BASE_URL}/v1/context/{slot_name}", headers=_HEADERS, timeout=10)
    if r.status_code == 404:
        return {"status": "not_found", "slot_name": slot_name, "slot_number": slot_number}
    r.raise_for_status()
    data = r.json()
    data["status"] = "loaded"
    return data


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
