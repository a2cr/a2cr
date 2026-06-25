import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { CallToolResult } from "@modelcontextprotocol/sdk/types.js";
import { z } from "zod/v4";

import { A2crApiClient, A2crHttpError, type FetchLike } from "./api.js";
import { type A2crConfig, loadConfig } from "./config.js";
import type { FernetKeyInput } from "./crypto.js";
import { A2crLocalStore } from "./localStore.js";
import { addSaveResponseDefaults, buildSaveContextRequest, decryptLoadedContext, type SaveContextArgs } from "./workbaton.js";
import {
  buildStoreWorkStashRequest,
  decryptLoadedWorkStash,
  validateEntryKey,
  type StoreWorkStashArgs,
} from "./workstash.js";

export interface A2crClient {
  getAccountLimits(): Promise<unknown>;
  listContexts(): Promise<unknown>;
  saveContext(body: Record<string, unknown>, clientType?: string | null): Promise<Record<string, unknown>>;
  loadContextByName(slotName: string): Promise<Record<string, unknown>>;
  loadContextByNumber(slotNumber: number): Promise<Record<string, unknown>>;
  storeWorkStash(body: Record<string, unknown>): Promise<Record<string, unknown>>;
  getWorkStash(entryKey: string): Promise<Record<string, unknown>>;
  listWorkStash(tagFilter?: string | null): Promise<unknown>;
  deleteWorkStash(entryKey: string): Promise<Record<string, unknown>>;
}

export interface A2crToolHandlers {
  getAccountLimits(): Promise<unknown>;
  listContexts(): Promise<unknown>;
  saveContext(args: SaveContextArgs): Promise<Record<string, unknown>>;
  loadContext(args: { slot_name?: string | null; slot_number?: number | null }): Promise<Record<string, unknown>>;
  storeWorkStash(args: StoreWorkStashArgs): Promise<Record<string, unknown>>;
  getWorkStash(args: { entry_key: string }): Promise<Record<string, unknown>>;
  listWorkStash(args: { tag_filter?: string | null }): Promise<unknown>;
  deleteWorkStash(args: { entry_key: string }): Promise<Record<string, unknown>>;
}

export interface A2crToolHandlerOptions {
  client?: A2crClient;
  config?: A2crConfig;
  fetchImpl?: FetchLike;
  key?: FernetKeyInput;
}

export function createA2crToolHandlers(options: A2crToolHandlerOptions = {}): A2crToolHandlers {
  const config = options.config ?? loadConfig();
  const client = options.client ?? (options.fetchImpl ? new A2crApiClient(config, options.fetchImpl) : new A2crLocalStore(config));
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
    storeWorkStash: async (args) => {
      const { body } = buildStoreWorkStashRequest(args, options.key);
      return client.storeWorkStash(body);
    },
    getWorkStash: async (args) => {
      try {
        validateEntryKey(args.entry_key);
        return decryptLoadedWorkStash(await client.getWorkStash(args.entry_key), options.key);
      } catch (error) {
        if (error instanceof A2crHttpError && error.statusCode === 404) {
          return {
            status: "not_found",
            entry_key: args.entry_key,
          };
        }
        throw error;
      }
    },
    listWorkStash: (args) => client.listWorkStash(args.tag_filter ?? null),
    deleteWorkStash: async (args) => {
      try {
        validateEntryKey(args.entry_key);
        return await client.deleteWorkStash(args.entry_key);
      } catch (error) {
        if (error instanceof A2crHttpError && error.statusCode === 404) {
          return {
            status: "not_found",
            entry_key: args.entry_key,
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
        "Return the current local workspace limits for Slots, retention choices, body size, WorkStash, and handoff policy.",
      annotations: { readOnlyHint: true, openWorldHint: false },
    },
    async () => toolResult(await handlers.getAccountLimits(), "limits"),
  );

  server.registerTool(
    "list_contexts",
    {
      title: "List WorkBaton Slots",
      description: "List active WorkBaton Slot metadata only, including expiry times and sizes.",
      annotations: { readOnlyHint: true, openWorldHint: false },
    },
    async () => toolResult(await handlers.listContexts(), "contexts"),
  );

  server.registerTool(
    "save_context",
    {
      title: "Save WorkBaton",
      description:
        "Save compact WorkBaton handoff content to the local A2CR workspace after local validation.",
      annotations: { readOnlyHint: false, destructiveHint: true, openWorldHint: false },
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
        "Load a WorkBaton by name or fixed Slot number from the local A2CR workspace.",
      inputSchema: {
        slot_name: z.string().optional().nullable(),
        slot_number: z.number().int().positive().optional().nullable(),
      },
      annotations: { readOnlyHint: true, openWorldHint: false },
    },
    async (args) => toolResult(await handlers.loadContext(args), "result"),
  );

  server.registerTool(
    "store_work_stash",
    {
      title: "Store WorkStash",
      description:
        "Store a temporary supporting note in the local A2CR workspace after encrypting it locally. Record the entry_key in WorkBaton references or next_action.",
      annotations: { readOnlyHint: false, destructiveHint: true, openWorldHint: false },
      inputSchema: {
        entry_key: z.string().min(1).max(256).describe("Stable WorkStash key to create or overwrite."),
        value: z.string().min(1).describe("Temporary supporting note. Do not include secrets, full transcripts, long logs, or source dumps."),
        tags: z.array(z.string()).optional().nullable(),
        project: z.string().optional().nullable(),
      },
    },
    async (args) => toolResult(await handlers.storeWorkStash(args), "result"),
  );

  server.registerTool(
    "get_work_stash",
    {
      title: "Get WorkStash",
      description:
        "Load one referenced WorkStash entry from the local A2CR workspace and decrypt it locally.",
      annotations: { readOnlyHint: true, openWorldHint: false },
      inputSchema: {
        entry_key: z.string().min(1).max(256).describe("WorkStash entry_key to load."),
      },
    },
    async (args) => toolResult(await handlers.getWorkStash(args), "result"),
  );

  server.registerTool(
    "list_work_stash",
    {
      title: "List WorkStash",
      description: "List local WorkStash metadata only. Stored values are not returned.",
      annotations: { readOnlyHint: true, openWorldHint: false },
      inputSchema: {
        tag_filter: z.string().optional().nullable(),
      },
    },
    async (args) => toolResult(await handlers.listWorkStash(args), "result"),
  );

  server.registerTool(
    "delete_work_stash",
    {
      title: "Delete WorkStash",
      description: "Delete one local WorkStash entry that is no longer needed.",
      annotations: { readOnlyHint: false, destructiveHint: true, openWorldHint: false },
      inputSchema: {
        entry_key: z.string().min(1).max(256).describe("WorkStash entry_key to delete."),
      },
    },
    async (args) => toolResult(await handlers.deleteWorkStash(args), "result"),
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
