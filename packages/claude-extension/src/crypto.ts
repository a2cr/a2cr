import {
  createCipheriv,
  createDecipheriv,
  createHash,
  createHmac,
  randomBytes,
  timingSafeEqual,
} from "node:crypto";
import {
  chmodSync,
  closeSync,
  constants,
  existsSync,
  mkdirSync,
  openSync,
  readFileSync,
  writeFileSync,
} from "node:fs";
import { homedir } from "node:os";
import { dirname, join } from "node:path";

const FERNET_VERSION = 0x80;
const FERNET_KEY_BYTES = 32;
const FERNET_SIGNING_KEY_BYTES = 16;
const FERNET_IV_BYTES = 16;
const FERNET_HMAC_BYTES = 32;

export type FernetKeyInput = Buffer | Uint8Array | string;

export interface FernetEncryptOptions {
  iv?: Buffer | Uint8Array;
  now?: Date | number;
}

export interface EncryptedWorkBatonContent {
  version: 1;
  alg: "Fernet";
  nonce: "embedded";
  ciphertext: string;
  key_wrap: {
    type: "local-key";
    kid: string;
  };
}

export interface EncryptedWorkStashValue {
  version: 1;
  alg: "Fernet";
  ciphertext: string;
  key_wrap: {
    type: "local-key";
    kid: string;
  };
}

interface NormalizedFernetKey {
  signing: Buffer;
  encryption: Buffer;
}

export class InvalidFernetTokenError extends Error {
  constructor(message = "Invalid Fernet token.") {
    super(message);
    this.name = "InvalidFernetTokenError";
  }
}

export class MissingClientKeyError extends Error {
  constructor(path: string) {
    super(`A2CR client encryption key is unavailable at ${path}.`);
    this.name = "MissingClientKeyError";
  }
}

export function compactJson(value: unknown): string {
  const serialized = JSON.stringify(value);
  if (serialized === undefined) {
    throw new TypeError("A2CR WorkBaton content must be JSON serializable.");
  }
  return serialized;
}

export function generateFernetKey(): Buffer {
  return Buffer.from(base64UrlEncode(randomBytes(FERNET_KEY_BYTES)), "utf8");
}

export function keyId(key: FernetKeyInput): string {
  return createHash("sha256").update(normalizeKeyBytes(key)).digest("hex").slice(0, 16);
}

export function resolveClientKeyPath(env: NodeJS.ProcessEnv = process.env): string {
  if (env.A2CR_CLIENT_KEY_FILE) {
    return expandUserPath(env.A2CR_CLIENT_KEY_FILE);
  }
  if (env.A2CR_CONFIG_DIR) {
    return join(expandUserPath(env.A2CR_CONFIG_DIR), "workbaton.key");
  }
  if (process.platform === "win32") {
    return join(env.APPDATA ?? join(homedir(), "AppData", "Roaming"), "A2CR", "workbaton.key");
  }
  return join(env.XDG_CONFIG_HOME ?? join(homedir(), ".config"), "a2cr", "workbaton.key");
}

export function loadClientKey(options: { create?: boolean; env?: NodeJS.ProcessEnv } = {}): Buffer | null {
  const path = resolveClientKeyPath(options.env);
  if (existsSync(path)) {
    return stripAsciiWhitespace(readFileSync(path));
  }
  if (!options.create) {
    return null;
  }

  mkdirSync(dirname(path), { recursive: true });
  const key = generateFernetKey();
  try {
    const fd = openSync(path, constants.O_WRONLY | constants.O_CREAT | constants.O_EXCL, 0o600);
    try {
      writeFileSync(fd, key);
    } finally {
      closeSync(fd);
    }
    if (process.platform !== "win32") {
      chmodSync(path, 0o600);
    }
    return key;
  } catch (error) {
    if (isNodeError(error) && error.code === "EEXIST") {
      return stripAsciiWhitespace(readFileSync(path));
    }
    throw error;
  }
}

export function requireClientKey(options: { create?: boolean; env?: NodeJS.ProcessEnv } = {}): Buffer {
  const key = loadClientKey(options);
  if (key !== null) {
    return key;
  }
  throw new MissingClientKeyError(resolveClientKeyPath(options.env));
}

export function encryptFernet(
  plaintext: Buffer | Uint8Array | string,
  key: FernetKeyInput,
  options: FernetEncryptOptions = {},
): string {
  const normalized = normalizeFernetKey(key);
  const iv = normalizeIv(options.iv ?? randomBytes(FERNET_IV_BYTES));
  const timestamp = normalizeTimestamp(options.now ?? Date.now());
  const header = Buffer.alloc(1 + 8 + FERNET_IV_BYTES);

  header[0] = FERNET_VERSION;
  header.writeBigUInt64BE(BigInt(timestamp), 1);
  iv.copy(header, 9);

  const cipher = createCipheriv("aes-128-cbc", normalized.encryption, iv);
  const ciphertext = Buffer.concat([
    cipher.update(Buffer.isBuffer(plaintext) ? plaintext : Buffer.from(plaintext)),
    cipher.final(),
  ]);
  const signed = Buffer.concat([header, ciphertext]);
  const hmac = createHmac("sha256", normalized.signing).update(signed).digest();

  return base64UrlEncode(Buffer.concat([signed, hmac]));
}

export function decryptFernet(token: string, key: FernetKeyInput): Buffer {
  const normalized = normalizeFernetKey(key);
  const decoded = base64UrlDecode(token);
  const minimumLength = 1 + 8 + FERNET_IV_BYTES + FERNET_IV_BYTES + FERNET_HMAC_BYTES;
  if (decoded.length < minimumLength || decoded[0] !== FERNET_VERSION) {
    throw new InvalidFernetTokenError();
  }

  const signed = decoded.subarray(0, decoded.length - FERNET_HMAC_BYTES);
  const expectedHmac = createHmac("sha256", normalized.signing).update(signed).digest();
  const actualHmac = decoded.subarray(decoded.length - FERNET_HMAC_BYTES);
  if (!timingSafeEqual(expectedHmac, actualHmac)) {
    throw new InvalidFernetTokenError();
  }

  const iv = decoded.subarray(9, 9 + FERNET_IV_BYTES);
  const ciphertext = decoded.subarray(9 + FERNET_IV_BYTES, decoded.length - FERNET_HMAC_BYTES);
  try {
    const decipher = createDecipheriv("aes-128-cbc", normalized.encryption, iv);
    return Buffer.concat([decipher.update(ciphertext), decipher.final()]);
  } catch {
    throw new InvalidFernetTokenError();
  }
}

export function encryptWorkBatonContent(
  content: Record<string, unknown>,
  key: FernetKeyInput = requireClientKey({ create: true }),
  options: FernetEncryptOptions = {},
): EncryptedWorkBatonContent {
  return {
    version: 1,
    alg: "Fernet",
    nonce: "embedded",
    ciphertext: encryptFernet(compactJson(content), key, options),
    key_wrap: {
      type: "local-key",
      kid: keyId(key),
    },
  };
}

export function decryptWorkBatonContent(
  encrypted: Pick<EncryptedWorkBatonContent, "ciphertext">,
  key: FernetKeyInput = requireClientKey({ create: false }),
): Record<string, unknown> {
  const plaintext = decryptFernet(encrypted.ciphertext, key).toString("utf8");
  const parsed: unknown = JSON.parse(plaintext);
  if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new TypeError("Decrypted WorkBaton content must be a JSON object.");
  }
  return parsed as Record<string, unknown>;
}

export function encryptWorkStashValue(
  value: string,
  key: FernetKeyInput = requireClientKey({ create: true }),
  options: FernetEncryptOptions = {},
): EncryptedWorkStashValue {
  return {
    version: 1,
    alg: "Fernet",
    ciphertext: encryptFernet(value, key, options),
    key_wrap: {
      type: "local-key",
      kid: keyId(key),
    },
  };
}

export function decryptWorkStashValue(
  encrypted: Pick<EncryptedWorkStashValue, "ciphertext">,
  key: FernetKeyInput = requireClientKey({ create: false }),
): string {
  return decryptFernet(encrypted.ciphertext, key).toString("utf8");
}

function normalizeFernetKey(key: FernetKeyInput): NormalizedFernetKey {
  const encoded = normalizeKeyBytes(key);
  const decoded = base64UrlDecode(encoded.toString("utf8"));
  if (decoded.length !== FERNET_KEY_BYTES) {
    throw new TypeError("Fernet key must decode to exactly 32 bytes.");
  }
  return {
    signing: decoded.subarray(0, FERNET_SIGNING_KEY_BYTES),
    encryption: decoded.subarray(FERNET_SIGNING_KEY_BYTES),
  };
}

function normalizeKeyBytes(key: FernetKeyInput): Buffer {
  const bytes = Buffer.isBuffer(key) ? key : Buffer.from(key);
  const stripped = stripAsciiWhitespace(bytes);
  if (stripped.length === 0) {
    throw new TypeError("Fernet key must not be empty.");
  }
  return stripped;
}

function normalizeIv(iv: Buffer | Uint8Array): Buffer {
  const buffer = Buffer.from(iv);
  if (buffer.length !== FERNET_IV_BYTES) {
    throw new TypeError("Fernet IV must be exactly 16 bytes.");
  }
  return buffer;
}

function normalizeTimestamp(value: Date | number): number {
  const seconds = value instanceof Date ? Math.floor(value.getTime() / 1000) : Math.floor(value / 1000);
  if (!Number.isSafeInteger(seconds) || seconds < 0) {
    throw new TypeError("Fernet timestamp must be a non-negative safe integer.");
  }
  return seconds;
}

function stripAsciiWhitespace(value: Buffer): Buffer {
  let start = 0;
  let end = value.length;
  while (start < end && isAsciiWhitespace(value[start])) {
    start += 1;
  }
  while (end > start && isAsciiWhitespace(value[end - 1])) {
    end -= 1;
  }
  return value.subarray(start, end);
}

function isAsciiWhitespace(value: number): boolean {
  return value === 0x09 || value === 0x0a || value === 0x0b || value === 0x0c || value === 0x0d || value === 0x20;
}

function base64UrlEncode(value: Buffer): string {
  return value.toString("base64").replaceAll("+", "-").replaceAll("/", "_");
}

function base64UrlDecode(value: string): Buffer {
  return Buffer.from(value.replaceAll("-", "+").replaceAll("_", "/"), "base64");
}

function expandUserPath(path: string): string {
  if (path === "~") {
    return homedir();
  }
  if (path.startsWith("~/") || path.startsWith("~\\")) {
    return join(homedir(), path.slice(2));
  }
  return path;
}

function isNodeError(error: unknown): error is NodeJS.ErrnoException {
  return error instanceof Error && "code" in error;
}
