BEGIN;

CREATE SCHEMA IF NOT EXISTS app;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'a2cr_app') THEN
    CREATE ROLE a2cr_app LOGIN;
  END IF;
END
$$;

CREATE OR REPLACE FUNCTION app.current_user_id()
RETURNS uuid
LANGUAGE sql
STABLE
AS $$
  SELECT NULLIF(current_setting('app.user_id', true), '')::uuid
$$;

CREATE OR REPLACE FUNCTION app.touch_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

CREATE TABLE IF NOT EXISTS public.user_profiles (
  user_id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  plan text NOT NULL DEFAULT 'free' CHECK (plan IN ('free', 'pro')),
  context_detail_level text NOT NULL DEFAULT 'compact'
    CHECK (context_detail_level IN ('compact', 'detailed')),
  default_retention_seconds integer NOT NULL DEFAULT 86400,
  preferred_locale text NOT NULL DEFAULT 'auto',
  response_language text NOT NULL DEFAULT 'auto',
  timezone text NOT NULL DEFAULT 'UTC',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (plan = 'pro' OR context_detail_level = 'compact'),
  CHECK (
    (plan = 'free' AND default_retention_seconds IN (900, 1800, 3600, 10800, 21600, 43200, 86400)) OR
    (plan = 'pro' AND default_retention_seconds IN (900, 1800, 3600, 10800, 21600, 43200, 86400, 259200, 604800, 864000, 1209600, 2592000))
  )
);

CREATE TABLE IF NOT EXISTS public.contexts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  slot_name text NOT NULL CHECK (slot_name ~ '^[A-Za-z0-9_-]{1,64}$'),
  slot_number integer NOT NULL CHECK (slot_number >= 1),
  content text NOT NULL,
  detail_level text NOT NULL DEFAULT 'compact'
    CHECK (detail_level IN ('compact', 'detailed')),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz NOT NULL,
  size_bytes integer NOT NULL CHECK (size_bytes >= 0),
  original_tokens integer,
  compressed_tokens integer NOT NULL CHECK (compressed_tokens >= 0),
  saved_tokens integer NOT NULL DEFAULT 0,
  load_count integer NOT NULL DEFAULT 0 CHECK (load_count >= 0),
  model_source text,
  encryption_mode text NOT NULL DEFAULT 'client' CHECK (encryption_mode = 'client'),
  encryption_version integer NOT NULL DEFAULT 1,
  encryption_metadata jsonb,
  encryption_key_version integer NOT NULL DEFAULT 1,
  UNIQUE (user_id, slot_name),
  UNIQUE (user_id, slot_number)
);

CREATE TABLE IF NOT EXISTS public.stats (
  user_id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  total_saves integer NOT NULL DEFAULT 0 CHECK (total_saves >= 0),
  total_loads integer NOT NULL DEFAULT 0 CHECK (total_loads >= 0),
  total_deletes integer NOT NULL DEFAULT 0 CHECK (total_deletes >= 0),
  total_tokens_saved integer NOT NULL DEFAULT 0 CHECK (total_tokens_saved >= 0),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.api_keys (
  user_id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  key_hash text NOT NULL,
  key_prefix text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  last_used_at timestamptz,
  last_used_ip_hash text,
  revoked_at timestamptz
);

CREATE TABLE IF NOT EXISTS public.access_logs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  action text NOT NULL,
  slot_name text,
  client_type text NOT NULL,
  result text NOT NULL,
  error_code text,
  size_bytes integer,
  request_id text,
  ip_hash text,
  user_agent_hash text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS api_keys_hash_idx ON public.api_keys(key_hash);
CREATE INDEX IF NOT EXISTS contexts_user_expires_idx ON public.contexts(user_id, expires_at);
CREATE INDEX IF NOT EXISTS contexts_user_slot_number_idx ON public.contexts(user_id, slot_number);
CREATE INDEX IF NOT EXISTS access_logs_user_created_idx ON public.access_logs(user_id, created_at DESC);

DROP TRIGGER IF EXISTS user_profiles_touch_updated_at ON public.user_profiles;
CREATE TRIGGER user_profiles_touch_updated_at
BEFORE UPDATE ON public.user_profiles
FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();

DROP TRIGGER IF EXISTS contexts_touch_updated_at ON public.contexts;
CREATE TRIGGER contexts_touch_updated_at
BEFORE UPDATE ON public.contexts
FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();

DROP TRIGGER IF EXISTS stats_touch_updated_at ON public.stats;
CREATE TRIGGER stats_touch_updated_at
BEFORE UPDATE ON public.stats
FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();

CREATE OR REPLACE FUNCTION app.resolve_api_key(p_key_hash text, p_ip_hash text)
RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $$
DECLARE
  v_user_id uuid;
BEGIN
  SELECT user_id INTO v_user_id
  FROM public.api_keys
  WHERE key_hash = p_key_hash
    AND revoked_at IS NULL;

  IF v_user_id IS NOT NULL THEN
    UPDATE public.api_keys
    SET last_used_at = now(),
        last_used_ip_hash = p_ip_hash
    WHERE user_id = v_user_id;
  END IF;

  RETURN v_user_id;
END;
$$;

CREATE OR REPLACE FUNCTION app.record_context_save(
  p_user_id uuid,
  p_saved_tokens integer
)
RETURNS void
LANGUAGE sql
AS $$
  INSERT INTO public.stats (user_id, total_saves, total_tokens_saved)
  VALUES (p_user_id, 1, GREATEST(p_saved_tokens, 0))
  ON CONFLICT (user_id) DO UPDATE
  SET total_saves = public.stats.total_saves + 1,
      total_tokens_saved = public.stats.total_tokens_saved + GREATEST(p_saved_tokens, 0),
      updated_at = now()
$$;

CREATE OR REPLACE FUNCTION app.record_context_load(p_user_id uuid)
RETURNS void
LANGUAGE sql
AS $$
  INSERT INTO public.stats (user_id, total_loads)
  VALUES (p_user_id, 1)
  ON CONFLICT (user_id) DO UPDATE
  SET total_loads = public.stats.total_loads + 1,
      updated_at = now()
$$;

CREATE OR REPLACE FUNCTION app.record_context_delete(p_user_id uuid)
RETURNS void
LANGUAGE sql
AS $$
  INSERT INTO public.stats (user_id, total_deletes)
  VALUES (p_user_id, 1)
  ON CONFLICT (user_id) DO UPDATE
  SET total_deletes = public.stats.total_deletes + 1,
      updated_at = now()
$$;

CREATE OR REPLACE FUNCTION app.expire_contexts()
RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $$
DECLARE
  v_deleted_count integer;
BEGIN
  WITH expired AS (
    SELECT id, user_id, slot_name
    FROM public.contexts
    WHERE expires_at <= now()
  ),
  logged AS (
    INSERT INTO public.access_logs (user_id, action, slot_name, client_type, result)
    SELECT user_id, 'context.expire', slot_name, 'system', 'success'
    FROM expired
    RETURNING 1
  ),
  deleted AS (
    DELETE FROM public.contexts c
    USING expired
    WHERE c.id = expired.id
      AND EXISTS (SELECT 1 FROM logged)
    RETURNING 1
  )
  SELECT count(*) INTO v_deleted_count FROM deleted;

  RETURN v_deleted_count;
END;
$$;

ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.contexts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.access_logs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS users_read_profile ON public.user_profiles;
CREATE POLICY users_read_profile ON public.user_profiles
  FOR SELECT
  USING (user_id = app.current_user_id());

DROP POLICY IF EXISTS users_create_free_profile ON public.user_profiles;
CREATE POLICY users_create_free_profile ON public.user_profiles
  FOR INSERT
  WITH CHECK (user_id = app.current_user_id() AND plan = 'free');

DROP POLICY IF EXISTS users_update_profile ON public.user_profiles;
CREATE POLICY users_update_profile ON public.user_profiles
  FOR UPDATE
  USING (user_id = app.current_user_id())
  WITH CHECK (user_id = app.current_user_id());

DROP POLICY IF EXISTS users_own_slots ON public.contexts;
CREATE POLICY users_own_slots ON public.contexts
  FOR ALL
  USING (user_id = app.current_user_id())
  WITH CHECK (user_id = app.current_user_id());

DROP POLICY IF EXISTS users_own_stats ON public.stats;
CREATE POLICY users_own_stats ON public.stats
  FOR ALL
  USING (user_id = app.current_user_id())
  WITH CHECK (user_id = app.current_user_id());

DROP POLICY IF EXISTS users_own_api_key ON public.api_keys;
CREATE POLICY users_own_api_key ON public.api_keys
  FOR ALL
  USING (user_id = app.current_user_id())
  WITH CHECK (user_id = app.current_user_id());

DROP POLICY IF EXISTS users_own_access_logs ON public.access_logs;
CREATE POLICY users_own_access_logs ON public.access_logs
  FOR ALL
  USING (user_id = app.current_user_id())
  WITH CHECK (user_id = app.current_user_id());

REVOKE ALL ON SCHEMA public FROM a2cr_app;
GRANT USAGE ON SCHEMA public, app TO a2cr_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON
  public.user_profiles,
  public.contexts,
  public.stats,
  public.api_keys,
  public.access_logs
TO a2cr_app;
GRANT EXECUTE ON FUNCTION app.current_user_id() TO a2cr_app;
GRANT EXECUTE ON FUNCTION app.resolve_api_key(text, text) TO a2cr_app;
GRANT EXECUTE ON FUNCTION app.record_context_save(uuid, integer) TO a2cr_app;
GRANT EXECUTE ON FUNCTION app.record_context_load(uuid) TO a2cr_app;
GRANT EXECUTE ON FUNCTION app.record_context_delete(uuid) TO a2cr_app;
GRANT EXECUTE ON FUNCTION app.expire_contexts() TO a2cr_app;

REVOKE ALL ON FUNCTION app.resolve_api_key(text, text) FROM PUBLIC;

COMMIT;
