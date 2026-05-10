BEGIN;

ALTER TABLE public.work_thread_tasks
  ADD COLUMN IF NOT EXISTS failure_reason text;

DO $$
BEGIN
  ALTER TABLE public.work_thread_tasks
    ADD CONSTRAINT work_thread_tasks_failure_reason_length
    CHECK (failure_reason IS NULL OR length(failure_reason) BETWEEN 1 AND 500);
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

COMMIT;
