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


def test_public_human_guide_serves_static_html():
    with TestClient(app) as client:
        response = client.get("/guide")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert '<link rel="canonical" href="https://a2cr.app/guide"' in response.text
    assert '<link rel="alternate" hreflang="en" href="https://a2cr.app/en/guide"' in response.text
    assert '<noscript id="a2cr-static-description">' in response.text
    assert "A2CR ガイド" in response.text
    assert "読むより、AIに読ませる" in response.text
    assert "このアプリを説明して" in response.text
    assert "https://a2cr.app/mcp" in response.text
    assert "local client keyは利用者側が管理します" in response.text
    assert "client-encrypted" in response.text
    assert "WorkBatonはclient-encryptedのみです" in response.text
    assert "A2CRはWorkBaton本文の平文保存を受け付けません" in response.text
    assert "圧縮・要約機能との違い" in response.text
    assert "会話ログのダイエット" in response.text
    assert "サブエージェントとの違い" in response.text
    assert "環境をまたいで引き継ぐ" in response.text
    assert "AIエージェント向けガイド: https://a2cr.app/agent-guide" in response.text
    assert '<div id="root"></div>' in response.text


def test_public_english_human_guide_serves_static_html():
    with TestClient(app) as client:
        response = client.get("/en/guide")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert '<link rel="canonical" href="https://a2cr.app/en/guide"' in response.text
    assert '<link rel="alternate" hreflang="ja" href="https://a2cr.app/guide"' in response.text
    assert '<noscript id="a2cr-static-description">' in response.text
    assert "A2CR Guide" in response.text
    assert "Let your AI read it" in response.text
    assert "ask it to explain A2CR" in response.text
    assert "A2CR is not an AI" in response.text
    assert "local client key is managed by the user" in response.text
    assert "client-encrypted" in response.text
    assert "WorkBaton is client-encrypted only" in response.text
    assert "A2CR does not accept plaintext WorkBaton bodies" in response.text
    assert "Compression / summarization vs A2CR / WorkBaton" in response.text
    assert "diet for a conversation log" in response.text
    assert "Sub-agents vs A2CR" in response.text
    assert "carries the environment itself forward" in response.text
    assert "AI agent guide: https://a2cr.app/en/agent-guide" in response.text
    assert '<div id="root"></div>' in response.text


def test_public_agent_guide_serves_static_html():
    with TestClient(app) as client:
        response = client.get("/en/agent-guide")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert '<link rel="canonical" href="https://a2cr.app/en/agent-guide"' in response.text
    assert '<link rel="alternate" hreflang="ja" href="https://a2cr.app/agent-guide"' in response.text
    assert '<noscript id="a2cr-static-description">' in response.text
    assert "A2CR AI Agent Guide" in response.text
    assert "Do not guess direct HTTP API calls" in response.text
    assert "PyPI package a2cr-mcp registered as one local stdio MCP server named a2cr" in response.text
    assert "first call resume_context(slot_name=" in response.text
    assert "Use list_contexts only when no Slot is provided" in response.text
    assert "Never save secrets" in response.text
    assert "Use WorkBaton and WorkStash proactively" in response.text
    assert "context_contamination" in response.text
    assert "suggest continuing in a fresh AI window" in response.text
    assert "The local client key is managed by the user" in response.text
    assert "old client-encrypted slots cannot be recovered" in response.text
    assert '<div id="root"></div>' in response.text


def test_public_manual_serves_static_html():
    with TestClient(app) as client:
        response = client.get("/en/manual")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert '<link rel="canonical" href="https://a2cr.app/en/manual"' in response.text
    assert '<link rel="alternate" hreflang="ja" href="https://a2cr.app/manual"' in response.text
    assert '<noscript id="a2cr-static-description">' in response.text
    assert "A2CR Manual" in response.text
    assert "python --version" in response.text
    assert "python -m pip install --upgrade a2cr-mcp" in response.text
    assert "AGENTS.md, CLAUDE.md, or another project memory file" in response.text
    assert "resume_context(slot_number=N)" in response.text
    assert "WorkStash entry_key values" in response.text
    assert "context contamination" in response.text
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
    assert "<loc>https://a2cr.app/agent-guide</loc>" in sitemap.text
    assert "<loc>https://a2cr.app/en/agent-guide</loc>" in sitemap.text
    assert "<loc>https://a2cr.app/manual</loc>" in sitemap.text
    assert "<loc>https://a2cr.app/en/manual</loc>" in sitemap.text
    assert llms.status_code == 200
    assert "Public guide (English): https://a2cr.app/en/guide" in llms.text
    assert "AI agent guide (agent-readable HTML): https://a2cr.app/agent-guide.html" in llms.text
    assert "Manual (English): https://a2cr.app/en/manual" in llms.text
    assert "MCP service URL: https://a2cr.app/mcp" in llms.text
    assert "A2CR is not an AI" in llms.text
    assert "Official AI-agent setup is the PyPI package a2cr-mcp" in llms.text
    assert 'first call resume_context(slot_name="...")' in llms.text
    assert "Use list_contexts only when no Slot is provided" in llms.text
    assert "Use WorkBaton and WorkStash proactively" in llms.text
    assert 'reason="context_contamination"' in llms.text
    assert "suggest continuing in a fresh AI window" in llms.text
    assert "local client key is managed by the user" in llms.text
    assert "old client-encrypted slots cannot be recovered" in llms.text
    assert "WorkBaton is client-encrypted only" in llms.text
    assert "A2CR does not accept plaintext WorkBaton bodies" in llms.text
    assert 'command = "a2cr-mcp"' in llms.text
