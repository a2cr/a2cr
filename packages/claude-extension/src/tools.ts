import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { CallToolResult } from "@modelcontextprotocol/sdk/types.js";
import { z } from "zod/v4";

import { A2crApiClient, A2crHttpError, type FetchLike } from "./api.js";
import { type A2crConfig, loadConfig } from "./config.js";
import type { FernetKeyInput } from "./crypto.js";
import { addSaveResponseDefaults, buildSaveContextRequest, decryptLoadedContext, type SaveContextArgs } from "./workbaton.js";

export interface A2crClient {
  getAccountLimits(): Promise<unknown>;
  listContexts(): Promise<unknown>;
  saveContext(body: Record<string, unknown>, clientType?: string | null): Promise<Record<string, unknown>>;
  loadContextByName(slotName: string): Promise<Record<string, unknown>>;
  loadContextByNumber(slotNumber: number): Promise<Record<string, unknown>>;
}

export interface A2crToolHandlers {
  getAccountLimits(): Promise<unknown>;
  listContexts(): Promise<unknown>;
  saveContext(args: SaveContextArgs): Promise<Record<string, unknown>>;
  loadContext(args: { slot_name?: string | null; slot_number?: number | null }): Promise<Record<string, unknown>>;
}

export interface A2crToolHandlerOptions {
  client?: A2crClient;
  config?: A2crConfig;
  fetchImpl?: FetchLike;
  key?: FernetKeyInput;
}

export function createA2crToolHandlers(options: A2crToolHandlerOptions = {}): A2crToolHandlers {
  const client = options.client ?? new A2crApiClient(options.config ?? loadConfig(), options.fetchImpl);
  return {
    getAccountLimits: () => client.getAccountLimits(),
    listContexts: () => client.listContexts(),
    saveContext: async (args) => {
      const { body, content, normalizedModelSource } = buildSaveContextRequest(args, options.key);
      const result = await client.saveContext(body, normalizedModelSource);
      return addSaveResponseDefaults(result, args.slot_name, content);
    },
    loadContext: async (args) => {
      if (args.slot_number === null || args.slot_number === undefined) {
        if (!args.slot_name) {
          return {
            status: "validation_error",
            message: "slot_number or slot_name is required",
          };
        }
      }
      try {
        const data =
          args.slot_number !== null && args.slot_number !== undefined
            ? await client.loadContextByNumber(args.slot_number)
            : await client.loadContextByName(args.slot_name as string);
        return decryptLoadedContext({ ...data, status: "loaded" }, options.key);
      } catch (error) {
        if (error instanceof A2crHttpError && error.statusCode === 404) {
          return {
            status: "not_found",
            slot_name: args.slot_name ?? null,
            slot_number: args.slot_number ?? null,
          };
        }
        throw error;
      }
    },
  };
}

export function registerA2crTools(server: McpServer, handlers: A2crToolHandlers = createA2crToolHandlers()): void {
  server.registerTool(
    "get_account_limits",
    {
      title: "Get Account Limits",
      description:
        "Return the current account limits for Slots, retention choices, body size, WorkStash, and handoff policy.",
      annotations: { readOnlyHint: true },
    },
    async () => toolResult(await handlers.getAccountLimits(), "limits"),
  );

  server.registerTool(
    "list_contexts",
    {
      title: "List WorkBaton Slots",
      description: "List active WorkBaton Slot metadata only, including expiry times and sizes.",
      annotations: { readOnlyHint: true },
    },
    async () => toolResult(await handlers.listContexts(), "contexts"),
  );

  server.registerTool(
    "save_context",
    {
      title: "Save WorkBaton",
      description:
        "Save compact WorkBaton handoff content to A2CR after local validation and local Fernet encryption. A2CR receives ciphertext only.",
      annotations: { readOnlyHint: false, destructiveHint: true },
      inputSchema: {
        slot_name: z.string().min(1).describe("Named WorkBaton slot to create or overwrite."),
        content: z.record(z.string(), z.unknown()).describe("Compact WorkBaton JSON object."),
        original_length: z.number().int().nonnegative().optional().nullable(),
        model_source: z.string().optional().nullable(),
        slot_number: z.number().int().positive().optional().nullable(),
        preferred_response_language: z.string().optional().nullable(),
      },
    },
    async (args) => toolResult(await handlers.saveContext(args), "result"),
  );

  server.registerTool(
    "load_context",
    {
      title: "Load WorkBaton",
      description:
        "Load a WorkBaton by name or fixed Slot number and decrypt client-encrypted content locally before returning it.",
      inputSchema: {
        slot_name: z.string().optional().nullable(),
        slot_number: z.number().int().positive().optional().nullable(),
      },
      annotations: { readOnlyHint: true },
    },
    async (args) => toolResult(await handlers.loadContext(args), "result"),
  );
}

function toolResult(data: unknown, wrapperKey: string): CallToolResult {
  const structuredContent: Record<string, unknown> =
    data !== null && typeof data === "object" && !Array.isArray(data)
      ? (data as Record<string, unknown>)
      : { [wrapperKey]: data };
  return {
    content: [
      {
        type: "text",
        text: JSON.stringify(data, null, 2),
      },
    ],
    structuredContent,
  };
}
