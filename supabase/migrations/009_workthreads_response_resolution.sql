BEGIN;

ALTER TABLE public.work_thread_messages
  ADD COLUMN IF NOT EXISTS resolved_at timestamptz,
  ADD COLUMN IF NOT EXISTS resolved_by_message_id uuid;

CREATE INDEX IF NOT EXISTS work_thread_messages_pending_response_idx
  ON public.work_thread_messages(thread_id, created_at ASC)
  WHERE requires_response AND resolved_at IS NULL;

COMMIT;
