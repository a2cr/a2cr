export type Plan = "free" | "pro";
export type DetailLevel = "compact" | "detailed";
export type EncryptionMode = "client";

export type DashboardProfile = {
  user_id: string;
  plan: Plan | string;
  context_detail_level: DetailLevel | string;
  default_retention_seconds: number;
  preferred_locale: string;
  response_language: string;
  timezone: string;
  created_at: string;
  updated_at: string;
};

export type DashboardContext = {
  slot_name: string;
  slot_number: number;
  encryption_mode: EncryptionMode | string;
  created_at: string;
  updated_at: string;
  expires_at: string;
  size_bytes: number;
  compressed_tokens: number;
  saved_tokens: number;
  detail_level: string;
  model_source: string | null;
  load_count: number;
  resume_context_call: string;
  resume_prompt: string;
};

export type DashboardStats = {
  total_saves: number;
  total_loads: number;
  total_deletes: number;
  total_tokens_saved: number;
  active_slots: number;
};

export type DashboardAccessLog = {
  action: string;
  slot_name: string | null;
  client_type: string;
  result: string;
  error_code: string | null;
  size_bytes: number | null;
  request_id: string | null;
  created_at: string;
};

export type DashboardApiKey = {
  key_prefix: string;
  created_at: string;
  last_used_at: string | null;
  revoked_at: string | null;
};

export type DashboardWorkThread = {
  thread_id: string;
  title: string;
  purpose: string | null;
  status: string;
  loop_status: string;
  final_slot_name: string | null;
  message_count: number;
  task_count: number;
  task_status_counts: Record<string, number>;
  agent_names: string[];
  last_activity_at: string;
  created_at: string;
  updated_at: string;
};

export type CreatedApiKey = {
  api_key: string;
  key_prefix: string;
  created_at: string;
};

export type WorkStashUsage = {
  total_size_bytes: number;
  quota_bytes: number;
  entry_count: number;
  entry_limit: number;
};

export type DashboardData = {
  profile: DashboardProfile;
  contexts: DashboardContext[];
  stats: DashboardStats;
  accessLogs: DashboardAccessLog[];
  apiKey: DashboardApiKey | null;
  workthreads: DashboardWorkThread[];
  workStash: WorkStashUsage | null;
};

export type ProfilePatch = Partial<{
  context_detail_level: DetailLevel;
  default_retention_seconds: number;
  preferred_locale: string;
  response_language: string;
  timezone: string;
}>;
