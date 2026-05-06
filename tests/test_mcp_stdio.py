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
            captured["json"] = json
            return FakeResponse()

    monkeypatch.setattr(server.httpx, "Client", FakeClient)

    result = server.save_context("slot-a", CONTENT, model_source="codex")

    assert result["slot_name"] == "slot-a"
    assert "content" not in captured["json"]
    assert captured["json"]["encrypted_content"]["alg"] == "Fernet"
    assert CONTENT["goal"] not in captured["json"]["encrypted_content"]["ciphertext"]
