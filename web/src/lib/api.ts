import type {
  CreatedApiKey,
  DashboardAccessLog,
  DashboardContext,
  DashboardData,
  DashboardProfile,
  DashboardStats,
  DashboardWorkThread,
  ProfilePatch
} from "./types";

const apiBase = import.meta.env.VITE_A2CR_API_BASE?.replace(/\/$/, "") || "";

type ApiErrorPayload = {
  code?: string;
  message?: string;
  detail?: string;
};

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

const DASHBOARD_GET_RETRY_DELAYS_MS = [250, 750];

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function isRetryableDashboardError(error: unknown): boolean {
  if (error instanceof ApiError) {
    return error.status >= 500;
  }
  return error instanceof TypeError;
}

async function parseError(response: Response): Promise<ApiError> {
  let payload: ApiErrorPayload = {};
  try {
    payload = (await response.json()) as ApiErrorPayload;
  } catch {
    payload = {};
  }
  const code = payload.code || `http_${response.status}`;
  const message = payload.message || payload.detail || "Request failed";
  return new ApiError(response.status, code, message);
}

async function dashboardFetchOnce<T>(
  path: string,
  token: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, {
    ...options,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(options.headers || {})
    }
  });
  if (!response.ok) {
    throw await parseError(response);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export async function dashboardFetch<T>(
  path: string,
  token: string,
  options: RequestInit = {}
): Promise<T> {
  const method = (options.method || "GET").toUpperCase();
  const retryDelays = method === "GET" ? DASHBOARD_GET_RETRY_DELAYS_MS : [];

  for (let attempt = 0; ; attempt += 1) {
    try {
      return await dashboardFetchOnce<T>(path, token, options);
    } catch (error) {
      const retryDelay = retryDelays[attempt];
      if (retryDelay === undefined || !isRetryableDashboardError(error)) {
        throw error;
      }
      await sleep(retryDelay);
    }
  }
}

export async function loadDashboardData(token: string): Promise<DashboardData> {
  const profile = await dashboardFetch<DashboardProfile>("/api/dashboard/profile", token);
  const contexts = await dashboardFetch<DashboardContext[]>("/api/dashboard/contexts", token);
  const stats = await dashboardFetch<DashboardStats>("/api/dashboard/stats", token);
  const accessLogs = await dashboardFetch<DashboardAccessLog[]>("/api/dashboard/access-logs?limit=25", token).catch(
    () => []
  );

  const workthreads =
    profile.plan === "pro"
      ? await dashboardFetch<DashboardWorkThread[]>("/api/dashboard/workthreads", token).catch(() => [])
      : [];

  const apiKey = null;
  return { profile, contexts, stats, accessLogs, apiKey, workthreads };
}

export function updateProfile(token: string, patch: ProfilePatch) {
  return dashboardFetch<DashboardProfile>("/api/dashboard/profile", token, {
    method: "PATCH",
    body: JSON.stringify(patch)
  });
}

export function createApiKey(token: string) {
  return dashboardFetch<CreatedApiKey>("/api/dashboard/api-key", token, {
    method: "POST"
  });
}

export function revokeApiKey(token: string) {
  return dashboardFetch<{ message: string }>("/api/dashboard/api-key", token, {
    method: "DELETE"
  });
}

export function deleteDashboardContext(token: string, slotName: string) {
  return dashboardFetch<{ message: string }>(`/api/dashboard/contexts/${encodeURIComponent(slotName)}`, token, {
    method: "DELETE"
  });
}
