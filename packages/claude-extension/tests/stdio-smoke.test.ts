import { execFileSync } from "node:child_process";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

const packageRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const distDir = join(packageRoot, "dist");
const serverEntrypoint = join(distDir, "index.js");

let tempDir: string;

beforeAll(() => {
  execFileSync(process.execPath, [join(packageRoot, "node_modules", "typescript", "bin", "tsc"), "-p", "tsconfig.json"], {
    cwd: packageRoot,
    stdio: "pipe",
  });
});

afterAll(async () => {
  await rm(distDir, { recursive: true, force: true });
  if (tempDir) {
    await rm(tempDir, { recursive: true, force: true });
  }
});

describe("MCP stdio smoke", () => {
  it("starts the Node wrapper separately and round-trips save/load through MCP tools", async () => {
    tempDir = await mkdtemp(join(tmpdir(), "a2cr-claude-stdio-"));
    const client = new Client({ name: "a2cr-claude-extension-smoke", version: "0.0.0" });
    const transport = new StdioClientTransport({
      command: process.execPath,
      args: [serverEntrypoint],
      cwd: packageRoot,
      env: cleanEnv({
        ...process.env,
        A2CR_LOCAL_STORE_FILE: join(tempDir, "claude-extension-store.json"),
        A2CR_CLIENT_KEY_FILE: join(tempDir, "workbaton-smoke.key"),
        A2CR_CLIENT_TYPE: "claude",
      }),
      stderr: "pipe",
    });

    try {
      await client.connect(transport);
      const tools = await client.listTools();
      expect(tools.tools.map((tool) => tool.name).sort()).toEqual([
        "delete_work_stash",
        "get_account_limits",
        "get_work_stash",
        "list_contexts",
        "list_work_stash",
        "load_context",
        "save_context",
        "store_work_stash",
      ]);
      const toolsByName = Object.fromEntries(tools.tools.map((tool) => [tool.name, tool]));
      expect(toolsByName.get_account_limits?.title).toBe("Get Account Limits");
      expect(toolsByName.get_account_limits?.annotations).toMatchObject({ readOnlyHint: true });
      expect(toolsByName.list_contexts?.title).toBe("List WorkBaton Slots");
      expect(toolsByName.list_contexts?.annotations).toMatchObject({ readOnlyHint: true });
      expect(toolsByName.load_context?.title).toBe("Load WorkBaton");
      expect(toolsByName.load_context?.annotations).toMatchObject({ readOnlyHint: true });
      expect(toolsByName.save_context?.title).toBe("Save WorkBaton");
      expect(toolsByName.save_context?.annotations).toMatchObject({
        readOnlyHint: false,
        destructiveHint: true,
      });
      expect(toolsByName.store_work_stash?.title).toBe("Store WorkStash");
      expect(toolsByName.store_work_stash?.annotations).toMatchObject({
        readOnlyHint: false,
        destructiveHint: true,
      });
      expect(toolsByName.get_work_stash?.title).toBe("Get WorkStash");
      expect(toolsByName.get_work_stash?.annotations).toMatchObject({ readOnlyHint: true });
      expect(toolsByName.list_work_stash?.title).toBe("List WorkStash");
      expect(toolsByName.list_work_stash?.annotations).toMatchObject({ readOnlyHint: true });
      expect(toolsByName.delete_work_stash?.title).toBe("Delete WorkStash");
      expect(toolsByName.delete_work_stash?.annotations).toMatchObject({
        readOnlyHint: false,
        destructiveHint: true,
      });

      const limits = await client.callTool({
        name: "get_account_limits",
        arguments: {},
      });
      expect(limits.structuredContent).toMatchObject({ storage_mode: "local", requires_api_key: false });

      const saveResult = await client.callTool({
        name: "save_context",
        arguments: {
          slot_name: "smoke-slot",
          slot_number: 3,
          content: {
            goal: "stdio smoke",
            current_state: "node wrapper started",
            next_action: "load decrypted content",
          },
          model_source: "claude",
        },
      });
      expect(saveResult.structuredContent).toMatchObject({
        slot_name: "smoke-slot",
        slot_number: 3,
        status: "saved",
      });

      const listed = await client.callTool({
        name: "list_contexts",
        arguments: {},
      });
      expect(listed.structuredContent).toMatchObject({
        contexts: [
          {
            slot_name: "smoke-slot",
            slot_number: 3,
            storage_mode: "local",
          },
        ],
      });

      const loadResult = await client.callTool({
        name: "load_context",
        arguments: {
          slot_name: "smoke-slot",
        },
      });
      expect(loadResult.structuredContent).toMatchObject({
        status: "loaded",
        content: {
          goal: "stdio smoke",
          current_state: "node wrapper started",
          next_action: "load decrypted content",
        },
        encrypted_content: null,
      });

      const stashResult = await client.callTool({
        name: "store_work_stash",
        arguments: {
          entry_key: "smoke-note",
          value: "short supporting note",
          tags: ["smoke"],
          project: "claude-extension",
        },
      });
      expect(stashResult.structuredContent).toMatchObject({
        status: "stored",
        entry_key: "smoke-note",
        storage_mode: "local",
      });

      const stashList = await client.callTool({
        name: "list_work_stash",
        arguments: { tag_filter: "smoke" },
      });
      expect(stashList.structuredContent).toMatchObject({
        status: "ok",
        entries: [
          {
            entry_key: "smoke-note",
            tags: ["smoke"],
            storage_mode: "local",
          },
        ],
      });
      expect(JSON.stringify(stashList.structuredContent)).not.toContain("short supporting note");

      const stashLoad = await client.callTool({
        name: "get_work_stash",
        arguments: { entry_key: "smoke-note" },
      });
      expect(stashLoad.structuredContent).toMatchObject({
        status: "loaded",
        entry_key: "smoke-note",
        value: "short supporting note",
        encrypted_value: null,
      });

      const stashDelete = await client.callTool({
        name: "delete_work_stash",
        arguments: { entry_key: "smoke-note" },
      });
      expect(stashDelete.structuredContent).toMatchObject({
        status: "deleted",
        entry_key: "smoke-note",
      });
    } finally {
      await client.close();
    }
  });
});

function cleanEnv(env: NodeJS.ProcessEnv): Record<string, string> {
  return Object.fromEntries(Object.entries(env).filter((entry): entry is [string, string] => entry[1] !== undefined));
}
