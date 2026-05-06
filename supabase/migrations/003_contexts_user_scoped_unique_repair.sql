BEGIN;

-- Repair older deployments that may still have single-column unique constraints
-- from the local MVP schema. WorkBaton slot names and fixed slot numbers must be
-- unique per user, not globally across all users.
DO $$
DECLARE
  r record;
BEGIN
  FOR r IN
    SELECT conname
    FROM pg_constraint
    WHERE conrelid = 'public.contexts'::regclass
      AND contype = 'u'
      AND pg_get_constraintdef(oid) IN ('UNIQUE (slot_name)', 'UNIQUE (slot_number)')
  LOOP
    EXECUTE format('ALTER TABLE public.contexts DROP CONSTRAINT %I', r.conname);
  END LOOP;

  FOR r IN
    SELECT indexrelid::regclass AS index_name
    FROM pg_index
    WHERE indrelid = 'public.contexts'::regclass
      AND indisunique
      AND NOT EXISTS (
        SELECT 1
        FROM pg_constraint c
        WHERE c.conindid = pg_index.indexrelid
      )
      AND (
        ARRAY(
          SELECT a.attname
          FROM unnest(indkey) WITH ORDINALITY AS k(attnum, ord)
          JOIN pg_attribute a
            ON a.attrelid = indrelid
           AND a.attnum = k.attnum
          ORDER BY k.ord
        ) = ARRAY['slot_name']
        OR
        ARRAY(
          SELECT a.attname
          FROM unnest(indkey) WITH ORDINALITY AS k(attnum, ord)
          JOIN pg_attribute a
            ON a.attrelid = indrelid
           AND a.attnum = k.attnum
          ORDER BY k.ord
        ) = ARRAY['slot_number']
      )
  LOOP
    EXECUTE format('DROP INDEX IF EXISTS %s', r.index_name);
  END LOOP;
END
$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conrelid = 'public.contexts'::regclass
      AND contype = 'u'
      AND pg_get_constraintdef(oid) = 'UNIQUE (user_id, slot_name)'
  ) THEN
    ALTER TABLE public.contexts
      ADD CONSTRAINT contexts_user_id_slot_name_key UNIQUE (user_id, slot_name);
  END IF;

  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conrelid = 'public.contexts'::regclass
      AND contype = 'u'
      AND pg_get_constraintdef(oid) = 'UNIQUE (user_id, slot_number)'
  ) THEN
    ALTER TABLE public.contexts
      ADD CONSTRAINT contexts_user_id_slot_number_key UNIQUE (user_id, slot_number);
  END IF;
END
$$;

CREATE INDEX IF NOT EXISTS contexts_user_expires_idx ON public.contexts(user_id, expires_at);
CREATE INDEX IF NOT EXISTS contexts_user_slot_number_idx ON public.contexts(user_id, slot_number);

COMMIT;
