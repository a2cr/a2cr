import { existsSync } from "node:fs";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, describe, expect, it } from "vitest";

import { decryptWorkBatonContent } from "../src/crypto.js";
import {
  addSaveResponseDefaults,
  buildSaveContextRequest,
  decryptLoadedContext,
  normalizeModelSource,
  validateWorkBatonContent,
} from "../src/workbaton.js";

const TEST_KEY = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=";

let tempDirs: string[] = [];

afterEach(async () => {
  await Promise.all(tempDirs.map((dir) => rm(dir, { recursive: true, force: true })));
  tempDirs = [];
});

describe("WorkBaton helpers", () => {
  it("builds encrypted save requests without plaintext content", () => {
    const { body, content, normalizedModelSource } = buildSaveContextRequest(
      {
        slot_name: "demo",
        content: {
          goal: "client encrypt",
          current_state: "roundtrip",
          next_action: "assert",
        },
        model_source: "Anthropic Claude",
        preferred_response_language: "ja",
      },
      TEST_KEY,
    );

    expect(normalizedModelSource).toBe("claude");
    expect(body.model_source).toBe("claude");
    expect(body.compressed_tokens).toBeGreaterThan(0);
    expect(JSON.stringify(body)).not.toContain("client encrypt");
    expect(decryptWorkBatonContent(body.encrypted_content as { ciphertext: string }, TEST_KEY)).toEqual(content);
    expect(content.language_context).toEqual({
      preferred_response_language: "ja",
      source: "conversation_before_save",
      confidence: "high",
    });
  });

  it("decrypts loaded client-encrypted contexts and attaches language guidance", () => {
    const { body } = buildSaveContextRequest(
      {
        slot_name: "demo",
        content: {
          goal: "load",
          current_state: "encrypted",
          next_action: "return content",
          language_context: {
            preferred_response_language: "ja",
            source: "conversation_before_save",
            confidence: "high",
          },
        },
      },
      TEST_KEY,
    );

    const loaded = decryptLoadedContext(
      {
        status: "loaded",
        encryption_mode: "client",
        content: null,
        encrypted_content: body.encrypted_content,
      },
      TEST_KEY,
    );

    expect(loaded.status).toBe("loaded");
    expect(loaded.encrypted_content).toBeNull();
    expect(loaded.response_language_hint).toBe("ja");
    expect(loaded.agent_continuity_guidance).toMatchObject({ use_proactively: true });
  });

  it("reports a missing local key without creating one during decrypt-only loading", async () => {
    const dir = await mkdtemp(join(tmpdir(), "a2cr-workbaton-"));
    tempDirs.push(dir);
    const missingKeyPath = join(dir, "missing.key");
    const previous = process.env.A2CR_CLIENT_KEY_FILE;
    process.env.A2CR_CLIENT_KEY_FILE = missingKeyPath;
    try {
      const loaded = decryptLoadedContext({
        status: "loaded",
        encryption_mode: "client",
        content: null,
        encrypted_content: {
          version: 1,
          alg: "Fernet",
          nonce: "embedded",
          ciphertext: "not-a-real-token",
        },
      });

      expect(loaded.status).toBe("key_unavailable");
      expect(existsSync(missingKeyPath)).toBe(false);
    } finally {
      if (previous === undefined) {
        delete process.env.A2CR_CLIENT_KEY_FILE;
      } else {
        process.env.A2CR_CLIENT_KEY_FILE = previous;
      }
    }
  });

  it("rejects file-like, base64, and secret-like WorkBaton content", () => {
    const base = {
      goal: "g",
      current_state: "s",
      next_action: "n",
    };

    expect(() => validateWorkBatonContent({ ...base, attachment: "abc" })).toThrow("not file storage");
    expect(() => validateWorkBatonContent({ ...base, note: "A".repeat(256) })).toThrow("not file storage");
    expect(() => validateWorkBatonContent({ ...base, note: "API_KEY=real-secret-value" })).toThrow("secret material");
    expect(() => validateWorkBatonContent({ ...base, note: "Do not store API keys." })).not.toThrow();
  });

  it("normalizes known model sources and aliases", () => {
    expect(normalizeModelSource("OpenAI GPT-5")).toBe("gpt");
    expect(normalizeModelSource("Anthropic Claude")).toBe("claude");
    expect(normalizeModelSource("")).toBeNull();
    expect(normalizeModelSource("new-model-family")).toBe("other");
  });

  it("adds default save response fields", () => {
    expect(addSaveResponseDefaults({ slot_number: 2 }, "demo-slot", {})).toMatchObject({
      resume_context_call: "resume_context(slot_number=2)",
      user_facing_summary: "Saved A2CR WorkBaton demo-slot (Slot 2).",
      agent_continuity_guidance: {
        use_proactively: true,
      },
    });
  });
});
