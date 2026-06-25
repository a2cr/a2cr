import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname } from "node:path";

import { A2crHttpError } from "./api.js";
import type { A2crConfig } from "./config.js";

interface StoredContext {
  slot_name: string;
  slot_number: number | null;
  original_length: number | null;
  compressed_tokens: number | null;
  model_source: string | null;
  encrypted_content: unknown;
  created_at: string;
  updated_at: string;
}

interface StoredStashEntry {
  entry_key: string;
  tags: string[];
  project: string | null;
  size_bytes: number;
  encrypted_value: unknown;
  created_at: string;
  updated_at: string;
}

interface LocalStoreData {
  contexts: Record<string, StoredContext>;
  stash: Record<string, StoredStashEntry>;
  next_slot_number: number;
}

export class A2crLocalStore {
  constructor(private readonly config: A2crConfig) {}

  async getAccountLimits(): Promise<Record<string, unknown>> {
    const data = await this.readStore();
    return {
      storage_mode: "local",
      requires_api_key: false,
      local_store_path: this.config.localStorePath,
      active_context_count: Object.keys(data.contexts).length,
      workstash_entry_count: Object.keys(data.stash).length,
      max_body_bytes: null,
      workstash_quota_bytes: null,
      workstash_max_entry_bytes: null,
      retention: "manual",
      note: "Claude Desktop MCPB saves WorkBaton and WorkStash data to this local store and does not upload saved content.",
    };
  }

  async listContexts(): Promise<Array<Record<string, unknown>>> {
    const data = await this.readStore();
    return Object.values(data.contexts)
      .sort((left, right) => right.updated_at.localeCompare(left.updated_at))
      .map((item) => ({
        slot_name: item.slot_name,
        slot_number: item.slot_number,
        original_length: item.original_length,
        compressed_tokens: item.compressed_tokens,
        model_source: item.model_source,
        storage_mode: "local",
        created_at: item.created_at,
        updated_at: item.updated_at,
      }));
  }

  async saveContext(body: Record<string, unknown>): Promise<Record<string, unknown>> {
    const slotName = body.slot_name;
    if (typeof slotName !== "string" || !slotName.trim()) {
      return { status: "validation_error", message: "slot_name is required" };
    }
    const data = await this.readStore();
    const now = new Date().toISOString();
    const existing = data.contexts[slotName];
    const requestedSlotNumber = typeof body.slot_number === "number" ? body.slot_number : null;
    const slotNumber = requestedSlotNumber ?? existing?.slot_number ?? data.next_slot_number++;
    for (const [candidateName, candidate] of Object.entries(data.contexts)) {
      if (candidateName !== slotName && candidate.slot_number === slotNumber) {
        delete data.contexts[candidateName];
      }
    }

    data.contexts[slotName] = {
      slot_name: slotName,
      slot_number: slotNumber,
      original_length: numberOrNull(body.original_length),
      compressed_tokens: numberOrNull(body.compressed_tokens),
      model_source: stringOrNull(body.model_source),
      encrypted_content: body.encrypted_content,
      created_at: existing?.created_at ?? now,
      updated_at: now,
    };
    await this.writeStore(data);
    return {
      status: "saved",
      storage_mode: "local",
      slot_name: slotName,
      slot_number: slotNumber,
    };
  }

  async loadContextByName(slotName: string): Promise<Record<string, unknown>> {
    const data = await this.readStore();
    const item = data.contexts[slotName];
    if (!item) {
      throw new A2crHttpError(404, ["code=not_found"]);
    }
    return this.loadedContext(item);
  }

  async loadContextByNumber(slotNumber: number): Promise<Record<string, unknown>> {
    const data = await this.readStore();
    const item = Object.values(data.contexts).find((candidate) => candidate.slot_number === slotNumber);
    if (!item) {
      throw new A2crHttpError(404, ["code=not_found"]);
    }
    return this.loadedContext(item);
  }

  async storeWorkStash(body: Record<string, unknown>): Promise<Record<string, unknown>> {
    const entryKey = body.entry_key;
    if (typeof entryKey !== "string" || !entryKey.trim()) {
      return { status: "validation_error", message: "entry_key is required" };
    }
    const data = await this.readStore();
    const now = new Date().toISOString();
    const existing = data.stash[entryKey];
    const tags = Array.isArray(body.tags) ? body.tags.filter((tag): tag is string => typeof tag === "string") : [];
    const sizeBytes = typeof body.size_bytes === "number" ? body.size_bytes : 0;
    data.stash[entryKey] = {
      entry_key: entryKey,
      tags,
      project: stringOrNull(body.project),
      size_bytes: sizeBytes,
      encrypted_value: body.encrypted_value,
      created_at: existing?.created_at ?? now,
      updated_at: now,
    };
    await this.writeStore(data);
    return {
      status: "stored",
      storage_mode: "local",
      entry_key: entryKey,
      tags,
      size_bytes: sizeBytes,
      project: stringOrNull(body.project),
      updated_at: now,
    };
  }

  async getWorkStash(entryKey: string): Promise<Record<string, unknown>> {
    const data = await this.readStore();
    const item = data.stash[entryKey];
    if (!item) {
      throw new A2crHttpError(404, ["code=not_found"]);
    }
    return {
      status: "loaded",
      storage_mode: "local",
      entry_key: item.entry_key,
      tags: item.tags,
      project: item.project,
      size_bytes: item.size_bytes,
      encryption_mode: "client",
      value: null,
      encrypted_value: item.encrypted_value,
      created_at: item.created_at,
      updated_at: item.updated_at,
    };
  }

  async listWorkStash(tagFilter?: string | null): Promise<Record<string, unknown>> {
    const data = await this.readStore();
    const entries = Object.values(data.stash)
      .filter((item) => !tagFilter || item.tags.includes(tagFilter))
      .sort((left, right) => right.updated_at.localeCompare(left.updated_at))
      .map((item) => ({
        entry_key: item.entry_key,
        tags: item.tags,
        project: item.project,
        size_bytes: item.size_bytes,
        storage_mode: "local",
        created_at: item.created_at,
        updated_at: item.updated_at,
      }));
    return {
      status: "ok",
      storage_mode: "local",
      entries,
      entry_count: entries.length,
      total_size_bytes: entries.reduce((total, item) => total + item.size_bytes, 0),
      quota_bytes: null,
      entry_limit: null,
      cleanup_hint: "Delete WorkStash entries that are no longer referenced or useful.",
    };
  }

  async deleteWorkStash(entryKey: string): Promise<Record<string, unknown>> {
    const data = await this.readStore();
    if (!data.stash[entryKey]) {
      throw new A2crHttpError(404, ["code=not_found"]);
    }
    delete data.stash[entryKey];
    await this.writeStore(data);
    return {
      status: "deleted",
      storage_mode: "local",
      entry_key: entryKey,
    };
  }

  private loadedContext(item: StoredContext): Record<string, unknown> {
    return {
      slot_name: item.slot_name,
      slot_number: item.slot_number,
      original_length: item.original_length,
      compressed_tokens: item.compressed_tokens,
      model_source: item.model_source,
      storage_mode: "local",
      encryption_mode: "client",
      content: null,
      encrypted_content: item.encrypted_content,
      created_at: item.created_at,
      updated_at: item.updated_at,
    };
  }

  private async readStore(): Promise<LocalStoreData> {
    try {
      const parsed = JSON.parse(await readFile(this.config.localStorePath, "utf8")) as unknown;
      if (isLocalStoreData(parsed)) {
        return parsed;
      }
      return emptyStore();
    } catch (error) {
      if (isNodeError(error) && error.code === "ENOENT") {
        return emptyStore();
      }
      throw error;
    }
  }

  private async writeStore(data: LocalStoreData): Promise<void> {
    await mkdir(dirname(this.config.localStorePath), { recursive: true });
    await writeFile(this.config.localStorePath, `${JSON.stringify(data, null, 2)}\n`, "utf8");
  }
}

function emptyStore(): LocalStoreData {
  return { contexts: {}, stash: {}, next_slot_number: 1 };
}

function isLocalStoreData(value: unknown): value is LocalStoreData {
  if (
    value !== null &&
    typeof value === "object" &&
    !Array.isArray(value) &&
    typeof (value as LocalStoreData).contexts === "object" &&
    (value as LocalStoreData).contexts !== null &&
    typeof (value as LocalStoreData).next_slot_number === "number"
  ) {
    const data = value as LocalStoreData;
    if (typeof data.stash !== "object" || data.stash === null) {
      data.stash = {};
    }
    return true;
  }
  return false;
}

function numberOrNull(value: unknown): number | null {
  return typeof value === "number" ? value : null;
}

function stringOrNull(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

function isNodeError(error: unknown): error is NodeJS.ErrnoException {
  return error instanceof Error && "code" in error;
}
