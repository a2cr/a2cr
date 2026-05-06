import {
  ArrowRight,
  Bot,
  CheckCircle2,
  ClipboardList,
  KeyRound,
  LayoutDashboard,
  LogIn,
  PlugZap,
  ShieldCheck,
  TimerReset
} from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { CopyButton } from "../components/CopyButton";
import { LanguageToggle } from "../components/LanguageToggle";
import { serviceUrl } from "../lib/format";
import { useAuth } from "../providers/AuthProvider";

type ClientKey = "codex" | "claude" | "cursor";

const clientLabels: Record<ClientKey, string> = {
  codex: "Codex",
  claude: "Claude",
  cursor: "Cursor"
};

function mcpConfigSnippet(client: ClientKey): string {
  const url = serviceUrl();
  if (client === "codex") {
    return [
      '[mcp_servers."a2cr"]',
      `url = "${url}"`,
      "",
      '[mcp_servers."a2cr".http_headers]',
      'Authorization = "Bearer <A2CR_API_KEY>"'
    ].join("\n");
  }
  return JSON.stringify(
    {
      name: "a2cr",
      type: "streamable-http",
      url,
      headers: {
        Authorization: "Bearer <A2CR_API_KEY>"
      }
    },
    null,
    2
  );
}

function agentPrompt(language: "en" | "ja"): string {
  if (language === "ja") {
    return [
      "A2CR MCPを作業記憶として使ってください。",
      `A2CR service: ${serviceUrl()}`,
      "直接HTTP APIを推測せず、A2CR MCPツールだけを使います。",
      "作業開始時: list_contextsで既存Slotを確認し、関連するSlotがあればresume_contextで読み込みます。",
      "作業中: 会話が長くなる前、または重要な区切りでsave_contextします。",
      "保存内容はgoal、current_state、next_action、必要な補足だけに圧縮します。",
      "作業を止める時: 次にやることをnext_actionに明記してsave_contextします。",
      "自動保存前にget_account_limitsで上限を確認します。",
      "秘密情報、APIキー、Authorizationヘッダー、DB URL、全文履歴、長いログは保存しません。",
      "新しい窓では最初にresume_context(slot_name=\"...\")またはresume_context(slot_number=N)を実行します。"
    ].join("\n");
  }

  return [
    `A2CR service: ${serviceUrl()}`,
    "Use the A2CR MCP tool. Do not guess or call direct HTTP API endpoints.",
    "At the start of work, call list_contexts and resume a relevant Slot if one exists.",
    "During work, call save_context before the conversation gets long or at important milestones.",
    "Save only goal, current_state, next_action, and compact supporting facts.",
    "When pausing or finishing work, save the next action clearly in next_action.",
    "Call get_account_limits before automatic saves.",
    "Never save secrets, API keys, Authorization headers, private database URLs, full transcripts, or long logs.",
    "In a new window, first call resume_context(slot_name=\"...\") or resume_context(slot_number=N).",
    "After loading, continue in the language of the current user message."
  ].join("\n");
}

const copy = {
  en: {
    navGuide: "Guide",
    heroTitle: "A2CR setup guide",
    conceptTitle: "A2CR is not an AI.",
    conceptBody: "It is the baton that lets AI agents hand work to one another.",
    heroBody:
      "A2CR gives MCP-capable agents a small, durable WorkBaton: save the useful state of work now, then resume it from another window, model, or client later.",
    humanHookTitle:
      "Do you find yourself explaining the same work again every time a long AI session moves to a new chat?",
    humanHookBody:
      "A2CR saves only the current work state and hands it off safely to the next AI.",
    openDashboard: "Open dashboard",
    signIn: "Sign in",
    pricing: "Pricing",
    whatTitle: "What A2CR does",
    whatBody:
      "A2CR is not just a place to store notes. It is an MCP-first work-continuation layer that lets agents carry only the state they actually need into the next session.",
    impactEyebrow: "Impact",
    cleanContextTitle: "Clean context",
    valueTitle: "Why it matters",
    valueBody:
      "Long conversations make agents spend context on old noise. A2CR turns the current goal, state, and next action into a compact WorkBaton, so each new session starts clean.",
    valuePoints: [
      "Clean context reduces token waste and helps keep outputs stable.",
      "Lower token use can matter directly for subscription-based AI services and usage limits.",
      "Agents avoid dragging old assumptions, duplicate logs, and full chat history into every next step.",
      "The same WorkBaton can be resumed from another window, another model, or any AI agent configured with A2CR MCP."
    ],
    compareTitle: "Not the same as summarizing a chat",
    compareBody:
      "Summary and compression are useful, but they solve a different problem. They shorten one chat. A2CR passes a usable work state to another AI.",
    compareLead:
      "A summary is a diet for conversation logs. WorkBaton is a baton for work state.",
    compareHeaders: ["Comparison", "Summary / Compression", "A2CR / WorkBaton"],
    compareRows: [
      ["Goal", "Shorten a long conversation", "Hand off state so the next AI can resume work"],
      ["Target", "History inside that chat", "Another chat, another AI, or another tool"],
      ["Output", "Summary text", "goal / current_state / next_action / blockers"],
      ["Weakness", "Can preserve stale assumptions or noise", "Intentionally keeps only required work state"],
      ["Storage", "Depends on the chat or service", "External temporary relay DB"],
      ["Sharing", "Mostly inside the same AI service", "Shared across MCP-capable agents"],
      ["Expiry", "Depends on the service", "Explicit TTL"]
    ],
    protocolTitle: "From WorkBaton to WorkThreads",
    protocolBody:
      "WorkBaton hands one compact state to the next agent. Planned Pro WorkThreads expand that idea into a shared work thread where multiple agents can coordinate progress.",
    protocolPoints: [
      "One agent can design, another can implement, and another can review from the same shared work state.",
      "Different models or clients can cooperate without copying full transcripts between windows.",
      "This makes A2CR closer to a protocol-like work layer for agent collaboration than a simple save box."
    ],
    humanTitle: "Dashboard",
    agentTitle: "MCP tools",
    setupTitle: "MCP setup examples",
    setupNote:
      "Create an API key after signing in, then put it in your MCP client as a Bearer token. Client config locations vary; use your client's current MCP settings screen or config file.",
    usageTitle: "Basic workflow",
    agentContractTitle: "Semi-automation prompt",
    agentContractBody:
      "Put this into an agent's standing instructions so it can use A2CR at the start of work, during long sessions, and when pausing.",
    copyConfig: "Copy config",
    copyPrompt: "Copy prompt",
    clients: {
      codex:
        "Use the A2CR Streamable HTTP server from Codex config. Keep the API key out of repositories and shared logs.",
      claude:
        "Add A2CR as a Streamable HTTP MCP server in Claude's MCP configuration, then ask Claude to use the A2CR tools.",
      cursor:
        "Add the same Streamable HTTP server in Cursor's MCP settings, then let Cursor save and resume WorkBaton slots."
    },
    humanPoints: [
      "Issue or revoke an API key from the dashboard.",
      "See active WorkBaton slots without exposing saved bodies.",
      "Copy save and resume prompts for another AI window.",
      "Use fixed Slot numbers when you want predictable handoff targets."
    ],
    agentPoints: [
      "Call get_account_limits before automatic saves.",
      "Save only goal, current_state, next_action, and compact supporting facts.",
      "Use resume_context first in a fresh window.",
      "Respect returned candidates instead of guessing the right Slot.",
      "Do not save secrets or long logs."
    ],
    workflow: [
      "Ask your AI agent to read this guide and find your MCP config.",
      "Sign in to A2CR and issue an API key.",
      "Let the agent add the A2CR placeholder config and open the config file in a text editor.",
      "Paste the API key into the placeholder yourself, then save.",
      "Restart or reload the AI client.",
      "Ask the agent to verify A2CR with get_account_limits or list_contexts."
    ],
    wow: [
      "The handoff is tool-native: agents call MCP instead of scraping chat history.",
      "Saved content includes next_action, so the next agent knows what to do next.",
      "Slots are short-lived by default, reducing stale context buildup.",
      "Dashboard metadata stays visible while saved bodies remain off normal human views."
    ]
  },
  ja: {
    navGuide: "ガイド",
    heroTitle: "A2CRの使い方ガイド",
    conceptTitle: "A2CRはAIではありません。",
    conceptBody: "AI同士が作業を受け渡すためのバトンです。",
    heroBody:
      "A2CRは、Codex、Claude、CursorなどからMCPで使える作業引き継ぎサービスです。会話が長くなる前に要点だけをWorkBaton Slotへ保存して、別の窓やモデルから続きを再開できます。",
    humanHookTitle:
      "AIとの作業が長くなって、別のチャットに移るたびに説明し直していませんか？",
    humanHookBody:
      "A2CRは、今の作業状態だけを保存して、次のAIへ安全に引き継ぐサービスです。",
    openDashboard: "ダッシュボードを開く",
    signIn: "ログイン",
    pricing: "料金",
    whatTitle: "A2CR がすること",
    whatBody:
      "A2CRは、ただのメモ保存場所ではありません。AIエージェントが次の作業に必要な状態だけをMCP経由で受け渡すための、作業継続レイヤーです。",
    impactEyebrow: "価値",
    cleanContextTitle: "きれいなコンテキスト",
    valueTitle: "なぜ効くのか",
    valueBody:
      "長くなった会話には、古い前提、重複したログ、もう使わない情報が混ざります。A2CRは goal、current_state、next_action をWorkBatonとして整理し、新しい窓をきれいな文脈から始められるようにします。",
    valuePoints: [
      "コンテキストを常に整理できるため、Token消費を抑え、出力を安定させやすくなります。",
      "Tokenの節約は、サブスク型AIサービスの使用量や上限にも影響します。",
      "古い前提や長い履歴に引っ張られにくく、次のAIが必要な作業へすぐ入れます。",
      "同じWorkBatonを、別の窓、別モデル、A2CRのMCPの設定をしたAIエージェントから再開できます。"
    ],
    compareTitle: "要約・圧縮とは違います",
    compareBody:
      "「AIに要約・圧縮させればいい」と思うかもしれません。でも、それは1つのチャット内で情報量を減らす処理です。A2CRが扱うのは、別チャット・別AI・別ツールへ作業状態を渡すことです。",
    compareLead:
      "要約は、会話ログのダイエット。WorkBatonは、作業状態のバトンです。",
    compareHeaders: ["比較", "要約・圧縮", "A2CR / WorkBaton"],
    compareRows: [
      ["目的", "長い会話を短くする", "次のAIが作業再開できる状態を渡す"],
      ["対象", "そのチャット内の履歴", "別チャット・別AI・別ツール"],
      ["出力", "要約文", "goal / current_state / next_action / blockers"],
      ["弱点", "古い前提やノイズを拾うことがある", "必要な作業状態だけを意図的に残す"],
      ["保存", "チャットやサービスに依存", "外部の一時リレーDB"],
      ["共有", "基本そのAI/そのサービス内", "MCP対応エージェント間で共有"],
      ["消去", "サービス側仕様次第", "TTLで明示的に消える"]
    ],
    protocolTitle: "WorkBaton から WorkThreads へ",
    protocolBody:
      "WorkBatonは1つの作業状態を次へ渡す仕組みです。Proで予定しているWorkThreadsは、複数のAIエージェントが同じ作業スレッドで進捗を共有し、協業するための層です。",
    protocolPoints: [
      "設計担当、実装担当、レビュー担当のように、AIエージェント同士で役割分担しやすくなります。",
      "別のモデルやクライアントでも、全文履歴を貼り直さずに同じ作業状態へ参加できます。",
      "A2CRは単なる保存箱ではなく、AIエージェントの作業継続と協業のためのProtocol的な土台になり得ます。"
    ],
    humanTitle: "ダッシュボード",
    agentTitle: "MCPツール",
    setupTitle: "MCP 設定例",
    setupNote:
      "ログイン後にAPIキーを発行し、MCPクライアントへBearer tokenとして設定します。設定ファイルの場所はクライアントごとに変わるため、各クライアントの現在のMCP設定画面または設定ファイルを使ってください。",
    usageTitle: "基本の使い方",
    agentContractTitle: "半自動化プロンプト",
    agentContractBody:
      "このプロンプトをAIエージェントの初期指示に入れると、作業開始時・作業中・終了時にA2CRを作業記憶として使いやすくなります。",
    copyConfig: "設定をコピー",
    copyPrompt: "プロンプトをコピー",
    clients: {
      codex:
        "Codex の設定から A2CR の Streamable HTTP サーバーを使います。APIキーはリポジトリや共有ログに入れないでください。",
      claude:
        "Claude のMCP設定に A2CR を Streamable HTTP MCP サーバーとして追加し、A2CRツールを使うよう依頼します。",
      cursor:
        "Cursor のMCP設定に同じ Streamable HTTP サーバーを追加し、WorkBatonスロットの保存・再開に使います。"
    },
    humanPoints: [
      "ダッシュボードでAPIキーを発行・失効できます。",
      "保存本文を表示せずに、有効なWorkBatonスロットを確認できます。",
      "別のAI窓へ渡す保存・再開プロンプトをコピーできます。",
      "固定Slot番号を使うと、引き継ぎ先を予測しやすくできます。"
    ],
    agentPoints: [
      "自動保存前に get_account_limits を呼びます。",
      "goal、current_state、next_action と、必要な補足だけを簡潔に保存します。",
      "新しい窓では最初に resume_context を使います。",
      "候補が返ったら、正しいSlotを推測せず候補を提示します。",
      "秘密情報や長いログは保存しません。"
    ],
    workflow: [
      "AIエージェントにこのガイドを読ませ、MCP設定ファイルを探してもらいます。",
      "A2CRにログインしてAPIキーを発行します。",
      "AIエージェントにA2CR設定のひな形を追加してもらい、設定ファイルをテキストエディタで開いてもらいます。",
      "APIキーの貼り付けだけは人間が行い、保存します。",
      "AIクライアントまたはエージェントを再起動します。",
      "get_account_limits または list_contexts で接続確認してもらいます。"
    ],
    wow: [
      "引き継ぎがMCPツール前提なので、チャット履歴を無理に読ませる必要がありません。",
      "保存内容にnext_actionが入るため、次のエージェントが何をすべきか分かります。",
      "スロットは短命が標準なので、古い文脈が溜まりにくい設計です。",
      "通常の画面では本文を表示せず、メタデータだけを確認できます。"
    ]
  }
};

function PublicHeader() {
  const { i18n } = useTranslation();
  const { session } = useAuth();
  const location = useLocation();
  const isEnglishRoute = location.pathname.startsWith("/en/");
  const text = isEnglishRoute ? copy.en : i18n.language.startsWith("ja") ? copy.ja : copy.en;

  return (
    <header className="border-b border-neutral-200 bg-white">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-4 py-4 sm:px-6">
        <Link to="/" className="flex items-center gap-3">
          <img src="/brand/a2cr-logo.png" alt="A2CR" className="h-8 w-auto object-contain" />
          <span className="sr-only">A2CR</span>
        </Link>
        <div className="flex flex-wrap items-center justify-end gap-2">
          <Link
            to={isEnglishRoute ? "/en/guide" : "/guide"}
            className="rounded-md bg-neutral-100 px-3 py-2 text-sm font-medium text-neutral-900"
          >
            {text.navGuide}
          </Link>
          <Link
            to="/pricing"
            className="rounded-md px-3 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-100"
          >
            {text.pricing}
          </Link>
          <Link
            to={session ? "/dashboard" : "/login"}
            className="rounded-md px-3 py-2 text-sm font-medium text-emerald-800 hover:bg-emerald-50"
          >
            {session ? text.openDashboard : text.signIn}
          </Link>
          <LanguageToggle />
        </div>
      </div>
    </header>
  );
}

function SectionTitle({
  eyebrow,
  title,
  body,
  inverse = false
}: {
  eyebrow: string;
  title: string;
  body?: string;
  inverse?: boolean;
}) {
  return (
    <div>
      <div className={`text-xs font-semibold uppercase tracking-normal ${inverse ? "text-emerald-300" : "text-emerald-700"}`}>
        {eyebrow}
      </div>
      <h2 className={`mt-2 text-2xl font-semibold tracking-normal ${inverse ? "text-white" : "text-neutral-950"}`}>
        {title}
      </h2>
      {body && (
        <p className={`mt-3 max-w-3xl text-sm leading-6 ${inverse ? "text-neutral-300" : "text-neutral-600"}`}>
          {body}
        </p>
      )}
    </div>
  );
}

export function GuidePage() {
  const { i18n } = useTranslation();
  const { session } = useAuth();
  const location = useLocation();
  const isEnglishRoute = location.pathname.startsWith("/en/");
  const text = isEnglishRoute ? copy.en : i18n.language.startsWith("ja") ? copy.ja : copy.en;
  const primaryTo = session ? "/dashboard" : "/login";
  const PrimaryIcon = session ? LayoutDashboard : LogIn;
  const promptLanguage = isEnglishRoute ? "en" : i18n.language.startsWith("ja") ? "ja" : "en";
  const prompt = agentPrompt(promptLanguage);

  return (
    <div className="min-h-screen bg-neutral-50 text-neutral-950">
      <PublicHeader />
      <main>
        <section className="border-b border-neutral-200 bg-white">
          <div className="mx-auto grid max-w-7xl gap-8 px-4 py-14 sm:px-6 lg:grid-cols-[0.95fr_1.05fr] lg:items-center">
            <div>
              <img src="/brand/a2cr-logo.png" alt="A2CR" className="mb-6 w-full max-w-md object-contain" />
              <h1 className="max-w-3xl text-4xl font-semibold tracking-normal sm:text-5xl">
                {text.heroTitle}
              </h1>
              <div className="mt-5 max-w-2xl">
                <p className="text-2xl font-semibold leading-8 text-neutral-950">{text.conceptTitle}</p>
                <p className="mt-2 text-xl font-semibold leading-8 text-emerald-800">{text.conceptBody}</p>
              </div>
              <p className="mt-5 max-w-2xl text-base leading-7 text-neutral-600">{text.heroBody}</p>
              <div className="mt-5 max-w-2xl rounded-md border border-emerald-200 bg-emerald-50 p-4">
                <p className="text-base font-semibold leading-7 text-emerald-950">{text.humanHookTitle}</p>
                <p className="mt-2 text-sm leading-6 text-emerald-900">{text.humanHookBody}</p>
              </div>
              <div className="mt-8 flex flex-wrap gap-3">
                <Link
                  to={primaryTo}
                  className="inline-flex h-11 items-center gap-2 rounded-md bg-emerald-700 px-4 text-sm font-semibold text-white hover:bg-emerald-800"
                >
                  <PrimaryIcon className="size-4" aria-hidden="true" />
                  {session ? text.openDashboard : text.signIn}
                </Link>
                <Link
                  to="/pricing"
                  className="inline-flex h-11 items-center gap-2 rounded-md border border-neutral-300 bg-white px-4 text-sm font-semibold text-neutral-800 hover:bg-neutral-100"
                >
                  {text.pricing}
                  <ArrowRight className="size-4" aria-hidden="true" />
                </Link>
              </div>
            </div>

            <div className="grid gap-3">
              {[
                { icon: TimerReset, title: "WorkBaton", body: text.wow[0] },
                { icon: Bot, title: "Agent-ready", body: text.wow[1] },
                { icon: ShieldCheck, title: "Inspectable", body: text.wow[3] }
              ].map(({ icon: Icon, title, body }) => (
                <article key={title} className="rounded-md border border-neutral-200 bg-neutral-50 p-4">
                  <div className="flex items-start gap-3">
                    <div className="grid size-9 shrink-0 place-items-center rounded-md bg-emerald-100 text-emerald-800">
                      <Icon className="size-4" aria-hidden="true" />
                    </div>
                    <div>
                      <h2 className="text-base font-semibold">{title}</h2>
                      <p className="mt-1 text-sm leading-6 text-neutral-600">{body}</p>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="mx-auto grid max-w-7xl gap-6 px-4 py-12 sm:px-6 lg:grid-cols-[0.8fr_1.2fr]">
          <SectionTitle eyebrow="A2CR" title={text.whatTitle} body={text.whatBody} />
          <div className="grid gap-3 md:grid-cols-2">
            <article className="rounded-md border border-neutral-200 bg-white p-4">
              <div className="mb-3 flex items-center gap-2">
                <ClipboardList className="size-5 text-emerald-700" aria-hidden="true" />
                <h2 className="font-semibold">{text.humanTitle}</h2>
              </div>
              <ul className="grid gap-2 text-sm leading-6 text-neutral-700">
                {text.humanPoints.map((point) => (
                  <li key={point} className="flex gap-2">
                    <CheckCircle2 className="mt-1 size-4 shrink-0 text-emerald-700" aria-hidden="true" />
                    <span>{point}</span>
                  </li>
                ))}
              </ul>
            </article>
            <article className="rounded-md border border-neutral-200 bg-white p-4">
              <div className="mb-3 flex items-center gap-2">
                <Bot className="size-5 text-emerald-700" aria-hidden="true" />
                <h2 className="font-semibold">{text.agentTitle}</h2>
              </div>
              <ul className="grid gap-2 text-sm leading-6 text-neutral-700">
                {text.agentPoints.map((point) => (
                  <li key={point} className="flex gap-2">
                    <CheckCircle2 className="mt-1 size-4 shrink-0 text-emerald-700" aria-hidden="true" />
                    <span>{point}</span>
                  </li>
                ))}
              </ul>
            </article>
          </div>
        </section>

        <section className="border-y border-neutral-200 bg-white">
          <div className="mx-auto grid max-w-7xl gap-6 px-4 py-12 sm:px-6 lg:grid-cols-[0.8fr_1.2fr]">
            <SectionTitle eyebrow={text.impactEyebrow} title={text.valueTitle} body={text.valueBody} />
            <div className="grid gap-3">
              <article className="rounded-md border border-neutral-200 bg-neutral-50 p-4">
                <div className="mb-3 flex items-center gap-2">
                  <TimerReset className="size-5 text-emerald-700" aria-hidden="true" />
                  <h2 className="font-semibold">{text.cleanContextTitle}</h2>
                </div>
                <ul className="grid gap-2 text-sm leading-6 text-neutral-700">
                  {text.valuePoints.map((point) => (
                    <li key={point} className="flex gap-2">
                      <CheckCircle2 className="mt-1 size-4 shrink-0 text-emerald-700" aria-hidden="true" />
                      <span>{point}</span>
                    </li>
                  ))}
                </ul>
              </article>
              <article className="rounded-md border border-neutral-200 bg-neutral-50 p-4">
                <div className="mb-3 flex items-center gap-2">
                  <Bot className="size-5 text-emerald-700" aria-hidden="true" />
                  <h2 className="font-semibold">{text.protocolTitle}</h2>
                </div>
                <p className="mb-3 text-sm leading-6 text-neutral-600">{text.protocolBody}</p>
                <ul className="grid gap-2 text-sm leading-6 text-neutral-700">
                  {text.protocolPoints.map((point) => (
                    <li key={point} className="flex gap-2">
                      <CheckCircle2 className="mt-1 size-4 shrink-0 text-emerald-700" aria-hidden="true" />
                      <span>{point}</span>
                    </li>
                  ))}
                </ul>
              </article>
            </div>
          </div>
        </section>

        <section className="mx-auto grid max-w-7xl gap-6 px-4 py-12 sm:px-6 lg:grid-cols-[0.8fr_1.2fr]">
          <SectionTitle eyebrow="WorkBaton" title={text.compareTitle} body={text.compareBody} />
          <div className="overflow-hidden rounded-md border border-neutral-200 bg-white">
            <div className="border-b border-neutral-200 bg-emerald-50 p-4">
              <p className="text-sm font-semibold leading-6 text-emerald-950">{text.compareLead}</p>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-[720px] w-full border-collapse text-left text-sm">
                <thead className="bg-neutral-50 text-neutral-950">
                  <tr>
                    {text.compareHeaders.map((header) => (
                      <th key={header} className="border-b border-neutral-200 px-4 py-3 font-semibold">
                        {header}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {text.compareRows.map((row) => (
                    <tr key={row[0]} className="border-b border-neutral-100 last:border-0">
                      {row.map((cell, index) => (
                        <td
                          key={cell}
                          className={`px-4 py-3 align-top leading-6 ${
                            index === 0 ? "font-semibold text-neutral-950" : "text-neutral-700"
                          }`}
                        >
                          {cell}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        <section className="border-y border-neutral-200 bg-white">
          <div className="mx-auto grid max-w-7xl gap-6 px-4 py-12 sm:px-6 lg:grid-cols-[0.8fr_1.2fr]">
            <SectionTitle eyebrow="MCP" title={text.setupTitle} body={text.setupNote} />
            <div className="grid gap-4">
              {(Object.keys(clientLabels) as ClientKey[]).map((client) => {
                const snippet = mcpConfigSnippet(client);
                return (
                  <article key={client} className="rounded-md border border-neutral-200 bg-neutral-50 p-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <PlugZap className="size-5 text-emerald-700" aria-hidden="true" />
                          <h3 className="font-semibold">{clientLabels[client]}</h3>
                        </div>
                        <p className="mt-2 text-sm leading-6 text-neutral-600">{text.clients[client]}</p>
                      </div>
                      <CopyButton value={snippet} label={text.copyConfig} compact />
                    </div>
                    <pre className="mt-3 max-h-72 overflow-auto rounded-md bg-neutral-950 p-3 text-xs text-neutral-50">
                      {snippet}
                    </pre>
                  </article>
                );
              })}
            </div>
          </div>
        </section>

        <section className="mx-auto grid max-w-7xl gap-6 px-4 py-12 sm:px-6 lg:grid-cols-[0.8fr_1.2fr]">
          <SectionTitle eyebrow="Workflow" title={text.usageTitle} />
          <div className="grid gap-3">
            {text.workflow.map((step, index) => (
              <div key={step} className="flex gap-3 rounded-md border border-neutral-200 bg-white p-4">
                <div className="grid size-8 shrink-0 place-items-center rounded-md bg-neutral-900 text-sm font-semibold text-white">
                  {index + 1}
                </div>
                <p className="pt-1 text-sm leading-6 text-neutral-700">{step}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="bg-neutral-950 text-white">
          <div className="mx-auto grid max-w-7xl gap-6 px-4 py-12 sm:px-6 lg:grid-cols-[0.8fr_1.2fr]">
            <SectionTitle eyebrow="Agent" title={text.agentContractTitle} body={text.agentContractBody} inverse />
            <div className="rounded-md border border-white/15 bg-white/[0.06] p-4">
              <div className="mb-3 flex items-center justify-between gap-3">
                <div className="flex items-center gap-2 text-sm font-semibold">
                  <KeyRound className="size-4 text-emerald-300" aria-hidden="true" />
                  A2CR MCP
                </div>
                <CopyButton value={prompt} label={text.copyPrompt} compact />
              </div>
              <pre className="max-h-80 overflow-auto whitespace-pre-wrap rounded-md bg-black p-3 text-xs leading-5 text-neutral-100">
                {prompt}
              </pre>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
