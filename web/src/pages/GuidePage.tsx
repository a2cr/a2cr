import { Bot, CheckCircle2, LayoutDashboard, LogIn, PlugZap, ShieldCheck } from "lucide-react";
import type { ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { CopyButton } from "../components/CopyButton";
import { LanguageToggle } from "../components/LanguageToggle";
import { serviceUrl } from "../lib/format";
import { useAuth } from "../providers/AuthProvider";

type Language = "en" | "ja";
type GuideKind = "human" | "agent";
type ClientKey = "codex" | "generic";

const clientLabels: Record<ClientKey, string> = {
  codex: "Codex",
  generic: "Claude / Cursor / Generic MCP"
};

function mcpConfigSnippet(client: ClientKey): string {
  const url = serviceUrl();
  const baseUrl = (() => {
    try {
      return new URL(url, window.location.origin).origin;
    } catch {
      return url.replace(/\/mcp\/?$/, "");
    }
  })();
  if (client === "codex") {
    return [
      '[mcp_servers."a2cr"]',
      'command = "python"',
      'args = ["<A2CR_REPO>/mcp/server.py"]',
      "",
      '[mcp_servers."a2cr".env]',
      'A2CR_API_KEY = "<A2CR_API_KEY>"',
      `A2CR_BASE_URL = "${baseUrl}"`,
      `A2CR_SERVICE_URL = "${url}"`,
      '# Optional: A2CR_CLIENT_KEY_FILE = "<path-to-workbaton.key>"'
    ].join("\n");
  }
  return JSON.stringify(
    {
      mcpServers: {
        a2cr: {
          command: "python",
          args: ["<A2CR_REPO>/mcp/server.py"],
          env: {
            A2CR_API_KEY: "<A2CR_API_KEY>",
            A2CR_BASE_URL: baseUrl,
            A2CR_SERVICE_URL: url,
            A2CR_CLIENT_KEY_FILE: "<optional-path-to-workbaton.key>"
          }
        }
      }
    },
    null,
    2
  );
}

function agentPrompt(language: Language): string {
  if (language === "ja") {
    return [
      `A2CR service: ${serviceUrl()}`,
      "A2CR MCPを作業記憶として使ってください。",
      "直接HTTP APIを推測せず、A2CR MCPツールだけを使います。",
      "WorkBatonの公式ルートは、a2crという名前のローカルstdio MCPラッパーです。",
      "resume promptにSlotがある場合は、最初にresume_context(slot_name=\"...\")またはresume_context(slot_number=N)を実行します。",
      "list_contextsは、Slotが提示されておらず、ユーザーが検索を求めた場合だけ使います。",
      "作業中は、会話が長くなる前または重要な区切りでsave_contextします。",
      "保存する内容はgoal、current_state、next_action、必要な判断・制約・参照だけに絞ります。",
      "APIキー、Authorization header、DB URL、秘密情報、全文ログ、長い会話履歴は保存しません。",
      "自動保存前にはget_account_limitsで制限を確認します。",
      "読み込み後は、現在のユーザーの言語で続けます。"
    ].join("\n");
  }
  return [
    `A2CR service: ${serviceUrl()}`,
    "Use A2CR MCP as working memory.",
    "Do not guess direct HTTP API endpoints. Use only the A2CR MCP tools.",
    "Use the local stdio MCP wrapper named a2cr as the official WorkBaton path.",
    "When a resume prompt provides a Slot, first call resume_context(slot_name=\"...\") or resume_context(slot_number=N).",
    "Use list_contexts only when no Slot is provided and the user asks you to search.",
    "During work, call save_context before the conversation gets long or at important milestones.",
    "Save only goal, current_state, next_action, and compact supporting facts.",
    "Never save secrets, API keys, Authorization headers, private database URLs, full transcripts, or long logs.",
    "Call get_account_limits before automatic saves.",
    "After loading, continue in the language of the current user message."
  ].join("\n");
}

const text = {
  en: {
    navHuman: "Guide",
    navAgent: "AI agent guide",
    pricing: "Pricing",
    signIn: "Sign in",
    dashboard: "Open dashboard",
    humanTitle: "A2CR guide",
    humanBody:
      "Every time an AI session ends, your context resets. A2CR solves this with WorkBaton checkpoints — compact snapshots of work state that any MCP-capable AI can resume, whether that's a new window, a different model, or the next day.",
    agentTitle: "A2CR guide for AI agents",
    agentBody:
      "You are an AI agent. This page contains everything you need to configure A2CR MCP, understand WorkBaton and WorkStash, and start using them immediately. Read the tool table, save timing rules, and do-not-save list before beginning work.",
    whatTitle: "What A2CR does",
    whatPoints: [
      "WorkBaton saves only the work state the next AI needs to continue — goal, progress, next action, key decisions. Not the full chat history.",
      "WorkStash holds detailed supporting notes separately so the checkpoint stays compact and the next AI retrieves only what it needs."
    ],
    comparisonTitle: "What A2CR is different from",
    comparisonBody:
      "A2CR is not a chat summarizer, a file store, or a sub-agent feature. WorkBaton is a structured work-state handoff — carrying only what the next AI needs to continue, not the whole conversation.",
    agentTeaserTitle: "Let your AI read it",
    agentTeaserBody:
      "Show the AI agent guide to the AI you already use and ask it to explain A2CR in your context. The guide covers tools, rules, save timing, and what never to save — all in a format your AI can act on directly.",
    agentTeaserLink: "Open AI agent guide",
    compressionCompareTitle: "Compression / summarization vs A2CR / WorkBaton",
    compressionCompareHeaders: ["Comparison", "Compression / summarization", "A2CR / WorkBaton"],
    compressionCompareRows: [
      ["Purpose", "Shorten a long conversation", "Pass a state that lets the next AI resume work"],
      ["Scope", "History inside that chat", "Another chat, another AI, or another tool"],
      ["Output", "Summary text", "Work state such as goal / current_state / next_action / blockers"],
      ["Risk", "Can keep old assumptions and noise", "Intentionally keeps only the state needed for the work"],
      ["Storage", "Chat-dependent", "External temporary relay DB"],
      ["Sharing", "Usually inside that AI service", "Shared between MCP-capable agents"],
      ["Deletion", "Depends on the service", "Explicitly expires by TTL"]
    ],
    compressionCompareNote:
      "Compression is a diet for a conversation log. A2CR is a baton for work state.",
    subagentCompareTitle: "Sub-agents vs A2CR",
    subagentCompareHeaders: ["Comparison", "Sub-agent", "A2CR"],
    subagentCompareRows: [
      ["Main use", "Divide work inside the same environment", "Carry the environment itself forward"],
      ["Effective scope", "That chat and its parent agent", "Across ChatGPT / Claude / Codex / Cursor / Roo / local LLMs"],
      ["State sharing", "Depends on the parent agent's context", "Stored in an external temporary relay DB"],
      ["Session movement", "Weak", "Strong"],
      ["External service integration", "Usually weak", "Possible when the tool supports MCP"],
      ["Time limit", "Usually none", "Expires by TTL"],
      ["Neutrality", "Tied to a specific tool", "Aims to be tool-independent"]
    ],
    keyTitle: "Important: local client key",
    keyBody:
      "WorkBaton requires the local stdio MCP wrapper. The wrapper creates a local client key on the user's machine and encrypts WorkBaton content before sending it to A2CR.",
    keyPoints: [
      "The local client key is managed by the user, not by the service administrator.",
      "A2CR stores and returns ciphertext for client-encrypted WorkBaton slots and cannot decrypt those bodies.",
      "If the local client key is lost, older client-encrypted slots cannot be recovered by A2CR.",
      "Creating a new local client key works for future saves, but it cannot decrypt old slots saved with the previous key."
    ],
    encryptionTitle: "Storage modes",
    storageRows: [
      ["Client-encrypted only", "The local stdio MCP wrapper encrypts before upload; A2CR stores and returns ciphertext only."]
    ],
    noOverclaim:
      "WorkBaton bodies are never accepted as plaintext by A2CR. Direct remote HTTP MCP saving is disabled; use the local stdio wrapper so encryption happens before upload. Legacy local SQLite saves are not the official AI-agent path.",
    setupTitle: "MCP setup",
    setupBody:
      "Sign in to A2CR, issue an API key from Settings, then add the local stdio wrapper to your MCP client using the config below. Paste the API key into the config file yourself — never share it in chat. The wrapper creates and manages a local client key on your machine.",
    agentSetupTitle: "MCP setup — step by step",
    agentSetupBody:
      "Follow these steps in order. The API key must be entered by the user — never ask them to share it in chat, never generate or guess one.",
    agentSetupSteps: [
      "Tell the user to sign in at https://a2cr.app/ and go to Settings → API key → Issue new key.",
      "Ask the user to copy the key and paste it into the MCP config themselves. Do not ask them to share it in chat.",
      "Clone the A2CR repository so that mcp/server.py is available on the user's machine.",
      "Add exactly one MCP server named a2cr using the config snippet below that matches the user's client.",
      "Call get_account_limits to verify the connection is working.",
      "Confirm to the user: 'A2CR is connected. I will save WorkBaton checkpoints at task milestones automatically.'"
    ],
    workflowTitle: "Basic workflow",
    workflow: [
      "Sign in to A2CR and issue an API key.",
      "Add one MCP server named a2cr to your MCP client using the local stdio wrapper.",
      "Ask the AI agent to verify the connection with get_account_limits.",
      "Save a WorkBaton before the session gets long or at a clear task boundary.",
      "Resume from the saved Slot in a new window with resume_context."
    ],
    agentRulesTitle: "Rules for AI agents",
    agentRules: [
      "Preserve existing MCP server settings. Do not delete unrelated servers.",
      "Ask the user to paste the API key into the config themselves when possible.",
      "Do not print API keys, Authorization headers, or full secret configs in chat.",
      "Use MCP tools rather than guessed direct HTTP API calls.",
      "Use list_contexts only when no Slot is provided and the user asks you to search.",
      "Do not use the legacy local SQLite API for WorkBaton saves.",
      "Never save secrets, full transcripts, or long logs into WorkBaton.",
      "Use WorkStash for detailed notes that would bloat the WorkBaton — store the returned entry_key in WorkBaton references."
    ],
    connectTitle: "Connect once, then your AI handles the rest",
    connectBody:
      "When your AI client connects to A2CR through MCP, the server sends it a complete set of instructions — what tools exist, when to use them, and what never to save. Your AI reads these before starting work.",
    connectPoints: [
      "Your AI learns WorkBaton rules from the server, not from your prompts.",
      "One instruction at the start of a session is enough: tell the AI to save checkpoints at milestones.",
      "Any MCP-capable AI — Claude, Codex, Gemini, Cursor — receives the same instructions.",
      "No plugin, no custom prompt engineering, no repeated setup."
    ],
    connectPromptLabel: "After connecting, tell your AI once:",
    connectPromptExample: "A2CR is connected. Save a WorkBaton checkpoint at each task milestone.",
    cleanContextTitle: "Clean context vs. compressed context",
    cleanContextBody:
      "Built-in compression shrinks a long conversation. WorkBaton distills it — keeping only what the next AI needs to continue without noise.",
    cleanContextHeaders: ["", "Auto-compression", "WorkBaton distillation"],
    cleanContextRows: [
      ["What it does", "Shortens everything in the conversation", "Extracts only the signal needed for the next step"],
      ["Failed attempts", "Remain as noise, just smaller", "Saved as structured warnings that prevent repetition"],
      ["Old assumptions", "Compressed in, still present", "Left out entirely — fresh start"],
      ["Next AI clarity", "Must process compressed noise", "Receives only goal, state, next action, and blockers"],
      ["Quality over time", "Degrades with each session", "Resets to clean at each checkpoint"]
    ],
    cleanContextNote: "Compression is a diet. WorkBaton is a fresh start.",
    scenarioTitle: "When to use WorkBaton",
    scenarios: [
      {
        title: "Session cuts off mid-task",
        body: "Resume from the last checkpoint without re-explaining anything. The next AI knows exactly where to pick up."
      },
      {
        title: "Switching AI tools or models",
        body: "Start in Claude, continue in Codex or Gemini. WorkBaton carries the work state across tools."
      },
      {
        title: "Long projects spanning multiple days",
        body: "End each session with a WorkBaton checkpoint. Store detailed notes in WorkStash so the core checkpoint stays compact. Start the next session clean, without dragging yesterday's noise forward."
      },
      {
        title: "Handing work to another agent",
        body: "One AI completes a phase, stores key findings in WorkStash, and saves a WorkBaton pointing to them. Another AI picks up from the next action."
      }
    ],
    toolsTitle: "A2CR MCP tools",
    toolsHeaders: ["Tool", "When to call"],
    toolsRows: [
      ["explain_a2cr_flows", "Call first when newly connected or unsure which flow applies."],
      ["should_save_workbaton", "Call when unsure if a checkpoint is appropriate or whether this MCP surface can save."],
      ["get_account_limits", "Call before automatic or large saves to confirm plan limits and detail level."],
      ["save_context", "Call via the local stdio wrapper at task milestones, phase completions, or context pressure."],
      ["resume_context", "Call at the start of a new window to load the last checkpoint."],
      ["load_context", "Call when the slot name or number is already known."],
      ["list_contexts", "Call only when the user asks to search and no slot name is provided."],
      ["delete_context", "Call only when the user explicitly requests deletion."],
      ["should_use_work_stash", "Call when unsure whether a note belongs in WorkStash or inline in the WorkBaton."],
      ["store_work_stash", "Call to save detailed supporting notes that would bloat the WorkBaton — file paths, API findings, failed approaches. Record the returned entry_key in WorkBaton references or next_action."],
      ["get_work_stash", "Call to retrieve a specific stash entry by entry_key. Fetch only what the current task needs."],
      ["list_work_stash", "Call to locate a stash entry when the entry_key is not in the WorkBaton references."],
      ["delete_work_stash", "Call after a task phase completes to remove stash entries that are no longer needed."]
    ],
    saveTriggersTitle: "When to save autonomously",
    saveTriggers: [
      "The conversation is getting long or context window pressure is detected.",
      "A coherent task phase or milestone is complete.",
      "Tests, builds, or important checks just passed.",
      "The next concrete action is clear and should survive a new window.",
      "The user is about to switch tools, models, or windows.",
      "A new window just resumed from a WorkBaton and state has materially changed.",
      "There is a blocker that another window or agent should continue from later."
    ],
    doNotSaveTitle: "When not to save",
    doNotSave: [
      "Prohibited material is present: secrets, API keys, auth headers, private DB URLs, .env content, or personal data.",
      "The only content is a full transcript, long logs, generated caches, build artifacts, or large source files.",
      "The next_action is not yet clear — wait for a stable boundary.",
      "The user explicitly asked not to save.",
      "You are on the remote MCP surface only and cannot reach the local stdio wrapper."
    ],
    workbatonSectionTitle: "WorkBaton",
    workbatonSectionBody: "A compact, structured snapshot of where work stands. Saved at task milestones and loaded by the next AI to continue without re-explanation.",
    workbatonPoints: [
      "Saves goal, current progress, next action, key decisions, and blockers — nothing more than what the next AI needs.",
      "Encrypted on your machine before upload. A2CR stores ciphertext only and cannot read the body.",
      "Any MCP-capable AI — Claude, Codex, Cursor, Gemini — can resume from the same checkpoint.",
      "Session cuts, model switches, and multi-day projects all become routine handoffs instead of lost work."
    ],
    workstashSectionTitle: "WorkStash — supporting memory for WorkBaton",
    workstashSectionBody: "WorkBaton stays compact by design. When detailed notes — confirmed file paths, API findings, failed approaches, or intermediate results — would bloat the checkpoint, store them in WorkStash instead. Record the entry_key in the WorkBaton references field so the next window retrieves only what it needs.",
    workstashPoints: [
      "Store supporting notes with store_work_stash and record the entry_key in WorkBaton references or next_action.",
      "Retrieve only the entries needed for the current task with get_work_stash(entry_key).",
      "Delete entries with delete_work_stash when a task phase completes and the note is no longer useful.",
      "Never store secrets, API keys, auth headers, private database URLs, full transcripts, or large source files in WorkStash.",
      "WorkStash is temporary supporting memory — not a durable knowledge base or file store."
    ],
    combinedTitle: "WorkBaton + WorkStash together",
    combinedBody: "WorkBaton is the spine. WorkStash is the detail. Together they give you an AI that arrives at each new session knowing exactly where to go and what it already learned.",
    combinedPoints: [
      "The WorkBaton stays compact because detailed notes live in WorkStash — fast to load, focused on direction.",
      "The next AI reads the checkpoint first, then retrieves only the WorkStash entries it actually needs.",
      "Failed approaches stored in WorkStash prevent the next window from repeating the same mistake.",
      "Every session starts with clean context and peak performance — no re-explanation from the user.",
      "Selective retrieval means fewer tokens per session, so subscription limits go further."
    ],
    batonThreadsTitle: "WorkBaton vs WorkThreads",
    batonThreadsBody: "A2CR has two flows. WorkBaton is available now. WorkThreads is planned for a future release.",
    batonThreadsHeaders: ["", "WorkBaton", "WorkThreads"],
    batonThreadsRows: [
      ["Shape", "Serial checkpoint handoff", "Collaborative multi-agent workspace"],
      ["Flow", "window → new window", "agent ↔ agents"],
      ["Save path", "Local stdio wrapper only — client-encrypted before upload", "Remote MCP — encrypted at rest by A2CR"],
      ["Primary use", "Resume work in a new session or tool", "Coordinate tasks between multiple agents"],
      ["Key tools", "save_context / resume_context", "create_workthread / post_workthread_message"]
    ],
    chainedHandoffTitle: "Chained handoffs",
    chainedHandoffBody:
      "When continuing from a previous WorkBaton, link the chain so the next AI understands the full context:",
    chainedHandoffPoints: [
      "previous_slot — the slot this save continues from.",
      "completed_since_previous — work completed after the prior slot was loaded.",
      "remaining_tasks_ordered — ordered next tasks for the next AI.",
      "validation — test results, build outcomes, and smoke checks.",
      "do_not_use_slots — stale slots and why to avoid them."
    ],
    copyConfig: "Copy config",
    copyPrompt: "Copy prompt"
  },
  ja: {
    navHuman: "ガイド",
    navAgent: "AI向けガイド",
    pricing: "料金",
    signIn: "ログイン",
    dashboard: "ダッシュボード",
    humanTitle: "A2CR ガイド",
    humanBody:
      "AIのセッションが終わるたびに、積み上げた文脈がリセットされます。A2CRはWorkBatonチェックポイントでこれを解決します。作業状態をコンパクトなスナップショットとして保存し、新しいウィンドウ・別モデル・翌日から、どのMCP対応AIでも続きを再開できます。",
    agentTitle: "A2CR AIエージェント向けガイド",
    agentBody:
      "あなたはAIエージェントです。このページにはA2CR MCPの設定、WorkBatonとWorkStashの使い方、即座に利用を開始するために必要なことが全て記載されています。作業を始める前に、ツール一覧・保存タイミング・保存禁止事項を確認してください。",
    whatTitle: "A2CRがすること",
    whatPoints: [
      "WorkBatonは次のAIが続きに必要な作業状態だけを保存します。goal・進捗・次のアクション・判断事項。会話履歴全体ではありません。",
      "WorkStashが詳細な補助メモを別に保管するので、チェックポイントはコンパクトに保たれ、次のAIは必要なものだけを取り出せます。"
    ],
    comparisonTitle: "A2CRが何と違うか",
    comparisonBody:
      "A2CRはチャット要約でも、ファイル保存機能でも、サブエージェント機能でもありません。WorkBatonは構造化された作業状態の引き継ぎ — 次のAIが続きに必要なものだけを渡します。",
    agentTeaserTitle: "読むより、AIに読ませる",
    agentTeaserBody:
      "AI向けガイドを、ふだん使っているAIに見せて「このアプリを説明して」と頼んでください。ツール一覧・保存ルール・タイミング・禁止事項まで、そのままAIが動けるフォーマットで書かれています。",
    agentTeaserLink: "AI向けガイドを見る",
    compressionCompareTitle: "圧縮・要約機能との違い",
    compressionCompareHeaders: ["比較", "圧縮・要約機能", "A2CR / WorkBaton"],
    compressionCompareRows: [
      ["目的", "長い会話を短くする", "次のAIが作業再開できる状態を渡す"],
      ["対象", "そのチャット内の履歴", "別チャット・別AI・別ツール"],
      ["出力", "要約文", "goal / current_state / next_action / blockers などの作業状態"],
      ["問題点", "古い前提やノイズを拾うことがある", "必要な作業状態だけを意図的に残す"],
      ["保存", "チャット依存", "外部の一時リレーDB"],
      ["共有", "基本そのAI/そのサービス内", "MCP対応エージェント間で共有"],
      ["消去", "サービス側仕様次第", "TTLで明示的に消える"]
    ],
    compressionCompareNote:
      "圧縮機能は、ざっくり言えば「会話ログのダイエット」です。A2CRは「作業状態のバトン」です。",
    subagentCompareTitle: "サブエージェントとの違い",
    subagentCompareHeaders: ["比較", "サブエージェント", "A2CR"],
    subagentCompareRows: [
      ["主な用途", "同じ環境内で分業する", "環境をまたいで引き継ぐ"],
      ["有効範囲", "そのチャット・その親エージェント内", "ChatGPT / Claude / Codex / Cursor / Roo / ローカルLLMなど横断"],
      ["状態共有", "親エージェントの文脈に依存", "外部の一時リレーDBに保存"],
      ["セッション移動", "弱い", "強い"],
      ["別サービス連携", "基本弱い", "MCP対応なら可能"],
      ["時間削除", "基本なし", "TTLで消える"],
      ["中立性", "特定ツール依存", "ツール非依存を狙える"]
    ],
    keyTitle: "重要: local client key",
    keyBody:
      "WorkBatonではローカルstdio MCP wrapperを使います。このwrapperがユーザーの端末上でlocal client keyを作り、WorkBaton本文を暗号化してからA2CRへ送ります。",
    keyPoints: [
      "local client keyは利用者側が管理します。サービス管理者は管理しません。",
      "client-encrypted Slotでは、A2CRは暗号文だけを保存・返却し、本文を復号できません。",
      "local client keyを失うと、過去にその鍵で保存したclient-encrypted SlotはA2CR側でも復旧できません。",
      "local client keyを作り直した後に新しく保存したSlotは読めますが、旧鍵で保存したSlotは旧鍵なしでは読めません。"
    ],
    encryptionTitle: "保存方式",
    storageRows: [
      ["Client-encryptedのみ", "ローカルstdio MCP wrapperが送信前に暗号化し、A2CRは暗号文だけを保存・返却します。"]
    ],
    noOverclaim:
      "A2CRはWorkBaton本文の平文保存を受け付けません。直接HTTP MCPからの保存は無効化し、ローカルstdio wrapperで暗号化してから送る前提です。",
    setupTitle: "MCP設定",
    setupBody:
      "A2CRにサインインし、設定からAPIキーを発行後、下の設定スニペットを使いMCPクライアントにローカルstdio wrapperを追加します。APIキーはご自身で設定ファイルに貼り付けてください。チャットでは共有しないでください。wrapperがlocal client keyを端末上に作成・管理します。",
    agentSetupTitle: "MCP設定 — 手順",
    agentSetupBody:
      "以下の手順を順番に実行します。APIキーはユーザー本人が貼り付けます。チャットで共有させず、生成・推測も禁止です。",
    agentSetupSteps: [
      "ユーザーに https://a2cr.app/ でサインインし、設定 → APIキー → 新しいキーを発行 を行ってもらいます。",
      "コピーしたAPIキーをMCPの設定ファイルに自分で貼り付けてもらいます。チャットでは共有させないでください。",
      "A2CRリポジトリをクローンし、mcp/server.py がユーザーの端末上に用意されるようにします。",
      "下の設定スニペットを使い、ユーザーのクライアント（Codex または Generic）に合わせてa2crという名前のMCPサーバーを1つ追加します。",
      "get_account_limits を呼び出して接続を確認します。",
      "ユーザーに伝えます：「A2CRが接続されました。作業の節目でWorkBatonチェックポイントを自動的に保存します。」"
    ],
    workflowTitle: "基本の流れ",
    workflow: [
      "A2CRへログインし、APIキーを発行します。",
      "ローカルstdio wrapperを使い、a2crという名前のMCP serverを1つだけ追加します。",
      "AIエージェントにget_account_limitsで接続確認してもらいます。",
      "会話が長くなる前、または作業の区切りでWorkBatonを保存します。",
      "新しい窓でresume_contextを使い、保存したSlotから再開します。"
    ],
    agentRulesTitle: "AIエージェントのルール",
    agentRules: [
      "既存のMCP server設定を消さず、関係ない設定を保持します。",
      "可能ならAPIキーの貼り付けはユーザー本人に行ってもらいます。",
      "APIキー、Authorization header、secretをチャットやログに表示しません。",
      "HTTP APIを推測せず、MCPツールを使います。",
      "list_contextsは、Slotが提示されておらず、ユーザーが検索を求めた場合だけ使います。",
      "秘密情報、全文履歴、長いログをWorkBatonに保存しません。",
      "WorkBatonを肥大化させる詳細メモはWorkStashに保存し、WorkBatonのreferencesにentry_keyを記録する。"
    ],
    connectTitle: "一度接続すれば、あとはAIが自律的に動く",
    connectBody:
      "AIクライアントがMCPでA2CRに接続すると、サーバーはAIにツール一覧と完全な指示を送ります。どのツールをいつ使うか、何を保存してはいけないか — これをAIは作業前に読み込みます。",
    connectPoints: [
      "WorkBatonのルールはサーバーから届く。プロンプトに毎回書く必要はない。",
      "セッション開始時に一言伝えるだけで十分。あとはAIが自律的に保存タイミングを判断する。",
      "Claude、Codex、Gemini、Cursorなど、MCP対応AIなら同じ指示を受け取る。",
      "プラグイン不要、プロンプトエンジニアリング不要、毎回のセットアップ不要。"
    ],
    connectPromptLabel: "接続後、AIに一度だけ伝える：",
    connectPromptExample: "A2CRが接続されています。作業の節目でWorkBatonチェックポイントを保存してください。",
    cleanContextTitle: "綺麗なコンテキスト vs 圧縮されたコンテキスト",
    cleanContextBody:
      "組み込みの圧縮機能は長い会話を短くします。WorkBatonは蒸留します — 次のAIが続きに必要な情報だけを抽出する。",
    cleanContextHeaders: ["", "自動圧縮", "WorkBaton蒸留"],
    cleanContextRows: [
      ["やること", "会話の全体を短くする", "次のステップに必要なシグナルだけを抽出する"],
      ["失敗した試行", "ノイズとして残る（小さくなるだけ）", "繰り返しを防ぐ構造化された警告として保存される"],
      ["古い前提", "圧縮されたまま残る", "完全に取り除かれる — 新鮮なスタート"],
      ["次のAIの明瞭さ", "圧縮されたノイズを処理しなければならない", "goal・現在地・次のアクション・ブロッカーだけを受け取る"],
      ["品質の変化", "セッションごとに劣化する", "チェックポイントごとに綺麗にリセットされる"]
    ],
    cleanContextNote: "圧縮はダイエット。WorkBatonはリフレッシュ。",
    scenarioTitle: "WorkBatonを使う場面",
    scenarios: [
      {
        title: "作業中にセッションが切れた",
        body: "最後のチェックポイントから再開。再説明は不要で、次のAIはどこから続けるか正確に把握している。"
      },
      {
        title: "AIツールやモデルを切り替える",
        body: "Claudeで始めてCodexやGeminiで続ける。WorkBatonが作業状態をツールをまたいで運ぶ。"
      },
      {
        title: "複数日にわたる長いプロジェクト",
        body: "セッション終了時にWorkBatonチェックポイントを保存。詳細メモはWorkStashに保管してコアを軽く保ちます。次のセッションは昨日のノイズを引きずらずクリーンに始まります。"
      },
      {
        title: "別のエージェントへ作業を引き継ぐ",
        body: "あるAIがフェーズを完了し、調査結果をWorkStashに保存してそれを参照するWorkBatonを作成。別のAIが次のアクションから作業を開始する。"
      }
    ],
    toolsTitle: "A2CR MCPツール一覧",
    toolsHeaders: ["ツール", "呼ぶタイミング"],
    toolsRows: [
      ["explain_a2cr_flows", "接続直後、またはどのフローを使うか迷ったとき最初に呼ぶ。"],
      ["should_save_workbaton", "チェックポイントが適切か、このMCP面から保存できるか確認したいとき。"],
      ["get_account_limits", "自動保存や大きな保存の前に、プラン制限と保存粒度を確認する。"],
      ["save_context", "ローカルstdio wrapper経由で、作業の節目・フェーズ完了・コンテキスト圧迫時に呼ぶ。"],
      ["resume_context", "新しいウィンドウの最初に呼んで、最後のチェックポイントを読み込む。"],
      ["load_context", "スロット名または番号がすでに分かっている場合の直接ロード。"],
      ["list_contexts", "ユーザーが検索を求めており、スロット名が提示されていない場合のみ使う。"],
      ["delete_context", "ユーザーが明示的に削除を要求した場合のみ使う。"],
      ["should_use_work_stash", "メモをWorkStashに保存すべきか、WorkBatonにインラインで書くべきか迷ったとき。"],
      ["store_work_stash", "WorkBatonを肥大化させる詳細メモ（ファイルパス・API調査・失敗した試み）を保存する。返ったentry_keyをWorkBatonのreferencesまたはnext_actionに記録する。"],
      ["get_work_stash", "entry_keyを指定して特定のスタッシュエントリを取り出す。現在のタスクに必要なものだけ取得する。"],
      ["list_work_stash", "entry_keyが分からないときにスタッシュエントリを探す。"],
      ["delete_work_stash", "タスクフェーズ完了後、不要になったスタッシュエントリを削除する。"]
    ],
    saveTriggersTitle: "自律的に保存するタイミング",
    saveTriggers: [
      "会話が長くなってきた、またはコンテキストウィンドウの圧迫を感じた。",
      "一貫した作業フェーズや区切りが完了した。",
      "テスト・ビルド・重要な確認が通った直後。",
      "次の具体的なアクションが明確で、新しいウィンドウに引き継ぐ価値がある。",
      "ユーザーがツール・モデル・ウィンドウを切り替えようとしている。",
      "新しいウィンドウがWorkBatonから再開し、状態が実質的に変化した。",
      "別のウィンドウやエージェントが後で続けるべきブロッカーがある。"
    ],
    doNotSaveTitle: "保存してはいけないとき",
    doNotSave: [
      "禁止コンテンツが含まれる：secret、APIキー、認証ヘッダー、プライベートDB URL、.env、個人データ。",
      "内容が会話全文・長大ログ・生成キャッシュ・ビルド成果物・大きなソースファイルのみ。",
      "next_actionがまだ明確でない — 安定した区切りまで待つ。",
      "ユーザーが保存しないよう明示的に指示した。",
      "リモートMCP面のみで接続しており、ローカルstdio wrapperに届かない。"
    ],
    workbatonSectionTitle: "WorkBaton",
    workbatonSectionBody: "作業の現在地をコンパクトに構造化したスナップショット。作業の節目に保存し、次のAIが再説明なしに続きから動けます。",
    workbatonPoints: [
      "goal・現在の進捗・次のアクション・判断事項・ブロッカーだけを保存。次のAIが必要な情報のみです。",
      "アップロード前にあなたの端末で暗号化されます。A2CRは暗号文のみを保存し、本文を読むことはできません。",
      "MCP対応のAI（Claude・Codex・Cursor・Geminiなど）なら、同じチェックポイントから再開できます。",
      "セッション切れ・モデル切り替え・複数日プロジェクトが、いずれも失われた作業ではなく通常の引き継ぎになります。"
    ],
    workstashSectionTitle: "WorkStash — WorkBatonを補う一時メモ",
    workstashSectionBody: "WorkBatonはコンパクトさが前提です。確認済みファイルパス・API調査結果・失敗した試み・中間結果など、チェックポイントを肥大化させる詳細メモはWorkStashに保管します。entry_keyをWorkBatonのreferencesまたはnext_actionに記録し、次のウィンドウが必要なものだけ取り出せるようにします。",
    workstashPoints: [
      "store_work_stashで補助メモを保存し、entry_keyをWorkBatonのreferencesまたはnext_actionに記録する。",
      "get_work_stash(entry_key)で、現在のタスクに必要なエントリだけを取り出す。",
      "タスクフェーズが完了してメモが不要になったらdelete_work_stashで削除する。",
      "シークレット・APIキー・認証ヘッダー・プライベートDB URL・全文履歴・大きなソースファイルはWorkStashに保存しない。",
      "WorkStashは一時的な補助メモであり、永続的なナレッジベースやファイル保存場所ではない。"
    ],
    combinedTitle: "WorkBaton + WorkStash を組み合わせると",
    combinedBody: "WorkBatonが骨格で、WorkStashが詳細です。組み合わせることで、新しいセッションに来たAIは「どこへ向かうか」と「すでに何を調べたか」の両方を持っています。",
    combinedPoints: [
      "詳細メモはWorkStashに分離されるので、WorkBatonは常に軽くすぐに読み込める。",
      "次のAIはまずチェックポイントで方向を確認し、実際に必要なWorkStashエントリだけを取り出して動く。",
      "WorkStashに記録した失敗した試みが、次のウィンドウが同じ過ちを繰り返すことを防ぐ。",
      "毎回クリーンなコンテキストでスタート。ピークのパフォーマンス、ユーザーからの再説明ゼロ。",
      "選択的な取得でセッションあたりのトークン消費が抑えられ、サブスクの使用量が節約できる。"
    ],
    batonThreadsTitle: "WorkBaton vs WorkThreads",
    batonThreadsBody: "A2CRには2つのフローがある。WorkBatonは現在利用可能。WorkThreadsは将来のリリースで提供予定。",
    batonThreadsHeaders: ["", "WorkBaton", "WorkThreads"],
    batonThreadsRows: [
      ["形状", "シリアルチェックポイント引き継ぎ", "複数エージェントの協調ワークスペース"],
      ["フロー", "window → 新しいwindow", "agent ↔ agents"],
      ["保存パス", "ローカルstdio wrapperのみ（送信前にクライアント暗号化）", "リモートMCP（A2CRがサーバー側で暗号化）"],
      ["主な用途", "新しいセッションやツールで作業を再開する", "複数エージェント間でタスクを調整する"],
      ["主なツール", "save_context / resume_context", "create_workthread / post_workthread_message"]
    ],
    chainedHandoffTitle: "チェーン引き継ぎ",
    chainedHandoffBody:
      "前のWorkBatonから続ける場合は、以下のフィールドでチェーンをつなぐと次のAIが全体の文脈を理解できる：",
    chainedHandoffPoints: [
      "previous_slot — このセーブが引き継ぐ前のスロット情報。",
      "completed_since_previous — 前のスロットをロードした後に完了した作業。",
      "remaining_tasks_ordered — 次のAIへの優先順タスク一覧。",
      "validation — テスト結果・ビルド成果・スモークチェックの記録。",
      "do_not_use_slots — 陳腐化したスロットと使ってはいけない理由。"
    ],
    copyConfig: "設定をコピー",
    copyPrompt: "プロンプトをコピー"
  }
};

function PublicHeader({ language, kind }: { language: Language; kind: GuideKind }) {
  const { session } = useAuth();
  const humanPath = language === "ja" ? "/guide" : "/en/guide";
  const agentPath = language === "ja" ? "/agent-guide" : "/en/agent-guide";
  const t = text[language];

  return (
    <header className="border-b border-neutral-200 bg-white">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-4 py-4 sm:px-6">
        <Link to="/" className="flex items-center gap-3">
          <img src="/brand/a2cr-logo.png" alt="A2CR" className="h-8 w-auto object-contain" />
          <span className="sr-only">A2CR</span>
        </Link>
        <div className="flex flex-wrap items-center justify-end gap-2">
          <Link
            to={humanPath}
            className={`rounded-md px-3 py-2 text-sm font-medium ${kind === "human" ? "bg-neutral-900 text-white" : "text-neutral-700 hover:bg-neutral-100"}`}
          >
            {t.navHuman}
          </Link>
          <Link
            to={agentPath}
            className={`rounded-md px-3 py-2 text-sm font-medium ${kind === "agent" ? "bg-neutral-900 text-white" : "text-neutral-700 hover:bg-neutral-100"}`}
          >
            {t.navAgent}
          </Link>
          <Link to="/pricing" className="rounded-md px-3 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-100">
            {t.pricing}
          </Link>
          <Link to={session ? "/dashboard" : "/login"} className="rounded-md px-3 py-2 text-sm font-medium text-emerald-800 hover:bg-emerald-50">
            {session ? t.dashboard : t.signIn}
          </Link>
          <LanguageToggle />
        </div>
      </div>
    </header>
  );
}

function Section({
  eyebrow,
  title,
  body,
  children
}: {
  eyebrow: string;
  title: string;
  body?: string;
  children?: ReactNode;
}) {
  return (
    <section className="mx-auto grid max-w-7xl gap-6 px-4 py-10 sm:px-6 lg:grid-cols-[0.8fr_1.2fr]">
      <div>
        <div className="text-xs font-semibold uppercase tracking-normal text-emerald-700">{eyebrow}</div>
        <h2 className="mt-2 text-2xl font-semibold tracking-normal text-neutral-950">{title}</h2>
        {body && <p className="mt-3 max-w-3xl text-sm leading-6 text-neutral-600">{body}</p>}
      </div>
      <div>{children}</div>
    </section>
  );
}

function BulletList({ items }: { items: string[] }) {
  return (
    <ul className="grid gap-3">
      {items.map((item) => (
        <li key={item} className="flex gap-3 rounded-md border border-neutral-200 bg-white p-4 text-sm leading-6 text-neutral-700">
          <CheckCircle2 className="mt-1 size-4 shrink-0 text-emerald-700" aria-hidden="true" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

function ComparisonTable({
  title,
  headers,
  rows,
  note
}: {
  title: string;
  headers: string[];
  rows: string[][];
  note?: string;
}) {
  return (
    <article className="rounded-md border border-neutral-200 bg-white">
      <div className="border-b border-neutral-200 px-4 py-3">
        <h3 className="font-semibold text-neutral-950">{title}</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[720px] text-left text-sm">
          <thead className="bg-neutral-50 text-neutral-950">
            <tr>
              {headers.map((header) => (
                <th key={header} className="border-b border-neutral-200 px-4 py-3 font-semibold">
                  {header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map(([label, first, second]) => (
              <tr key={label} className="border-b border-neutral-100 last:border-b-0">
                <th className="w-36 px-4 py-3 align-top font-semibold text-neutral-950">{label}</th>
                <td className="px-4 py-3 align-top leading-6 text-neutral-700">{first}</td>
                <td className="px-4 py-3 align-top leading-6 text-neutral-700">{second}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {note && <p className="border-t border-neutral-100 px-4 py-3 text-sm font-semibold leading-6 text-neutral-800">{note}</p>}
    </article>
  );
}

function PlainSection({
  eyebrow,
  title,
  body,
  children
}: {
  eyebrow: string;
  title: string;
  body?: string;
  children?: ReactNode;
}) {
  return (
    <section className="border-t border-neutral-200 py-8">
      <div className="text-xs font-semibold uppercase tracking-normal text-neutral-500">{eyebrow}</div>
      <h2 className="mt-2 text-xl font-semibold tracking-normal text-neutral-950">{title}</h2>
      {body && <p className="mt-3 text-sm leading-6 text-neutral-700">{body}</p>}
      {children && <div className="mt-4">{children}</div>}
    </section>
  );
}

function PlainBulletList({ items }: { items: string[] }) {
  return (
    <ul className="list-disc space-y-2 pl-5 text-sm leading-6 text-neutral-700">
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}

export function GuidePage() {
  const { i18n } = useTranslation();
  const { session } = useAuth();
  const location = useLocation();
  const language: Language = location.pathname.startsWith("/en/") ? "en" : i18n.language.startsWith("ja") ? "ja" : "en";
  const kind: GuideKind = location.pathname.includes("agent-guide") ? "agent" : "human";
  const t = text[language];
  const title = kind === "agent" ? t.agentTitle : t.humanTitle;
  const body = kind === "agent" ? t.agentBody : t.humanBody;
  const prompt = agentPrompt(language);

  if (kind === "agent") {
    return (
      <div className="min-h-screen bg-white text-neutral-950">
        <PublicHeader language={language} kind={kind} />
        <main className="mx-auto max-w-4xl px-4 py-10 sm:px-6">
          <div className="pb-8">
            <h1 className="text-3xl font-semibold tracking-normal sm:text-4xl">{title}</h1>
            <p className="mt-4 max-w-3xl text-sm leading-6 text-neutral-700">{body}</p>
          </div>

          <PlainSection eyebrow="A2CR" title={t.whatTitle}>
            <PlainBulletList items={t.whatPoints} />
          </PlainSection>

          <PlainSection eyebrow="WorkBaton" title={t.workbatonSectionTitle} body={t.workbatonSectionBody}>
            <PlainBulletList items={t.workbatonPoints} />
          </PlainSection>

          <PlainSection eyebrow="WorkStash" title={t.workstashSectionTitle} body={t.workstashSectionBody}>
            <PlainBulletList items={t.workstashPoints} />
          </PlainSection>

          <PlainSection eyebrow="Together" title={t.combinedTitle} body={t.combinedBody}>
            <PlainBulletList items={t.combinedPoints} />
          </PlainSection>

          <PlainSection eyebrow="Setup" title={t.agentSetupTitle} body={t.agentSetupBody}>
            <PlainBulletList items={t.agentSetupSteps} />
            <div className="mt-4 grid gap-3">
              {(Object.keys(clientLabels) as ClientKey[]).map((client) => {
                const snippet = mcpConfigSnippet(client);
                return (
                  <div key={client}>
                    <div className="mb-2 flex items-center justify-between gap-3">
                      <div className="text-sm font-semibold text-neutral-950">{clientLabels[client]}</div>
                      <CopyButton value={snippet} label={t.copyConfig} compact />
                    </div>
                    <pre className="overflow-auto rounded-md bg-neutral-950 p-3 text-xs leading-5 text-neutral-50">{snippet}</pre>
                  </div>
                );
              })}
            </div>
          </PlainSection>

          <PlainSection eyebrow="Workflow" title={t.workflowTitle}>
            <PlainBulletList items={t.workflow} />
          </PlainSection>

          <PlainSection eyebrow="Connect first" title={t.connectTitle} body={t.connectBody}>
            <PlainBulletList items={t.connectPoints} />
            <div className="mt-4 rounded-md border border-emerald-200 bg-emerald-50 p-3">
              <div className="mb-1 text-xs font-semibold text-emerald-700">{t.connectPromptLabel}</div>
              <pre className="whitespace-pre-wrap text-xs leading-5 text-emerald-900">{t.connectPromptExample}</pre>
            </div>
          </PlainSection>

          <PlainSection eyebrow="Tools" title={t.toolsTitle}>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-neutral-200">
                    {t.toolsHeaders.map((h) => (
                      <th key={h} className="pb-2 pr-4 font-semibold text-neutral-950">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {t.toolsRows.map(([tool, when]) => (
                    <tr key={tool} className="border-t border-neutral-100">
                      <td className="w-56 py-2 pr-4 align-top font-mono text-xs font-semibold text-neutral-950">{tool}</td>
                      <td className="py-2 leading-6 text-neutral-700">{when}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </PlainSection>

          <PlainSection eyebrow="Save timing" title={t.saveTriggersTitle}>
            <PlainBulletList items={t.saveTriggers} />
          </PlainSection>

          <PlainSection eyebrow="Do not save" title={t.doNotSaveTitle}>
            <PlainBulletList items={t.doNotSave} />
          </PlainSection>

          <PlainSection eyebrow="WorkBaton vs WorkThreads" title={t.batonThreadsTitle} body={t.batonThreadsBody}>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[560px] text-left text-sm">
                <thead>
                  <tr className="border-b border-neutral-200">
                    {t.batonThreadsHeaders.map((h, i) => (
                      <th key={i} className="pb-2 pr-4 font-semibold text-neutral-950">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {t.batonThreadsRows.map(([label, baton, threads]) => (
                    <tr key={label} className="border-t border-neutral-100">
                      <th className="w-28 py-2 pr-4 align-top font-semibold text-neutral-950">{label}</th>
                      <td className="py-2 pr-4 align-top leading-6 text-neutral-700">{baton}</td>
                      <td className="py-2 leading-6 text-neutral-700">{threads}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </PlainSection>

          <PlainSection eyebrow="Chained handoff" title={t.chainedHandoffTitle} body={t.chainedHandoffBody}>
            <PlainBulletList items={t.chainedHandoffPoints} />
          </PlainSection>

          <PlainSection eyebrow="Security" title={t.keyTitle} body={t.keyBody}>
            <PlainBulletList items={t.keyPoints} />
          </PlainSection>

          <PlainSection eyebrow="Encryption" title={t.encryptionTitle} body={t.noOverclaim}>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <tbody>
                  {t.storageRows.map(([mode, description]) => (
                    <tr key={mode} className="border-t border-neutral-200 first:border-t-0">
                      <th className="w-48 py-3 pr-4 font-semibold text-neutral-950">{mode}</th>
                      <td className="py-3 leading-6 text-neutral-700">{description}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </PlainSection>

          <PlainSection eyebrow="Agent" title={t.agentRulesTitle}>
            <PlainBulletList items={t.agentRules} />
          </PlainSection>

          <PlainSection eyebrow="Prompt" title="Semi-automation prompt">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div className="text-sm font-semibold">A2CR MCP</div>
              <CopyButton value={prompt} label={t.copyPrompt} compact />
            </div>
            <pre className="max-h-96 overflow-auto whitespace-pre-wrap border border-neutral-200 bg-neutral-50 p-3 text-xs leading-5 text-neutral-800">
              {prompt}
            </pre>
          </PlainSection>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-neutral-50 text-neutral-950">
      <PublicHeader language={language} kind={kind} />
      <main>
        <section className="border-b border-neutral-200 bg-white">
          <div className="mx-auto grid max-w-7xl gap-8 px-4 py-14 sm:px-6 lg:grid-cols-[0.95fr_1.05fr] lg:items-center">
            <div>
              <img src="/brand/a2cr-logo.png" alt="A2CR" className="mb-6 w-full max-w-md object-contain" />
              <h1 className="max-w-3xl text-4xl font-semibold tracking-normal sm:text-5xl">{title}</h1>
              <p className="mt-5 max-w-2xl text-base leading-7 text-neutral-600">{body}</p>
              <div className="mt-8 flex flex-wrap gap-3">
                <Link
                  to={session ? "/dashboard" : "/login"}
                  className="inline-flex h-11 items-center gap-2 rounded-md bg-emerald-700 px-4 text-sm font-semibold text-white hover:bg-emerald-800"
                >
                  {session ? <LayoutDashboard className="size-4" /> : <LogIn className="size-4" />}
                  {session ? t.dashboard : t.signIn}
                </Link>
                <Link
                  to={language === "ja" ? "/agent-guide" : "/en/agent-guide"}
                  className="inline-flex h-11 items-center gap-2 rounded-md border border-neutral-300 bg-white px-4 text-sm font-semibold text-neutral-800 hover:bg-neutral-100"
                >
                  <Bot className="size-4" aria-hidden="true" />
                  {t.navAgent}
                </Link>
              </div>
            </div>
            <div className="grid gap-3">
              <article className="rounded-md border border-red-200 bg-red-50 p-4">
                <div className="flex items-start gap-3">
                  <ShieldCheck className="mt-1 size-5 shrink-0 text-red-700" aria-hidden="true" />
                  <div>
                    <h2 className="font-semibold text-red-950">{t.keyTitle}</h2>
                    <p className="mt-2 text-sm leading-6 text-red-900">{t.keyBody}</p>
                  </div>
                </div>
              </article>
              <article className="rounded-md border border-neutral-200 bg-neutral-50 p-4">
                <div className="flex items-start gap-3">
                  <PlugZap className="mt-1 size-5 shrink-0 text-emerald-700" aria-hidden="true" />
                  <p className="text-sm leading-6 text-neutral-700">{t.noOverclaim}</p>
                </div>
              </article>
              <article className="rounded-md border border-neutral-200 bg-white p-4">
                <div className="flex items-start gap-3">
                  <Bot className="mt-1 size-5 shrink-0 text-neutral-700" aria-hidden="true" />
                  <div>
                    <h2 className="font-semibold text-neutral-950">{t.agentTeaserTitle}</h2>
                    <p className="mt-2 text-sm leading-6 text-neutral-700">{t.agentTeaserBody}</p>
                    <Link
                      to={language === "ja" ? "/agent-guide" : "/en/agent-guide"}
                      className="mt-3 inline-flex text-sm font-semibold text-emerald-800 hover:text-emerald-900"
                    >
                      {t.agentTeaserLink}
                    </Link>
                  </div>
                </div>
              </article>
            </div>
          </div>
        </section>

        <Section eyebrow="A2CR" title={t.whatTitle}>
          <BulletList items={t.whatPoints} />
        </Section>

        <section className="border-y border-neutral-200 bg-white">
          <Section eyebrow="WorkBaton" title={t.workbatonSectionTitle} body={t.workbatonSectionBody}>
            <BulletList items={t.workbatonPoints} />
          </Section>
        </section>

        <section className="border-y border-neutral-200 bg-white">
          <Section eyebrow="WorkStash" title={t.workstashSectionTitle} body={t.workstashSectionBody}>
            <BulletList items={t.workstashPoints} />
          </Section>
        </section>

        <section className="border-y border-neutral-200 bg-emerald-50">
          <Section eyebrow="Together" title={t.combinedTitle} body={t.combinedBody}>
            <BulletList items={t.combinedPoints} />
          </Section>
        </section>

        <section className="border-y border-neutral-200 bg-white">
          <Section eyebrow="Compare" title={t.comparisonTitle} body={t.comparisonBody}>
            <div className="grid gap-4">
              <ComparisonTable
                title={t.compressionCompareTitle}
                headers={t.compressionCompareHeaders}
                rows={t.compressionCompareRows}
                note={t.compressionCompareNote}
              />
              <ComparisonTable title={t.subagentCompareTitle} headers={t.subagentCompareHeaders} rows={t.subagentCompareRows} />
            </div>
          </Section>
        </section>

        <section className="border-y border-neutral-200 bg-white">
          <Section eyebrow="How it works" title={t.connectTitle} body={t.connectBody}>
            <div className="grid gap-4">
              <BulletList items={t.connectPoints} />
              <article className="rounded-md border border-emerald-200 bg-emerald-50 p-4">
                <div className="mb-2 text-xs font-semibold uppercase tracking-normal text-emerald-700">{t.connectPromptLabel}</div>
                <pre className="whitespace-pre-wrap text-sm leading-6 text-emerald-900">{t.connectPromptExample}</pre>
              </article>
            </div>
          </Section>
        </section>

        <section className="border-y border-neutral-200 bg-white">
          <Section eyebrow="Context quality" title={t.cleanContextTitle} body={t.cleanContextBody}>
            <div className="grid gap-4">
              <ComparisonTable
                title={t.cleanContextTitle}
                headers={t.cleanContextHeaders}
                rows={t.cleanContextRows}
                note={t.cleanContextNote}
              />
            </div>
          </Section>
        </section>

        <section className="border-y border-neutral-200 bg-white">
          <Section eyebrow="Use cases" title={t.scenarioTitle}>
            <div className="grid gap-3 sm:grid-cols-2">
              {t.scenarios.map((s) => (
                <article key={s.title} className="rounded-md border border-neutral-200 bg-white p-4">
                  <h3 className="font-semibold text-neutral-950">{s.title}</h3>
                  <p className="mt-2 text-sm leading-6 text-neutral-700">{s.body}</p>
                </article>
              ))}
            </div>
          </Section>
        </section>

        <section className="border-y border-neutral-200 bg-white">
          <Section eyebrow="Security" title={t.keyTitle} body={t.keyBody}>
            <BulletList items={t.keyPoints} />
          </Section>
        </section>

        <Section eyebrow="Encryption" title={t.encryptionTitle} body={t.noOverclaim}>
          <div className="overflow-hidden rounded-md border border-neutral-200 bg-white">
            <table className="w-full text-left text-sm">
              <tbody>
                {t.storageRows.map(([mode, description]) => (
                  <tr key={mode} className="border-b border-neutral-100 last:border-0">
                    <th className="w-48 px-4 py-3 font-semibold text-neutral-950">{mode}</th>
                    <td className="px-4 py-3 leading-6 text-neutral-700">{description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>

        <section className="border-y border-neutral-200 bg-white">
          <Section eyebrow="MCP" title={t.setupTitle} body={t.setupBody}>
            <div className="grid gap-4">
              {(Object.keys(clientLabels) as ClientKey[]).map((client) => {
                const snippet = mcpConfigSnippet(client);
                return (
                  <article key={client} className="rounded-md border border-neutral-200 bg-neutral-50 p-4">
                    <div className="mb-3 flex items-center justify-between gap-3">
                      <h3 className="font-semibold">{clientLabels[client]}</h3>
                      <CopyButton value={snippet} label={t.copyConfig} compact />
                    </div>
                    <pre className="max-h-72 overflow-auto rounded-md bg-neutral-950 p-3 text-xs text-neutral-50">{snippet}</pre>
                  </article>
                );
              })}
            </div>
          </Section>
        </section>
        <Section eyebrow="Workflow" title={t.workflowTitle}>
          <BulletList items={t.workflow} />
        </Section>
      </main>
    </div>
  );
}
