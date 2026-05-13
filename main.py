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
        description="A2CR keeps long AI sessions light by saving focused WorkBaton checkpoints within the available size budget, reducing context waste, and resuming work across Codex, Claude, Cursor, and other MCP clients.",
        canonical="https://a2cr.app/",
        og_type="website",
        json_ld_type="SoftwareApplication",
        machine_text="""
        # A2CR

        A2CR is not an AI.
        It is the baton that lets AI agents hand work to one another.

        A2CR is an MCP-first work-continuation layer.

        It lets MCP-capable tools save focused WorkBaton checkpoints and resume work later from another window, model, or AI agent configured with A2CR MCP.

        Long AI sessions get heavy because the work history grows. Later turns often need earlier requirements, decisions, files, errors, and corrections, so the active context can become slower and more token-hungry.

        A2CR keeps context light. When work reaches a milestone or context pressure appears, an agent can save a focused WorkBaton with the goal, current state, next action, blockers, and validation. Pro has a larger size budget, so it can carry a richer handoff while still moving bulky support notes to WorkStash. A fresh AI session can resume from that distilled state instead of carrying the entire chat history forward.

        Important URLs:
        - Guide: https://a2cr.app/en/guide
        - Manual: https://a2cr.app/en/manual
        - AI agent guide: https://a2cr.app/en/agent-guide
        - Pricing: https://a2cr.app/pricing
        - MCP service URL: https://a2cr.app/mcp
        - LLM notes: https://a2cr.app/llms.txt

        Public setup:
        - Install or update the local stdio MCP wrapper with python -m pip install --upgrade a2cr-mcp.
        - Register the installed a2cr-mcp command as one MCP server named a2cr.
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
        - Python が使える状態で python -m pip install --upgrade a2cr-mcp を実行し、ローカルstdio MCP wrapperをインストールします。
        - MCP設定では command を a2cr-mcp、args を空配列にし、MCP server名は a2cr にします。
        - WorkBatonはclient-encryptedのみです。
        - A2CRはWorkBaton本文の平文保存を受け付けません。
        - ローカルstdio MCP wrapperが送信前に暗号化し、A2CRは暗号文だけを保存・返却します。
        - 直接HTTP MCPからのWorkBaton保存は無効化されています。
        - local client keyは利用者側が管理します。サービス管理者は管理しません。
        - API keyの全文は発行時に一度だけ表示されます。再発行すると別のAPI keyになるため、MCP設定の更新が必要です。
        - local client keyファイルは、ローカルstdio MCP wrapperが初回のclient-encrypted保存時に作成します。
        - A2CR_CLIENT_KEY_FILEを指定するとkeyファイルのパスを固定できます。A2CR_CONFIG_DIRを指定すると、そのディレクトリ内のworkbaton.keyを使います。
        - どちらも未指定の場合、Windowsでは%APPDATA%\\A2CR\\workbaton.key、macOS/Linuxでは$XDG_CONFIG_HOME/a2cr/workbaton.keyまたは~/.config/a2cr/workbaton.keyが既定です。
        - 別のPCで同じWorkBatonを再開するには、A2CR API keyと同じlocal client keyファイルの両方が必要です。API keyだけでは本文を復号できません。
        - local client keyを失うと、旧鍵で保存したclient-encrypted SlotはA2CR側でも復旧できません。
        - local client keyを作り直すと、それ以後に新しい鍵で保存したSlotは読めますが、旧鍵で保存したSlotには旧鍵が必要です。

        インフラとデータ境界:
        - ホスト版A2CRはデータ層にSupabase/Postgres、アプリ層にRailwayを使います。
        - ユーザーごとの行分離はSupabase Row Level Security（RLS）とleast-privileged a2cr_app runtime roleで行います。
        - 公式WorkBaton保存経路では本文を端末側で暗号化してから送信するため、A2CRはWorkBaton本文の暗号文を保存します。
        - SupabaseとRailwayはSOC 2 / compliance情報を公開しています。これは基盤リスクの説明には役立ちますが、A2CR自体がSOC 2認証済みという意味ではなく、A2CR側のRLS、クライアント暗号化、鍵管理、スモークテストの代わりにはなりません。

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

        MCP / A2A / A2CR:
        - MCPはAIエージェントをツール、API、外部データへ接続します。
        - A2AはAIエージェント同士を委任、通信、協調のために接続します。
        - A2CRはAI窓、モデル、ツール、時間をまたいで、次のセッションが再開できるコンパクトな作業状態を保存します。
        - A2CRはMCPやA2Aの代替ではなく補完関係です。
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
        - Install the local stdio MCP wrapper with python -m pip install --upgrade a2cr-mcp.
        - In MCP config, set command to a2cr-mcp, args to an empty array, and MCP server name to a2cr.
        - WorkBaton is client-encrypted only.
        - A2CR does not accept plaintext WorkBaton bodies.
        - The local stdio MCP wrapper encrypts before upload, and A2CR stores and returns ciphertext only.
        - Direct remote HTTP MCP saving is disabled for WorkBaton.
        - The local client key is managed by the user, not by the service administrator.
        - The full API key is shown only once when issued. Reissuing creates a different API key, so MCP configs must be updated.
        - The local stdio MCP wrapper creates the local client key file during the first client-encrypted save when no key file exists.
        - Set A2CR_CLIENT_KEY_FILE to choose the exact key file path, or A2CR_CONFIG_DIR to choose the directory that contains workbaton.key.
        - If neither variable is set, the default path is %APPDATA%\\A2CR\\workbaton.key on Windows, and $XDG_CONFIG_HOME/a2cr/workbaton.key or ~/.config/a2cr/workbaton.key on macOS/Linux.
        - To resume from another PC, the user needs the A2CR API key plus the same local client key file. The API key alone cannot decrypt saved WorkBaton bodies.
        - If the local client key is lost, old client-encrypted slots cannot be recovered by A2CR.
        - Slots saved after creating a new local client key can be read with that new key, but old slots still need the old key.

        Infrastructure and data boundaries:
        - Hosted A2CR uses Supabase/Postgres for the data layer and Railway for the app runtime.
        - User-owned rows are isolated with Supabase Row Level Security (RLS) and the least-privileged a2cr_app runtime role.
        - Official WorkBaton saves are encrypted locally before upload, so A2CR stores ciphertext for WorkBaton bodies.
        - Supabase and Railway publish SOC 2 / compliance information for their platforms. That helps with vendor risk, but it does not make A2CR itself SOC 2 certified and does not replace A2CR's own RLS, client encryption, key hygiene, and smoke tests.

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

        MCP / A2A / A2CR:
        - MCP connects an AI agent to tools, APIs, and external data.
        - A2A connects AI agents to other AI agents for delegation, communication, and collaboration.
        - A2CR preserves compact work state across AI windows, models, tools, and time so the next session can resume from a clean handoff.
        - A2CR is complementary to MCP and A2A, not a replacement for either protocol.
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
        WorkBatonの公式ルートは、PyPI package a2cr-mcpをa2crという名前のローカルstdio MCP serverとして登録する方法です。

        ルール:
        - resume promptにSlotがある場合は、最初にresume_context(slot_name="...")またはresume_context(slot_number=N)を実行します。
        - list_contextsは、Slotが提示されておらず、ユーザーが検索を求めた場合だけ使います。
        - 作業中は、会話が長くなる前または重要な区切りでsave_contextします。
        - 保存する内容はgoal、current_state、next_action、必要な判断、制約、参照だけに絞ります。
        - APIキー、Authorization header、DB URL、秘密情報、全文ログ、長い会話履歴は保存しません。
        - 自動保存前にはget_account_limitsで制限を確認します。

        FAQ:
        - CLAUDE.md / AGENTS.md はプロジェクトの永続情報です。ルール、設計方針、セットアップ手順を書きます。
        - WorkBaton は今この瞬間の作業状態です。goal, current_state, next_action, validation, blockers を次の AI に渡します。
        - WorkStash は WorkBaton を肥大化させないための一時的な補助メモです。entry_key を WorkBaton に記録します。
        - WorkThreads は複数エージェントの共同作業向けに予定している機能です。現在使う WorkBaton は serial handoff 用です。
        - MCPはAIエージェントをツール、API、外部データへ接続します。A2AはAIエージェント同士を委任・通信・協調のために接続します。A2CRは作業状態をセッション間で引き継ぎます。

        暗号化:
        - local client keyは利用者側が管理します。
        - API keyの全文は発行時に一度だけ表示されます。再発行すると別のAPI keyになります。
        - local client keyファイルはwrapperが初回のclient-encrypted保存時に作成します。A2CR_CLIENT_KEY_FILEでパスを固定でき、A2CR_CONFIG_DIRでworkbaton.keyを置くディレクトリを指定できます。
        - 既定ではWindowsは%APPDATA%\\A2CR\\workbaton.key、macOS/Linuxは$XDG_CONFIG_HOME/a2cr/workbaton.keyまたは~/.config/a2cr/workbaton.keyです。
        - 別のPCで同じWorkBatonを再開するには、A2CR API keyと同じlocal client keyファイルの両方が必要です。
        - client-encrypted WorkBaton Slotは、A2CRサーバーでは復号できません。
        - local client keyを失うと、旧鍵で保存したclient-encrypted Slotは復旧できません。
        - 新しいlocal client keyで保存したSlotは、その新しい鍵で読めます。

        インフラ:
        - ホスト版A2CRはデータ層にSupabase/Postgres、アプリ層にRailwayを使います。
        - ユーザーごとの行分離はSupabase RLSとleast-privileged a2cr_app runtime roleで行います。
        - 公式WorkBaton保存経路では本文を端末側で暗号化してから送信するため、A2CRはWorkBaton本文の暗号文を保存します。
        - SupabaseとRailwayはSOC 2 / compliance情報を公開していますが、A2CR自体がSOC 2認証済みという意味ではありません。
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
        The official WorkBaton path is the PyPI package a2cr-mcp registered as one local stdio MCP server named a2cr.
        Do not use the legacy local SQLite API for WorkBaton saves.

        Rules:
        - When a resume prompt provides a Slot, first call resume_context(slot_name="...") or resume_context(slot_number=N).
        - Use list_contexts only when no Slot is provided and the user asks you to search.
        - During work, call save_context before the conversation gets long or at important milestones.
        - Use WorkBaton and WorkStash proactively when they help preserve useful work state; do not wait for the user to ask.
        - If the conversation feels noisy, contradictory, stale, or polluted by old task state, call should_save_workbaton with reason="context_drift" or reason="context_contamination".
        - If saving is recommended, use the available WorkBaton size budget intelligently, move safe bulky support notes into WorkStash, record the entry_key in WorkBaton, and suggest continuing in a fresh AI window.
        - Save only goal, current_state, next_action, and resume-critical supporting facts.
        - Never save secrets, API keys, Authorization headers, private database URLs, full transcripts, or long logs.
        - Call get_account_limits before automatic saves.

        FAQ:
        - CLAUDE.md and AGENTS.md are project memory: durable rules, conventions, setup notes, and project-level guidance.
        - WorkBaton is current handoff state: goal, current_state, next_action, validation, blockers, and what the next AI should do.
        - WorkStash is temporary supporting memory for safe details that would bloat the WorkBaton. Record returned entry_key values in WorkBaton references or next_action.
        - WorkThreads is planned for multi-agent collaboration. WorkBaton is available now for serial handoff from one AI window to the next.
        - MCP connects agents to tools. A2A connects agents to agents. A2CR carries work state across sessions.

        Encryption:
        - The local client key is managed by the user.
        - The full API key is shown only once when issued. Reissuing creates a different API key.
        - The wrapper creates the local client key file during the first client-encrypted save. A2CR_CLIENT_KEY_FILE fixes the exact path, and A2CR_CONFIG_DIR chooses the directory containing workbaton.key.
        - Defaults are %APPDATA%\\A2CR\\workbaton.key on Windows, and $XDG_CONFIG_HOME/a2cr/workbaton.key or ~/.config/a2cr/workbaton.key on macOS/Linux.
        - To resume from another PC, the user needs both the A2CR API key and the same local client key file.
        - Client-encrypted WorkBaton slots cannot be decrypted by the A2CR server.
        - If the local client key is lost, old client-encrypted slots cannot be recovered.
        - Slots saved after creating a new local client key can be read with that new key.

        Infrastructure:
        - Hosted A2CR uses Supabase/Postgres for the data layer and Railway for the app runtime.
        - User-owned rows are isolated with Supabase RLS and the least-privileged a2cr_app runtime role.
        - Official WorkBaton saves are encrypted locally before upload, so A2CR stores ciphertext for WorkBaton bodies.
        - Supabase and Railway publish SOC 2 / compliance information, but that does not make A2CR itself SOC 2 certified.
        """,
    ),
    "manual": _seo(
        title="A2CR 使用説明書 - セットアップと保存・読み込み",
        description="A2CR のログイン、API key 発行、MCP 設定、AGENTS.md / CLAUDE.md 追記、WorkBaton Slot 保存・読み込み、MCP と WorkStash で AI が受け取る情報をまとめた使用説明書です。",
        canonical="https://a2cr.app/manual",
        alternates={"ja": "https://a2cr.app/manual", "en": "https://a2cr.app/en/manual"},
        machine_text="""
        # A2CR 使用説明書

        このページは、ユーザー向けガイドと AI エージェント向けガイドとは別の実用手順です。

        ログインから初回利用まで:
        - 現在の local stdio MCP wrapper は Python のプログラムです。AI クライアントが裏側で起動するため Python が必要です。
        - 推奨バージョンは Python 3.13 です。Python 3.12 以上なら利用できる想定ですが、迷ったら Python 3.13 を入れてください。
        - Python 3.15 alpha / beta などの開発版は避けてください。
        - ターミナルで python --version を実行するとバージョンを確認できます。
        - Python が使える状態になったら python -m pip install --upgrade a2cr-mcp で PyPI から wrapper をインストールします。
        - A2CR にログインし、Settings で API key を発行します。
        - API keyの全文は発行時に一度だけ表示されます。再発行すると別のAPI keyになるため、MCP設定を更新してください。
        - API key は AI チャットに貼らず、ユーザー自身が MCP 設定ファイルに貼り付けます。
        - MCP 設定では command を a2cr-mcp、args を空配列にします。
        - MCP server 名は a2cr にします。既存 MCP server は消しません。
        - local client keyファイルはa2cr-mcp wrapperが初回のclient-encrypted保存時に作成します。A2CR_CLIENT_KEY_FILEで保存場所を固定できます。
        - 別のPCで同じWorkBatonを再開するには、A2CR API keyと同じlocal client keyファイルの両方が必要です。
        - 新しい AI セッションで get_account_limits と explain_a2cr_flows を呼び、接続と利用可能な flow を確認します。

        AGENTS.md / CLAUDE.md などへの追記:
        - A2CR MCP tools may be used proactively when they help preserve useful work state.
        - Use the configured MCP tools only; do not invent direct HTTP API calls.
        - Use WorkBaton at milestones, after validation, before likely context loss, or when context drift/contamination is detected.
        - Use WorkStash for safe supporting notes that would bloat the WorkBaton.
        - Record WorkStash entry_key values in WorkBaton references or next_action.
        - Never save secrets, API keys, Authorization headers, cookies, private DB URLs, personal data, full transcripts, long logs, generated caches, git diffs, or large source-code bodies.

        Slot への保存:
        - get_account_limits で plan limit、WorkBaton size budget、WorkStash quota を確認します。
        - should_save_workbaton で保存判断を確認します。
        - save_context には goal, current_state, next_action, decisions, blockers, validation, references を compact に入れます。
        - 詳細な file path, API notes, failed attempts, validation notes は WorkStash に分けます。

        Slot からの読み込み:
        - 新しい AI 窓で resume_context(slot_number=N) または resume_context(slot_name="...") を実行します。
        - AI は goal, current_state, next_action, decisions, blockers, validation, references を読みます。
        - Slot metadata, response_language_hint, language_context, agent_continuity_guidance も利用可能な場合があります。
        - WorkStash entry_key がある場合、現在の作業に必要な entry だけ get_work_stash で取得します。

        MCP 接続時に AI が受け取る情報:
        - WorkBaton はサイズ予算内の focused serial checkpoint handoff であり、chat log や file store ではありません。
        - WorkStash は一時的な補助メモであり、永続的な knowledge base ではありません。
        - local stdio wrapper が公式 WorkBaton 保存経路です。A2CR は client-encrypted WorkBaton body を復号できません。
        - explain_a2cr_flows, get_account_limits, should_save_workbaton, save_context, resume_context, get_work_stash などの tool description と safety rule を AI が受け取ります。

        自発利用:
        - MCP tool descriptions、AGENTS.md / CLAUDE.md、読み込んだ WorkBaton が揃うと、対応 AI は必要に応じて WorkBaton / WorkStash を自発利用できます。
        - context drift または context contamination を感じたら should_save_workbaton を呼び、必要なら現在のサイズ予算内で focused WorkBaton を保存して新しい AI 窓への移行を提案します。
        """,
    ),
    "en/manual": _seo(
        title="A2CR Manual - Setup, Save, and Resume",
        description="A practical A2CR manual covering login, API key setup, MCP config, AGENTS.md and CLAUDE.md snippets, WorkBaton Slot save/resume, and what AI agents receive from MCP and WorkStash.",
        canonical="https://a2cr.app/en/manual",
        alternates={"ja": "https://a2cr.app/manual", "en": "https://a2cr.app/en/manual"},
        machine_text="""
        # A2CR Manual

        This page is the practical operating manual separate from the public concept guide and the AI agent guide.

        From sign-in to first use:
        - The current local stdio MCP wrapper is a Python program. The AI client starts it in the background, so Python is required.
        - Recommended version: Python 3.13. Python 3.12 or newer is expected to work, but choose Python 3.13 if unsure.
        - Avoid development builds such as Python 3.15 alpha or beta.
        - Run python --version in a terminal to check the installed version.
        - After Python is available, install the wrapper from PyPI with python -m pip install --upgrade a2cr-mcp.
        - Sign in to A2CR and issue an API key from Settings.
        - The full API key is shown only once when issued. Reissuing creates a different API key, so MCP configs must be updated.
        - Do not paste the API key into AI chat. The user should paste it into the MCP config locally.
        - In the MCP config, set command to a2cr-mcp and args to an empty array.
        - Add exactly one MCP server named a2cr. Preserve existing MCP servers.
        - The a2cr-mcp wrapper creates the local client key file during the first client-encrypted save. A2CR_CLIENT_KEY_FILE can pin the key location.
        - To resume the same WorkBaton from another PC, the user needs both the A2CR API key and the same local client key file.
        - In a new AI session, call get_account_limits and explain_a2cr_flows to verify the connection and learn the available flows.

        Add to AGENTS.md, CLAUDE.md, or another project memory file:
        - A2CR MCP tools may be used proactively when they help preserve useful work state.
        - Use configured MCP tools only; do not invent direct HTTP API calls.
        - Use WorkBaton at milestones, after validation, before likely context loss, or when context drift/contamination is detected.
        - Use WorkStash for safe supporting notes that would bloat the WorkBaton.
        - Record WorkStash entry_key values in WorkBaton references or next_action.
        - Never save secrets, API keys, Authorization headers, cookies, private DB URLs, personal data, full transcripts, long logs, generated caches, git diffs, or large source-code bodies.

        Saving to a Slot:
        - Call get_account_limits to confirm plan limits, WorkBaton size budget, and WorkStash quota.
        - Call should_save_workbaton when the save is discretionary.
        - Save focused goal, current_state, next_action, decisions, blockers, validation, and references with save_context.
        - Move detailed file paths, API notes, failed attempts, and validation notes to WorkStash.

        Reading from a Slot:
        - In a fresh AI window, call resume_context(slot_number=N) or resume_context(slot_name="...").
        - The AI reads goal, current_state, next_action, decisions, blockers, validation, and references.
        - Slot metadata, response_language_hint, language_context, and agent_continuity_guidance may also be available.
        - If WorkStash entry_key values are referenced, call get_work_stash only for entries needed for the current task.

        What the AI receives from MCP:
        - WorkBaton is a compact serial checkpoint handoff, not a chat log or file store.
        - WorkStash is temporary supporting memory, not a durable knowledge base.
        - The local stdio wrapper is the official WorkBaton save path. A2CR cannot decrypt client-encrypted WorkBaton bodies.
        - The AI receives tool descriptions and safety rules for explain_a2cr_flows, get_account_limits, should_save_workbaton, save_context, resume_context, get_work_stash, and related tools.

        Autonomy:
        - With MCP tool descriptions, AGENTS.md / CLAUDE.md, and a loaded WorkBaton, capable AI agents can use WorkBaton and WorkStash proactively when needed.
        - If context drift or context contamination appears, the agent can call should_save_workbaton, save a focused WorkBaton within the current size budget when recommended, and suggest continuing in a fresh AI window.
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
        - 24KB WorkBaton body budget
        - 100 saves per hour
        - 200 loads per hour

        Planned Pro plan:
        - 50 Slots
        - Longer retention options
        - 64KB WorkBaton body budget
        - 300 saves per hour
        - 600 loads per hour
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
