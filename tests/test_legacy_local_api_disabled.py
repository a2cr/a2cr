from fastapi.testclient import TestClient

from main import app


def test_legacy_local_context_api_is_disabled_without_explicit_opt_in(monkeypatch):
    monkeypatch.delenv("A2CR_ENABLE_LEGACY_LOCAL_API", raising=False)

    with TestClient(app) as client:
        response = client.post(
            "/v1/context/save",
            json={
                "slot_name": "local-disabled",
                "encrypted_content": {
                    "version": 1,
                    "alg": "Fernet",
                    "nonce": "embedded",
                    "ciphertext": "ciphertext",
                },
            },
            headers={"X-API-Key": "test-api-key-1234567890abcdef"},
        )

    assert response.status_code == 410
    assert response.json()["code"] == "legacy_local_api_disabled"
