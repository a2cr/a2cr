import {
  Activity,
  Boxes,
  ChevronDown,
  ChevronRight,
  Clock3,
  Loader2,
  RefreshCw,
  RotateCcw,
  Save,
  TimerReset,
  Trash2
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ComponentType } from "react";
import { useTranslation } from "react-i18next";

import { CopyButton } from "../components/CopyButton";
import { Notice } from "../components/Notice";
import { ApiError, deleteDashboardContext, loadDashboardData } from "../lib/api";
import { buildSavePrompt } from "../lib/prompts";
import type { DashboardContext, DashboardData, DashboardWorkThread } from "../lib/types";
import { formatBytes, formatDateTime, formatNumber } from "../lib/format";
import { useAuth } from "../providers/AuthProvider";

function Stat({
  label,
  value,
  icon: Icon
}: {
  label: string;
  value: string;
  icon: ComponentType<{ className?: string }>;
}) {
  return (
    <div className="rounded-md border border-neutral-200 bg-white p-4">
      <div className="flex items-center justify-between gap-3">
        <div className="text-sm text-neutral-500">{label}</div>
        <Icon className="size-4 text-emerald-700" aria-hidden="true" />
      </div>
      <div className="mt-2 text-2xl font-semibold tracking-normal">{value}</div>
    </div>
  );
}

function SlotCard({
  item,
  timezone,
  isNewest,
  deleting,
  onDelete
}: {
  item: DashboardContext;
  timezone: string;
  isNewest: boolean;
  deleting: boolean;
  onDelete: (slotName: string) => void;
}) {
  const { t } = useTranslation();
  const encryptionLabel = "Client-encrypted";
  const deleteLabel = t("dashboard.deleteSlot");
  return (
    <article className="rounded-md border border-neutral-200 bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="rounded bg-amber-100 px-2 py-1 text-xs font-semibold text-amber-900">
              Slot {item.slot_number}
            </span>
            <span className="rounded bg-neutral-100 px-2 py-1 text-xs font-medium text-neutral-700">
              {item.detail_level}
            </span>
            <span className="rounded bg-emerald-100 px-2 py-1 text-xs font-medium text-emerald-900">
              {encryptionLabel}
            </span>
            {isNewest && (
              <span className="rounded bg-rose-100 px-2 py-1 text-xs font-semibold text-rose-700">
                new
              </span>
            )}
          </div>
          <h2 className="mt-3 truncate text-lg font-semibold">{item.slot_name}</h2>
        </div>
        <div className="flex shrink-0 gap-2">
          <CopyButton value={item.resume_context_call} label={t("dashboard.copyResumeCall")} compact />
          <CopyButton value={item.resume_prompt} label={t("dashboard.copyResumePrompt")} compact />
          <button
            type="button"
            title={deleteLabel}
            aria-label={deleteLabel}
            disabled={deleting}
            onClick={() => onDelete(item.slot_name)}
            className="inline-flex size-9 items-center justify-center rounded-md border border-rose-200 bg-white text-rose-700 hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {deleting ? (
              <Loader2 className="size-4 animate-spin" aria-hidden="true" />
            ) : (
              <Trash2 className="size-4" aria-hidden="true" />
            )}
          </button>
        </div>
      </div>

      <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
        <div>
          <dt className="text-neutral-500">{t("common.updated")}</dt>
          <dd className="mt-1 font-medium">{formatDateTime(item.updated_at, timezone)}</dd>
        </div>
        <div>
          <dt className="text-neutral-500">{t("common.expires")}</dt>
          <dd className="mt-1 font-medium">{formatDateTime(item.expires_at, timezone)}</dd>
        </div>
        <div>
          <dt className="text-neutral-500">{t("dashboard.size")}</dt>
          <dd className="mt-1 font-medium">{formatBytes(item.size_bytes)}</dd>
        </div>
        <div>
          <dt className="text-neutral-500">{t("dashboard.loads")}</dt>
          <dd className="mt-1 font-medium">{formatNumber(item.load_count)}</dd>
        </div>
        <div>
          <dt className="text-neutral-500">{t("dashboard.tokens")}</dt>
          <dd className="mt-1 font-medium">{formatNumber(item.compressed_tokens)}</dd>
        </div>
        <div>
          <dt className="text-neutral-500">{t("dashboard.source")}</dt>
          <dd className="mt-1 font-medium">{item.model_source || t("common.none")}</dd>
        </div>
      </dl>
    </article>
  );
}

function WorkThreadCard({ item, timezone }: { item: DashboardWorkThread; timezone: string }) {
  const taskStatus = Object.entries(item.task_status_counts)
    .map(([status, count]) => `${status}: ${count}`)
    .join(", ");

  return (
    <article className="rounded-md border border-neutral-200 bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded bg-emerald-100 px-2 py-1 text-xs font-semibold text-emerald-900">
              {item.status}
            </span>
            {item.loop_status !== "ok" && (
              <span className="rounded bg-rose-100 px-2 py-1 text-xs font-semibold text-rose-900">
                {item.loop_status}
              </span>
            )}
          </div>
          <h2 className="mt-3 truncate text-lg font-semibold">{item.title}</h2>
          {item.purpose && <div className="mt-1 truncate text-sm text-neutral-500">{item.purpose}</div>}
        </div>
      </div>

      <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
        <div>
          <dt className="text-neutral-500">Messages</dt>
          <dd className="mt-1 font-medium">{formatNumber(item.message_count)}</dd>
        </div>
        <div>
          <dt className="text-neutral-500">Tasks</dt>
          <dd className="mt-1 font-medium">{formatNumber(item.task_count)}</dd>
        </div>
        <div>
          <dt className="text-neutral-500">Agents</dt>
          <dd className="mt-1 truncate font-medium">{item.agent_names.join(", ") || "-"}</dd>
        </div>
        <div>
          <dt className="text-neutral-500">Task status</dt>
          <dd className="mt-1 truncate font-medium">{taskStatus || "-"}</dd>
        </div>
        <div>
          <dt className="text-neutral-500">Last activity</dt>
          <dd className="mt-1 font-medium">{formatDateTime(item.last_activity_at, timezone)}</dd>
        </div>
        <div>
          <dt className="text-neutral-500">Result Slot</dt>
          <dd className="mt-1 truncate font-medium">{item.final_slot_name || "-"}</dd>
        </div>
      </dl>
    </article>
  );
}

function newestFirst(left: string, right: string) {
  return Date.parse(right) - Date.parse(left);
}

export function DashboardPage() {
  const { t } = useTranslation();
  const { session } = useAuth();
  const refreshInFlight = useRef(false);
  const dataRef = useRef<DashboardData | null>(null);
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [autoReload, setAutoReload] = useState(false);
  const [slotsOpen, setSlotsOpen] = useState(true);
  const [accessLogsOpen, setAccessLogsOpen] = useState(true);
  const [deletingSlotName, setDeletingSlotName] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!session?.access_token) {
      setLoading(false);
      return;
    }
    if (refreshInFlight.current) {
      return;
    }
    refreshInFlight.current = true;
    setRefreshing(true);
    setError(null);
    try {
      const nextData = await loadDashboardData(session.access_token);
      dataRef.current = nextData;
      setData(nextData);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError(t("errors.unauthenticated"));
      } else if (dataRef.current) {
        setError(t("errors.refreshFailedCached"));
      } else {
        setError(err instanceof Error ? err.message : t("errors.generic"));
      }
    } finally {
      refreshInFlight.current = false;
      setRefreshing(false);
      setLoading(false);
    }
  }, [session?.access_token, t]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (!autoReload) {
      return;
    }
    void refresh();
    const id = window.setInterval(() => void refresh(), 30000);
    return () => window.clearInterval(id);
  }, [autoReload, refresh]);

  const deleteSlot = useCallback(
    async (slotName: string) => {
      if (!session?.access_token) {
        setError(t("errors.unauthenticated"));
        return;
      }
      if (!window.confirm(t("dashboard.confirmDeleteSlot", { slot: slotName }))) {
        return;
      }
      setDeletingSlotName(slotName);
      setError(null);
      try {
        await deleteDashboardContext(session.access_token, slotName);
        await refresh();
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          setError(t("errors.unauthenticated"));
        } else {
          setError(err instanceof Error ? err.message : t("errors.generic"));
        }
      } finally {
        setDeletingSlotName(null);
      }
    },
    [refresh, session?.access_token, t]
  );

  const timezone = data?.profile.timezone || "UTC";
  const savePrompt = useMemo(() => buildSavePrompt(data?.contexts || []), [data?.contexts]);
  const contextsByNewest = useMemo(
    () => [...(data?.contexts || [])].sort((a, b) => newestFirst(a.updated_at, b.updated_at)),
    [data?.contexts]
  );
  const accessLogsByNewest = useMemo(
    () => [...(data?.accessLogs || [])].sort((a, b) => newestFirst(a.created_at, b.created_at)),
    [data?.accessLogs]
  );
  const tokensSavedValue =
    data && data.stats.total_tokens_saved > 0
      ? formatNumber(data.stats.total_tokens_saved)
      : data && data.stats.total_saves > 0
        ? t("dashboard.notCalculated")
        : "0";

  if (loading) {
    return (
      <div className="flex min-h-80 items-center justify-center rounded-md border border-neutral-200 bg-white">
        <Loader2 className="mr-3 size-5 animate-spin text-emerald-700" aria-hidden="true" />
        {t("common.loading")}
      </div>
    );
  }

  return (
    <div className="grid gap-5">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">{t("dashboard.title")}</h1>
          <div className="mt-1 text-sm text-neutral-500">
            {t("common.plan")}: {data?.profile.plan || t("common.free")}
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => setAutoReload((value) => !value)}
            className={`inline-flex items-center gap-2 rounded-md border px-3 py-2 text-sm font-medium ${
              autoReload
                ? "border-emerald-700 bg-emerald-700 text-white"
                : "border-neutral-300 bg-white text-neutral-700 hover:bg-neutral-100"
            }`}
          >
            <TimerReset className="size-4" aria-hidden="true" />
            {t("dashboard.autoReload")}
          </button>
          <CopyButton value={savePrompt} label={t("dashboard.copySavePrompt")} />
          <button
            type="button"
            onClick={() => void refresh()}
            disabled={refreshing}
            aria-busy={refreshing}
            className="inline-flex items-center gap-2 rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-100 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <RefreshCw className={`size-4 ${refreshing ? "animate-spin" : ""}`} aria-hidden="true" />
            {t("common.refresh")}
          </button>
        </div>
      </div>

      {error && <Notice tone="danger">{error}</Notice>}

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <Stat label={t("dashboard.activeSlots")} value={formatNumber(data?.stats.active_slots || 0)} icon={Boxes} />
        <Stat label={t("dashboard.totalSaves")} value={formatNumber(data?.stats.total_saves || 0)} icon={Save} />
        <Stat label={t("dashboard.totalLoads")} value={formatNumber(data?.stats.total_loads || 0)} icon={RotateCcw} />
        <Stat label={t("dashboard.totalDeletes")} value={formatNumber(data?.stats.total_deletes || 0)} icon={Activity} />
        <Stat label={t("dashboard.tokensSaved")} value={tokensSavedValue} icon={Clock3} />
      </section>

      <section className="grid gap-3">
        <h2 className="text-base font-semibold">
          <button
            type="button"
            onClick={() => setSlotsOpen((value) => !value)}
            className="flex w-full items-center justify-between gap-3 rounded-md px-1 py-1 text-left hover:bg-neutral-100"
            aria-expanded={slotsOpen}
          >
            <span>{t("dashboard.slots")}</span>
            {slotsOpen ? (
              <ChevronDown className="size-4 text-neutral-500" aria-hidden="true" />
            ) : (
              <ChevronRight className="size-4 text-neutral-500" aria-hidden="true" />
            )}
          </button>
        </h2>
        {slotsOpen &&
          (contextsByNewest.length > 0 ? (
            <div className="grid gap-3 xl:grid-cols-2">
              {contextsByNewest.map((item, index) => (
                <SlotCard
                  key={`${item.slot_number}-${item.slot_name}`}
                  item={item}
                  timezone={timezone}
                  isNewest={index === 0}
                  deleting={deletingSlotName === item.slot_name}
                  onDelete={deleteSlot}
                />
              ))}
            </div>
          ) : (
            <div className="rounded-md border border-dashed border-neutral-300 bg-white p-6">
              <div className="text-lg font-semibold">{t("dashboard.emptyTitle")}</div>
              <div className="mt-1 text-sm text-neutral-500">{t("dashboard.emptyBody")}</div>
            </div>
          ))}
      </section>

      {data && data.profile.plan === "pro" && (
        <section className="grid gap-3">
          <h2 className="text-base font-semibold">WorkThreads</h2>
          {data.workthreads.length > 0 ? (
            <div className="grid gap-3 xl:grid-cols-2">
              {data.workthreads.map((item) => (
                <WorkThreadCard key={item.thread_id} item={item} timezone={timezone} />
              ))}
            </div>
          ) : (
            <div className="rounded-md border border-dashed border-neutral-300 bg-white p-6">
              <div className="text-lg font-semibold">No active WorkThreads</div>
              <div className="mt-1 text-sm text-neutral-500">Durable handoff threads will appear here.</div>
            </div>
          )}
        </section>
      )}

      <section className="grid gap-3">
        <h2 className="text-base font-semibold">
          <button
            type="button"
            onClick={() => setAccessLogsOpen((value) => !value)}
            className="flex w-full items-center justify-between gap-3 rounded-md px-1 py-1 text-left hover:bg-neutral-100"
            aria-expanded={accessLogsOpen}
          >
            <span>{t("dashboard.accessLogs")}</span>
            {accessLogsOpen ? (
              <ChevronDown className="size-4 text-neutral-500" aria-hidden="true" />
            ) : (
              <ChevronRight className="size-4 text-neutral-500" aria-hidden="true" />
            )}
          </button>
        </h2>
        {accessLogsOpen && (
          <div className="overflow-hidden rounded-md border border-neutral-200 bg-white">
            {accessLogsByNewest.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="min-w-full text-left text-sm">
                  <thead className="border-b border-neutral-200 bg-neutral-50 text-xs uppercase text-neutral-500">
                    <tr>
                      <th className="px-3 py-2 font-semibold">{t("common.created")}</th>
                      <th className="px-3 py-2 font-semibold">{t("common.action")}</th>
                      <th className="px-3 py-2 font-semibold">{t("common.slot")}</th>
                      <th className="px-3 py-2 font-semibold">{t("common.client")}</th>
                      <th className="px-3 py-2 font-semibold">{t("common.status")}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-neutral-100">
                    {accessLogsByNewest.map((item) => (
                      <tr key={`${item.created_at}-${item.action}-${item.request_id || ""}`}>
                        <td className="whitespace-nowrap px-3 py-2">{formatDateTime(item.created_at, timezone)}</td>
                        <td className="whitespace-nowrap px-3 py-2 font-medium">{item.action}</td>
                        <td className="whitespace-nowrap px-3 py-2">{item.slot_name || "-"}</td>
                        <td className="whitespace-nowrap px-3 py-2">{item.client_type}</td>
                        <td className="whitespace-nowrap px-3 py-2">
                          <span className="rounded bg-neutral-100 px-2 py-1 text-xs font-medium text-neutral-700">
                            {item.result}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="p-6 text-sm text-neutral-500">{t("dashboard.noLogs")}</div>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
