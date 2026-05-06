BEGIN;

DELETE FROM public.contexts
WHERE encryption_mode <> 'client';

ALTER TABLE public.contexts
  ALTER COLUMN encryption_mode SET DEFAULT 'client';

ALTER TABLE public.contexts
  DROP CONSTRAINT IF EXISTS contexts_encryption_mode_check;

ALTER TABLE public.contexts
  ADD CONSTRAINT contexts_encryption_mode_check
  CHECK (encryption_mode = 'client');

COMMIT;
