from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from main import app
from routers.web_context import get_current_api_user
from services.auth import AuthenticatedUser
from services.web_context import (
    WebContextMetadata,
    WebLoadResult,
    WebResumeResult,
    WebSaveResult,
)
import services.web_context as web_context_service


USER_ID = UUID("00000000-0000-0000-0000-0000000000a1")
CONTENT = {
    "goal": "ship web context api",
    "current_state": "testing route",
    "next_action": "assert response",
}


def encrypted(label: str = "ciphertext") -> dict:
    return {
        "version": 1,
        "alg": "Fernet",
        "nonce": "embedded",
        "ciphertext": label,
        "key_wrap": {"type": "local-key", "kid": "test"},
    }


@pytest.fixture
def client():
    app.dependency_overrides[get_current_api_user] = lambda: AuthenticatedUser(USER_ID, "api_key")
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def future_time():
    return datetime.now(timezone.utc) + timedelta(hours=1)


def metadata(slot_name="slot-a", slot_number=1):
    return WebContextMetadata(
        slot_name=slot_name,
        slot_number=slot_number,
        expires_at=future_time(),
        updated_at=future_time(),
        size_bytes=120,
        compressed_tokens=12,
        detail_level="compact",
        model_source="gpt",
        load_count=0,
    )


def load_result(slot_name="slot-a", slot_number=1):
    return WebLoadResult(
        slot_name=slot_name,
        slot_number=slot_number,
        content=None,
        expires_at=future_time(),
        compressed_tokens=12,
        detail_level="compact",
        model_source="gpt",
        load_count=1,
        encrypted_content=encrypted(slot_name),
    )


def test_web_save_context_returns_resume_prompt_without_content_or_key(client, monkeypatch):
    captured = {}

    def fake_save_context(**kwargs):
        captured.update(kwargs)
        return WebSaveResult(
            slot_name=kwargs["slot_name"],
            slot_number=kwargs["slot_number"],
            expires_at=future_time(),
            compressed_tokens=12,
            saved_tokens=8,
            resume_context_call='resume_context(slot_name="slot-a")',
            resume_prompt=(
                "A2CR service: https://a2cr.example\n"
                "Use the A2CR MCP tool. Do not guess or call direct HTTP API endpoints.\n"
                'First run: resume_context(slot_name="slot-a")'
            ),
        )

    monkeypatch.setattr(web_context_service, "save_context", fake_save_context)

    response = client.post(
        "/api/v1/context",
        json={
            "slot_name": "slot-a",
            "slot_number": 1,
            "encrypted_content": encrypted("slot-a"),
            "model_source": "codex",
            "retention_seconds": 86400,
            "detail_level": "compact",
        },
        headers={"Authorization": "Bearer sk-test-secret", "X-A2CR-Client-Type": "mcp"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["slot_name"] == "slot-a"
    assert body["resume_context_call"] == 'resume_context(slot_name="slot-a")'
    assert "A2CR MCP tool" in body["resume_prompt"]
    assert "direct HTTP API" in body["resume_prompt"]
    assert "ship web context api" not in body["resume_prompt"]
    assert "sk-test-secret" not in body["resume_prompt"]
    assert captured["user_id"] == USER_ID
    assert captured["content_dict"] is None
    assert captured["encrypted_content"]["ciphertext"] == "slot-a"
    assert captured["model_source"] == "codex"
    assert captured["retention_seconds"] == 86400
    assert captured["detail_level"] == "compact"
    assert captured["meta"].client_type == "mcp"


def test_web_list_contexts_returns_metadata_without_content(client, monkeypatch):
    monkeypatch.setattr(web_context_service, "list_contexts", lambda **_: [metadata()])

    response = client.get("/api/v1/contexts", headers={"Authorization": "Bearer sk-test-secret"})

    assert response.status_code == 200
    body = response.json()
    assert body[0]["slot_name"] == "slot-a"
    assert "content" not in body[0]


def test_web_load_context_returns_ciphertext_for_api_key_route(client, monkeypatch):
    monkeypatch.setattr(web_context_service, "load_context", lambda **_: load_result())

    response = client.get("/api/v1/context/slot-a", headers={"Authorization": "Bearer sk-test-secret"})

    assert response.status_code == 200
    body = response.json()
    assert body["content"] is None
    assert body["encrypted_content"]["ciphertext"] == "slot-a"
    assert body["load_count"] == 1


def test_web_resume_context_returns_candidates_without_loading_content(client, monkeypatch):
    monkeypatch.setattr(
        web_context_service,
        "resume_context",
        lambda **_: WebResumeResult(mode="candidates", candidates=[metadata("proj-a", 1), metadata("proj-b", 2)]),
    )

    response = client.get(
        "/api/v1/context/resume?project=proj",
        headers={"Authorization": "Bearer sk-test-secret"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "candidates"
    assert body["context"] is None
    assert len(body["candidates"]) == 2
    assert "content" not in body["candidates"][0]


def test_web_resume_context_loads_exact_slot(client, monkeypatch):
    monkeypatch.setattr(
        web_context_service,
        "resume_context",
        lambda **_: WebResumeResult(mode="loaded", context=load_result("slot-a", 1)),
    )

    response = client.get(
        "/api/v1/context/resume?slot_name=slot-a",
        headers={"Authorization": "Bearer sk-test-secret"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "loaded"
    assert body["context"]["content"] is None
    assert body["context"]["encrypted_content"]["ciphertext"] == "slot-a"
    assert body["candidates"] == []


def test_web_delete_context_returns_deleted(client, monkeypatch):
    captured = {}

    def fake_delete_context(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(web_context_service, "delete_context", fake_delete_context)

    response = client.delete("/api/v1/context/slot-a", headers={"Authorization": "Bearer sk-test-secret"})

    assert response.status_code == 200
    assert response.json() == {"message": "deleted"}
    assert captured["slot_name"] == "slot-a"
    assert captured["user_id"] == USER_ID
