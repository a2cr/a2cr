import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, describe, expect, it } from "vitest";

import {
  compactJson,
  decryptFernet,
  decryptWorkBatonContent,
  decryptWorkStashValue,
  encryptFernet,
  encryptWorkBatonContent,
  encryptWorkStashValue,
  keyId,
  loadClientKey,
  resolveClientKeyPath,
} from "../src/crypto.js";

const TEST_KEY = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=";
const FIXED_IV = Buffer.from("00112233445566778899aabbccddeeff", "hex");
const FIXED_NOW_MS = 1_714_222_400_000;
const PYTHON = process.env.PYTHON ?? "python";

const batonContent = {
  goal: "client encrypt",
  current_state: "roundtrip with ja: \u3053\u3093\u306b\u3061\u306f",
  next_action: "assert",
};

let tempDirs: string[] = [];

afterEach(async () => {
  await Promise.all(tempDirs.map((dir) => rm(dir, { recursive: true, force: true })));
  tempDirs = [];
});

describe("Fernet compatibility", () => {
  it("decrypts Python-generated WorkBaton and WorkStash fixtures", () => {
    const pythonFixture = runPython<{
      baton_token: string;
      stash_token: string;
    }>(
      `
import json
import sys
from cryptography.fernet import Fernet

data = json.load(sys.stdin)
fernet = Fernet(data["key"].encode("utf-8"))
baton_plaintext = json.dumps(data["content"], ensure_ascii=False, separators=(",", ":")).encode("utf-8")
stash_plaintext = data["stash"].encode("utf-8")
print(json.dumps({
    "baton_token": fernet.encrypt(baton_plaintext).decode("utf-8"),
    "stash_token": fernet.encrypt(stash_plaintext).decode("utf-8"),
}))
`,
      {
        key: TEST_KEY,
        content: batonContent,
        stash: "raw stash value\nsecond line",
      },
    );

    expect(
      decryptWorkBatonContent(
        {
          ciphertext: pythonFixture.baton_token,
        },
        TEST_KEY,
      ),
    ).toEqual(batonContent);
    expect(decryptWorkStashValue({ ciphertext: pythonFixture.stash_token }, TEST_KEY)).toBe(
      "raw stash value\nsecond line",
    );
  });

  it("creates Node-generated Fernet tokens that Python can decrypt", () => {
    const batonEncrypted = encryptWorkBatonContent(batonContent, TEST_KEY, {
      iv: FIXED_IV,
      now: FIXED_NOW_MS,
    });
    const stashEncrypted = encryptWorkStashValue("node stash value", TEST_KEY, {
      iv: FIXED_IV,
      now: FIXED_NOW_MS,
    });

    const pythonDecrypted = runPython<{
      baton_plaintext: string;
      stash_plaintext: string;
    }>(
      `
import json
import sys
from cryptography.fernet import Fernet

data = json.load(sys.stdin)
fernet = Fernet(data["key"].encode("utf-8"))
print(json.dumps({
    "baton_plaintext": fernet.decrypt(data["baton_token"].encode("utf-8")).decode("utf-8"),
    "stash_plaintext": fernet.decrypt(data["stash_token"].encode("utf-8")).decode("utf-8"),
}))
`,
      {
        key: TEST_KEY,
        baton_token: batonEncrypted.ciphertext,
        stash_token: stashEncrypted.ciphertext,
      },
    );

    expect(pythonDecrypted.baton_plaintext).toBe(compactJson(batonContent));
    expect(JSON.parse(pythonDecrypted.baton_plaintext)).toEqual(batonContent);
    expect(pythonDecrypted.stash_plaintext).toBe("node stash value");
  });

  it("matches Python key id behavior by hashing the encoded Fernet key bytes", () => {
    const pythonKid = runPython<{ kid: string }>(
      `
import hashlib
import json
import sys

data = json.load(sys.stdin)
print(json.dumps({"kid": hashlib.sha256(data["key"].encode("utf-8")).hexdigest()[:16]}))
`,
      {
        key: TEST_KEY,
      },
    );

    expect(keyId(TEST_KEY)).toBe(pythonKid.kid);
    expect(encryptWorkBatonContent(batonContent, TEST_KEY).key_wrap.kid).toBe(pythonKid.kid);
  });

  it("rejects tampered Fernet tokens", () => {
    const token = encryptFernet("hello", TEST_KEY, {
      iv: FIXED_IV,
      now: FIXED_NOW_MS,
    });
    const tampered = `${token.slice(0, -2)}AA`;

    expect(() => decryptFernet(tampered, TEST_KEY)).toThrow("Invalid Fernet token");
  });

  it("does not create a local key during decrypt-only loading", async () => {
    const dir = await mkdtemp(join(tmpdir(), "a2cr-claude-extension-"));
    tempDirs.push(dir);
    const env = {
      ...process.env,
      A2CR_CLIENT_KEY_FILE: join(dir, "missing-workbaton.key"),
    };

    expect(loadClientKey({ create: false, env })).toBeNull();
    expect(existsSync(resolveClientKeyPath(env))).toBe(false);
  });
});

function runPython<T>(script: string, input: unknown): T {
  const stdout = execFileSync(PYTHON, ["-c", script], {
    env: {
      ...process.env,
      PYTHONIOENCODING: "utf-8",
    },
    input: JSON.stringify(input),
    encoding: "utf8",
  });
  return JSON.parse(stdout) as T;
}
