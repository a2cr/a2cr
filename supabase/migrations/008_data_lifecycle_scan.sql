BEGIN;

CREATE OR REPLACE FUNCTION app.data_lifecycle_scan(
  p_access_log_retention interval DEFAULT interval '30 days'
)
RETURNS TABLE (
  expired_contexts bigint,
  legacy_contexts bigint,
  old_access_logs bigint,
  contexts_without_profile bigint,
  stats_without_profile bigint,
  api_keys_without_profile bigint,
  access_logs_without_profile bigint,
  work_threads_without_profile bigint,
  work_thread_messages_without_thread bigint,
  work_thread_tasks_without_thread bigint,
  work_thread_runs_without_thread bigint,
  work_thread_messages_user_mismatch bigint,
  work_thread_tasks_user_mismatch bigint,
  work_thread_runs_user_mismatch bigint,
  work_threads_final_slot_missing_context bigint
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $$
  SELECT
    (SELECT count(*) FROM public.contexts WHERE expires_at <= now()) AS expired_contexts,
    (SELECT count(*) FROM public.contexts WHERE encryption_mode <> 'client') AS legacy_contexts,
    (SELECT count(*) FROM public.access_logs WHERE created_at < now() - p_access_log_retention) AS old_access_logs,
    (
      SELECT count(*)
      FROM public.contexts c
      LEFT JOIN public.user_profiles p ON p.user_id = c.user_id
      WHERE p.user_id IS NULL
    ) AS contexts_without_profile,
    (
      SELECT count(*)
      FROM public.stats s
      LEFT JOIN public.user_profiles p ON p.user_id = s.user_id
      WHERE p.user_id IS NULL
    ) AS stats_without_profile,
    (
      SELECT count(*)
      FROM public.api_keys k
      LEFT JOIN public.user_profiles p ON p.user_id = k.user_id
      WHERE p.user_id IS NULL
    ) AS api_keys_without_profile,
    (
      SELECT count(*)
      FROM public.access_logs l
      LEFT JOIN public.user_profiles p ON p.user_id = l.user_id
      WHERE p.user_id IS NULL
    ) AS access_logs_without_profile,
    (
      SELECT count(*)
      FROM public.work_threads t
      LEFT JOIN public.user_profiles p ON p.user_id = t.user_id
      WHERE p.user_id IS NULL
    ) AS work_threads_without_profile,
    (
      SELECT count(*)
      FROM public.work_thread_messages m
      LEFT JOIN public.work_threads t ON t.id = m.thread_id
      WHERE t.id IS NULL
    ) AS work_thread_messages_without_thread,
    (
      SELECT count(*)
      FROM public.work_thread_tasks task
      LEFT JOIN public.work_threads t ON t.id = task.thread_id
      WHERE t.id IS NULL
    ) AS work_thread_tasks_without_thread,
    (
      SELECT count(*)
      FROM public.work_thread_runs r
      LEFT JOIN public.work_threads t ON t.id = r.thread_id
      WHERE t.id IS NULL
    ) AS work_thread_runs_without_thread,
    (
      SELECT count(*)
      FROM public.work_thread_messages m
      JOIN public.work_threads t ON t.id = m.thread_id
      WHERE m.user_id <> t.user_id
    ) AS work_thread_messages_user_mismatch,
    (
      SELECT count(*)
      FROM public.work_thread_tasks task
      JOIN public.work_threads t ON t.id = task.thread_id
      WHERE task.user_id <> t.user_id
    ) AS work_thread_tasks_user_mismatch,
    (
      SELECT count(*)
      FROM public.work_thread_runs r
      JOIN public.work_threads t ON t.id = r.thread_id
      WHERE r.user_id <> t.user_id
    ) AS work_thread_runs_user_mismatch,
    (
      SELECT count(*)
      FROM public.work_threads t
      LEFT JOIN public.contexts c
        ON c.user_id = t.user_id
       AND c.slot_name = t.final_slot_name
      WHERE t.final_slot_name IS NOT NULL
        AND c.id IS NULL
    ) AS work_threads_final_slot_missing_context
$$;

GRANT EXECUTE ON FUNCTION app.data_lifecycle_scan(interval) TO a2cr_app;
REVOKE ALL ON FUNCTION app.data_lifecycle_scan(interval) FROM PUBLIC;

INSERT INTO app.schema_migrations (migration_id)
VALUES ('008_data_lifecycle_scan')
ON CONFLICT (migration_id) DO NOTHING;

COMMIT;
