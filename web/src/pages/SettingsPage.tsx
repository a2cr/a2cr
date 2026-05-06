import { KeyRound, Loader2, RotateCcw, Save, ShieldCheck } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { CopyButton } from "../components/CopyButton";
import { Notice } from "../components/Notice";
import { createApiKey, dashboardFetch, revokeApiKey, updateProfile } from "../lib/api";
import { buildGenericResumePrompt } from "../lib/prompts";
import type { DashboardApiKey, DashboardProfile, DetailLevel, ProfilePatch } from "../lib/types";
import {
  FREE_RETENTION_SECONDS,
  PRO_RETENTION_SECONDS,
  formatDateTime,
  retentionLabel,
  serviceUrl
} from "../lib/format";
import { setAppLanguage } from "../i18n";
import { useAuth } from "../providers/AuthProvider";

const localeOptions = ["auto", "en", "ja"];
const responseLanguageOptions = ["auto", "en", "ja"];
const timezoneOptions = ["UTC", "Asia/Tokyo", "America/Los_Angeles", "America/New_York", "Europe/London", "Europe/Paris"];
const setupTabs = ["codex", "claude", "cursor"] as const;

function mcpConfigSnippet(client: string): string {
  const serverUrl = serviceUrl();
  const baseUrl = (() => {
    try {
      return new URL(serverUrl, window.location.origin).origin;
    } catch {
      return serverUrl.replace(/\/mcp\/?$/, "");
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
      `A2CR_SERVICE_URL = "${serverUrl}"`,
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
            A2CR_SERVICE_URL: serverUrl,
            A2CR_CLIENT_KEY_FILE: "<optional-path-to-workbaton.key>"
          }
        }
      }
    },
    null,
    2
  );
}

export function SettingsPage() {
  const { t, i18n } = useTranslation();
  const { session } = useAuth();
  const [profile, setProfile] = useState<DashboardProfile | null>(null);
  const [apiKey, setApiKey] = useState<DashboardApiKey | null>(null);
  const [newApiKey, setNewApiKey] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [setupTab, setSetupTab] = useState<(typeof setupTabs)[number]>("codex");

  const token = session?.access_token;

  const load = useCallback(async () => {
    if (!token) {
      return;
    }
    setError(null);
    try {
      const [nextProfile, nextApiKey] = await Promise.all([
        dashboardFetch<DashboardProfile>("/api/dashboard/profile", token),
        dashboardFetch<DashboardApiKey | null>("/api/dashboard/api-key", token)
      ]);
      setProfile(nextProfile);
      setApiKey(nextApiKey);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("errors.generic"));
    } finally {
      setLoading(false);
    }
  }, [token, t]);

  useEffect(() => {
    void load();
  }, [load]);

  const retentionOptions = useMemo(() => {
    if (profile?.plan === "pro") {
      return PRO_RETENTION_SECONDS;
    }
    return FREE_RETENTION_SECONDS;
  }, [profile?.plan]);

  const patchProfile = async (patch: ProfilePatch) => {
    if (!token || !profile) {
      return;
    }
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const updated = await updateProfile(token, patch);
      setProfile(updated);
      setNotice(t("settings.saved"));
    } catch (err) {
      setError(err instanceof Error ? err.message : t("errors.generic"));
    } finally {
      setBusy(false);
    }
  };

  const issueKey = async () => {
    if (!token) {
      return;
    }
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const created = await createApiKey(token);
      setNewApiKey(created.api_key);
      setApiKey({
        key_prefix: created.key_prefix,
        created_at: created.created_at,
        last_used_at: null,
        revoked_at: null
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : t("errors.generic"));
    } finally {
      setBusy(false);
    }
  };

  const revokeKey = async () => {
    if (!token) {
      return;
    }
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await revokeApiKey(token);
      setApiKey(null);
      setNewApiKey(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("errors.generic"));
    } finally {
      setBusy(false);
    }
  };

  if (loading || !profile) {
    return (
      <div className="flex min-h-80 items-center justify-center rounded-md border border-neutral-200 bg-white">
        <Loader2 className="mr-3 size-5 animate-spin text-emerald-700" aria-hidden="true" />
        {t("common.loading")}
      </div>
    );
  }

  const timezone = profile.timezone || "UTC";
  const snippet = mcpConfigSnippet(setupTab);

  return (
    <div className="grid gap-5">
      <div>
        <h1 className="text-2xl font-semibold tracking-normal">{t("settings.title")}</h1>
        <div className="mt-1 text-sm text-neutral-500">
          {t("common.plan")}: {profile.plan}
        </div>
      </div>

      {error && <Notice tone="danger">{error}</Notice>}
      {notice && <Notice tone="success">{notice}</Notice>}

      <section className="grid gap-3 lg:grid-cols-[1fr_1fr]">
        <div className="rounded-md border border-neutral-200 bg-white p-4">
          <div className="mb-4 flex items-center gap-2">
            <ShieldCheck className="size-5 text-emerald-700" aria-hidden="true" />
            <h2 className="text-base font-semibold">{t("settings.account")}</h2>
          </div>

          <div className="grid gap-4">
            <label className="grid gap-1 text-sm">
              <span className="font-medium">{t("settings.retention")}</span>
              <select
                value={profile.default_retention_seconds}
                disabled={busy}
                onChange={(event) =>
                  void patchProfile({ default_retention_seconds: Number(event.target.value) })
                }
                className="h-10 rounded-md border border-neutral-300 bg-white px-3"
              >
                {retentionOptions.map((seconds) => (
                  <option key={seconds} value={seconds}>
                    {retentionLabel(seconds)}
                  </option>
                ))}
              </select>
            </label>

            <label className="grid gap-1 text-sm">
              <span className="font-medium">{t("settings.detailLevel")}</span>
              <select
                value={profile.context_detail_level}
                disabled={busy || profile.plan !== "pro"}
                onChange={(event) =>
                  void patchProfile({ context_detail_level: event.target.value as DetailLevel })
                }
                className="h-10 rounded-md border border-neutral-300 bg-white px-3 disabled:bg-neutral-100"
              >
                <option value="compact">{t("common.compact")}</option>
                {profile.plan === "pro" && <option value="detailed">{t("common.detailed")}</option>}
              </select>
            </label>

            <label className="grid gap-1 text-sm">
              <span className="font-medium">{t("settings.locale")}</span>
              <select
                value={profile.preferred_locale}
                disabled={busy}
                onChange={(event) => {
                  const value = event.target.value;
                  if (value === "en" || value === "ja") {
                    void setAppLanguage(value);
                  }
                  void patchProfile({ preferred_locale: value });
                }}
                className="h-10 rounded-md border border-neutral-300 bg-white px-3"
              >
                {localeOptions.map((value) => (
                  <option key={value} value={value}>
                    {value === "auto" ? t("common.auto") : value.toUpperCase()}
                  </option>
                ))}
              </select>
            </label>

            <label className="grid gap-1 text-sm">
              <span className="font-medium">{t("settings.responseLanguage")}</span>
              <select
                value={profile.response_language}
                disabled={busy}
                onChange={(event) => void patchProfile({ response_language: event.target.value })}
                className="h-10 rounded-md border border-neutral-300 bg-white px-3"
              >
                {responseLanguageOptions.map((value) => (
                  <option key={value} value={value}>
                    {value === "auto" ? t("common.auto") : value.toUpperCase()}
                  </option>
                ))}
              </select>
            </label>

            <label className="grid gap-1 text-sm">
              <span className="font-medium">{t("settings.timezone")}</span>
              <select
                value={profile.timezone}
                disabled={busy}
                onChange={(event) => void patchProfile({ timezone: event.target.value })}
                className="h-10 rounded-md border border-neutral-300 bg-white px-3"
              >
                {timezoneOptions.map((value) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>

        <div className="rounded-md border border-neutral-200 bg-white p-4">
          <div className="mb-4 flex items-center gap-2">
            <KeyRound className="size-5 text-emerald-700" aria-hidden="true" />
            <h2 className="text-base font-semibold">{t("settings.apiKey")}</h2>
          </div>

          <dl className="grid gap-3 text-sm">
            <div>
              <dt className="text-neutral-500">{t("settings.apiKeyPrefix")}</dt>
              <dd className="mt-1 font-mono text-sm font-medium">
                {apiKey?.key_prefix || t("settings.noApiKey")}
              </dd>
            </div>
            <div>
              <dt className="text-neutral-500">{t("common.created")}</dt>
              <dd className="mt-1 font-medium">{formatDateTime(apiKey?.created_at, timezone)}</dd>
            </div>
            <div>
              <dt className="text-neutral-500">{t("common.lastUsed")}</dt>
              <dd className="mt-1 font-medium">{formatDateTime(apiKey?.last_used_at, timezone)}</dd>
            </div>
          </dl>

          {newApiKey && (
            <div className="mt-4 rounded-md border border-amber-300 bg-amber-50 p-3">
              <div className="mb-2 text-sm font-semibold text-amber-950">{t("settings.newApiKey")}</div>
              <div className="flex min-w-0 items-center gap-2">
                <code className="min-w-0 flex-1 overflow-x-auto rounded bg-white px-2 py-2 text-xs">
                  {newApiKey}
                </code>
                <CopyButton value={newApiKey} compact />
              </div>
              <p className="mt-2 text-xs text-amber-900">{t("settings.keyShownOnce")}</p>
            </div>
          )}

          <div className="mt-4 flex flex-wrap gap-2">
            <button
              type="button"
              disabled={busy}
              onClick={() => void issueKey()}
              className="inline-flex items-center gap-2 rounded-md bg-neutral-900 px-3 py-2 text-sm font-semibold text-white hover:bg-neutral-700 disabled:bg-neutral-300"
            >
              <Save className="size-4" aria-hidden="true" />
              {t("common.issue")}
            </button>
            <button
              type="button"
              disabled={busy || !apiKey}
              onClick={() => void revokeKey()}
              className="inline-flex items-center gap-2 rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-100 disabled:cursor-not-allowed disabled:bg-neutral-100"
            >
              <RotateCcw className="size-4" aria-hidden="true" />
              {t("common.revoke")}
            </button>
          </div>
        </div>
      </section>

      <section className="grid gap-3 rounded-md border border-neutral-200 bg-white p-4">
        <h2 className="text-base font-semibold">{t("settings.setup")}</h2>
        <div className="flex flex-wrap gap-2">
          {setupTabs.map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setSetupTab(tab)}
              className={`rounded-md px-3 py-2 text-sm font-medium ${
                setupTab === tab ? "bg-emerald-700 text-white" : "bg-neutral-100 text-neutral-700 hover:bg-neutral-200"
              }`}
            >
              {tab[0].toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>
        <div className="grid gap-2">
          <pre className="max-h-80 overflow-auto rounded-md bg-neutral-950 p-3 text-xs text-neutral-50">
            {snippet}
          </pre>
          <div>
            <CopyButton value={snippet} />
          </div>
        </div>
      </section>

      <section className="grid gap-3 rounded-md border border-neutral-200 bg-white p-4">
        <h2 className="text-base font-semibold">{t("settings.genericResume")}</h2>
        <pre className="max-h-80 overflow-auto whitespace-pre-wrap rounded-md bg-neutral-50 p-3 text-sm">
          {buildGenericResumePrompt()}
        </pre>
        <div>
          <CopyButton value={buildGenericResumePrompt()} />
        </div>
        <div className="sr-only">Current UI language: {i18n.language}</div>
      </section>
    </div>
  );
}
