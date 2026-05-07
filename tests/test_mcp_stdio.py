import importlib.util
from pathlib import Path


CONTENT = {
    "goal": "client encrypt",
    "current_state": "roundtrip",
    "next_action": "assert",
}


def load_stdio_server():
    path = Path(__file__).resolve().parents[1] / "mcp" / "server.py"
    spec = importlib.util.spec_from_file_location("a2cr_stdio_mcp_server", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_mcp_stdio_client_encryption_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("A2CR_CLIENT_KEY_FILE", str(tmp_path / "workbaton.key"))
    server = load_stdio_server()

    encrypted = server._encrypt_content(CONTENT)
    loaded = server._decrypt_loaded_context(
        {
            "status": "loaded",
            "encryption_mode": "client",
            "content": None,
            "encrypted_content": encrypted,
        }
    )

    assert encrypted["ciphertext"] != CONTENT["goal"]
    assert loaded["status"] == "loaded"
    assert loaded["content"] == CONTENT
    assert loaded["encrypted_content"] is None


def test_mcp_stdio_client_encrypted_load_reports_missing_key(tmp_path, monkeypatch):
    monkeypatch.setenv("A2CR_CLIENT_KEY_FILE", str(tmp_path / "missing.key"))
    server = load_stdio_server()

    loaded = server._decrypt_loaded_context(
        {
            "status": "loaded",
            "encryption_mode": "client",
            "content": None,
            "encrypted_content": {
                "version": 1,
                "alg": "Fernet",
                "nonce": "embedded",
                "ciphertext": "not-a-real-token",
            },
        }
    )

    assert loaded["status"] == "key_unavailable"
    assert loaded["content"] is None
    assert "key file is missing" in loaded["message"]


def test_mcp_stdio_save_posts_encrypted_content(tmp_path, monkeypatch):
    monkeypatch.setenv("A2CR_CLIENT_KEY_FILE", str(tmp_path / "workbaton.key"))
    server = load_stdio_server()
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "slot_name": "slot-a",
                "slot_number": 1,
                "expires_at": "2026-05-06T00:00:00",
                "compressed_tokens": 10,
                "saved_tokens": None,
            }

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, json, headers, timeout):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            return FakeResponse()

    monkeypatch.setattr(server.httpx, "Client", FakeClient)

    result = server.save_context("slot-a", CONTENT, model_source="codex")

    assert result["slot_name"] == "slot-a"
    assert captured["url"].endswith("/api/v1/context")
    assert "Authorization" in captured["headers"]
    assert captured["json"]["detail_level"] == "compact"
    assert "content" not in captured["json"]
    assert captured["json"]["encrypted_content"]["alg"] == "Fernet"
    assert CONTENT["goal"] not in captured["json"]["encrypted_content"]["ciphertext"]


def test_mcp_stdio_get_account_limits_uses_api_key_route():
    server = load_stdio_server()
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "plan": "free",
                "allowed_detail_levels": ["compact"],
                "max_body_bytes": 32768,
            }

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, url, headers, timeout):
            captured["url"] = url
            captured["headers"] = headers
            captured["timeout"] = timeout
            return FakeResponse()

    server.httpx.Client = FakeClient

    result = server.get_account_limits()

    assert captured["url"].endswith("/api/v1/account/limits")
    assert "Authorization" in captured["headers"]
    assert result["plan"] == "free"
    assert result["allowed_detail_levels"] == ["compact"]


def test_mcp_stdio_and_agent_guide_document_chained_handoff_fields():
    server = load_stdio_server()
    skill = (Path(__file__).resolve().parents[1] / "docs/templates/skills/a2cr-agent/SKILL.md").read_text(
        encoding="utf-8"
    )
    fields = [
        "previous_slot",
        "supersedes_slots",
        "latest_slot_hint",
        "completed_since_previous",
        "remaining_tasks_ordered",
        "validation",
        "workspace_status",
        "do_not_use_slots",
        "Free/compact saves",
    ]

    for field in fields:
        assert field in server.SAVE_DESCRIPTION
        assert field in skill


def test_mcp_stdio_and_agent_guide_document_free_pro_forbidden_material():
    server = load_stdio_server()
    skill = (Path(__file__).resolve().parents[1] / "docs/templates/skills/a2cr-agent/SKILL.md").read_text(
        encoding="utf-8"
    )
    forbidden_terms = [
        "Forbidden for both Free and Pro",
        "local client key",
        "API keys",
        "Authorization headers",
        "private database URLs",
        "customer data",
        "personal data",
        "full transcripts",
        "long logs",
        "git diffs",
        "Pro allows more safe handoff context, not more sensitive data",
    ]

    for term in forbidden_terms:
        assert term in server.SAVE_DESCRIPTION
        assert term in skill
