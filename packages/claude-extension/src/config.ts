import { URL } from "node:url";
import { join } from "node:path";
import { homedir } from "node:os";

export interface A2crConfig {
  apiKey: string;
  baseUrl: string;
  clientType: string;
  localStorePath: string;
}

export class A2crConfigurationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "A2crConfigurationError";
  }
}

export function loadConfig(env: NodeJS.ProcessEnv = process.env): A2crConfig {
  const baseUrl = normalizeBaseUrl(env.A2CR_BASE_URL ?? "local://a2cr");
  if (isLocalBaseUrl(baseUrl) && env.A2CR_ALLOW_LOCAL_BASE_URL !== "1") {
    throw new A2crConfigurationError(
      "A2CR refuses localhost A2CR_BASE_URL by default. Set A2CR_ALLOW_LOCAL_BASE_URL=1 only for explicit local tests.",
    );
  }

  return {
    apiKey: env.A2CR_API_KEY ?? "",
    baseUrl,
    clientType: (env.A2CR_CLIENT_TYPE ?? "mcp").trim() || "mcp",
    localStorePath: resolveLocalStorePath(env),
  };
}

export function normalizeBaseUrl(value: string): string {
  let normalized = value.trim().replace(/\/+$/, "");
  if (normalized.endsWith("/mcp")) {
    normalized = normalized.slice(0, -4).replace(/\/+$/, "");
  }
  return normalized;
}

function isLocalBaseUrl(value: string): boolean {
  if (value.startsWith("local://")) {
    return false;
  }
  const host = new URL(value).hostname;
  return host === "localhost" || host === "127.0.0.1" || host === "::1";
}

function resolveLocalStorePath(env: NodeJS.ProcessEnv): string {
  if (env.A2CR_LOCAL_STORE_FILE) {
    return expandUserPath(env.A2CR_LOCAL_STORE_FILE);
  }
  if (env.A2CR_LOCAL_DB) {
    return `${expandUserPath(env.A2CR_LOCAL_DB)}.claude-extension.json`;
  }
  if (process.platform === "win32") {
    const root = env.LOCALAPPDATA ?? join(homedir(), "AppData", "Local");
    return join(root, "A2CR", "claude-extension-store.json");
  }
  if (process.platform === "darwin") {
    return join(homedir(), "Library", "Application Support", "A2CR", "claude-extension-store.json");
  }
  return join(env.XDG_DATA_HOME ?? join(homedir(), ".local", "share"), "a2cr", "claude-extension-store.json");
}

function expandUserPath(value: string): string {
  if (value === "~") {
    return homedir();
  }
  if (value.startsWith("~/") || value.startsWith("~\\")) {
    return join(homedir(), value.slice(2));
  }
  return value;
}
