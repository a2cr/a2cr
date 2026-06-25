import {
  InvalidFernetTokenError,
  MissingClientKeyError,
  decryptWorkStashValue,
  encryptWorkStashValue,
  type EncryptedWorkStashValue,
  type FernetKeyInput,
} from "./crypto.js";

const ENTRY_KEY_PATTERN = /^[A-Za-z0-9_.:-]{1,256}$/;
const TAG_PATTERN = /^[A-Za-z0-9_.:-]{1,64}$/;

export interface StoreWorkStashArgs {
  entry_key: string;
  value: string;
  tags?: string[] | null;
  project?: string | null;
}

export function buildStoreWorkStashRequest(
  args: StoreWorkStashArgs,
  key?: FernetKeyInput,
): {
  body: Record<string, unknown>;
  tags: string[];
} {
  validateEntryKey(args.entry_key);
  const value = normalizeValue(args.value);
  const tags = normalizeTags(args.tags);
  return {
    tags,
    body: {
      entry_key: args.entry_key,
      encrypted_value: encryptWorkStashValue(value, key),
      size_bytes: Buffer.byteLength(value, "utf8"),
      tags,
      project: normalizeOptionalText(args.project),
    },
  };
}

export function decryptLoadedWorkStash(data: Record<string, unknown>, key?: FernetKeyInput): Record<string, unknown> {
  if (data.encryption_mode !== "client") {
    return data;
  }
  const encryptedValue = data.encrypted_value;
  if (!isEncryptedWorkStashValue(encryptedValue)) {
    return {
      ...data,
      value: null,
      encrypted_value: null,
      status: "decrypt_failed",
      message: "Client-encrypted WorkStash entry did not include encrypted_value.",
    };
  }
  try {
    return {
      ...data,
      value: decryptWorkStashValue(encryptedValue, key),
      encrypted_value: null,
      status: data.status ?? "loaded",
    };
  } catch (error) {
    if (error instanceof MissingClientKeyError) {
      return {
        ...data,
        value: null,
        encrypted_value: null,
        status: "key_unavailable",
        message: "This WorkStash entry is client-encrypted, but the local A2CR key file is missing.",
      };
    }
    if (error instanceof InvalidFernetTokenError) {
      return {
        ...data,
        value: null,
        encrypted_value: null,
        status: "decrypt_failed",
        message: "This WorkStash entry is client-encrypted, but the local A2CR key could not decrypt it.",
      };
    }
    throw error;
  }
}

export function validateEntryKey(entryKey: string): void {
  if (!ENTRY_KEY_PATTERN.test(entryKey)) {
    throw new Error(
      "entry_key must be 1-256 characters and contain only letters, digits, underscore, dot, colon, or hyphen.",
    );
  }
}

function normalizeValue(value: string): string {
  if (typeof value !== "string" || !value.trim()) {
    throw new Error("WorkStash value must be a non-empty string.");
  }
  return value;
}

function normalizeTags(tags: string[] | null | undefined): string[] {
  if (tags === null || tags === undefined) {
    return [];
  }
  if (!Array.isArray(tags)) {
    throw new Error("WorkStash tags must be an array of short strings.");
  }
  const normalized = tags.map((tag) => tag.trim()).filter(Boolean);
  if (normalized.some((tag) => !TAG_PATTERN.test(tag))) {
    throw new Error("WorkStash tags must be 1-64 characters using letters, digits, underscore, dot, colon, or hyphen.");
  }
  return [...new Set(normalized)].slice(0, 20);
}

function normalizeOptionalText(value: string | null | undefined): string | null {
  if (value === null || value === undefined) {
    return null;
  }
  const normalized = value.trim();
  return normalized ? normalized : null;
}

function isEncryptedWorkStashValue(value: unknown): value is EncryptedWorkStashValue {
  return value !== null && typeof value === "object" && typeof (value as Record<string, unknown>).ciphertext === "string";
}
