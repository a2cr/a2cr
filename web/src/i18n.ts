import i18n from "i18next";
import { initReactI18next } from "react-i18next";

const resources = {
  en: {
    translation: {
      appName: "A2CR",
      appSubtitle: "Agent-to-Agent Context Relay",
      nav: {
        dashboard: "Dashboard",
        guide: "Guide",
        settings: "Settings",
        pricing: "Pricing",
        signOut: "Sign out"
      },
      auth: {
        title: "Sign in to A2CR",
        google: "Continue with Google",
        missingConfig: "Supabase public config is not set.",
        missingConfigBody: "Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY for the React dashboard.",
        signingIn: "Opening Google sign-in"
      },
      top: {
        heroBody:
          "Stop re-explaining your project every session. A2CR saves focused WorkBaton checkpoints so any MCP-capable AI configured with A2CR MCP can pick up exactly where the last one left off, across windows, models, and days.",
        ctaDashboard: "Open dashboard",
        ctaPricing: "View pricing",
        points: {
          checkpoints: {
            title: "Your AI remembers where it stopped",
            body: "WorkBaton saves goal, progress, and next step before the session ends. The next configured MCP-capable AI resumes without re-explaining anything."
          },
          mcp: {
            title: "Works across Claude, Codex, Cursor, and more",
            body: "Any MCP-capable client configured with A2CR MCP connects to the same checkpoint layer. Start in one tool, continue in another without losing state."
          },
          inspection: {
            title: "You stay in control",
            body: "The dashboard shows usage, limits, and access logs without exposing your saved content. Saved bodies are client-encrypted — A2CR cannot read them."
          }
        },
        originTitle: "How A2CR works",
        originBody:
          "A2CR runs as a hosted service. Install a2cr-mcp from PyPI, connect your AI via MCP, save encrypted WorkBaton checkpoints through the local stdio wrapper, and resume from any new window or tool.",
        surfaces: {
          dashboard: "View slots, usage, limits, and access logs. Saved content is never exposed.",
          api: "Authenticated paths for WorkBaton save, load, resume, and delete.",
          mcp: "MCP tools for AI clients. WorkBaton saving uses the PyPI-installed local stdio wrapper for client-side encryption before upload."
        }
      },
      common: {
        loading: "Loading",
        refresh: "Refresh",
        copy: "Copy",
        copied: "Copied",
        save: "Save",
        cancel: "Cancel",
        issue: "Issue key",
        revoke: "Revoke",
        never: "Never",
        none: "None",
        auto: "Auto",
        compact: "Compact",
        detailed: "Detailed",
        free: "Free",
        pro: "Pro",
        empty: "No active slots",
        status: "Status",
        updated: "Updated",
        expires: "Expires",
        created: "Created",
        lastUsed: "Last used",
        plan: "Plan",
        action: "Action",
        slot: "Slot",
        slotNumber: "Slot number",
        client: "Client"
      },
      dashboard: {
        title: "WorkBaton",
        activeSlots: "Active slots",
        totalSaves: "Total saves",
        totalLoads: "Total loads",
        totalDeletes: "Deletes",
        tokensSaved: "Estimated tokens saved",
        tokensSavedHelp:
          "Estimate = original source context length converted to tokens minus saved WorkBaton tokens. Saves without original_length are not calculated.",
        copySavePrompt: "Copy save prompt",
        copyResumePrompt: "Copy resume prompt",
        copyResumeCall: "Copy call",
        deleteSlot: "Delete slot",
        confirmDeleteSlot: "Delete {{slot}}?",
        autoReload: "Auto reload",
        slots: "Slots",
        accessLogs: "Access logs",
        size: "Size",
        tokens: "Saved tokens",
        loads: "Loads",
        detail: "Detail",
        source: "Source",
        noLogs: "No access logs",
        notCalculated: "Not calculated",
        emptyTitle: "No active WorkBaton slots",
        emptyBody: "Create a checkpoint from an MCP-capable AI client and it will appear here.",
        workStash: "WorkStash",
        workStashStorage: "Storage",
        workStashEntries: "Entries"
      },
      settings: {
        title: "Settings",
        account: "Account",
        apiKey: "API key",
        apiKeyPrefix: "Current prefix",
        newApiKey: "New API key",
        keyShownOnce: "Shown once. Store it in your MCP client configuration. Reissuing creates a different API key.",
        retention: "Default retention",
        locale: "Interface language",
        responseLanguage: "Response language",
        timezone: "Timezone",
        setup: "MCP setup",
        setupInstall: "Install or update the wrapper first: python -m pip install --upgrade a2cr-mcp. Then use the config snippet below.",
        genericResume: "Generic resume prompt",
        saved: "Settings saved",
        noApiKey: "No active API key"
      },
      pricing: {
        title: "Pricing",
        freeName: "Free",
        proName: "Pro",
        freePrice: "$0",
        proPrice: "$8 / month",
        slots: "Active slots",
        retention: "Retention",
        body: "Checkpoint size",
        handoff: "AI handoff",
        focusedHandoff: "Focused size budget",
        richerHandoff: "Richer size budget",
        saves: "Saves",
        loads: "Loads",
        logs: "Access logs",
        workthreads: "WorkThreads",
        workStash: "WorkStash storage",
        notIncluded: "Not included",
        planned: "Coming soon",
        comingSoon: "Coming soon"
      },
      errors: {
        generic: "Request failed",
        refreshFailedCached: "Refresh failed. Showing the last successful data.",
        unauthenticated: "Sign in again to continue"
      }
    }
  },
  ja: {
    translation: {
      appName: "A2CR",
      appSubtitle: "Agent-to-Agent Context Relay",
      nav: {
        dashboard: "ダッシュボード",
        guide: "ガイド",
        settings: "設定",
        pricing: "料金",
        signOut: "サインアウト"
      },
      auth: {
        title: "A2CR にログイン",
        google: "Google で続行",
        missingConfig: "Supabase の公開設定が未設定です。",
        missingConfigBody: "React ダッシュボード用に VITE_SUPABASE_URL と VITE_SUPABASE_ANON_KEY を設定してください。",
        signingIn: "Google ログインを開いています"
      },
      top: {
        heroBody:
          "毎回最初から説明し直すのをやめましょう。A2CR は AI の作業状態を WorkBaton として保存し、新しいウィンドウ・別の AI・翌日からでも、続きを再開できます。",
        ctaDashboard: "ダッシュボードを開く",
        ctaPricing: "料金を見る",
        points: {
          checkpoints: {
            title: "AI が途中を覚えている",
            body: "WorkBaton が goal・進捗・次のステップを保存。セッションが切れても、次の AI が迷わず続きから動き始めます。"
          },
          mcp: {
            title: "Claude・Codex・Cursor を横断",
            body: "MCP 対応クライアントなら同じチェックポイント層に接続できます。ツールをまたいでも作業の続きが保たれます。"
          },
          inspection: {
            title: "内容は見せずに状態を管理",
            body: "ダッシュボードはスロット・利用状況・アクセスログを表示します。保存本文はクライアント側で暗号化され、A2CR には見えません。"
          }
        },
        originTitle: "A2CR の仕組み",
        originBody:
          "A2CR はホスト型サービスです。PyPI から a2cr-mcp を入れ、AI は MCP 経由で接続し、ローカル stdio wrapper で暗号化した WorkBaton チェックポイントを保存。新しいウィンドウやツールからいつでも再開できます。",
        surfaces: {
          dashboard: "スロット・利用状況・上限・アクセスログを確認できます。保存本文は表示されません。",
          api: "WorkBaton の保存・読込・再開・削除の認証済み API パスを提供します。",
          mcp: "AI クライアント向けの MCP ツール群。WorkBaton 保存は PyPI で入れたローカル stdio wrapper を経由してクライアント側で暗号化してから送信します。"
        }
      },
      common: {
        loading: "読み込み中",
        refresh: "更新",
        copy: "コピー",
        copied: "コピー済み",
        save: "保存",
        cancel: "キャンセル",
        issue: "キー発行",
        revoke: "失効",
        never: "なし",
        none: "なし",
        auto: "自動",
        compact: "簡潔",
        detailed: "詳細",
        free: "Free",
        pro: "Pro",
        empty: "有効なスロットはありません",
        status: "状態",
        updated: "更新",
        expires: "期限",
        created: "作成",
        lastUsed: "最終利用",
        plan: "プラン",
        action: "操作",
        slot: "スロット",
        slotNumber: "スロット番号",
        client: "クライアント"
      },
      dashboard: {
        title: "WorkBaton",
        activeSlots: "有効スロット",
        totalSaves: "累計保存",
        totalLoads: "累計ロード",
        totalDeletes: "削除",
        tokensSaved: "推定節約トークン",
        tokensSavedHelp:
          "元の会話量の推定値をトークン換算し、保存トークンを引いた推定値です。保存時に original_length が無いものは未計算です。",
        copySavePrompt: "保存プロンプトをコピー",
        copyResumePrompt: "再開プロンプトをコピー",
        copyResumeCall: "呼び出しをコピー",
        deleteSlot: "\u524a\u9664",
        confirmDeleteSlot: "{{slot}}\u3092\u524a\u9664\u3057\u307e\u3059\u304b\uff1f",
        autoReload: "自動更新",
        slots: "スロット",
        accessLogs: "アクセスログ",
        size: "サイズ",
        tokens: "保存トークン",
        loads: "ロード",
        detail: "粒度",
        source: "保存元",
        noLogs: "アクセスログはありません",
        notCalculated: "未計算",
        emptyTitle: "有効な WorkBaton スロットはありません",
        emptyBody: "MCP 対応 AI クライアントからチェックポイントを保存すると、ここに表示されます。",
        workStash: "WorkStash",
        workStashStorage: "ストレージ",
        workStashEntries: "エントリ数"
      },
      settings: {
        title: "設定",
        account: "アカウント",
        apiKey: "API キー",
        apiKeyPrefix: "現在のプレフィックス",
        newApiKey: "新しい API キー",
        keyShownOnce: "表示は一度だけです。MCP クライアント設定に保存してください。再発行すると別の API key になります。",
        retention: "標準の保存期間",
        locale: "画面言語",
        responseLanguage: "応答言語",
        timezone: "タイムゾーン",
        setup: "MCP 設定",
        setupInstall: "先に python -m pip install --upgrade a2cr-mcp で wrapper をインストールまたは更新し、その後に下の設定例を使います。",
        genericResume: "汎用再開プロンプト",
        saved: "設定を保存しました",
        noApiKey: "有効な API キーはありません"
      },
      pricing: {
        title: "料金",
        freeName: "Free",
        proName: "Pro",
        freePrice: "$0",
        proPrice: "$8 / 月",
        slots: "有効スロット",
        retention: "保存期間",
        body: "チェックポイントサイズ",
        handoff: "AI引き継ぎ",
        focusedHandoff: "小さめのサイズ予算",
        richerHandoff: "厚めのサイズ予算",
        saves: "保存",
        loads: "ロード",
        logs: "アクセスログ",
        workthreads: "WorkThreads",
        workStash: "WorkStash ストレージ",
        notIncluded: "対象外",
        planned: "近日公開",
        comingSoon: "近日公開"
      },
      errors: {
        generic: "リクエストに失敗しました",
        refreshFailedCached: "更新に失敗しました。前回取得できた表示を維持しています。",
        unauthenticated: "もう一度ログインしてください"
      }
    }
  }
};

const storedLanguage = window.localStorage.getItem("a2cr.language");
const browserLanguage = navigator.language.startsWith("ja") ? "ja" : "en";

i18n.use(initReactI18next).init({
  resources,
  lng: storedLanguage || browserLanguage,
  fallbackLng: "en",
  interpolation: {
    escapeValue: false
  }
});

export function setAppLanguage(language: "en" | "ja") {
  window.localStorage.setItem("a2cr.language", language);
  return i18n.changeLanguage(language);
}

export default i18n;
