import asyncio
from contextlib import asynccontextmanager
import html
import json
from pathlib import Path

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
        "machine_text": "A2CR is an MCP-first context relay service. Use https://a2cr.app/guide for setup, https://a2cr.app/pricing for plans, and https://a2cr.app/mcp as the Streamable HTTP MCP endpoint.",
    },
    "guide": {
        "title": "A2CRの使い方ガイド",
        "description": "A2CRの使い方ガイド。Codex、Claude、CursorなどのMCP設定と、WorkBaton Slotで作業の続きを引き継ぐ流れを説明します。",
        "canonical": "https://a2cr.app/guide",
        "og_type": "article",
        "json_ld_type": "TechArticle",
        "alternates": {"ja": "https://a2cr.app/guide", "en": "https://a2cr.app/en/guide"},
        "machine_text": "A2CRの使い方ガイド。MCP endpointは https://a2cr.app/mcp です。Codexの例: [mcp_servers.\"a2cr\"] url = \"https://a2cr.app/mcp\" と Authorization = \"Bearer <A2CR_API_KEY>\" を設定します。ClaudeやCursorでは Streamable HTTP MCP server として同じURLとBearer tokenを設定します。作業が長くなる前に save_context で goal、current_state、next_action、必要な補足だけを保存します。新しい窓では resume_context または load_context から始めます。APIキー、Authorizationヘッダー、DB URL、秘密情報、長いログ、全文履歴は保存しません。",
    },
    "en/guide": {
        "title": "A2CR Setup Guide",
        "description": "A2CR setup guide. Learn how to connect Codex, Claude, Cursor, and other MCP clients, then save and resume WorkBaton slots.",
        "canonical": "https://a2cr.app/en/guide",
        "og_type": "article",
        "json_ld_type": "TechArticle",
        "alternates": {"ja": "https://a2cr.app/guide", "en": "https://a2cr.app/en/guide"},
        "machine_text": "A2CR setup guide. MCP endpoint: https://a2cr.app/mcp. Codex TOML example: [mcp_servers.\"a2cr\"] url = \"https://a2cr.app/mcp\" and Authorization = \"Bearer <A2CR_API_KEY>\" under http_headers. For Claude and Cursor, register the same URL as a Streamable HTTP MCP server with a Bearer token. Before a session gets long, call save_context with goal, current_state, next_action, and compact supporting facts. In a fresh window, start with resume_context or load_context. Never save secrets, API keys, Authorization headers, private database URLs, full transcripts, or long logs.",
    },
    "pricing": {
        "title": "A2CR Pricing - WorkBaton plans",
        "description": "A2CR pricing for MCP-based WorkBaton context relay. Start with Free and review planned Pro limits for larger workflows.",
        "canonical": "https://a2cr.app/pricing",
        "og_type": "website",
        "json_ld_type": "WebPage",
        "machine_text": "A2CR pricing: Free includes 3 Slots, up to 24h retention options, 32KB compact saves, 100 saves/hour, and 300 loads/hour. Pro is planned with 100 Slots, longer retention, 128KB saves, higher rate limits, and WorkThreads.",
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
    return (
        '<script type="text/plain" id="a2cr-machine-readable">\n'
        f"{html.escape(seo['machine_text'])}\n"
        "</script>"
    )


def _static_description_block(route_key: str) -> str:
    seo = ROUTE_SEO.get(route_key)
    if seo is None:
        return ""
    return "\n".join(
        [
            '<noscript id="a2cr-static-description">',
            '<section style="max-width: 960px; margin: 32px auto; padding: 0 16px; font-family: system-ui, -apple-system, BlinkMacSystemFont, \'Segoe UI\', sans-serif; line-height: 1.7;">',
            f"<h1>{html.escape(seo['title'])}</h1>",
            f"<p>{html.escape(seo['description'])}</p>",
            f"<p>{html.escape(seo['machine_text'])}</p>",
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
