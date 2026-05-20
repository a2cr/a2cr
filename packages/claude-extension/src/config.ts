import { URL } from "node:url";

export interface A2crConfig {
  apiKey: string;
  baseUrl: string;
  clientType: string;
}

export class A2crConfigurationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "A2crConfigurationError";
  }
}

export function loadConfig(env: NodeJS.ProcessEnv = process.env): A2crConfig {
  const baseUrl = normalizeBaseUrl(env.A2CR_BASE_URL ?? "https://a2cr.app");
  if (isLocalBaseUrl(baseUrl) && env.A2CR_ALLOW_LOCAL_BASE_URL !== "1") {
    throw new A2crConfigurationError(
      "A2CR refuses localhost A2CR_BASE_URL by default. Set A2CR_ALLOW_LOCAL_BASE_URL=1 only for explicit local tests.",
    );
  }

  return {
    apiKey: env.A2CR_API_KEY ?? "",
    baseUrl,
    clientType: (env.A2CR_CLIENT_TYPE ?? "mcp").trim() || "mcp",
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
  const host = new URL(value).hostname;
  return host === "localhost" || host === "127.0.0.1" || host === "::1";
}
