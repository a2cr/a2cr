import { execFileSync } from "node:child_process";
import { createServer, type IncomingMessage, type ServerResponse } from "node:http";
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

interface CapturedRequest {
  method: string;
  url: string;
  body: string;
  headers: IncomingMessage["headers"];
}

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
    const capturedRequests: CapturedRequest[] = [];
    let savedEncryptedContent: unknown = null;

    const apiServer = createServer(async (request, response) => {
      const body = await readRequestBody(request);
      capturedRequests.push({
        method: request.method ?? "GET",
        url: request.url ?? "/",
        body,
        headers: request.headers,
      });

      if (request.method === "GET" && request.url === "/api/v1/account/limits") {
        writeJson(response, {
          plan: "smoke",
          max_body_bytes: 24576,
        });
        return;
      }

      if (request.method === "GET" && request.url === "/api/v1/contexts") {
        writeJson(response, []);
        return;
      }

      if (request.method === "POST" && request.url === "/api/v1/context") {
        const parsed = JSON.parse(body) as Record<string, unknown>;
        savedEncryptedContent = parsed.encrypted_content;
        writeJson(response, {
          slot_name: parsed.slot_name,
          slot_number: parsed.slot_number,
          status: "saved",
        });
        return;
      }

      if (request.method === "GET" && request.url === "/api/v1/context/smoke-slot") {
        writeJson(response, {
          slot_name: "smoke-slot",
          slot_number: 3,
          encryption_mode: "client",
          content: null,
          encrypted_content: savedEncryptedContent,
        });
        return;
      }

      writeJson(response, { code: "not_found" }, 404);
    });

    await new Promise<void>((resolveListen) => apiServer.listen(0, "127.0.0.1", resolveListen));
    const address = apiServer.address();
    if (address === null || typeof address === "string") {
      throw new Error("Mock A2CR API did not bind to a TCP port.");
    }

    const client = new Client({ name: "a2cr-claude-extension-smoke", version: "0.0.0" });
    const transport = new StdioClientTransport({
      command: process.execPath,
      args: [serverEntrypoint],
      cwd: packageRoot,
      env: cleanEnv({
        ...process.env,
        A2CR_API_KEY: "SMOKE_TEST_API_KEY",
        A2CR_BASE_URL: `http://127.0.0.1:${address.port}`,
        A2CR_ALLOW_LOCAL_BASE_URL: "1",
        A2CR_CLIENT_KEY_FILE: join(tempDir, "workbaton-smoke.key"),
        A2CR_CLIENT_TYPE: "claude",
      }),
      stderr: "pipe",
    });

    try {
      await client.connect(transport);
      const tools = await client.listTools();
      expect(tools.tools.map((tool) => tool.name).sort()).toEqual([
        "get_account_limits",
        "list_contexts",
        "load_context",
        "save_context",
      ]);

      const limits = await client.callTool({
        name: "get_account_limits",
        arguments: {},
      });
      expect(limits.structuredContent).toMatchObject({ plan: "smoke" });

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

      const saveRequest = capturedRequests.find(
        (item) => item.method === "POST" && item.url === "/api/v1/context",
      );
      expect(saveRequest).toBeDefined();
      expect(saveRequest?.body).not.toContain("stdio smoke");
      expect(saveRequest?.body).toContain("\"encrypted_content\"");
      expect(saveRequest?.headers.authorization).toBe("Bearer SMOKE_TEST_API_KEY");
      expect(saveRequest?.headers["x-a2cr-client-type"]).toBe("claude");
      expect(saveRequest?.headers["x-a2cr-mcp-version"]).toBe("0.1.6");

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
    } finally {
      await client.close();
      await new Promise<void>((resolveClose, rejectClose) => {
        apiServer.close((error) => (error ? rejectClose(error) : resolveClose()));
      });
    }
  });
});

function writeJson(response: ServerResponse, body: unknown, status = 200): void {
  response.writeHead(status, {
    "content-type": "application/json",
  });
  response.end(JSON.stringify(body));
}

function readRequestBody(request: IncomingMessage): Promise<string> {
  return new Promise((resolveRead, rejectRead) => {
    const chunks: Buffer[] = [];
    request.on("data", (chunk: Buffer) => chunks.push(chunk));
    request.on("end", () => resolveRead(Buffer.concat(chunks).toString("utf8")));
    request.on("error", rejectRead);
  });
}

function cleanEnv(env: NodeJS.ProcessEnv): Record<string, string> {
  return Object.fromEntries(Object.entries(env).filter((entry): entry is [string, string] => entry[1] !== undefined));
}
