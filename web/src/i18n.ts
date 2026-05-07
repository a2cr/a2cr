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
          "A2CR keeps AI work moving across windows, models, and MCP clients with compact, inspectable WorkBaton checkpoints.",
        ctaDashboard: "Open dashboard",
        ctaPricing: "View pricing",
        points: {
          checkpoints: {
            title: "WorkBaton checkpoints",
            body: "Save the state of an AI task before a window fills up, then resume it from another client."
          },
          mcp: {
            title: "MCP-first handoff",
            body: "Codex, Claude, Cursor, and other MCP-capable clients can call the same shared context layer."
          },
          inspection: {
            title: "Built for inspection",
            body: "The dashboard shows slots, usage, limits, and access logs without exposing saved bodies."
          }
        },
        originTitle: "One origin for the MVP",
        originBody:
          "The hosted app serves the dashboard, authenticated APIs, and Streamable HTTP MCP endpoint from the same A2CR origin.",
        surfaces: {
          dashboard: "Slots, profile, keys, limits, and access log visibility.",
          api: "Authenticated WorkBaton ciphertext save, load, resume, and delete paths.",
          mcp: "Shared metadata and account tools for AI clients; WorkBaton saving uses the local stdio wrapper."
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
        client: "Client"
      },
      dashboard: {
        title: "WorkBaton",
        activeSlots: "Active slots",
        totalSaves: "Total saves",
        totalLoads: "Total loads",
        totalDeletes: "Deletes",
        tokensSaved: "Estimated tokens saved",
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
        emptyBody: "Create a checkpoint from an MCP-capable AI client and it will appear here."
      },
      settings: {
        title: "Settings",
        account: "Account",
        apiKey: "API key",
        apiKeyPrefix: "Current prefix",
        newApiKey: "New API key",
        keyShownOnce: "Shown once. Store it in your MCP client configuration.",
        retention: "Default retention",
        detailLevel: "Context detail",
        locale: "Interface language",
        responseLanguage: "Response language",
        timezone: "Timezone",
        setup: "MCP setup",
        genericResume: "Generic resume prompt",
        saved: "Settings saved",
        noApiKey: "No active API key"
      },
      pricing: {
        title: "Pricing",
        freeName: "Free",
        proName: "Pro",
        freePrice: "$0",
        proPrice: "$5 / month",
        slots: "Active slots",
        retention: "Retention",
        body: "Checkpoint size",
        detail: "Detail levels",
        saves: "Saves",
        loads: "Loads",
        logs: "Access logs",
        workthreads: "WorkThreads",
        notIncluded: "Not included",
        planned: "Post-MVP"
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
          "A2CR は、AI 作業の文脈を別の窓・モデル・MCP クライアントへ引き継ぐための、コンパクトで確認しやすい WorkBaton チェックポイントを提供します。",
        ctaDashboard: "ダッシュボードを開く",
        ctaPricing: "料金を見る",
        points: {
          checkpoints: {
            title: "WorkBaton チェックポイント",
            body: "AI 作業の状態を、コンテキストが詰まる前に保存し、別のクライアントから再開できます。"
          },
          mcp: {
            title: "MCP 前提の引き継ぎ",
            body: "Codex、Claude、Cursor などの MCP 対応クライアントが、同じ共有コンテキスト層を呼び出せます。"
          },
          inspection: {
            title: "確認しやすい設計",
            body: "ダッシュボードでは、保存本文を表示せずに、スロット、利用状況、上限、アクセスログを確認できます。"
          }
        },
        originTitle: "MVP は 1 つの origin で",
        originBody:
          "ホスト版アプリは、ダッシュボード、認証済み API、Streamable HTTP MCP エンドポイントを同じ A2CR origin から提供します。",
        surfaces: {
          dashboard: "スロット、プロフィール、キー、上限、アクセスログを確認できます。",
          api: "認証済みの WorkBaton 暗号文保存、読込、再開、削除 API を提供します。",
          mcp: "AI クライアント向けのメタデータ/アカウント系ツールです。WorkBaton保存はローカルstdio wrapperを使います。"
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
        client: "クライアント"
      },
      dashboard: {
        title: "WorkBaton",
        activeSlots: "有効スロット",
        totalSaves: "累計保存",
        totalLoads: "累計ロード",
        totalDeletes: "削除",
        tokensSaved: "推定節約トークン",
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
        emptyBody: "MCP 対応 AI クライアントからチェックポイントを保存すると、ここに表示されます。"
      },
      settings: {
        title: "設定",
        account: "アカウント",
        apiKey: "API キー",
        apiKeyPrefix: "現在のプレフィックス",
        newApiKey: "新しい API キー",
        keyShownOnce: "表示は一度だけです。MCP クライアント設定に保存してください。",
        retention: "標準の保存期間",
        detailLevel: "保存粒度",
        locale: "画面言語",
        responseLanguage: "応答言語",
        timezone: "タイムゾーン",
        setup: "MCP 設定",
        genericResume: "汎用再開プロンプト",
        saved: "設定を保存しました",
        noApiKey: "有効な API キーはありません"
      },
      pricing: {
        title: "料金",
        freeName: "Free",
        proName: "Pro",
        freePrice: "$0",
        proPrice: "$5 / 月",
        slots: "有効スロット",
        retention: "保存期間",
        body: "チェックポイントサイズ",
        detail: "保存粒度",
        saves: "保存",
        loads: "ロード",
        logs: "アクセスログ",
        workthreads: "WorkThreads",
        notIncluded: "対象外",
        planned: "MVP 後"
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
