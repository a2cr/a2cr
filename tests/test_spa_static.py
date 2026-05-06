from fastapi.testclient import TestClient

from main import app


def test_public_home_serves_indexable_spa_html():
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert '<meta name="robots" content="index, follow"' in response.text
    assert '<link rel="canonical" href="https://a2cr.app/"' in response.text
    assert "Agent-to-Agent Context Relay" in response.text
    assert '<div id="root"></div>' in response.text
    assert '<noscript id="a2cr-static-description">' in response.text


def test_public_pricing_serves_indexable_spa_html():
    with TestClient(app) as client:
        response = client.get("/pricing")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert '<meta name="robots" content="index, follow"' in response.text
    assert '<link rel="canonical" href="https://a2cr.app/pricing"' in response.text
    assert "A2CR Pricing" in response.text
    assert '<div id="root"></div>' in response.text
    assert '<noscript id="a2cr-static-description">' in response.text


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
    assert '<link rel="canonical" href="https://a2cr.app/guide"' in response.text
    assert '<link rel="alternate" hreflang="en" href="https://a2cr.app/en/guide"' in response.text
    assert '<script type="text/plain" id="a2cr-machine-readable">' in response.text
    assert '<noscript id="a2cr-static-description">' in response.text
    assert "https://a2cr.app/mcp" in response.text
    assert "save_context" in response.text
    assert '<div id="root"></div>' in response.text


def test_public_english_guide_serves_static_ai_readable_html():
    with TestClient(app) as client:
        response = client.get("/en/guide")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert '<link rel="canonical" href="https://a2cr.app/en/guide"' in response.text
    assert '<link rel="alternate" hreflang="ja" href="https://a2cr.app/guide"' in response.text
    assert "A2CR setup guide" in response.text
    assert '<script type="text/plain" id="a2cr-machine-readable">' in response.text
    assert '<noscript id="a2cr-static-description">' in response.text
    assert "https://a2cr.app/mcp" in response.text
    assert "save_context" in response.text
    assert '<div id="root"></div>' in response.text


def test_public_seo_support_files_are_served():
    with TestClient(app) as client:
        robots = client.get("/robots.txt")
        sitemap = client.get("/sitemap.xml")
        llms = client.get("/llms.txt")

    assert robots.status_code == 200
    assert "Sitemap: https://a2cr.app/sitemap.xml" in robots.text
    assert sitemap.status_code == 200
    assert "<loc>https://a2cr.app/guide</loc>" in sitemap.text
    assert "<loc>https://a2cr.app/en/guide</loc>" in sitemap.text
    assert llms.status_code == 200
    assert "Public guide (English): https://a2cr.app/en/guide" in llms.text
    assert "MCP endpoint: https://a2cr.app/mcp" in llms.text
