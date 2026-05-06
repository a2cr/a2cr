BEGIN;

ALTER TABLE public.contexts
  ADD COLUMN IF NOT EXISTS encryption_mode text NOT NULL DEFAULT 'client',
  ADD COLUMN IF NOT EXISTS encryption_version integer NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS encryption_metadata jsonb;

DELETE FROM public.contexts
WHERE encryption_mode <> 'client';

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'contexts_encryption_mode_check'
  ) THEN
    ALTER TABLE public.contexts
      ADD CONSTRAINT contexts_encryption_mode_check
      CHECK (encryption_mode = 'client');
  END IF;
END
$$;

COMMIT;
