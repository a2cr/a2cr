import type { A2crConfig } from "./config.js";
import { A2CR_MCP_COMPAT_VERSION } from "./version.js";

const HTTP_TIMEOUT_MS = 10_000;
const SAFE_HTTP_ERROR_VALUE = /^[A-Za-z0-9_.:-]{1,128}$/;

export type FetchLike = (input: string, init?: RequestInit) => Promise<Response>;

export class A2crHttpError extends Error {
  constructor(
    readonly statusCode: number,
    readonly safeDetails: string[],
  ) {
    const suffix = safeDetails.length > 0 ? ` (${safeDetails.join(", ")})` : "";
    super(`A2CR HTTP request failed with status ${statusCode}${suffix}`);
    this.name = "A2crHttpError";
  }
}

export class A2crApiClient {
  constructor(
    private readonly config: A2crConfig,
    private readonly fetchImpl: FetchLike = fetch,
  ) {}

  getAccountLimits(): Promise<unknown> {
    return this.requestJson("GET", "/api/v1/account/limits");
  }

  listContexts(): Promise<unknown> {
    return this.requestJson("GET", "/api/v1/contexts");
  }

  saveContext(body: Record<string, unknown>, clientType?: string | null): Promise<Record<string, unknown>> {
    return this.requestJson("POST", "/api/v1/context", {
      body,
      clientType,
    }) as Promise<Record<string, unknown>>;
  }

  loadContextByName(slotName: string): Promise<Record<string, unknown>> {
    return this.requestJson("GET", `/api/v1/context/${pathSegment(slotName)}`) as Promise<Record<string, unknown>>;
  }

  loadContextByNumber(slotNumber: number): Promise<Record<string, unknown>> {
    return this.requestJson("GET", `/api/v1/context/slot/${slotNumber}`) as Promise<Record<string, unknown>>;
  }

  private async requestJson(
    method: string,
    path: string,
    options: { body?: unknown; clientType?: string | null } = {},
  ): Promise<unknown> {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), HTTP_TIMEOUT_MS);
    try {
      const response = await this.fetchImpl(`${this.config.baseUrl}${path}`, {
        method,
        headers: this.headers(options.clientType),
        body: options.body === undefined ? undefined : JSON.stringify(options.body),
        signal: controller.signal,
      });
      if (!response.ok) {
        throw new A2crHttpError(response.status, await safeHttpErrorDetails(response));
      }
      return parseJsonResponse(response);
    } finally {
      clearTimeout(timeout);
    }
  }

  private headers(clientType?: string | null): HeadersInit {
    const headers: Record<string, string> = {
      Authorization: `Bearer ${this.config.apiKey}`,
      "Content-Type": "application/json",
      "X-A2CR-Client-Type": (clientType ?? this.config.clientType).trim() || this.config.clientType,
      "X-A2CR-MCP-Version": A2CR_MCP_COMPAT_VERSION,
    };
    return headers;
  }
}

export function pathSegment(value: string): string {
  return encodeURIComponent(value);
}

async function parseJsonResponse(response: Response): Promise<unknown> {
  if (response.status === 204) {
    return {};
  }
  const text = await response.text();
  if (!text.trim()) {
    return {};
  }
  return JSON.parse(text) as unknown;
}

async function safeHttpErrorDetails(response: Response): Promise<string[]> {
  const data = await safeJsonObject(response);
  const errorCode = data.code ?? response.headers.get("x-a2cr-error-code");
  const fields: Array<[string, unknown]> = [
    ["code", errorCode],
    ["action", data.action],
    ["request_id", data.request_id ?? response.headers.get("x-request-id")],
    ["retry_after", data.retry_after ?? response.headers.get("retry-after")],
    ["hint", httpErrorHint(response.status, errorCode)],
  ];
  return fields.flatMap(([name, value]) => {
    const safeValue = safeHttpErrorValue(value);
    return safeValue === null ? [] : [`${name}=${safeValue}`];
  });
}

async function safeJsonObject(response: Response): Promise<Record<string, unknown>> {
  try {
    const parsed: unknown = await response.clone().json();
    return parsed !== null && typeof parsed === "object" && !Array.isArray(parsed)
      ? (parsed as Record<string, unknown>)
      : {};
  } catch {
    return {};
  }
}

function safeHttpErrorValue(value: unknown): string | null {
  if (value === null || value === undefined) {
    return null;
  }
  const text = String(value);
  return SAFE_HTTP_ERROR_VALUE.test(text) ? text : null;
}

function httpErrorHint(statusCode: number, code: unknown): string | null {
  const normalizedCode = String(code ?? "").trim().toLowerCase();
  if (statusCode === 401 || statusCode === 403) {
    return "check_api_key";
  }
  if (statusCode === 404) {
    return "not_found";
  }
  if (statusCode === 413 || normalizedCode.includes("body")) {
    return "reduce_body_size";
  }
  if (statusCode === 429) {
    return "retry_later";
  }
  if (statusCode >= 500) {
    return "retry_later";
  }
  return null;
}
