from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_agent_connection_code_uses_official_saas_path_by_default():
    server = read("a2cr_mcp/server.py")

    assert '"https://a2cr.app"' in server
    assert "A2CR_ALLOW_LOCAL_BASE_URL" in server
    assert "refuses localhost A2CR_BASE_URL by default" in server


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

    assert "Official AI-agent setup is the PyPI package a2cr-mcp" in docs["web/public/llms.txt"]
    assert 'command = "a2cr-mcp"' in docs["web/public/llms.txt"]
    assert "python -m pip install --upgrade a2cr-mcp" in docs["docs/usage.md"]
    assert "Use `list_contexts` only when no Slot is provided" in docs[
        "docs/templates/skills/a2cr-agent/SKILL.md"
    ]
    assert "Do not configure the hosted `/mcp` URL directly for WorkBaton" in docs[
        "docs/templates/skills/a2cr-agent/SKILL.md"
    ]
    assert "WorkStash temporary work memory" in docs["docs/templates/skills/a2cr-agent/SKILL.md"]
    assert "WorkStash is temporary work memory" in docs["docs/usage.md"]
    assert "The full API key is shown only once" in docs["README.md"]
    assert "To resume the same WorkBaton from another PC" in docs["README.md"]
    assert "%APPDATA%\\A2CR\\workbaton.key" in docs["README.md"]
    assert "The full API key is shown only once" in docs["docs/usage.md"]
    assert "To resume the same WorkBaton from another PC" in docs["docs/usage.md"]
    assert "%APPDATA%\\A2CR\\workbaton.key" in docs["docs/usage.md"]
    assert "`store_work_stash`" in docs["docs/usage.md"]
    assert "Good WorkStash entries" in docs["docs/usage.md"]
    assert "Bad WorkStash entries" in docs["docs/usage.md"]
    assert "Context Freshness" in docs["docs/usage.md"]
    assert "Good WorkStash entries" in docs["docs/templates/skills/a2cr-agent/SKILL.md"]
    assert "Keep Context Fresh" in docs["docs/templates/skills/a2cr-agent/SKILL.md"]
    assert "Routine saves should report `user_facing_summary`" in docs["docs/templates/skills/a2cr-agent/SKILL.md"]
    assert "not number of notes: Free gets 256KB total" in docs["docs/usage.md"]
    assert "Pro gets 2048KB total" in docs["docs/usage.md"]
    assert "not number of notes: Free has 256KB total" in docs["docs/templates/skills/a2cr-agent/SKILL.md"]
    assert "Pro has 2048KB total" in docs["docs/templates/skills/a2cr-agent/SKILL.md"]
    assert "The legacy local SQLite WorkBaton API is disabled by default" in docs["README.md"]
    assert "Supabase/Postgres for the data layer and Railway" in docs["README.md"]
    assert "least-privileged `a2cr_app` runtime role" in docs["README.md"]
    assert "MCP / A2A / A2CR Positioning" in docs["README.md"]
    assert "A2CR is complementary to MCP and A2A" in docs["README.md"]
    assert "A2CR_BASE_URL\": \"https://a2cr.app" in docs["docs/usage.md"]
    assert '"A2CR_API_STYLE": "legacy"' not in docs["docs/usage.md"]


def test_public_launch_docs_match_free_preview_and_later_billing_direction():
    docs = {
        "README.md": read("README.md"),
        "docs/github-publication-draft.md": read("docs/github-publication-draft.md"),
        "docs/runbooks/saas-launch-roadmap.md": read("docs/runbooks/saas-launch-roadmap.md"),
        "docs/a2cr-service-cost-estimate.md": read("docs/a2cr-service-cost-estimate.md"),
        "docs/superpowers/specs/2026-05-06-a2cr-operations-legal-admin-spec.md": read(
            "docs/superpowers/specs/2026-05-06-a2cr-operations-legal-admin-spec.md"
        ),
    }

    assert "Free public preview for WorkBaton and WorkStash" in docs["README.md"]
    assert "WorkBaton and WorkStash are the first public free preview scope" in docs[
        "docs/github-publication-draft.md"
    ]
    assert "official MCP listing/application" in docs["docs/runbooks/saas-launch-roadmap.md"]
    assert "Set the first Pro list price to $8/month" in docs["docs/a2cr-service-cost-estimate.md"]
    assert "Merchant of Record fees" in docs["docs/runbooks/saas-launch-roadmap.md"]
    assert "outsourcing tax/VAT and payment compliance" in docs["docs/a2cr-service-cost-estimate.md"]
    assert "Virtual office/business address" in docs["docs/a2cr-service-cost-estimate.md"]
    assert "Business Address / Virtual Office Planning" in docs[
        "docs/superpowers/specs/2026-05-06-a2cr-operations-legal-admin-spec.md"
    ]
    assert "personal home address" in docs["docs/github-publication-draft.md"]

    for content in docs.values():
        assert "Lemon Squeezy" in content
        assert "Stripe" not in content
        assert "$5 / month" not in content


def test_legacy_local_mcp_entrypoint_is_removed():
    assert not (ROOT / "run_mcp_server.py").exists()
