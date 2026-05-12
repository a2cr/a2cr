import { ArrowRight, Bot, CheckCircle2, LayoutDashboard, LogIn, PlugZap, ShieldCheck } from "lucide-react";
import type { ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { CopyButton } from "../components/CopyButton";
import { LanguageToggle } from "../components/LanguageToggle";
import { serviceUrl } from "../lib/format";
import { useAuth } from "../providers/AuthProvider";

type Language = "en" | "ja";
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
      'command = "a2cr-mcp"',
      "args = []",
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
          command: "a2cr-mcp",
          args: [],
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

const text = {
  en: {
    navGuide: "Guide",
    navAgent: "AI agent guide",
    navManual: "Manual",
    pricing: "Pricing",
    signIn: "Sign in",
    dashboard: "Open dashboard",
    heroTitle: "A2CR setup and operation manual",
    heroBody:
      "A practical path from sign-in to real use: issue an API key, connect MCP, add project memory instructions, save WorkBaton slots, resume them, and understand what the AI receives from MCP, WorkBaton, and WorkStash.",
    startCta: "Start with sign-in",
    guideCta: "Read concept guide",
    overviewTitle: "What this page covers",
    overviewItems: [
      "For beginners: the exact sequence from login to a working MCP setup.",
      "For project owners: the text to add to AGENTS.md, CLAUDE.md, or another memory file so AI agents use A2CR proactively.",
      "For daily use: how to save to a Slot, resume from a Slot, and decide when WorkStash is needed.",
      "For trust and debugging: what information the AI receives from MCP tool descriptions, explain_a2cr_flows, resume_context, and WorkStash reads."
    ],
    stepsTitle: "From login to first successful use",
    steps: [
      {
        title: "Confirm Python is available",
        body: "The current A2CR MCP wrapper runs with Python. In a terminal, run python --version. If the command is not found, install Python first, then reopen the terminal or AI client."
      },
      {
        title: "Sign in and issue an API key",
        body: "Open A2CR, sign in, go to Settings, then issue an API key. The key is shown once. If you issue a new key later, it is a different key. Paste it into your MCP config yourself; do not paste secrets into chat."
      },
      {
        title: "Install the A2CR MCP wrapper",
        body: "Install the local stdio MCP wrapper as the a2cr-mcp command. The AI client starts this command in the background when it needs A2CR tools."
      },
      {
        title: "Add one MCP server named a2cr",
        body: "Add the config for your client. Keep existing MCP servers intact. The official WorkBaton save path is the local stdio wrapper because it encrypts before upload."
      },
      {
        title: "Ask the AI to verify the connection",
        body: "In a new AI session, ask it to call get_account_limits and explain_a2cr_flows. A working setup should report plan limits and explain WorkBaton, WorkStash, and WorkThreads boundaries."
      },
      {
        title: "Add project memory instructions",
        body: "Add the snippet below to AGENTS.md, CLAUDE.md, or the equivalent memory file. This is what makes capable AI agents use A2CR when needed without being reminded every time."
      },
      {
        title: "Save and resume once",
        body: "Save a small WorkBaton at a clear milestone, open a fresh AI window, then resume with resume_context(slot_number=N) or resume_context(slot_name=\"...\")."
      }
    ],
    configTitle: "MCP config examples",
    configBody:
      "Use one of these examples after installing a2cr-mcp. Replace placeholders locally. Do not send the API key to an AI chat.",
    accessTitle: "Using the same WorkBaton from another PC",
    accessBody:
      "A2CR needs two different secrets for another PC to resume the same encrypted WorkBaton: the A2CR API key for access, and the same local client key for decryption.",
    accessItems: [
      "The full API key is shown only once when issued. Reissuing creates a different API key, so update every MCP config that should keep using A2CR.",
      "The local client key file is created by the a2cr-mcp wrapper during the first client-encrypted save when no key file exists.",
      "Set A2CR_CLIENT_KEY_FILE to choose the exact key file path. Set A2CR_CONFIG_DIR to choose the directory that contains workbaton.key.",
      "If neither variable is set, the default path is %APPDATA%\\A2CR\\workbaton.key on Windows, and $XDG_CONFIG_HOME/a2cr/workbaton.key or ~/.config/a2cr/workbaton.key on macOS/Linux.",
      "API key only: the PC can access encrypted slot data but cannot read the WorkBaton body. API key plus the same local client key: the PC can decrypt and resume it."
    ],
    copyConfig: "Copy config",
    memoryTitle: "Project memory snippet",
    memoryBody:
      "Put this in the file your AI reads at the start of a project. Common targets are AGENTS.md for Codex/ChatGPT-style agents and CLAUDE.md for Claude Code.",
    memoryFiles: [
      ["Codex / ChatGPT-style agents", "AGENTS.md"],
      ["Claude Code", "CLAUDE.md"],
      ["Gemini CLI", "GEMINI.md"],
      ["Cursor", ".cursor/rules/a2cr.mdc"],
      ["Windsurf", ".windsurfrules"],
      ["Roo Code", ".roorules"],
      ["GitHub Copilot", ".github/copilot-instructions.md"]
    ] as [string, string][],
    memorySnippet:
      "## A2CR WorkBaton / WorkStash Autonomy\n\nA2CR MCP tools may be used proactively when they help preserve useful work state. Use the configured MCP tools only; do not invent direct HTTP API calls.\n\nAt the start of a session, when the tools are available, call get_account_limits and explain_a2cr_flows to confirm the connection, WorkBaton size budget, WorkStash quota, and available flows.\n\nUse WorkBaton for focused handoff checkpoints at task milestones, after validation, before likely context loss, or when context drift/contamination is detected. If unsure, call should_save_workbaton, then save_context when recommended.\n\nUse WorkStash for safe supporting notes that would bloat the WorkBaton body, such as confirmed file paths, API findings, failed attempts, or concise validation notes. Record the returned entry_key in the WorkBaton references or next_action.\n\nIf the conversation feels noisy, contradictory, stale, or polluted by old task state, call should_save_workbaton with reason=\"context_drift\" or reason=\"context_contamination\". If saving is recommended, use the available WorkBaton size budget intelligently, move safe bulky notes into WorkStash, record entry_key values, and suggest continuing in a fresh AI window.\n\nNever save secrets, API keys, Authorization headers, cookies, private database URLs, personal data, full transcripts, long logs, generated caches, git diffs, or large source-code bodies.",
    copySnippet: "Copy snippet",
    saveTitle: "Saving to a Slot",
    saveBody:
      "A WorkBaton Slot should contain enough state for the next AI to continue, not a full transcript. Routine saves should happen at clear boundaries.",
    saveChecklist: [
      "Call get_account_limits before automatic or large saves so the AI knows plan limits and WorkBaton size budget.",
      "Call should_save_workbaton when the save is discretionary or related to context pressure.",
      "Save goal, current_state, next_action, key decisions, blockers, validation status, and any WorkStash entry_key references.",
      "Keep the body focused on resume-critical state. Move bulky supporting notes to WorkStash instead of making the WorkBaton large.",
      "Never include secrets, .env content, API keys, authorization headers, long logs, or full transcripts."
    ],
    saveExample:
      'save_context({\n  slot_name: "my-project-next-step",\n  body: {\n    goal: "Continue the feature from the last verified state.",\n    current_state: "Implementation is complete; build passed.",\n    next_action: "Open a fresh window and run the smoke test.",\n    decisions: ["Use the existing local stdio MCP wrapper."],\n    blockers: [],\n    validation: ["npm run build passed"],\n    references: ["work_stash:entry_key_if_needed"]\n  }\n})',
    resumeTitle: "Reading from a Slot",
    resumeBody:
      "In a new AI window, give the Slot number or Slot name. The AI should load that exact Slot first, then retrieve only referenced WorkStash entries needed for the current task.",
    resumeExamples: [
      "resume_context(slot_number=5)",
      'resume_context(slot_name="my-project-next-step")'
    ],
    loadItems: [
      "The saved handoff content: goal, current_state, next_action, decisions, blockers, validation, and references.",
      "Slot metadata such as slot_name, slot_number, expiry, encryption mode, load count, and status.",
      "Language hints such as response_language_hint or language_context when present.",
      "Advisory agent_continuity_guidance about using WorkBaton and WorkStash proactively.",
      "Any referenced WorkStash entry_key values. The AI should call get_work_stash only for entries needed to continue."
    ],
    mcpTitle: "What the AI receives from MCP",
    mcpBody:
      "When A2CR MCP is connected, the AI does not only receive tool names. The tool descriptions and flow guidance teach it what A2CR is for and how to use it safely.",
    mcpItems: [
      "WorkBaton is a compact serial checkpoint handoff, not a chat log, file store, or live multi-agent task lease.",
      "WorkStash is temporary supporting memory for safe notes that would make the WorkBaton too large.",
      "The local stdio wrapper is the official WorkBaton save path because it encrypts content locally before upload.",
      "Direct guessed HTTP API calls should not be used. The configured MCP tools are the supported path.",
      "The AI should call explain_a2cr_flows when newly connected or unsure which flow applies.",
      "The AI should call get_account_limits before automatic saves so it respects plan, size budget, WorkStash limits, and rate limits.",
      "The AI receives safety rules for material that must not be stored."
    ],
    stashTitle: "What WorkStash adds",
    stashBody:
      "WorkStash is useful when the next AI may need supporting notes, but putting those notes into the WorkBaton would make the checkpoint noisy.",
    stashGood: [
      "Confirmed file paths and target modules.",
      "API behavior notes or reproduction details.",
      "Failed attempts and why they failed.",
      "Concise validation summaries.",
      "Small decisions that support the next action."
    ],
    stashBad: [
      "Secrets, API keys, auth headers, cookies, private DB URLs, or .env content.",
      "Personal data, full transcripts, long logs, generated caches, git diffs, or large source-code bodies.",
      "Durable knowledge-base content that should live in repository docs instead."
    ],
    autonomyTitle: "How automatic use becomes reliable",
    autonomyBody:
      "A2CR cannot force every AI client to behave the same way. The reliable pattern is to combine MCP tool descriptions, project memory files, and a capable agent that respects tool guidance.",
    autonomyItems: [
      "MCP tells the agent what tools exist, what each tool is for, and which data must not be saved.",
      "AGENTS.md, CLAUDE.md, or another memory file tells the agent to use WorkBaton and WorkStash when needed without waiting for the user.",
      "The loaded WorkBaton tells the new window the current goal, state, next action, and any WorkStash references.",
      "When context drift or contamination appears, the agent can call should_save_workbaton and suggest a fresh window."
    ],
    pythonTitle: "Python prerequisite",
    pythonBody:
      "The current A2CR local stdio MCP wrapper is a Python program. The AI client starts that local program in the background, so Python must be available before A2CR MCP can run.",
    pythonItems: [
      "Recommended version: Python 3.13.",
      "Python 3.12 or newer is expected to work, but choose Python 3.13 if you are unsure.",
      "Avoid development builds such as Python 3.15 alpha or beta.",
      "Installation is left to the user's environment. If unsure, ask your AI agent how to install Python for your OS."
    ],
    pythonCommandLabel: "Check your Python version:",
    pythonCommand: "python --version",
    installTitle: "Install a2cr-mcp",
    installBody:
      "After Python is available, install the A2CR MCP wrapper from PyPI. This creates the a2cr-mcp command used in the MCP config below.",
    installCommandLabel: "Install or update command:",
    installCommand: "python -m pip install --upgrade a2cr-mcp"
  },
  ja: {
    navGuide: "ガイド",
    navAgent: "AI向けガイド",
    navManual: "使用説明書",
    pricing: "料金",
    signIn: "ログイン",
    dashboard: "ダッシュボード",
    heroTitle: "A2CR セットアップ・使用説明書",
    heroBody:
      "ログインから実際に使えるようになるまでの具体的な流れ、AGENTS.md / CLAUDE.md への追記、Slot への保存と読み込み、MCP / WorkBaton / WorkStash から AI が受け取る情報を一つの手順としてまとめています。",
    startCta: "ログインから始める",
    guideCta: "概念ガイドを見る",
    overviewTitle: "このページでできること",
    overviewItems: [
      "素人でも迷わないように、ログインから MCP 接続完了までを順番に確認できます。",
      "AI エージェントが自発的に A2CR を使うために、AGENTS.md や CLAUDE.md へ追加する文章を確認できます。",
      "WorkBaton Slot への保存方法、Slot からの読み込み方法、WorkStash を使う判断基準を確認できます。",
      "MCP 接続時、resume_context 実行時、WorkStash 取得時に AI が受け取る情報の種類を確認できます。"
    ],
    stepsTitle: "ログインから初回利用まで",
    steps: [
      {
        title: "Python が使えるか確認する",
        body: "現在の A2CR MCP wrapper は Python で動きます。ターミナルで python --version を実行し、Python が使えることを確認します。見つからない場合は先に Python をインストールし、ターミナルや AI クライアントを開き直します。"
      },
      {
        title: "ログインして API key を発行する",
        body: "A2CR にログインし、Settings から API key を発行します。キーは一度だけ表示されます。後から再発行すると別の API key になります。AI チャットに貼らず、ユーザー自身が MCP 設定ファイルへ貼り付けます。"
      },
      {
        title: "A2CR MCP wrapper をインストールする",
        body: "local stdio MCP wrapper を a2cr-mcp コマンドとしてインストールします。AI クライアントは、A2CR tools が必要な時にこのコマンドを裏側で起動します。"
      },
      {
        title: "a2cr という MCP server を 1 つ追加する",
        body: "利用中のクライアントに合わせて設定を追加します。既存の MCP server は消さないでください。WorkBaton の公式保存経路は、送信前にローカルで暗号化する stdio wrapper です。"
      },
      {
        title: "AI に接続確認をさせる",
        body: "新しい AI セッションで get_account_limits と explain_a2cr_flows を呼ばせます。成功すると、プラン制限と WorkBaton / WorkStash / WorkThreads の使い分けを確認できます。"
      },
      {
        title: "プロジェクト memory file に追記する",
        body: "下の文章を AGENTS.md、CLAUDE.md、または同等の memory file に追加します。これにより、対応 AI は毎回ユーザーに言われなくても必要時に A2CR を使う方針を読みます。"
      },
      {
        title: "一度保存して、新しい窓で読み込む",
        body: "区切りのよい時点で小さな WorkBaton を保存し、新しい AI 窓で resume_context(slot_number=N) または resume_context(slot_name=\"...\") を実行します。"
      }
    ],
    configTitle: "MCP 設定例",
    configBody:
      "a2cr-mcp をインストールした後、下の形を参考に MCP 設定を追加します。API key は AI チャットへ送らず、ローカル設定ファイルに貼り付けます。",
    accessTitle: "別のPCで同じ WorkBaton を使う",
    accessBody:
      "別のPCで同じ暗号化済み WorkBaton を再開するには、A2CRへアクセスするための API key と、本文を復号するための同じ local client key の両方が必要です。",
    accessItems: [
      "API key の全文は発行時に一度だけ表示されます。再発行すると別の API key になるため、A2CR を使い続ける MCP 設定は新しい key に更新してください。",
      "local client key ファイルは、既存ファイルがない状態で初回の client-encrypted 保存を行う時に、a2cr-mcp wrapper が作成します。",
      "A2CR_CLIENT_KEY_FILE を指定すると、使う key ファイルのパスを固定できます。A2CR_CONFIG_DIR を指定すると、そのディレクトリ内の workbaton.key が使われます。",
      "どちらも未指定の場合、Windows では %APPDATA%\\A2CR\\workbaton.key、macOS/Linux では $XDG_CONFIG_HOME/a2cr/workbaton.key または ~/.config/a2cr/workbaton.key が既定の保存場所です。",
      "API key だけでは暗号化済み Slot へアクセスできても本文は読めません。API key と同じ local client key の両方があるPCだけが、保存済み WorkBaton を復号して再開できます。"
    ],
    copyConfig: "設定をコピー",
    memoryTitle: "AGENTS.md / CLAUDE.md に追加する文章",
    memoryBody:
      "AI がプロジェクト開始時に読むファイルへ入れます。Codex / ChatGPT 系なら AGENTS.md、Claude Code なら CLAUDE.md が代表例です。",
    memoryFiles: [
      ["Codex / ChatGPT 系エージェント", "AGENTS.md"],
      ["Claude Code", "CLAUDE.md"],
      ["Gemini CLI", "GEMINI.md"],
      ["Cursor", ".cursor/rules/a2cr.mdc"],
      ["Windsurf", ".windsurfrules"],
      ["Roo Code", ".roorules"],
      ["GitHub Copilot", ".github/copilot-instructions.md"]
    ] as [string, string][],
    memorySnippet:
      "## A2CR WorkBaton / WorkStash Autonomy\n\nA2CR MCP tools may be used proactively when they help preserve useful work state. Use the configured MCP tools only; do not invent direct HTTP API calls.\n\nAt the start of a session, when the tools are available, call get_account_limits and explain_a2cr_flows to confirm the connection, WorkBaton size budget, WorkStash quota, and available flows.\n\nUse WorkBaton for focused handoff checkpoints at task milestones, after validation, before likely context loss, or when context drift/contamination is detected. If unsure, call should_save_workbaton, then save_context when recommended.\n\nUse WorkStash for safe supporting notes that would bloat the WorkBaton body, such as confirmed file paths, API findings, failed attempts, or concise validation notes. Record the returned entry_key in the WorkBaton references or next_action.\n\nIf the conversation feels noisy, contradictory, stale, or polluted by old task state, call should_save_workbaton with reason=\"context_drift\" or reason=\"context_contamination\". If saving is recommended, use the available WorkBaton size budget intelligently, move safe bulky notes into WorkStash, record entry_key values, and suggest continuing in a fresh AI window.\n\nNever save secrets, API keys, Authorization headers, cookies, private database URLs, personal data, full transcripts, long logs, generated caches, git diffs, or large source-code bodies.",
    copySnippet: "文章をコピー",
    saveTitle: "Slot へ保存する",
    saveBody:
      "WorkBaton Slot には、次の AI が作業を再開するために必要な状態だけを入れます。会話全文ではなく、区切りのよい作業状態です。",
    saveChecklist: [
      "自動保存や大きめの保存の前に get_account_limits を呼び、プラン制限、WorkBaton サイズ予算、WorkStash quota を確認します。",
      "保存すべきか迷う時や context 圧迫を感じた時は should_save_workbaton を呼びます。",
      "goal、current_state、next_action、重要な決定、blockers、validation、WorkStash entry_key 参照を保存します。",
      "WorkBaton は再開に必要な状態へ絞り、詳しいメモは WorkStash に分けます。",
      "secrets、.env、API key、認証ヘッダー、長いログ、会話全文は保存しません。"
    ],
    saveExample:
      'save_context({\n  slot_name: "my-project-next-step",\n  body: {\n    goal: "最後に検証済みの状態から機能を続ける。",\n    current_state: "実装は完了し、build は通っている。",\n    next_action: "新しい窓で再開し、smoke test を実行する。",\n    decisions: ["公式経路として local stdio MCP wrapper を使う。"],\n    blockers: [],\n    validation: ["npm run build passed"],\n    references: ["work_stash:必要な場合の entry_key"]\n  }\n})',
    resumeTitle: "Slot から読み込む",
    resumeBody:
      "新しい AI 窓では Slot number または Slot name を渡します。AI はまず指定 Slot を読み込み、必要な WorkStash entry_key だけを追加取得します。",
    resumeExamples: [
      "resume_context(slot_number=5)",
      'resume_context(slot_name="my-project-next-step")'
    ],
    loadItems: [
      "保存された引き継ぎ本文: goal、current_state、next_action、decisions、blockers、validation、references。",
      "Slot のメタ情報: slot_name、slot_number、expires_at、encryption_mode、load_count、status など。",
      "存在する場合は response_language_hint や language_context などの応答言語ヒント。",
      "WorkBaton / WorkStash を継続利用するための advisory な agent_continuity_guidance。",
      "WorkStash entry_key の参照。AI は現在の作業に必要なものだけ get_work_stash で取得します。"
    ],
    mcpTitle: "MCP 接続時に AI が受け取る情報",
    mcpBody:
      "A2CR MCP に接続すると、AI は単に tool 名だけを受け取るのではありません。tool descriptions と flow guidance から、A2CR の用途と安全な使い方を読み取ります。",
    mcpItems: [
      "WorkBaton はサイズ予算内の focused serial checkpoint handoff であり、chat log、file store、live multi-agent task lease ではないこと。",
      "WorkStash は、WorkBaton を肥大化させないための一時的な補助メモであること。",
      "local stdio wrapper が公式の WorkBaton 保存経路であり、送信前にローカルで暗号化すること。",
      "直接 HTTP API を推測して呼ばず、設定済み MCP tools を使うこと。",
      "接続直後や使い分けに迷う時は explain_a2cr_flows を呼ぶこと。",
      "自動保存前には get_account_limits を呼び、プラン、サイズ、detail、rate limit を尊重すること。",
      "保存してはいけない情報、つまり secrets、API key、認証ヘッダー、個人情報、長いログなど。"
    ],
    stashTitle: "WorkStash が加えるもの",
    stashBody:
      "WorkStash は、次の AI が参照する可能性はあるが、WorkBaton に入れると重くなる詳細メモを分けるために使います。",
    stashGood: [
      "確認済みの file path や対象 module。",
      "API の挙動メモや再現条件。",
      "失敗した試行と、なぜ失敗したか。",
      "短い検証結果の要約。",
      "next_action を支える小さな判断理由。"
    ],
    stashBad: [
      "secrets、API key、auth header、cookie、private DB URL、.env 内容。",
      "個人情報、会話全文、長いログ、生成キャッシュ、git diff、大きな source code 本文。",
      "本来 repository docs に書くべき永続的なナレッジ。"
    ],
    autonomyTitle: "自発利用が成立する仕組み",
    autonomyBody:
      "A2CR はすべての AI クライアントの動作を強制するものではありません。信頼性を上げる基本形は、MCP tool descriptions、プロジェクト memory file、それを読む性能のある AI エージェントを組み合わせることです。",
    autonomyItems: [
      "MCP が、どの tool があり、何に使い、何を保存してはいけないかを AI に渡します。",
      "AGENTS.md、CLAUDE.md などが、必要時に WorkBaton / WorkStash を自発利用する方針を AI に渡します。",
      "読み込まれた WorkBaton が、新しい窓へ goal、状態、next action、WorkStash 参照を渡します。",
      "context drift や context contamination を感じた時、AI は should_save_workbaton を呼び、新しい窓への移行を提案できます。"
    ],
    pythonTitle: "Python の事前確認",
    pythonBody:
      "現在の A2CR local stdio MCP wrapper は Python のプログラムです。AI クライアントは裏側でこのローカルプログラムを起動するため、A2CR MCP を使う前に Python が必要です。",
    pythonItems: [
      "推奨バージョン: Python 3.13。",
      "Python 3.12 以上なら利用できる想定ですが、迷ったら Python 3.13 を入れてください。",
      "Python 3.15 alpha / beta などの開発版は避けてください。",
      "インストール方法は利用環境によって違うため、ここでは細かく扱いません。分からない場合は、使っている AI に OS 名を添えて聞いてください。"
    ],
    pythonCommandLabel: "ターミナルで下記コマンドを実行すると、バージョンを確認できます。",
    pythonCommand: "python --version",
    installTitle: "a2cr-mcp をインストールする",
    installBody:
      "Python が使える状態になったら、PyPI から A2CR MCP wrapper をインストールします。これにより、下の MCP 設定で使う a2cr-mcp コマンドが作られます。",
    installCommandLabel: "インストールまたは更新コマンド:",
    installCommand: "python -m pip install --upgrade a2cr-mcp"
  }
};

function PublicHeader({ language }: { language: Language }) {
  const { session } = useAuth();
  const t = text[language];

  return (
    <header className="border-b border-neutral-200 bg-white">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-4 py-4 sm:px-6">
        <Link to="/" className="flex items-center gap-3">
          <img src="/brand/a2cr-logo-v2.png" alt="A2CR" className="h-20 w-auto object-contain" />
          <span className="sr-only">A2CR</span>
        </Link>
        <div className="flex flex-wrap items-center justify-end gap-2">
          <Link to={language === "ja" ? "/guide" : "/en/guide"} className="rounded-md px-3 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-100">
            {t.navGuide}
          </Link>
          <a href="/agent-guide.html" className="rounded-md px-3 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-100">
            {t.navAgent}
          </a>
          <Link to={language === "ja" ? "/manual" : "/en/manual"} className="rounded-md bg-neutral-900 px-3 py-2 text-sm font-medium text-white">
            {t.navManual}
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
  children,
  tone = "white"
}: {
  eyebrow: string;
  title: string;
  body?: string;
  children?: ReactNode;
  tone?: "white" | "tint";
}) {
  return (
    <section className={`border-y border-neutral-200 ${tone === "tint" ? "bg-emerald-50" : "bg-white"}`}>
      <div className="mx-auto grid max-w-7xl gap-6 px-4 py-10 sm:px-6 lg:grid-cols-[0.85fr_1.15fr]">
        <div>
          <div className="text-xs font-semibold uppercase tracking-normal text-emerald-700">{eyebrow}</div>
          <h2 className="mt-2 text-2xl font-semibold tracking-normal text-neutral-950">{title}</h2>
          {body && <p className="mt-3 max-w-3xl text-sm leading-6 text-neutral-600">{body}</p>}
        </div>
        <div>{children}</div>
      </div>
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

function StepList({ steps }: { steps: { title: string; body: string }[] }) {
  return (
    <ol className="grid gap-3">
      {steps.map((step, index) => (
        <li key={step.title} className="rounded-md border border-neutral-200 bg-white p-4">
          <div className="flex items-start gap-4">
            <span className="flex size-8 shrink-0 items-center justify-center rounded-md bg-emerald-700 text-sm font-semibold text-white">
              {index + 1}
            </span>
            <div>
              <h3 className="font-semibold text-neutral-950">{step.title}</h3>
              <p className="mt-2 text-sm leading-6 text-neutral-700">{step.body}</p>
            </div>
          </div>
        </li>
      ))}
    </ol>
  );
}

function CodeBlock({ value, label }: { value: string; label?: string }) {
  return (
    <div>
      {label && <div className="mb-2 text-sm font-semibold text-neutral-950">{label}</div>}
      <pre className="overflow-auto rounded-md bg-neutral-950 p-3 text-xs leading-5 text-neutral-50 whitespace-pre-wrap">{value}</pre>
    </div>
  );
}

export function ManualPage() {
  const { i18n } = useTranslation();
  const { session } = useAuth();
  const location = useLocation();
  const language: Language = location.pathname.startsWith("/en/") ? "en" : i18n.language.startsWith("ja") ? "ja" : "en";
  const t = text[language];
  const primaryTo = session ? "/dashboard" : "/login";

  return (
    <div className="min-h-screen bg-neutral-50 text-neutral-950">
      <PublicHeader language={language} />
      <main>
        <section className="border-b border-neutral-200 bg-white">
          <div className="mx-auto grid max-w-7xl gap-8 px-4 py-12 sm:px-6 lg:grid-cols-[0.95fr_1.05fr] lg:items-center">
            <div>
              <div className="mb-3 text-xs font-semibold uppercase tracking-normal text-emerald-700">Manual</div>
              <h1 className="max-w-3xl text-4xl font-semibold tracking-normal sm:text-5xl">{t.heroTitle}</h1>
              <p className="mt-5 max-w-2xl text-base leading-7 text-neutral-600">{t.heroBody}</p>
              <div className="mt-8 flex flex-wrap gap-3">
                <Link
                  to={primaryTo}
                  className="inline-flex h-11 items-center gap-2 rounded-md bg-emerald-700 px-4 text-sm font-semibold text-white hover:bg-emerald-800"
                >
                  {session ? <LayoutDashboard className="size-4" /> : <LogIn className="size-4" />}
                  {session ? t.dashboard : t.startCta}
                </Link>
                <Link
                  to={language === "ja" ? "/guide" : "/en/guide"}
                  className="inline-flex h-11 items-center gap-2 rounded-md border border-neutral-300 bg-white px-4 text-sm font-semibold text-neutral-800 hover:bg-neutral-100"
                >
                  {t.guideCta}
                  <ArrowRight className="size-4" aria-hidden="true" />
                </Link>
              </div>
            </div>
            <div className="grid gap-3">
              <article className="rounded-md border border-emerald-200 bg-emerald-50 p-4">
                <div className="flex items-start gap-3">
                  <PlugZap className="mt-1 size-5 shrink-0 text-emerald-700" aria-hidden="true" />
                  <p className="text-sm leading-6 text-emerald-900">{t.mcpItems[2]}</p>
                </div>
              </article>
              <article className="rounded-md border border-neutral-200 bg-white p-4">
                <div className="flex items-start gap-3">
                  <Bot className="mt-1 size-5 shrink-0 text-neutral-700" aria-hidden="true" />
                  <p className="text-sm leading-6 text-neutral-700">{t.autonomyItems[1]}</p>
                </div>
              </article>
              <article className="rounded-md border border-red-200 bg-red-50 p-4">
                <div className="flex items-start gap-3">
                  <ShieldCheck className="mt-1 size-5 shrink-0 text-red-700" aria-hidden="true" />
                  <p className="text-sm leading-6 text-red-900">{t.saveChecklist[4]}</p>
                </div>
              </article>
            </div>
          </div>
        </section>

        <Section eyebrow="Overview" title={t.overviewTitle}>
          <BulletList items={t.overviewItems} />
        </Section>

        <Section eyebrow="Prerequisite" title={t.pythonTitle} body={t.pythonBody}>
          <div className="grid gap-4">
            <BulletList items={t.pythonItems} />
            <CodeBlock value={t.pythonCommand} label={t.pythonCommandLabel} />
          </div>
        </Section>

        <Section eyebrow="Setup" title={t.stepsTitle} tone="tint">
          <StepList steps={t.steps} />
        </Section>

        <Section eyebrow="Install" title={t.installTitle} body={t.installBody}>
          <CodeBlock value={t.installCommand} label={t.installCommandLabel} />
        </Section>

        <Section eyebrow="MCP" title={t.configTitle} body={t.configBody}>
          <div className="grid gap-4">
            {(Object.keys(clientLabels) as ClientKey[]).map((client) => {
              const snippet = mcpConfigSnippet(client);
              return (
                <article key={client} className="rounded-md border border-neutral-200 bg-neutral-50 p-4">
                  <div className="mb-3 flex items-center justify-between gap-3">
                    <h3 className="font-semibold">{clientLabels[client]}</h3>
                    <CopyButton value={snippet} label={t.copyConfig} compact />
                  </div>
                  <CodeBlock value={snippet} />
                </article>
              );
            })}
          </div>
        </Section>

        <Section eyebrow="Keys" title={t.accessTitle} body={t.accessBody} tone="tint">
          <BulletList items={t.accessItems} />
        </Section>

        <Section eyebrow="Project memory" title={t.memoryTitle} body={t.memoryBody} tone="tint">
          <div className="grid gap-4">
            <div className="overflow-hidden rounded-md border border-neutral-200 bg-white">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-neutral-200 bg-neutral-50">
                    <th className="px-4 py-2 font-semibold text-neutral-950">AI / Tool</th>
                    <th className="px-4 py-2 font-semibold text-neutral-950">File</th>
                  </tr>
                </thead>
                <tbody>
                  {t.memoryFiles.map(([ai, file]) => (
                    <tr key={file} className="border-t border-neutral-100">
                      <td className="px-4 py-2 text-neutral-700">{ai}</td>
                      <td className="px-4 py-2 font-mono text-xs text-neutral-900">{file}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="flex items-center justify-between gap-3">
              <span className="text-sm font-semibold text-neutral-950">snippet</span>
              <CopyButton value={t.memorySnippet} label={t.copySnippet} compact />
            </div>
            <CodeBlock value={t.memorySnippet} />
          </div>
        </Section>

        <Section eyebrow="Save" title={t.saveTitle} body={t.saveBody}>
          <div className="grid gap-4">
            <BulletList items={t.saveChecklist} />
            <CodeBlock value={t.saveExample} label="example" />
          </div>
        </Section>

        <Section eyebrow="Resume" title={t.resumeTitle} body={t.resumeBody} tone="tint">
          <div className="grid gap-4">
            <div className="grid gap-3 sm:grid-cols-2">
              {t.resumeExamples.map((example) => (
                <CodeBlock key={example} value={example} />
              ))}
            </div>
            <BulletList items={t.loadItems} />
          </div>
        </Section>

        <Section eyebrow="MCP guidance" title={t.mcpTitle} body={t.mcpBody}>
          <BulletList items={t.mcpItems} />
        </Section>

        <Section eyebrow="WorkStash" title={t.stashTitle} body={t.stashBody} tone="tint">
          <div className="grid gap-4 lg:grid-cols-2">
            <article>
              <h3 className="mb-3 font-semibold text-neutral-950">Good WorkStash entries</h3>
              <BulletList items={t.stashGood} />
            </article>
            <article>
              <h3 className="mb-3 font-semibold text-neutral-950">Do not store</h3>
              <BulletList items={t.stashBad} />
            </article>
          </div>
        </Section>

        <Section eyebrow="Autonomy" title={t.autonomyTitle} body={t.autonomyBody}>
          <BulletList items={t.autonomyItems} />
        </Section>
      </main>
    </div>
  );
}
