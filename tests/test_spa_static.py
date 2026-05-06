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
    assert "A2CR_AI_READABLE_START" not in response.text
    assert '<template id="a2cr-ai-readable">' not in response.text
    assert '<script type="text/plain" id="a2cr-machine-readable">' not in response.text
    assert '<noscript id="a2cr-static-description">' in response.text
    assert "https://a2cr.app/mcp" in response.text
    assert "A2CRはAIではありません" in response.text
    assert "AI同士が作業を受け渡すためのバトン" in response.text
    assert "要約・圧縮との違い" in response.text
    assert "会話ログのダイエット" in response.text
    assert "作業状態のバトン" in response.text
    assert "save_context" in response.text
    assert "get_account_limits" in response.text
    assert "PASTE_A2CR_API_KEY_HERE" in response.text
    assert "設定ファイルをテキストエディタで開き" in response.text
    assert "クライアントまたはエージェントセッションを再起動" in response.text
    assert "既存のMCP設定を全削除しない" in response.text
    assert "Token節約" in response.text
    assert "出力安定" in response.text
    assert "WorkThreads" in response.text
    assert "Protocol的な土台" in response.text
    assert "A2CRのMCPの設定をしたAIエージェント" in response.text
    assert "半自動化プロンプト" in response.text
    assert "作業開始時は list_contexts" in response.text
    assert response.text.count("# A2CRの使い方ガイド") == 1
    assert response.text.count("## AIエージェントが理解すべきこと") == 1
    assert '<div id="root"></div>' in response.text


def test_public_english_guide_serves_static_ai_readable_html():
    with TestClient(app) as client:
        response = client.get("/en/guide")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert '<link rel="canonical" href="https://a2cr.app/en/guide"' in response.text
    assert '<link rel="alternate" hreflang="ja" href="https://a2cr.app/guide"' in response.text
    assert "A2CR setup guide" in response.text
    assert "A2CR_AI_READABLE_START" not in response.text
    assert '<template id="a2cr-ai-readable">' not in response.text
    assert '<script type="text/plain" id="a2cr-machine-readable">' not in response.text
    assert '<noscript id="a2cr-static-description">' in response.text
    assert "https://a2cr.app/mcp" in response.text
    assert "A2CR is not an AI" in response.text
    assert "baton that lets AI agents hand work" in response.text
    assert "Difference from summarizing or compressing a chat" in response.text
    assert "diet for conversation logs" in response.text
    assert "baton for work state" in response.text
    assert "save_context" in response.text
    assert "get_account_limits" in response.text
    assert "PASTE_A2CR_API_KEY_HERE" in response.text
    assert "Open the config file in a text editor" in response.text
    assert "restart or reload the MCP client" in response.text
    assert "Do not delete unrelated MCP servers" in response.text
    assert "external working memory" in response.text
    assert "token savings" in response.text
    assert "WorkThreads" in response.text
    assert "protocol-like foundation" in response.text
    assert "any AI agent configured with A2CR MCP" in response.text
    assert "Semi-automation prompt" in response.text
    assert "At the start of work, call list_contexts" in response.text
    assert response.text.count("# A2CR Setup Guide") == 1
    assert response.text.count("## What AI agents should understand") == 1
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
    assert "A2CR is not an AI" in llms.text
    assert "baton that lets AI agents hand work" in llms.text
    assert "Summary and compression shorten one chat" in llms.text
    assert "WorkBaton is a baton for work state" in llms.text
    assert "external working memory" in llms.text
    assert "protocol-like handoff layer" in llms.text
    assert "any AI agent configured with A2CR MCP" in llms.text
    assert "At the start of work, call list_contexts" in llms.text
