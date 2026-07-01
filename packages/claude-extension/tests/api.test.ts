import { describe, expect, it } from "vitest";

import { A2crApiClient, A2crHttpError } from "../src/api.js";
import type { A2crConfig } from "../src/config.js";

const config: A2crConfig = {
  apiKey: "TEST_API_KEY_SHOULD_NOT_LEAK",
  baseUrl: "https://a2cr.example",
  clientType: "mcp",
  localStorePath: "/tmp/a2cr-test-store.json",
};

describe("A2crApiClient", () => {
  it("URL-encodes path segments without preserving slash", async () => {
    const urls: string[] = [];
    const client = new A2crApiClient(config, async (input) => {
      urls.push(input);
      return jsonResponse({ encryption_mode: "server", content: {} });
    });

    await client.loadContextByName("key/a?x=1#frag");

    expect(urls).toEqual(["https://a2cr.example/api/v1/context/key%2Fa%3Fx%3D1%23frag"]);
  });

  it("sends Authorization and normalized client type headers", async () => {
    const requests: RequestInit[] = [];
    const client = new A2crApiClient(config, async (_input, init) => {
      requests.push(init ?? {});
      return jsonResponse({ ok: true });
    });

    await client.saveContext({ slot_name: "demo" }, "claude");

    expect(requests[0]?.method).toBe("POST");
    expect(requests[0]?.headers).toMatchObject({
      Authorization: "Bearer TEST_API_KEY_SHOULD_NOT_LEAK",
      "X-A2CR-Client-Type": "claude",
      "X-A2CR-MCP-Version": "0.1.8",
    });
  });

  it("keeps HTTP error messages to safe diagnostics only", async () => {
    const client = new A2crApiClient(config, async () =>
      jsonResponse(
        {
          code: "db_lock_timeout",
          action: "retry",
          request_id: "req_123",
          detail: "plaintext body and TEST_API_KEY_SHOULD_NOT_LEAK must stay out",
        },
        503,
      ),
    );

    await expect(client.getAccountLimits()).rejects.toThrow(A2crHttpError);
    await expect(client.getAccountLimits()).rejects.toThrow(
      "status 503 (code=db_lock_timeout, action=retry, request_id=req_123, hint=retry_later)",
    );
    await expect(client.getAccountLimits()).rejects.not.toThrow("TEST_API_KEY_SHOULD_NOT_LEAK");
  });
});

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "content-type": "application/json",
    },
  });
}
