from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_agent_connection_code_uses_official_saas_path_by_default():
    server = read("mcp/server.py")
    config = read("services/config.py")
    context_router = read("routers/context.py")

    assert '"https://a2cr.app"' in server
    assert "A2CR_ALLOW_LOCAL_BASE_URL" in server
    assert "refuses localhost A2CR_BASE_URL by default" in server
    assert "A2CR_ENABLE_LEGACY_LOCAL_API" in config
    assert "legacy_local_api_disabled" in context_router


def test_public_agent_docs_prefer_slot_first_stdio_path():
    docs = {
        "README.md": read("README.md"),
        "web/public/llms.txt": read("web/public/llms.txt"),
        "docs/templates/skills/a2cr-agent/SKILL.md": read("docs/templates/skills/a2cr-agent/SKILL.md"),
        "docs/usage.md": read("docs/usage.md"),
    }

    for content in docs.values():
        assert "local stdio" in content

    for path in ("README.md", "docs/templates/skills/a2cr-agent/SKILL.md", "docs/usage.md"):
        assert "A2CR_API_STYLE" in docs[path]

    assert "Official AI-agent setup is the local stdio MCP wrapper named a2cr" in docs["web/public/llms.txt"]
    assert "Use `list_contexts` only when no Slot is provided" in docs[
        "docs/templates/skills/a2cr-agent/SKILL.md"
    ]
    assert "Do not configure the hosted `/mcp` URL directly for WorkBaton" in docs[
        "docs/templates/skills/a2cr-agent/SKILL.md"
    ]
    assert "The legacy local SQLite WorkBaton API is disabled by default" in docs["README.md"]
    assert "A2CR_BASE_URL\": \"https://a2cr.app" in docs["docs/usage.md"]
    assert '"A2CR_API_STYLE": "legacy"' not in docs["docs/usage.md"]


def test_legacy_local_mcp_entrypoint_is_removed():
    assert not (ROOT / "run_mcp_server.py").exists()
