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
      mcpServers: {
        a2cr: {
          type: "streamable-http",
          url,
          headers: {
            Authorization: "Bearer <A2CR_API_KEY>"
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
      "作業開始時はlist_contextsで既存Slotを確認し、関連するSlotがあればresume_contextで読み込みます。",
      "作業中は、会話が長くなる前または重要な区切りでsave_contextします。",
      "保存する内容はgoal、current_state、next_action、必要な判断・制約・参照だけに絞ります。",
      "APIキー、Authorization header、DB URL、秘密情報、全文ログ、長い会話履歴は保存しません。",
      "自動保存前にはget_account_limitsで制限を確認します。",
      "新しい窓では最初にresume_context(slot_name=\"...\")またはresume_context(slot_number=N)を実行します。",
      "読み込み後は、現在のユーザーの言語で続けます。"
    ].join("\n");
  }
  return [
    `A2CR service: ${serviceUrl()}`,
    "Use A2CR MCP as working memory.",
    "Do not guess direct HTTP API endpoints. Use only the A2CR MCP tools.",
    "At the start of work, call list_contexts and resume a relevant Slot if one exists.",
    "During work, call save_context before the conversation gets long or at important milestones.",
    "Save only goal, current_state, next_action, and compact supporting facts.",
    "Never save secrets, API keys, Authorization headers, private database URLs, full transcripts, or long logs.",
    "Call get_account_limits before automatic saves.",
    "In a new window, first call resume_context(slot_name=\"...\") or resume_context(slot_number=N).",
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
      "Use A2CR to hand compact WorkBaton checkpoints from one AI session to the next without carrying the whole chat history forward.",
    agentTitle: "A2CR guide for AI agents",
    agentBody:
      "This page is written for AI agents configuring and using A2CR MCP on behalf of a user.",
    whatTitle: "What A2CR does",
    whatPoints: [
      "Saves only the useful work state: goal, current_state, next_action, decisions, constraints, and references.",
      "Lets another AI window, model, or MCP-capable client resume the work.",
      "Keeps dashboards focused on metadata rather than saved body content.",
      "Does not run LLM inference on the server."
    ],
    comparisonTitle: "What A2CR is different from",
    comparisonBody:
      "A2CR is not a chat summarizer or a sub-agent feature. It is a WorkBaton for handing useful work state across sessions, models, and tools.",
    agentTeaserTitle: "Let your AI read it",
    agentTeaserBody:
      "Show the AI agent guide to the AI agent you already use and ask it to explain A2CR. The guide is written for agents, so it can turn the app's role, limits, and setup into plain guidance for your situation.",
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
      "The local stdio MCP wrapper can use client-encrypted WorkBaton mode. It creates a local client key on the user's machine and encrypts WorkBaton content before sending it to A2CR.",
    keyPoints: [
      "The local client key is managed by the user, not by the service administrator.",
      "A2CR stores and returns ciphertext for client-encrypted WorkBaton slots and cannot decrypt those bodies.",
      "If the local client key is lost, older client-encrypted slots cannot be recovered by A2CR.",
      "Creating a new local client key works for future saves, but it cannot decrypt old slots saved with the previous key."
    ],
    encryptionTitle: "Storage modes",
    storageRows: [
      ["Server-encrypted", "A2CR stores Fernet-encrypted content and can decrypt it for authenticated MCP/API responses."],
      ["Client-encrypted", "The local stdio MCP wrapper encrypts before upload; A2CR stores ciphertext only."]
    ],
    noOverclaim:
      "Do not describe A2CR as a whole as zero-knowledge. Only client-encrypted WorkBaton slots should be described that way. WorkThreads are not covered by this claim.",
    setupTitle: "MCP setup",
    setupBody:
      "Create an API key after signing in, then put it in your MCP client as a Bearer token. Keep real keys out of repositories and logs.",
    workflowTitle: "Basic workflow",
    workflow: [
      "Sign in to A2CR and issue an API key.",
      "Add A2CR to your MCP client.",
      "Ask the AI agent to verify the connection with get_account_limits or list_contexts.",
      "Save a WorkBaton before the session gets long or at a clear task boundary.",
      "Resume from the saved Slot in a new window with resume_context."
    ],
    agentRulesTitle: "Rules for AI agents",
    agentRules: [
      "Preserve existing MCP server settings. Do not delete unrelated servers.",
      "Ask the user to paste the API key into the config themselves when possible.",
      "Do not print API keys, Authorization headers, or full secret configs in chat.",
      "Use MCP tools rather than guessed direct HTTP API calls.",
      "Never save secrets, full transcripts, or long logs into WorkBaton."
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
      "A2CRは、長いチャット履歴をそのまま引きずらず、必要な作業状態だけをWorkBatonとして次のAIセッションへ渡すためのサービスです。",
    agentTitle: "A2CR AIエージェント向けガイド",
    agentBody:
      "このページは、ユーザーの代わりにA2CR MCPを設定・利用するAIエージェント向けの手順です。",
    whatTitle: "A2CRがすること",
    whatPoints: [
      "goal、current_state、next_action、判断、制約、参照など、作業再開に必要な状態だけを保存します。",
      "別のAI窓、別モデル、MCP対応クライアントから作業を再開できます。",
      "ダッシュボードは本文ではなくメタデータ中心に表示します。",
      "A2CRサーバー自体はLLM推論を実行しません。"
    ],
    comparisonTitle: "A2CRが何と違うか",
    comparisonBody:
      "A2CRは、チャット要約機能でもサブエージェント機能でもありません。別チャット、別AI、別ツールへ作業状態を渡すためのWorkBatonです。",
    agentTeaserTitle: "読むより、AIに読ませる",
    agentTeaserBody:
      "AI向けガイドを、ふだん使っているAIエージェントに見せて「このアプリを説明して」と頼んでください。A2CRが何を渡し、何を保存しないのかまで、あなた向けにかみ砕いて説明できます。",
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
      "ローカルstdio MCP wrapperは、client-encrypted WorkBaton modeを利用できます。この場合、ユーザーの端末上でlocal client keyを作り、WorkBaton本文を暗号化してからA2CRへ送ります。",
    keyPoints: [
      "local client keyは利用者側が管理します。サービス管理者は管理しません。",
      "client-encrypted Slotでは、A2CRは暗号文だけを保存・返却し、本文を復号できません。",
      "local client keyを失うと、過去にその鍵で保存したclient-encrypted SlotはA2CR側でも復旧できません。",
      "local client keyを作り直した後に新しく保存したSlotは読めますが、旧鍵で保存したSlotは旧鍵なしでは読めません。"
    ],
    encryptionTitle: "保存方式",
    storageRows: [
      ["Server-encrypted", "A2CRがFernetで暗号化保存し、認証済みMCP/API応答時にサーバー側で復号できます。"],
      ["Client-encrypted", "ローカルstdio MCP wrapperが送信前に暗号化し、A2CRは暗号文だけを保存します。"]
    ],
    noOverclaim:
      "A2CR全体をゼロ知識とは表現しません。ゼロ知識相当と言えるのはclient-encrypted WorkBaton Slotに限ります。WorkThreadsはこの主張の対象外です。",
    setupTitle: "MCP設定",
    setupBody:
      "ログイン後にAPIキーを発行し、MCPクライアントへBearer tokenとして設定します。実際のキーはリポジトリやログに入れないでください。",
    workflowTitle: "基本の流れ",
    workflow: [
      "A2CRへログインし、APIキーを発行します。",
      "MCPクライアントにA2CRを追加します。",
      "AIエージェントにget_account_limitsまたはlist_contextsで接続確認してもらいます。",
      "会話が長くなる前、または作業の区切りでWorkBatonを保存します。",
      "新しい窓でresume_contextを使い、保存したSlotから再開します。"
    ],
    agentRulesTitle: "AIエージェントのルール",
    agentRules: [
      "既存のMCP server設定を消さず、関係ない設定を保持します。",
      "可能ならAPIキーの貼り付けはユーザー本人に行ってもらいます。",
      "APIキー、Authorization header、secretをチャットやログに表示しません。",
      "HTTP APIを推測せず、MCPツールを使います。",
      "秘密情報、全文履歴、長いログをWorkBatonに保存しません。"
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
