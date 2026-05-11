import asyncio
import html
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from textwrap import dedent
from uuid import uuid4

logger = logging.getLogger(__name__)

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from sqlalchemy.exc import SQLAlchemyError

from routers import dashboard, health, mcp_http, web_context, work_stash, workthreads
from services.config import (
    app_env,
    is_request_origin_allowed,
    is_web_runtime,
    validate_runtime_environment,
)
from services.db_errors import classify_db_error
from services.exceptions import AppError
from services.logs import sanitize_log_request_id

WEB_DIST_DIR = Path(__file__).resolve().parent / "web" / "dist"
WEB_PUBLIC_DIR = Path(__file__).resolve().parent / "web" / "public"
WEB_INDEX_FILE = WEB_DIST_DIR / "index.html"
WEB_SOURCE_INDEX_FILE = Path(__file__).resolve().parent / "web" / "index.html"

CONTENT_SECURITY_POLICY = "; ".join(
    [
        "default-src 'self'",
        "base-uri 'self'",
        "object-src 'none'",
        "frame-ancestors 'none'",
        "connect-src 'self' https://*.supabase.co",
        "img-src 'self' data: https://a2cr.app",
        "script-src 'self' 'unsafe-inline'",
        "style-src 'self' 'unsafe-inline'",
        "form-action 'self'",
    ]
)

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-Frame-Options": "DENY",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
    "Content-Security-Policy": CONTENT_SECURITY_POLICY,
}

def _seo(
    *,
    title: str,
    description: str,
    canonical: str,
    machine_text: str,
    og_type: str = "article",
    json_ld_type: str = "TechArticle",
    alternates: dict[str, str] | None = None,
) -> dict:
    return {
        "title": title,
        "description": description,
        "canonical": canonical,
        "og_type": og_type,
        "json_ld_type": json_ld_type,
        "alternates": alternates or {"ja": canonical, "en": canonical},
        "machine_text": dedent(machine_text).strip(),
    }


ROUTE_SEO = {
    "": _seo(
        title="A2CR - Agent-to-Agent Context Relay",
        description="A2CR is an MCP-first work-continuation layer for saving compact WorkBaton checkpoints, reducing context waste, and resuming work across Codex, Claude, Cursor, and other MCP clients.",
        canonical="https://a2cr.app/",
        og_type="website",
        json_ld_type="SoftwareApplication",
        machine_text="""
        # A2CR

        A2CR is not an AI.
        It is the baton that lets AI agents hand work to one another.

        A2CR is an MCP-first work-continuation layer.

        It lets MCP-capable tools save compact WorkBaton checkpoints and resume work later from another window, model, or AI agent configured with A2CR MCP.

        Important URLs:
        - Guide: https://a2cr.app/en/guide
        - AI agent guide: https://a2cr.app/en/agent-guide
        - Pricing: https://a2cr.app/pricing
        - MCP service URL: https://a2cr.app/mcp
        - LLM notes: https://a2cr.app/llms.txt
        """,
    ),
    "guide": _seo(
        title="A2CR ガイド",
        description="A2CRのガイド。WorkBaton、MCP設定、暗号化方式、local client keyの重要事項を説明します。",
        canonical="https://a2cr.app/guide",
        alternates={"ja": "https://a2cr.app/guide", "en": "https://a2cr.app/en/guide"},
        machine_text="""
        # A2CR ガイド

        A2CRは、AI作業の状態をWorkBatonとして保存し、別のAI窓、別モデル、MCP対応クライアントから再開するためのサービスです。

        A2CRはAIではありません。AI同士が作業を受け渡すためのバトンです。

        読むより、AIに読ませる:
        - AI向けガイドを、ふだん使っているAIエージェントに見せて「このアプリを説明して」と頼んでください。
        - A2CRが何を渡し、何を保存しないのかまで、あなた向けにかみ砕いて説明できます。

        重要事項:
        - WorkBatonはclient-encryptedのみです。
        - A2CRはWorkBaton本文の平文保存を受け付けません。
        - ローカルstdio MCP wrapperが送信前に暗号化し、A2CRは暗号文だけを保存・返却します。
        - 直接HTTP MCPからのWorkBaton保存は無効化されています。
        - local client keyは利用者側が管理します。サービス管理者は管理しません。
        - local client keyを失うと、旧鍵で保存したclient-encrypted SlotはA2CR側でも復旧できません。
        - local client keyを作り直すと、それ以後に新しい鍵で保存したSlotは読めますが、旧鍵で保存したSlotには旧鍵が必要です。

        関連ページ:
        - AIエージェント向けガイド: https://a2cr.app/agent-guide
        - English guide: https://a2cr.app/en/guide
        - MCP service URL: https://a2cr.app/mcp

        圧縮・要約機能との違い:
        - 圧縮・要約機能の目的は長い会話を短くすることです。
        - A2CR / WorkBatonの目的は、次のAIが作業再開できる状態を渡すことです。
        - 圧縮・要約機能の対象はそのチャット内の履歴です。
        - A2CR / WorkBatonの対象は別チャット、別AI、別ツールです。
        - 圧縮・要約機能の出力は要約文です。
        - A2CR / WorkBatonの出力はgoal、current_state、next_action、blockersなどの作業状態です。
        - 圧縮機能は、ざっくり言えば「会話ログのダイエット」です。A2CRは「作業状態のバトン」です。

        サブエージェントとの違い:
        - サブエージェントの主な用途は同じ環境内で分業することです。
        - A2CRの主な用途は環境をまたいで引き継ぐことです。
        - サブエージェントの有効範囲はそのチャット、その親エージェント内です。
        - A2CRはChatGPT、Claude、Codex、Cursor、Roo、ローカルLLMなどを横断できます。
        - サブエージェントの状態共有は親エージェントの文脈に依存します。
        - A2CRは外部の一時リレーDBに保存し、TTLで消えます。
        """,
    ),
    "en/guide": _seo(
        title="A2CR Guide",
        description="Guide for A2CR. Learn WorkBaton, MCP setup, storage modes, and local client key responsibilities.",
        canonical="https://a2cr.app/en/guide",
        alternates={"ja": "https://a2cr.app/guide", "en": "https://a2cr.app/en/guide"},
        machine_text="""
        # A2CR Guide

        A2CR saves AI work state as a WorkBaton so another AI window, model, or MCP-capable client can resume the work.

        A2CR is not an AI. It is the baton that lets AI agents hand work to one another.

        Let your AI read it:
        - Show the AI agent guide to the AI agent you already use and ask it to explain A2CR.
        - The guide is written for agents, so it can turn the app's role, limits, and setup into plain guidance for your situation.

        Important points:
        - WorkBaton is client-encrypted only.
        - A2CR does not accept plaintext WorkBaton bodies.
        - The local stdio MCP wrapper encrypts before upload, and A2CR stores and returns ciphertext only.
        - Direct remote HTTP MCP saving is disabled for WorkBaton.
        - The local client key is managed by the user, not by the service administrator.
        - If the local client key is lost, old client-encrypted slots cannot be recovered by A2CR.
        - Slots saved after creating a new local client key can be read with that new key, but old slots still need the old key.

        Related pages:
        - AI agent guide: https://a2cr.app/en/agent-guide
        - Japanese guide: https://a2cr.app/guide
        - MCP service URL: https://a2cr.app/mcp

        Compression / summarization vs A2CR / WorkBaton:
        - Compression and summarization shorten a long conversation.
        - A2CR / WorkBaton passes a state that lets the next AI resume work.
        - Compression and summarization target history inside that chat.
        - A2CR / WorkBaton targets another chat, another AI, or another tool.
        - Compression and summarization output summary text.
        - A2CR / WorkBaton outputs work state such as goal, current_state, next_action, and blockers.
        - Compression is a diet for a conversation log. A2CR is a baton for work state.

        Sub-agents vs A2CR:
        - Sub-agents divide work inside the same environment.
        - A2CR carries the environment itself forward.
        - Sub-agents are effective inside that chat and its parent agent.
        - A2CR can work across ChatGPT, Claude, Codex, Cursor, Roo, and local LLMs.
        - Sub-agent state sharing depends on the parent agent's context.
        - A2CR stores state in an external temporary relay DB and expires it by TTL.
        """,
    ),
    "agent-guide": _seo(
        title="A2CR AIエージェント向けガイド",
        description="A2CRを利用・設定するAIエージェント向けガイド。MCP利用ルール、保存方針、local client keyの重要事項を説明します。",
        canonical="https://a2cr.app/agent-guide",
        alternates={"ja": "https://a2cr.app/agent-guide", "en": "https://a2cr.app/en/agent-guide"},
        machine_text="""
        # A2CR AIエージェント向けガイド

        AIエージェントはA2CRをMCPツール経由の作業記憶として使います。直接HTTP APIを推測して呼ばないでください。
        WorkBatonの公式ルートは、a2crという名前のローカルstdio MCPラッパーです。

        ルール:
        - resume promptにSlotがある場合は、最初にresume_context(slot_name="...")またはresume_context(slot_number=N)を実行します。
        - list_contextsは、Slotが提示されておらず、ユーザーが検索を求めた場合だけ使います。
        - 作業中は、会話が長くなる前または重要な区切りでsave_contextします。
        - 保存する内容はgoal、current_state、next_action、必要な判断、制約、参照だけに絞ります。
        - APIキー、Authorization header、DB URL、秘密情報、全文ログ、長い会話履歴は保存しません。
        - 自動保存前にはget_account_limitsで制限を確認します。

        暗号化:
        - local client keyは利用者側が管理します。
        - client-encrypted WorkBaton Slotは、A2CRサーバーでは復号できません。
        - local client keyを失うと、旧鍵で保存したclient-encrypted Slotは復旧できません。
        - 新しいlocal client keyで保存したSlotは、その新しい鍵で読めます。
        """,
    ),
    "en/agent-guide": _seo(
        title="A2CR AI Agent Guide",
        description="Guide for AI agents using and configuring A2CR. Covers MCP rules, save policy, and local client key responsibilities.",
        canonical="https://a2cr.app/en/agent-guide",
        alternates={"ja": "https://a2cr.app/agent-guide", "en": "https://a2cr.app/en/agent-guide"},
        machine_text="""
        # A2CR AI Agent Guide

        AI agents should use A2CR through MCP tools as working memory. Do not guess direct HTTP API calls.
        The official WorkBaton path is the local stdio MCP wrapper named a2cr.
        Do not use the legacy local SQLite API for WorkBaton saves.

        Rules:
        - When a resume prompt provides a Slot, first call resume_context(slot_name="...") or resume_context(slot_number=N).
        - Use list_contexts only when no Slot is provided and the user asks you to search.
        - During work, call save_context before the conversation gets long or at important milestones.
        - Use WorkBaton and WorkStash proactively when they help preserve useful work state; do not wait for the user to ask.
        - If the conversation feels noisy, contradictory, stale, or polluted by old task state, call should_save_workbaton with reason="context_drift" or reason="context_contamination".
        - If saving is recommended, save a compact WorkBaton, move safe bulky support notes into WorkStash, record the entry_key in WorkBaton, and suggest continuing in a fresh AI window.
        - Save only goal, current_state, next_action, and compact supporting facts.
        - Never save secrets, API keys, Authorization headers, private database URLs, full transcripts, or long logs.
        - Call get_account_limits before automatic saves.

        Encryption:
        - The local client key is managed by the user.
        - Client-encrypted WorkBaton slots cannot be decrypted by the A2CR server.
        - If the local client key is lost, old client-encrypted slots cannot be recovered.
        - Slots saved after creating a new local client key can be read with that new key.
        """,
    ),
    "pricing": _seo(
        title="A2CR Pricing - WorkBaton plans",
        description="A2CR pricing for MCP-based WorkBaton context relay. Start with Free and review planned Pro limits for larger workflows.",
        canonical="https://a2cr.app/pricing",
        og_type="website",
        json_ld_type="WebPage",
        machine_text="""
        # A2CR Pricing

        Free plan:
        - 5 Slots
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
        """,
    ),
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
    return ""


def _static_description_block(route_key: str) -> str:
    seo = ROUTE_SEO.get(route_key)
    if seo is None:
        return ""
    escaped_machine_text = html.escape(seo["machine_text"])
    return "\n".join(
        [
            '<noscript id="a2cr-static-description">',
            '<section style="max-width: 960px; margin: 32px auto; padding: 0 16px; font-family: system-ui, -apple-system, BlinkMacSystemFont, \'Segoe UI\', sans-serif; line-height: 1.7;">',
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_runtime_environment()
    async with mcp_http.mcp_app.lifespan():
        yield


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


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    for name, value in SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    if app_env() == "production":
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


@app.exception_handler(AppError)
def app_error_handler(request: Request, exc: AppError):
    content = {"code": exc.code, "message": exc.message}
    content.update(exc.extra)
    return JSONResponse(
        status_code=exc.status,
        content=content,
        headers=exc.headers,
    )


def _safe_request_id(request: Request) -> str:
    request_id = sanitize_log_request_id(request.headers.get("x-request-id"))
    if request_id:
        return request_id
    return uuid4().hex


@app.exception_handler(RequestValidationError)
def request_validation_error_handler(request: Request, exc: RequestValidationError):
    details = [
        {
            "loc": list(error.get("loc", [])),
            "msg": error.get("msg", "Invalid input"),
            "type": error.get("type", "value_error"),
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "code": "invalid_request",
            "message": "Invalid request",
            "details": details,
            "request_id": _safe_request_id(request),
        },
    )


@app.exception_handler(SQLAlchemyError)
def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
    logger.error("DB error on %s %s", request.method, request.url.path, exc_info=exc)
    classification = classify_db_error(exc)
    content = {
        "code": classification.code,
        "message": classification.message,
        "request_id": _safe_request_id(request),
    }
    if classification.retry_after is not None:
        content["retry_after"] = classification.retry_after
    headers = {}
    if classification.retry_after is not None:
        headers["Retry-After"] = str(classification.retry_after)
    return JSONResponse(status_code=classification.status, content=content, headers=headers)


@app.exception_handler(Exception)
def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled error on %s %s", request.method, request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={
            "code": "internal_error",
            "message": "Request failed.",
            "request_id": _safe_request_id(request),
        },
    )


app.include_router(health.router)
app.include_router(web_context.router)
app.include_router(work_stash.router)
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
