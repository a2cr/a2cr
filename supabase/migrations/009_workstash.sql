BEGIN;

CREATE TABLE IF NOT EXISTS public.work_stash_entries (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  entry_key text NOT NULL CHECK (entry_key ~ '^[A-Za-z0-9_.:-]{1,256}$'),
  encrypted_value text NOT NULL,
  encryption_mode text NOT NULL DEFAULT 'client' CHECK (encryption_mode = 'client'),
  encryption_version integer NOT NULL DEFAULT 1,
  size_bytes integer NOT NULL CHECK (size_bytes >= 0),
  tags text[] NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz NOT NULL,
  last_accessed_at timestamptz,
  UNIQUE (user_id, entry_key)
);

CREATE INDEX IF NOT EXISTS work_stash_entries_user_expires_idx
  ON public.work_stash_entries(user_id, expires_at);

CREATE INDEX IF NOT EXISTS work_stash_entries_user_key_idx
  ON public.work_stash_entries(user_id, entry_key);

CREATE INDEX IF NOT EXISTS work_stash_entries_tags_idx
  ON public.work_stash_entries USING GIN (tags);

DROP TRIGGER IF EXISTS work_stash_entries_touch_updated_at ON public.work_stash_entries;
CREATE TRIGGER work_stash_entries_touch_updated_at
BEFORE UPDATE ON public.work_stash_entries
FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();

CREATE OR REPLACE FUNCTION app.expire_work_stash()
RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $$
DECLARE
  v_deleted_count integer;
BEGIN
  WITH expired AS (
    SELECT id, user_id, entry_key
    FROM public.work_stash_entries
    WHERE expires_at <= now()
  ),
  logged AS (
    INSERT INTO public.access_logs (user_id, action, slot_name, client_type, result)
    SELECT user_id, 'work_stash.expire', entry_key, 'system', 'success'
    FROM expired
    RETURNING 1
  ),
  deleted AS (
    DELETE FROM public.work_stash_entries e
    USING expired
    WHERE e.id = expired.id
      AND EXISTS (SELECT 1 FROM logged)
    RETURNING 1
  )
  SELECT count(*) INTO v_deleted_count FROM deleted;

  RETURN v_deleted_count;
END;
$$;

ALTER TABLE public.work_stash_entries ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS users_own_work_stash ON public.work_stash_entries;
CREATE POLICY users_own_work_stash ON public.work_stash_entries
  FOR ALL
  USING (user_id = app.current_user_id())
  WITH CHECK (user_id = app.current_user_id());

GRANT SELECT, INSERT, UPDATE, DELETE ON
  public.work_stash_entries
TO a2cr_app;

GRANT EXECUTE ON FUNCTION app.expire_work_stash() TO a2cr_app;

COMMIT;
