BEGIN;

CREATE TABLE IF NOT EXISTS app.schema_migrations (
  migration_id text PRIMARY KEY,
  applied_at timestamptz NOT NULL DEFAULT now()
);

INSERT INTO app.schema_migrations (migration_id)
VALUES
  ('001_base_schema'),
  ('002_workthreads'),
  ('003_contexts_user_scoped_unique_repair'),
  ('004_contexts_encryption_mode'),
  ('005_contexts_client_encrypted_only'),
  ('006_db_resilience_baseline')
ON CONFLICT (migration_id) DO NOTHING;

CREATE INDEX IF NOT EXISTS access_logs_user_action_created_idx
  ON public.access_logs(user_id, action, created_at DESC);

CREATE INDEX IF NOT EXISTS contexts_expires_idx
  ON public.contexts(expires_at);

CREATE OR REPLACE FUNCTION app.prune_access_logs(
  p_older_than interval,
  p_batch_size integer DEFAULT 1000
)
RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $$
DECLARE
  v_deleted_count integer;
BEGIN
  WITH doomed AS (
    SELECT id
    FROM public.access_logs
    WHERE created_at < now() - p_older_than
    ORDER BY created_at
    LIMIT LEAST(GREATEST(p_batch_size, 1), 10000)
  ),
  deleted AS (
    DELETE FROM public.access_logs l
    USING doomed
    WHERE l.id = doomed.id
    RETURNING 1
  )
  SELECT count(*) INTO v_deleted_count FROM deleted;

  RETURN v_deleted_count;
END;
$$;

GRANT SELECT, INSERT ON app.schema_migrations TO a2cr_app;
GRANT EXECUTE ON FUNCTION app.prune_access_logs(interval, integer) TO a2cr_app;

COMMIT;
