BEGIN;

CREATE UNIQUE INDEX IF NOT EXISTS work_thread_messages_idempotency_unique_idx
  ON public.work_thread_messages(thread_id, idempotency_key)
  WHERE idempotency_key IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS work_thread_messages_content_hash_unique_idx
  ON public.work_thread_messages(thread_id, content_hash);

INSERT INTO app.schema_migrations (migration_id)
VALUES ('007_workthreads_message_uniqueness')
ON CONFLICT (migration_id) DO NOTHING;

COMMIT;
