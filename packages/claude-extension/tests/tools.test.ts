import { describe, expect, it } from "vitest";

import { A2crHttpError } from "../src/api.js";
import { MCP_INSTRUCTIONS, createServer } from "../src/index.js";
import { createA2crToolHandlers } from "../src/tools.js";
import type { A2crClient } from "../src/tools.js";

const TEST_KEY = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=";

describe("A2CR tool handlers", () => {
  it("creates an MCP server with A2CR instructions", () => {
    const server = createServer();

    expect(server.isConnected()).toBe(false);
    expect(MCP_INSTRUCTIONS).toContain("save_context");
  });

  it("saves through the API client with encrypted content", async () => {
    const savedBodies: Record<string, unknown>[] = [];
    const handlers = createA2crToolHandlers({
      key: TEST_KEY,
      client: fakeClient({
        saveContext: async (body) => {
          savedBodies.push(body);
          return { slot_number: 5 };
        },
      }),
    });

    const result = await handlers.saveContext({
      slot_name: "demo",
      slot_number: 5,
      content: {
        goal: "client encrypt",
        current_state: "roundtrip",
        next_action: "assert",
      },
      model_source: "Codex",
    });

    expect(result.resume_context_call).toBe("resume_context(slot_number=5)");
    expect(savedBodies).toHaveLength(1);
    expect(JSON.stringify(savedBodies[0])).not.toContain("client encrypt");
    expect(savedBodies[0]?.model_source).toBe("codex");
  });

  it("loads and decrypts client-encrypted content", async () => {
    const saveHandlers = createA2crToolHandlers({
      key: TEST_KEY,
      client: fakeClient({
        saveContext: async (body) => body,
      }),
    });
    const saved = await saveHandlers.saveContext({
      slot_name: "demo",
      content: {
        goal: "load",
        current_state: "encrypted",
        next_action: "return content",
      },
    });

    const loadHandlers = createA2crToolHandlers({
      key: TEST_KEY,
      client: fakeClient({
        loadContextByName: async () => ({
          encryption_mode: "client",
          content: null,
          encrypted_content: saved.encrypted_content,
        }),
      }),
    });

    const loaded = await loadHandlers.loadContext({ slot_name: "demo" });

    expect(loaded.status).toBe("loaded");
    expect(loaded.content).toMatchObject({
      goal: "load",
      current_state: "encrypted",
      next_action: "return content",
    });
  });

  it("returns validation and not-found statuses for load_context", async () => {
    const handlers = createA2crToolHandlers({
      client: fakeClient({
        loadContextByNumber: async () => {
          throw new A2crHttpError(404, []);
        },
      }),
    });

    expect(await handlers.loadContext({})).toMatchObject({
      status: "validation_error",
    });
    expect(await handlers.loadContext({ slot_number: 9 })).toMatchObject({
      status: "not_found",
      slot_number: 9,
    });
  });
});

function fakeClient(overrides: Partial<A2crClient>): A2crClient {
  return {
    getAccountLimits: async () => ({}),
    listContexts: async () => [],
    saveContext: async () => ({}),
    loadContextByName: async () => ({}),
    loadContextByNumber: async () => ({}),
    ...overrides,
  };
}
