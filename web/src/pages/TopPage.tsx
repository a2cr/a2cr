import { ArrowRight, Check, LayoutDashboard, LogIn } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { LanguageToggle } from "../components/LanguageToggle";
import { useAuth } from "../providers/AuthProvider";

type Lang = "en" | "ja";

const pageContent = {
  en: {
    heroTitle: "At every milestone,\nthe next AI already knows.",
    heroBody:
      "Stop re-explaining your project every session. A2CR saves compact WorkBaton checkpoints at task milestones — so any MCP-capable AI picks up exactly where the last one left off.",

    painEyebrow: "The problem",
    painTitle: "Starting from zero, every single session?",
    painCards: [
      {
        title: "Session ends, context is gone",
        body: "Close the window, hit the context limit, switch models — and everything you explained has to be said again."
      },
      {
        title: "Every AI switch costs you",
        body: "Moving from one tool to another means re-establishing your project, decisions, and current state from scratch."
      },
      {
        title: "Long chats slow everything down",
        body: "The longer a session runs, the heavier the context — slower responses, higher token use, and no clean way out."
      }
    ],

    solutionEyebrow: "Solution",
    solutionTitle: "WorkBaton carries your work state to the next AI",
    solutionBody:
      "A WorkBaton is a compact snapshot of where work stands — not a chat log. Just what the next AI needs to continue without re-explanation.",
    workbatonLabel: "WorkBaton — the spine",
    workbatonPoints: [
      "Saves goal, current progress, next action, key decisions, and blockers.",
      "Encrypted on your machine before upload. A2CR cannot read the body.",
      "Any MCP-capable AI resumes from the same checkpoint."
    ],
    workstashLabel: "WorkStash — the detail",
    workstashPoints: [
      "Stores detailed notes that would bloat the WorkBaton: file paths, API findings, failed attempts.",
      "Returns an entry_key you record in WorkBaton so the next AI retrieves only what it needs.",
      "Keeps the checkpoint compact so every session starts fast."
    ],

    howEyebrow: "How it works",
    howTitle: "Three steps. Every session.",
    howSteps: [
      {
        num: "01",
        title: "Connect via MCP",
        body: "Add one MCP server named a2cr to your client config. The server sends your AI a complete set of instructions — what to save, when, and what never to include."
      },
      {
        num: "02",
        title: "AI saves at milestones automatically",
        body: "Your AI detects task milestones and context pressure on its own. It calls save_context before things get long — no reminder needed from you."
      },
      {
        num: "03",
        title: "Resume anywhere with clean context",
        body: "Open a new window, switch tools, or come back the next day. Call resume_context and your AI knows your goal, progress, and next action — without the chat history weight."
      }
    ],

    crossEyebrow: "Any AI",
    crossTitle: "Works with the AI you already use",
    crossBody:
      "Any MCP-capable client connects to the same checkpoint layer. Start in one tool, continue in another — no re-setup, no re-explanation.",
    crossTools: ["Claude", "Codex", "Cursor", "Gemini", "Cline", "Roo Code"],
    crossNote: "+ any other MCP-capable client",

    cleanEyebrow: "Clean context",
    cleanTitle: "Every new session starts fresh — and fully informed",
    cleanBody:
      "A2CR doesn't pass the chat history to the next AI. It passes only the work state. Each session begins with a clean context and peak AI performance.",
    cleanPoints: [
      "No stale assumptions carried over from old conversations.",
      "Faster responses from the start — no heavy context to process.",
      "Less token use per session — your subscription goes further.",
      "Failed approaches are recorded so the next AI doesn't repeat them."
    ],

    pricingEyebrow: "Pricing",
    pricingTitle: "Free to get started",
    pricingHighlights: [
      "5 active WorkBaton slots",
      "Up to 24h retention",
      "256 KB WorkStash storage",
      "100 saves / hour"
    ],
    pricingCta: "See full pricing",

    ctaFinalTitle: "Ready to stop re-explaining?",
    ctaFinalBody:
      "Setup takes under five minutes. Add one MCP server, issue an API key, and your AI starts saving checkpoints automatically.",
    ctaStart: "Get started free"
  },
  ja: {
    heroTitle: "作業の節目で、\nAIが続きを知っている。",
    heroBody:
      "毎回最初から説明し直すのをやめましょう。A2CR は作業の節目に WorkBaton チェックポイントを保存し、MCP 対応の AI なら続きから動き始めます。",

    painEyebrow: "課題",
    painTitle: "毎回、最初から説明し直していませんか？",
    painCards: [
      {
        title: "ウィンドウを閉じたら全部消える",
        body: "コンテキスト上限に達する・ウィンドウを閉じる・モデルを変える——そのたびに、説明し直しです。"
      },
      {
        title: "AIを切り替えるたびにゼロから",
        body: "別のツールに移るたびに、プロジェクトの背景・意思決定・今の進捗をイチから伝え直す必要があります。"
      },
      {
        title: "長い会話は重くなる一方",
        body: "セッションが長くなるほどコンテキストが肥大化。レスポンスが遅くなり、トークンが増え、途中で終われない状況に。"
      }
    ],

    solutionEyebrow: "解決策",
    solutionTitle: "WorkBaton が、作業状態を次の AI へ渡す",
    solutionBody:
      "WorkBaton はどこまで進んだかをコンパクトに記録したスナップショット。チャット履歴ではなく、次の AI が続きを始めるために必要な情報だけを保持します。",
    workbatonLabel: "WorkBaton — 作業の骨格",
    workbatonPoints: [
      "目標・進捗・次のアクション・意思決定・ブロッカーを保存。",
      "ローカルで暗号化してからアップロード。A2CR は内容を読めません。",
      "MCP 対応 AI ならどれでも同じチェックポイントから再開できます。"
    ],
    workstashLabel: "WorkStash — 詳細ノート",
    workstashPoints: [
      "WorkBaton を膨らませる詳細情報——ファイルパス・API 調査結果・失敗した試み——を別途保存。",
      "返ってくる entry_key を WorkBaton に記録し、次の AI は必要なものだけを取得します。",
      "チェックポイントをコンパクトに保ち、毎セッションを高速にスタート。"
    ],

    howEyebrow: "使い方",
    howTitle: "3ステップ、毎セッション。",
    howSteps: [
      {
        num: "01",
        title: "MCP で接続する",
        body: "クライアント設定に a2cr という MCP サーバーを 1 つ追加するだけ。サーバーが AI に対して、何をいつ保存するか・何を保存してはいけないかを伝えます。"
      },
      {
        num: "02",
        title: "AI が節目で自動保存",
        body: "AI が作業の節目やコンテキスト圧力を自分で判断して save_context を呼びます。「保存して」と伝える必要はありません。"
      },
      {
        num: "03",
        title: "クリーンな状態で再開",
        body: "新しいウィンドウを開く・ツールを切り替える・翌日作業を再開する——resume_context を呼ぶだけで、AI は目標・進捗・次のアクションを把握した状態で動き始めます。"
      }
    ],

    crossEyebrow: "MCP 対応",
    crossTitle: "使っている AI で、そのまま動く",
    crossBody:
      "MCP 対応クライアントなら同じチェックポイント層に接続できます。ツールをまたいでも、作業の続きが保たれます。",
    crossTools: ["Claude", "Codex", "Cursor", "Gemini", "Cline", "Roo Code"],
    crossNote: "+ その他 MCP 対応クライアント",

    cleanEyebrow: "クリーンなコンテキスト",
    cleanTitle: "新しいセッションは、軽く・速く・正確に始まる",
    cleanBody:
      "A2CR は次の AI にチャット履歴を渡しません。渡すのは作業状態だけ。だから新しいセッションは常にクリーンなコンテキストで、AI はピーク性能で動き始めます。",
    cleanPoints: [
      "古い会話の思い込みが残らない。",
      "最初から速いレスポンス——重いコンテキストを処理しなくていいから。",
      "セッションあたりのトークン消費が少なく、サブスクが長持ちする。",
      "失敗した試みが記録されているので、次の AI が同じ間違いを繰り返さない。"
    ],

    pricingEyebrow: "料金",
    pricingTitle: "無料で始められる",
    pricingHighlights: [
      "WorkBaton スロット 5 つ",
      "最大 24 時間保存",
      "WorkStash 256 KB",
      "保存 100 回 / 時間"
    ],
    pricingCta: "料金詳細を見る",

    ctaFinalTitle: "説明し直すのを、もうやめませんか。",
    ctaFinalBody:
      "セットアップは 5 分以内。MCP サーバーを 1 つ追加して API キーを発行すれば、AI が自動でチェックポイントを保存し始めます。",
    ctaStart: "無料で始める"
  }
};

export function TopPage() {
  const { t, i18n } = useTranslation();
  const { session } = useAuth();
  const lang: Lang = i18n.language.startsWith("ja") ? "ja" : "en";
  const c = pageContent[lang];

  const primaryTo = session ? "/dashboard" : "/login";
  const PrimaryIcon = session ? LayoutDashboard : LogIn;
  const primaryLabel = session ? t("top.ctaDashboard") : t("auth.google");

  return (
    <div className="min-h-screen bg-neutral-950 text-white">

      {/* ── NAV ── */}
      <header className="relative z-10 mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-4 py-4 sm:px-6">
        <Link to="/">
          <img src="/brand/a2cr-logo-dark.png" alt="A2CR" className="h-8 w-auto object-contain" />
        </Link>
        <div className="flex flex-wrap items-center justify-end gap-2">
          <Link to="/guide" className="rounded-md px-3 py-2 text-sm font-medium text-neutral-200 hover:bg-white/10">
            {t("nav.guide")}
          </Link>
          <Link to="/pricing" className="rounded-md px-3 py-2 text-sm font-medium text-neutral-200 hover:bg-white/10">
            {t("nav.pricing")}
          </Link>
          <LanguageToggle />
        </div>
      </header>

      <main>

        {/* ── HERO ── */}
        <section className="mx-auto max-w-7xl px-4 pb-24 pt-16 sm:px-6 sm:pt-28">
          <img src="/brand/a2cr-logo-dark.png" alt="A2CR" className="mb-10 w-full max-w-[200px] object-contain" />
          <h1 className="max-w-3xl whitespace-pre-line text-4xl font-semibold leading-tight tracking-tight text-white sm:text-5xl lg:text-6xl">
            {c.heroTitle}
          </h1>
          <p className="mt-6 max-w-2xl text-base leading-7 text-neutral-300 sm:text-lg">
            {c.heroBody}
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              to={primaryTo}
              className="inline-flex h-11 items-center gap-2 rounded-md bg-emerald-500 px-5 text-sm font-semibold text-neutral-950 hover:bg-emerald-400"
            >
              <PrimaryIcon className="size-4" aria-hidden="true" />
              {primaryLabel}
            </Link>
            <Link
              to="/guide"
              className="inline-flex h-11 items-center gap-2 rounded-md border border-white/20 px-5 text-sm font-semibold text-white hover:bg-white/10"
            >
              {t("nav.guide")}
              <ArrowRight className="size-4" aria-hidden="true" />
            </Link>
          </div>
        </section>

        {/* ── PAIN ── */}
        <section className="bg-neutral-100 text-neutral-950">
          <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 sm:py-24">
            <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-emerald-700">{c.painEyebrow}</p>
            <h2 className="mb-10 max-w-2xl text-3xl font-semibold tracking-tight sm:text-4xl">{c.painTitle}</h2>
            <div className="grid gap-4 sm:grid-cols-3">
              {c.painCards.map((card) => (
                <article key={card.title} className="rounded-md border border-neutral-200 bg-white p-6">
                  <div className="mb-3 size-8 rounded-md bg-neutral-100 flex items-center justify-center">
                    <span className="text-base font-bold text-neutral-400">—</span>
                  </div>
                  <h3 className="mb-2 font-semibold text-neutral-950">{card.title}</h3>
                  <p className="text-sm leading-6 text-neutral-600">{card.body}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        {/* ── SOLUTION ── */}
        <section className="bg-neutral-900 text-white">
          <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 sm:py-24">
            <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-emerald-400">{c.solutionEyebrow}</p>
            <h2 className="mb-3 max-w-2xl text-3xl font-semibold tracking-tight sm:text-4xl">{c.solutionTitle}</h2>
            <p className="mb-10 max-w-2xl text-base leading-7 text-neutral-300">{c.solutionBody}</p>
            <div className="grid gap-6 lg:grid-cols-2">
              <div className="rounded-md border border-white/10 bg-white/[0.04] p-6">
                <div className="mb-5 inline-block rounded-md bg-emerald-500 px-3 py-1 text-xs font-semibold text-neutral-950">
                  {c.workbatonLabel}
                </div>
                <ul className="space-y-3">
                  {c.workbatonPoints.map((pt) => (
                    <li key={pt} className="flex items-start gap-3 text-sm leading-6 text-neutral-300">
                      <Check className="mt-0.5 size-4 shrink-0 text-emerald-400" aria-hidden="true" />
                      {pt}
                    </li>
                  ))}
                </ul>
              </div>
              <div className="rounded-md border border-white/10 bg-white/[0.04] p-6">
                <div className="mb-5 inline-block rounded-md bg-white/10 px-3 py-1 text-xs font-semibold text-white">
                  {c.workstashLabel}
                </div>
                <ul className="space-y-3">
                  {c.workstashPoints.map((pt) => (
                    <li key={pt} className="flex items-start gap-3 text-sm leading-6 text-neutral-300">
                      <Check className="mt-0.5 size-4 shrink-0 text-emerald-400" aria-hidden="true" />
                      {pt}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </section>

        {/* ── HOW IT WORKS ── */}
        <section className="bg-white text-neutral-950">
          <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 sm:py-24">
            <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-emerald-700">{c.howEyebrow}</p>
            <h2 className="mb-14 max-w-2xl text-3xl font-semibold tracking-tight sm:text-4xl">{c.howTitle}</h2>
            <div className="grid gap-10 sm:grid-cols-3">
              {c.howSteps.map((step) => (
                <div key={step.num}>
                  <div className="mb-4 text-5xl font-semibold text-emerald-500">{step.num}</div>
                  <h3 className="mb-3 text-lg font-semibold text-neutral-950">{step.title}</h3>
                  <p className="text-sm leading-7 text-neutral-600">{step.body}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── CROSS-AI ── */}
        <section className="bg-neutral-950 text-white">
          <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 sm:py-24">
            <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-emerald-400">{c.crossEyebrow}</p>
            <h2 className="mb-3 max-w-2xl text-3xl font-semibold tracking-tight sm:text-4xl">{c.crossTitle}</h2>
            <p className="mb-10 max-w-2xl text-base leading-7 text-neutral-300">{c.crossBody}</p>
            <div className="flex flex-wrap gap-3">
              {c.crossTools.map((tool) => (
                <span
                  key={tool}
                  className="rounded-full border border-white/20 px-5 py-2 text-sm font-medium text-white"
                >
                  {tool}
                </span>
              ))}
              <span className="rounded-full border border-emerald-500/40 px-5 py-2 text-sm font-medium text-emerald-400">
                {c.crossNote}
              </span>
            </div>
          </div>
        </section>

        {/* ── CLEAN CONTEXT ── */}
        <section className="bg-neutral-900 text-white">
          <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 sm:py-24">
            <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-emerald-400">{c.cleanEyebrow}</p>
            <h2 className="mb-3 max-w-2xl text-3xl font-semibold tracking-tight sm:text-4xl">{c.cleanTitle}</h2>
            <p className="mb-8 max-w-2xl text-base leading-7 text-neutral-300">{c.cleanBody}</p>
            <ul className="grid gap-3 sm:grid-cols-2">
              {c.cleanPoints.map((pt) => (
                <li
                  key={pt}
                  className="flex items-start gap-3 rounded-md border border-white/10 bg-white/[0.04] p-4 text-sm leading-6 text-neutral-300"
                >
                  <Check className="mt-0.5 size-4 shrink-0 text-emerald-400" aria-hidden="true" />
                  {pt}
                </li>
              ))}
            </ul>
          </div>
        </section>

        {/* ── PRICING TEASER ── */}
        <section className="bg-neutral-100 text-neutral-950">
          <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 sm:py-24">
            <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-emerald-700">{c.pricingEyebrow}</p>
            <h2 className="mb-8 text-3xl font-semibold tracking-tight sm:text-4xl">{c.pricingTitle}</h2>
            <div className="max-w-xs rounded-md border border-neutral-200 bg-white p-6">
              <ul className="space-y-3">
                {c.pricingHighlights.map((item) => (
                  <li key={item} className="flex items-center gap-3 text-sm font-medium text-neutral-900">
                    <Check className="size-4 shrink-0 text-emerald-600" aria-hidden="true" />
                    {item}
                  </li>
                ))}
              </ul>
              <Link
                to="/pricing"
                className="mt-6 inline-flex items-center gap-1.5 text-sm font-semibold text-emerald-700 hover:text-emerald-800"
              >
                {c.pricingCta}
                <ArrowRight className="size-4" />
              </Link>
            </div>
          </div>
        </section>

        {/* ── FINAL CTA ── */}
        <section className="bg-neutral-950 text-white">
          <div className="mx-auto max-w-7xl px-4 py-20 text-center sm:px-6 sm:py-32">
            <h2 className="mb-4 text-3xl font-semibold tracking-tight sm:text-4xl lg:text-5xl">
              {c.ctaFinalTitle}
            </h2>
            <p className="mx-auto mb-10 max-w-xl text-base leading-7 text-neutral-300 sm:text-lg">
              {c.ctaFinalBody}
            </p>
            <Link
              to={primaryTo}
              className="inline-flex h-12 items-center gap-2 rounded-md bg-emerald-500 px-8 text-base font-semibold text-neutral-950 hover:bg-emerald-400"
            >
              <PrimaryIcon className="size-5" aria-hidden="true" />
              {session ? t("top.ctaDashboard") : c.ctaStart}
            </Link>
          </div>
        </section>

      </main>
    </div>
  );
}
