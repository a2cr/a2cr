import pytest
from fastapi.testclient import TestClient
from main import app

HEADERS = {"X-API-Key": "test-api-key-1234567890abcdef"}
CONTENT = {
    "goal": "test goal",
    "current_state": "testing",
    "next_action": "assert",
}


def encrypted(label: str = "ciphertext") -> dict:
    return {
        "version": 1,
        "alg": "Fernet",
        "nonce": "embedded",
        "ciphertext": label,
        "key_wrap": {"type": "local-key", "kid": "test"},
    }


def save_body(slot_name: str, slot_number: int | None = None, payload: dict | None = None) -> dict:
    body = {"slot_name": slot_name, "encrypted_content": payload or encrypted(slot_name)}
    if slot_number is not None:
        body["slot_number"] = slot_number
    return body


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_api_health_alias(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_save_returns_201(client, monkeypatch):
    monkeypatch.setenv("A2CR_SERVICE_URL", "https://example.test/mcp")
    r = client.post("/v1/context/save", json=save_body("test-slot"), headers=HEADERS)
    assert r.status_code == 201
    body = r.json()
    assert body["slot_name"] == "test-slot"
    assert body["slot_number"] == 1
    assert "expires_at" in body
    assert body["compressed_tokens"] > 0
    assert body["resume_context_call"] == 'resume_context(slot_name="test-slot")'
    assert "A2CR service: https://example.test/mcp" in body["resume_prompt"]
    assert 'resume_context(slot_name="test-slot")' in body["resume_prompt"]
    assert "resume_context(slot_number=1)" in body["resume_prompt"]
    assert "HTTP API" in body["resume_prompt"]
    assert "Do not read local files" not in body["resume_prompt"]
    assert "\u30ed\u30fc\u30ab\u30eb\u30d5\u30a1\u30a4\u30eb" not in body["resume_prompt"]
    assert "\u30d7\u30ed\u30b8\u30a7\u30af\u30c8\u30d5\u30a1\u30a4\u30eb" in body["resume_prompt"]


def test_save_accepts_fixed_slot_number(client):
    r = client.post(
        "/v1/context/save",
        json=save_body("fixed-slot", slot_number=3),
        headers=HEADERS,
    )
    assert r.status_code == 201
    assert r.json()["slot_number"] == 3


def test_save_rejects_invalid_slot_number(client):
    r = client.post(
        "/v1/context/save",
        json=save_body("bad-slot", slot_number=4),
        headers=HEADERS,
    )
    assert r.status_code == 422


def test_save_no_api_key_returns_401(client):
    r = client.post("/v1/context/save", json=save_body("s"))
    assert r.status_code == 401


def test_save_wrong_api_key_returns_401(client):
    r = client.post(
        "/v1/context/save",
        json=save_body("s"),
        headers={"X-API-Key": "wrong-key"},
    )
    assert r.status_code == 401


def test_save_slot_limit_returns_400(client):
    for i in range(3):
        client.post("/v1/context/save", json=save_body(f"slot-{i}"), headers=HEADERS)
    r = client.post("/v1/context/save", json=save_body("slot-overflow"), headers=HEADERS)
    assert r.status_code == 400
    assert r.json()["code"] == "slot_limit_exceeded"


@pytest.mark.parametrize(
    "slot_name",
    [
        "invalid name!",
        "<script>alert('x')</script>",
        "=HYPERLINK",
        "+SUM",
        "-cmd",
        "@HYPERLINK",
    ],
)
def test_save_invalid_slot_name_returns_422(client, slot_name):
    r = client.post(
        "/v1/context/save",
        json=save_body(slot_name),
        headers=HEADERS,
    )
    assert r.status_code == 422
    assert slot_name not in r.text
    assert "<script>" not in r.text
    assert "HYPERLINK" not in r.text


def test_load_existing(client):
    payload = encrypted("load-test")
    client.post("/v1/context/save", json=save_body("load-test", payload=payload), headers=HEADERS)
    r = client.get("/v1/context/load-test", headers=HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert body["content"] is None
    assert body["encrypted_content"] == payload
    assert body["encryption_mode"] == "client"
    assert body["slot_number"] == 1
    assert body["load_count"] == 1


def test_save_load_client_encrypted_context(client):
    encrypted_content = {
        "version": 1,
        "alg": "XChaCha20-Poly1305",
        "nonce": "nonce",
        "ciphertext": "ciphertext",
        "key_wrap": {"type": "local-key", "kid": "test"},
    }
    r = client.post(
        "/v1/context/save",
        json={"slot_name": "encrypted-api", "encrypted_content": encrypted_content},
        headers=HEADERS,
    )
    assert r.status_code == 201

    loaded = client.get("/v1/context/encrypted-api", headers=HEADERS)
    assert loaded.status_code == 200
    body = loaded.json()
    assert body["encryption_mode"] == "client"
    assert body["content"] is None
    assert body["encrypted_content"] == encrypted_content


def test_save_rejects_content_and_encrypted_content_together(client):
    r = client.post(
        "/v1/context/save",
        json={
            "slot_name": "bad-body",
            "content": CONTENT,
            "encrypted_content": {
                "version": 1,
                "alg": "XChaCha20-Poly1305",
                "nonce": "nonce",
                "ciphertext": "ciphertext",
            },
        },
        headers=HEADERS,
    )
    assert r.status_code == 422


def test_save_rejects_plaintext_content(client):
    r = client.post(
        "/v1/context/save",
        json={"slot_name": "plaintext-body", "content": CONTENT},
        headers=HEADERS,
    )
    assert r.status_code == 422


def test_load_by_slot_number(client):
    client.post(
        "/v1/context/save",
        json=save_body("number-load", slot_number=2, payload=encrypted("number-load")),
        headers=HEADERS,
    )
    r = client.get("/v1/context/slot/2", headers=HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert body["slot_name"] == "number-load"
    assert body["slot_number"] == 2
    assert body["content"] is None
    assert body["encrypted_content"]["ciphertext"] == "number-load"


def test_load_not_found_returns_404(client):
    r = client.get("/v1/context/no-such-slot", headers=HEADERS)
    assert r.status_code == 404
    assert r.json()["code"] == "slot_not_found"


def test_list_returns_slots(client):
    client.post("/v1/context/save", json=save_body("list-slot-a", slot_number=2), headers=HEADERS)
    client.post("/v1/context/save", json=save_body("list-slot-b", slot_number=1), headers=HEADERS)
    r = client.get("/v1/context/list", headers=HEADERS)
    assert r.status_code == 200
    names = [s["slot_name"] for s in r.json()]
    assert "list-slot-a" in names
    assert "list-slot-b" in names
    assert [s["slot_number"] for s in r.json()] == [1, 2]


def test_list_does_not_conflict_with_load(client):
    # "list" is a static path that must not be matched as slot_name
    r = client.get("/v1/context/list", headers=HEADERS)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_delete_removes_slot(client):
    client.post("/v1/context/save", json=save_body("del-slot"), headers=HEADERS)
    r = client.delete("/v1/context/del-slot", headers=HEADERS)
    assert r.status_code == 200
    assert r.json() == {"message": "deleted"}
    r2 = client.get("/v1/context/del-slot", headers=HEADERS)
    assert r2.status_code == 404


def test_delete_not_found_returns_404(client):
    r = client.delete("/v1/context/ghost", headers=HEADERS)
    assert r.status_code == 404
    assert r.json()["code"] == "slot_not_found"


def test_handoff_requires_client_decryption(client):
    client.post("/v1/context/save", json=save_body("handoff-slot"), headers=HEADERS)
    r = client.get("/v1/context/handoff-slot/handoff", headers=HEADERS)
    assert r.status_code == 422
    assert r.json()["code"] == "client_decryption_required"


def test_handoff_not_found_returns_404(client):
    r = client.get("/v1/context/ghost/handoff", headers=HEADERS)
    assert r.status_code == 404
