from fastapi.testclient import TestClient

from main import app


def test_spa_does_not_serve_dotfiles():
    with TestClient(app) as client:
        for path in ("/.env", "/.env.local", "/.git/config"):
            response = client.get(path)

            assert response.status_code == 404


def test_public_guide_serves_static_ai_readable_html():
    with TestClient(app) as client:
        response = client.get("/guide")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "JavaScriptなしで読めます" in response.text
    assert "https://a2cr.app/mcp" in response.text
    assert "save_context" in response.text
