import asyncio
from contextlib import asynccontextmanager
import html
import json
from pathlib import Path
from textwrap import dedent

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse

from services.db import init_db
from services.context import cleanup_expired
from services.config import is_request_origin_allowed, is_web_runtime, validate_runtime_environment
from services.exceptions import AppError
from routers import health, context, web_context, dashboard, workthreads, mcp_http

WEB_DIST_DIR = Path(__file__).resolve().parent / "web" / "dist"
WEB_PUBLIC_DIR = Path(__file__).resolve().parent / "web" / "public"
WEB_INDEX_FILE = WEB_DIST_DIR / "index.html"
WEB_SOURCE_INDEX_FILE = Path(__file__).resolve().parent / "web" / "index.html"

ROUTE_SEO = {
    "": {
        "title": "A2CR - Agent-to-Agent Context Relay",
        "description": "A2CR is an MCP-first context relay service for saving compact WorkBaton checkpoints and resuming work across Codex, Claude, Cursor, and other MCP clients.",
        "canonical": "https://a2cr.app/",
        "og_type": "website",
        "json_ld_type": "SoftwareApplication",
        "machine_text": dedent(
            """
            # A2CR

            A2CR is an MCP-first context relay service.

            It lets MCP-capable tools save compact WorkBaton checkpoints and resume work later from another window, model, or client.

            Important URLs:
            - Public guide: https://a2cr.app/guide
            - English guide: https://a2cr.app/en/guide
            - Pricing: https://a2cr.app/pricing
            - MCP endpoint: https://a2cr.app/mcp
            - LLM notes: https://a2cr.app/llms.txt
            """
        ).strip(),
    },
    "guide": {
        "title": "A2CRの使い方ガイド",
        "description": "A2CRの使い方ガイド。Codex、Claude、CursorなどのMCP設定と、WorkBaton Slotで作業の続きを引き継ぐ流れを説明します。",
        "canonical": "https://a2cr.app/guide",
        "og_type": "article",
        "json_ld_type": "TechArticle",
        "alternates": {"ja": "https://a2cr.app/guide", "en": "https://a2cr.app/en/guide"},
        "machine_text": dedent(
            """
            # A2CRの使い方ガイド

            A2CRは、Codex、Claude、CursorなどのMCP対応クライアントから使える作業引き継ぎサービスです。
            会話が長くなる前に、作業の要点だけをWorkBaton Slotへ保存し、新しい窓や別モデルから続きを再開できます。

            ## 重要なURL
            - サービス: https://a2cr.app/
            - 日本語ガイド: https://a2cr.app/guide
            - 英語ガイド: https://a2cr.app/en/guide
            - MCP endpoint: https://a2cr.app/mcp
            - 料金: https://a2cr.app/pricing

            ## Codexの設定例
            Windowsなら通常は C:\\Users\\<USER>\\.codex\\config.toml を編集します。
            既存の設定を消さず、次のA2CR serverだけを追記または更新します。

            [mcp_servers."a2cr"]
            url = "https://a2cr.app/mcp"

            [mcp_servers."a2cr".http_headers]
            Authorization = "Bearer <A2CR_API_KEY>"

            ## Claude / Cursor の設定例
            Streamable HTTP MCP serverとして、URLに https://a2cr.app/mcp を設定します。
            Authorizationヘッダーには Bearer <A2CR_API_KEY> を設定します。
            設定ファイルの場所や画面はクライアントのバージョンで変わるため、現在のMCP設定画面または公式の設定ファイルを確認してから編集します。

            JSON形式の例:

            {
              "mcpServers": {
                "a2cr": {
                  "type": "streamable-http",
                  "url": "https://a2cr.app/mcp",
                  "headers": {
                    "Authorization": "Bearer <A2CR_API_KEY>"
                  }
                }
              }
            }

            ## このページを読んだAIエージェントへの指示
            ユーザーに「A2CRのMCPを設定して」と頼まれたら、次の順番で進めます。

            1. このページの内容を読み、A2CR MCP endpoint が https://a2cr.app/mcp であることを確認します。
            2. 使っているクライアントが Codex、Claude、Cursor、その他のどれかを確認します。
            3. ユーザーにA2CRへログインしてAPIキーを発行してもらいます。APIキーはAIが推測しません。
            4. そのクライアントのMCP設定ファイルまたは設定画面を探します。
            5. 既存のMCP server設定を読み、消さないようにします。
            6. a2cr という名前のStreamable HTTP MCP serverを追加または更新します。
            7. URLは https://a2cr.app/mcp にします。
            8. Authorizationヘッダーは一旦 Bearer PASTE_A2CR_API_KEY_HERE のようなプレースホルダーにします。
            9. 設定ファイルをテキストエディタで開き、ユーザーにAPIキーだけを貼り付けて保存してもらいます。
            10. WindowsのCodexなら、例として notepad C:\\Users\\<USER>\\.codex\\config.toml を開きます。
            11. ClaudeやCursorでは、現在のMCP設定ファイルまたは設定画面を開きます。
            12. APIキー、Authorizationヘッダー、設定ファイル全文をチャットやログに不用意に表示しません。
            13. 保存後、クライアントまたはエージェントセッションを再起動・再読み込みするよう案内します。
            14. 再起動後、疎通確認として get_account_limits または list_contexts を実行します。
            15. 疎通確認に成功したら、A2CR MCPが利用可能になったことをユーザーへ伝えます。

            ## 推奨する導線
            1. ユーザーがAIエージェントにこのページを読ませます。
            2. AIエージェントがMCP設定ファイルを特定し、A2CR設定のひな形を入れます。
            3. ユーザーがA2CRのダッシュボードでAPIキーを取得します。
            4. AIエージェントが設定ファイルをテキストエディタで開きます。
            5. ユーザーがプレースホルダーをAPIキーに置き換えて保存します。
            6. AIエージェントまたはユーザーがクライアントを再起動します。
            7. AIエージェントが get_account_limits または list_contexts で接続確認します。

            ## 設定時の禁止事項
            既存のMCP設定を全削除しない。
            APIキーをリポジトリへコミットしない。
            APIキーをA2CRの保存Slotへ保存しない。
            HTTP APIを推測して直接呼ばない。
            必ずMCPクライアントの設定として登録する。

            ## 基本の使い方
            1. A2CRへログインしてAPIキーを発行します。
            2. Codex、Claude、CursorなどのMCP設定にA2CRを追加します。
            3. 作業が長くなりそうな時に save_context を呼びます。
            4. 保存する内容は goal、current_state、next_action、必要な補足だけにします。
            5. 新しい窓では最初に resume_context または load_context を呼びます。

            ## 保存してはいけないもの
            APIキー、Authorizationヘッダー、DB URL、秘密情報、長いログ、全文履歴は保存しません。
            HTTP APIを推測して直接呼ばず、必ずMCPツールを使います。
            """
        ).strip(),
    },
    "en/guide": {
        "title": "A2CR Setup Guide",
        "description": "A2CR setup guide. Learn how to connect Codex, Claude, Cursor, and other MCP clients, then save and resume WorkBaton slots.",
        "canonical": "https://a2cr.app/en/guide",
        "og_type": "article",
        "json_ld_type": "TechArticle",
        "alternates": {"ja": "https://a2cr.app/guide", "en": "https://a2cr.app/en/guide"},
        "machine_text": dedent(
            """
            # A2CR Setup Guide

            A2CR is a work handoff service for Codex, Claude, Cursor, and other MCP-capable clients.
            It saves compact WorkBaton checkpoints so work can continue from another window, model, or client.

            ## Important URLs
            - Service: https://a2cr.app/
            - Japanese guide: https://a2cr.app/guide
            - English guide: https://a2cr.app/en/guide
            - MCP endpoint: https://a2cr.app/mcp
            - Pricing: https://a2cr.app/pricing

            ## Codex config.toml example
            On Windows, the config file is usually C:\\Users\\<USER>\\.codex\\config.toml.
            Preserve existing settings and add or update only the A2CR server.

            [mcp_servers."a2cr"]
            url = "https://a2cr.app/mcp"

            [mcp_servers."a2cr".http_headers]
            Authorization = "Bearer <A2CR_API_KEY>"

            ## Claude / Cursor example
            Register https://a2cr.app/mcp as a Streamable HTTP MCP server.
            Add Authorization: Bearer <A2CR_API_KEY>.
            Config locations can vary by client version, so inspect the current MCP settings screen or official config file before editing.

            JSON example:

            {
              "mcpServers": {
                "a2cr": {
                  "type": "streamable-http",
                  "url": "https://a2cr.app/mcp",
                  "headers": {
                    "Authorization": "Bearer <A2CR_API_KEY>"
                  }
                }
              }
            }

            ## Instructions for AI agents reading this page
            If the user asks you to configure A2CR MCP, do this:

            1. Read this page and confirm that the A2CR MCP endpoint is https://a2cr.app/mcp.
            2. Identify whether the user is using Codex, Claude, Cursor, or another MCP client.
            3. Ask the user to sign in to A2CR and issue an API key. Do not guess the key.
            4. Locate that client's MCP config file or MCP settings screen.
            5. Read the existing MCP server settings and preserve them.
            6. Add or update a server named a2cr.
            7. Set the server type to Streamable HTTP when the client supports that field.
            8. Set the URL to https://a2cr.app/mcp.
            9. Set Authorization to a placeholder such as Bearer PASTE_A2CR_API_KEY_HERE.
            10. Open the config file in a text editor and ask the user to replace only the placeholder with their API key, then save.
            11. For Codex on Windows, opening notepad C:\\Users\\<USER>\\.codex\\config.toml is usually appropriate.
            12. For Claude or Cursor, open the current MCP settings file or MCP settings screen.
            13. Do not print the API key, Authorization header, or full secret config in chat or logs.
            14. After saving, tell the user to restart or reload the MCP client or AI agent session.
            15. After restart, verify the connection by running get_account_limits or list_contexts.
            16. If verification succeeds, tell the user that A2CR MCP is ready.

            ## Recommended setup flow
            1. The user asks an AI agent to read this page.
            2. The AI agent locates the MCP config and writes the A2CR placeholder config.
            3. The user obtains an API key from the A2CR dashboard.
            4. The AI agent opens the config file in a text editor.
            5. The user replaces the placeholder with the API key and saves the file.
            6. The AI agent or user restarts the client.
            7. The AI agent verifies the connection with get_account_limits or list_contexts.

            ## Do not do these things
            Do not delete unrelated MCP servers.
            Do not commit the API key to a repository.
            Do not save the API key into an A2CR Slot.
            Do not guess direct HTTP API calls.
            Configure A2CR through the MCP client.

            ## Basic workflow
            1. Sign in to A2CR and issue an API key.
            2. Add A2CR to your MCP client.
            3. Before the session gets too long, call save_context.
            4. Save only goal, current_state, next_action, and compact supporting facts.
            5. In a fresh window, first call resume_context or load_context.

            ## Safety rules
            Never save secrets, API keys, Authorization headers, private database URLs, full transcripts, or long logs.
            Use the MCP tools. Do not guess or call direct HTTP API endpoints.
            """
        ).strip(),
    },
    "pricing": {
        "title": "A2CR Pricing - WorkBaton plans",
        "description": "A2CR pricing for MCP-based WorkBaton context relay. Start with Free and review planned Pro limits for larger workflows.",
        "canonical": "https://a2cr.app/pricing",
        "og_type": "website",
        "json_ld_type": "WebPage",
        "machine_text": dedent(
            """
            # A2CR Pricing

            Free plan:
            - 3 Slots
            - Retention options up to 24 hours
            - 32KB compact saves
            - 100 saves per hour
            - 300 loads per hour

            Planned Pro plan:
            - 100 Slots
            - Longer retention options
            - 128KB saves
            - Higher rate limits
            - Planned WorkThreads support
            """
        ).strip(),
    },
}


def _index_file() -> Path | None:
    for candidate in (WEB_INDEX_FILE, WEB_SOURCE_INDEX_FILE):
        if candidate.exists():
            return candidate
    return None


def _route_key(full_path: str) -> str:
    return full_path.rstrip("/")


def _route_head(route_key: str) -> str:
    seo = ROUTE_SEO.get(route_key)
    if seo is None:
        return "\n".join(
            [
                '<meta name="robots" content="noindex, nofollow" />',
                "<title>A2CR</title>",
            ]
        )

    alternates = seo.get("alternates", {"ja": seo["canonical"], "en": seo["canonical"]})
    json_ld = {
        "@context": "https://schema.org",
        "@type": seo["json_ld_type"],
        "name": seo["title"],
        "url": seo["canonical"],
        "description": seo["description"],
        "isPartOf": {
            "@type": "WebSite",
            "name": "A2CR",
            "url": "https://a2cr.app/",
        },
    }
    if seo["json_ld_type"] == "SoftwareApplication":
        json_ld["applicationCategory"] = "DeveloperApplication"
        json_ld["operatingSystem"] = "Web"
        json_ld["offers"] = {
            "@type": "Offer",
            "price": "0",
            "priceCurrency": "USD",
        }

    return "\n".join(
        [
            '<meta name="robots" content="index, follow" />',
            f'<link rel="canonical" href="{html.escape(seo["canonical"])}" />',
            f'<link rel="alternate" hreflang="ja" href="{html.escape(alternates["ja"])}" />',
            f'<link rel="alternate" hreflang="en" href="{html.escape(alternates["en"])}" />',
            f'<link rel="alternate" hreflang="x-default" href="{html.escape(alternates["ja"])}" />',
            f'<meta name="description" content="{html.escape(seo["description"])}" />',
            f'<meta property="og:type" content="{html.escape(seo["og_type"])}" />',
            '<meta property="og:site_name" content="A2CR" />',
            f'<meta property="og:title" content="{html.escape(seo["title"])}" />',
            f'<meta property="og:description" content="{html.escape(seo["description"])}" />',
            f'<meta property="og:url" content="{html.escape(seo["canonical"])}" />',
            '<meta property="og:image" content="https://a2cr.app/brand/a2cr-logo.png" />',
            '<meta name="twitter:card" content="summary" />',
            f'<meta name="twitter:title" content="{html.escape(seo["title"])}" />',
            f'<meta name="twitter:description" content="{html.escape(seo["description"])}" />',
            f"<title>{html.escape(seo['title'])}</title>",
            '<script type="application/ld+json">',
            json.dumps(json_ld, ensure_ascii=False),
            "</script>",
        ]
    )


def _machine_readable_block(route_key: str) -> str:
    seo = ROUTE_SEO.get(route_key)
    if seo is None:
        return ""
    machine_text = seo["machine_text"].replace("</script", "<\\/script")
    return (
        '<script type="text/plain" id="a2cr-machine-readable">\n'
        f"{machine_text}\n"
        "</script>"
    )


def _comment_safe_text(value: str) -> str:
    return value.replace("--", "—")


def _static_description_block(route_key: str) -> str:
    seo = ROUTE_SEO.get(route_key)
    if seo is None:
        return ""
    escaped_machine_text = html.escape(seo["machine_text"])
    return "\n".join(
        [
            "<!-- A2CR_AI_READABLE_START",
            _comment_safe_text(seo["machine_text"]),
            "A2CR_AI_READABLE_END -->",
            '<template id="a2cr-ai-readable">',
            f"<pre>{escaped_machine_text}</pre>",
            "</template>",
            '<noscript id="a2cr-static-description">',
            '<section style="max-width: 960px; margin: 32px auto; padding: 0 16px; font-family: system-ui, -apple-system, BlinkMacSystemFont, \'Segoe UI\', sans-serif; line-height: 1.7;">',
            f"<h1>{html.escape(seo['title'])}</h1>",
            f"<p>{html.escape(seo['description'])}</p>",
            f'<pre style="white-space: pre-wrap;">{escaped_machine_text}</pre>',
            "</section>",
            "</noscript>",
        ]
    )


def _render_spa_index(full_path: str) -> str:
    index_file = _index_file()
    if index_file is None:
        raise HTTPException(status_code=404)
    route_key = _route_key(full_path)
    document = index_file.read_text(encoding="utf-8")
    route_head = _route_head(route_key)
    static_block = _static_description_block(route_key)
    machine_block = _machine_readable_block(route_key)
    if "<!-- A2CR_ROUTE_HEAD -->" in document:
        document = document.replace("<!-- A2CR_ROUTE_HEAD -->", route_head)
    else:
        document = document.replace("</head>", f"{route_head}\n</head>")
    if "<!-- A2CR_STATIC_DESCRIPTION -->" in document:
        document = document.replace("<!-- A2CR_STATIC_DESCRIPTION -->", static_block)
    else:
        document = document.replace("</body>", f"{static_block}\n</body>")
    if "<!-- A2CR_MACHINE_READABLE -->" in document:
        document = document.replace("<!-- A2CR_MACHINE_READABLE -->", machine_block)
    else:
        document = document.replace("</body>", f"{machine_block}\n</body>")
    return document


async def _cleanup_loop():
    while True:
        await asyncio.sleep(600)  # 10 minutes
        cleanup_expired()


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_runtime_environment()
    task = None
    if not is_web_runtime():
        init_db()
        task = asyncio.create_task(_cleanup_loop())
    try:
        async with mcp_http.mcp_app.lifespan():
            yield
    finally:
        if task is not None:
            task.cancel()


app = FastAPI(
    title="A2CR",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


@app.middleware("http")
async def same_origin_guard(request: Request, call_next):
    origin = request.headers.get("origin")
    if not is_request_origin_allowed(origin):
        return JSONResponse(
            status_code=403,
            content={"code": "origin_not_allowed", "message": "Origin not allowed"},
        )
    return await call_next(request)


@app.exception_handler(AppError)
def app_error_handler(request: Request, exc: AppError):
    content = {"code": exc.code, "message": exc.message}
    content.update(exc.extra)
    return JSONResponse(
        status_code=exc.status,
        content=content,
        headers=exc.headers,
    )


app.include_router(health.router)
app.include_router(context.router)
app.include_router(web_context.router)
app.include_router(dashboard.router)
app.include_router(workthreads.router)
app.mount("/mcp", mcp_http.mcp_app)


@app.api_route("/mcp", methods=["GET", "POST", "DELETE", "OPTIONS"])
async def serve_mcp_exact(request: Request):
    scope = dict(request.scope)
    scope["path"] = "/"
    scope["raw_path"] = b"/"
    scope["root_path"] = f'{scope.get("root_path", "")}/mcp'

    messages: asyncio.Queue[dict] = asyncio.Queue()

    async def send(message: dict):
        await messages.put(message)

    task = asyncio.create_task(mcp_http.mcp_app(scope, request.receive, send))
    first_message = asyncio.create_task(messages.get())
    done, _ = await asyncio.wait({task, first_message}, return_when=asyncio.FIRST_COMPLETED)
    if task in done and not first_message.done():
        await task
    start = first_message.result()
    raw_headers = start.get("headers", [])
    headers = {
        key.decode("latin-1"): value.decode("latin-1")
        for key, value in raw_headers
        if key.lower() != b"content-length"
    }

    async def body_stream():
        try:
            while True:
                message = await messages.get()
                if message["type"] != "http.response.body":
                    continue
                body = message.get("body", b"")
                if body:
                    yield body
                if not message.get("more_body", False):
                    break
            await task
        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(body_stream(), status_code=start["status"], headers=headers)


@app.get("/")
@app.get("/{full_path:path}")
def serve_spa(full_path: str = ""):
    if full_path.startswith(("api/", "mcp")):
        raise HTTPException(status_code=404)
    if any(part.startswith(".") for part in Path(full_path).parts):
        raise HTTPException(status_code=404)

    public_candidate = (WEB_PUBLIC_DIR / full_path).resolve()
    try:
        public_candidate.relative_to(WEB_PUBLIC_DIR.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=404) from exc
    if public_candidate.is_file():
        return FileResponse(public_candidate)
    candidate = (WEB_DIST_DIR / full_path).resolve()
    try:
        candidate.relative_to(WEB_DIST_DIR.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=404) from exc
    if candidate.is_file():
        return FileResponse(candidate)
    return HTMLResponse(_render_spa_index(full_path), media_type="text/html; charset=utf-8")
