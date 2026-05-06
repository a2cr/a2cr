BEGIN;

CREATE TABLE IF NOT EXISTS public.work_threads (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  title text NOT NULL CHECK (length(title) BETWEEN 1 AND 120),
  purpose text,
  status text NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'blocked', 'completed', 'archived')),
  loop_status text NOT NULL DEFAULT 'ok'
    CHECK (loop_status IN ('ok', 'warning', 'blocked')),
  final_slot_name text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.work_thread_messages (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  thread_id uuid NOT NULL REFERENCES public.work_threads(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  content text NOT NULL,
  content_hash text NOT NULL,
  message_type text NOT NULL
    CHECK (message_type IN ('note', 'question', 'answer', 'decision', 'handoff', 'blocked', 'result')),
  parent_message_id uuid,
  consultation_id text,
  requires_response boolean NOT NULL DEFAULT false,
  target_agent_name text,
  response_deadline timestamptz,
  idempotency_key text,
  agent_name text,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (id, created_at),
  CHECK (idempotency_key IS NULL OR length(idempotency_key) <= 120)
);

CREATE INDEX IF NOT EXISTS work_threads_user_updated_idx
  ON public.work_threads(user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS work_thread_messages_thread_created_idx
  ON public.work_thread_messages(thread_id, created_at ASC);
CREATE INDEX IF NOT EXISTS work_thread_messages_idempotency_idx
  ON public.work_thread_messages(thread_id, idempotency_key)
  WHERE idempotency_key IS NOT NULL;
CREATE INDEX IF NOT EXISTS work_thread_messages_content_hash_idx
  ON public.work_thread_messages(thread_id, content_hash);
CREATE INDEX IF NOT EXISTS work_thread_messages_unread_idx
  ON public.work_thread_messages(thread_id, created_at DESC)
  WHERE requires_response;

CREATE TABLE IF NOT EXISTS public.work_thread_tasks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  thread_id uuid NOT NULL REFERENCES public.work_threads(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  title text NOT NULL,
  status text NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'claimed', 'completed', 'failed')),
  lease_owner text,
  lease_expires_at timestamptz,
  result_message_id uuid,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS work_thread_tasks_claim_idx
  ON public.work_thread_tasks(user_id, status, lease_expires_at, created_at);

CREATE TABLE IF NOT EXISTS public.work_thread_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  thread_id uuid NOT NULL REFERENCES public.work_threads(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  status text NOT NULL CHECK (status IN ('success', 'timeout', 'failed')),
  reason text,
  created_at timestamptz NOT NULL DEFAULT now()
);

DROP TRIGGER IF EXISTS work_threads_touch_updated_at ON public.work_threads;
CREATE TRIGGER work_threads_touch_updated_at
BEFORE UPDATE ON public.work_threads
FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();

DROP TRIGGER IF EXISTS work_thread_tasks_touch_updated_at ON public.work_thread_tasks;
CREATE TRIGGER work_thread_tasks_touch_updated_at
BEFORE UPDATE ON public.work_thread_tasks
FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();

ALTER TABLE public.work_threads ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.work_thread_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.work_thread_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.work_thread_runs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS users_own_work_threads ON public.work_threads;
CREATE POLICY users_own_work_threads ON public.work_threads
  FOR ALL
  USING (user_id = app.current_user_id())
  WITH CHECK (user_id = app.current_user_id());

DROP POLICY IF EXISTS users_own_work_thread_messages ON public.work_thread_messages;
CREATE POLICY users_own_work_thread_messages ON public.work_thread_messages
  FOR ALL
  USING (user_id = app.current_user_id())
  WITH CHECK (user_id = app.current_user_id());

DROP POLICY IF EXISTS users_own_work_thread_tasks ON public.work_thread_tasks;
CREATE POLICY users_own_work_thread_tasks ON public.work_thread_tasks
  FOR ALL
  USING (user_id = app.current_user_id())
  WITH CHECK (user_id = app.current_user_id());

DROP POLICY IF EXISTS users_own_work_thread_runs ON public.work_thread_runs;
CREATE POLICY users_own_work_thread_runs ON public.work_thread_runs
  FOR ALL
  USING (user_id = app.current_user_id())
  WITH CHECK (user_id = app.current_user_id());

GRANT SELECT, INSERT, UPDATE, DELETE ON
  public.work_threads,
  public.work_thread_messages,
  public.work_thread_tasks,
  public.work_thread_runs
TO a2cr_app;

COMMIT;
