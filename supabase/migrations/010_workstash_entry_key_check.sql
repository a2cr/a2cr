BEGIN;

ALTER TABLE public.work_stash_entries
  DROP CONSTRAINT IF EXISTS work_stash_entries_entry_key_check;

ALTER TABLE public.work_stash_entries
  DROP CONSTRAINT IF EXISTS work_stash_entries_entry_key_format_check;

DO $$
DECLARE
  v_constraint_name text;
BEGIN
  SELECT conname INTO v_constraint_name
  FROM pg_constraint
  WHERE conrelid = 'public.work_stash_entries'::regclass
    AND contype = 'c'
    AND pg_get_constraintdef(oid) LIKE '%entry_key%~%';

  IF v_constraint_name IS NOT NULL THEN
    EXECUTE format(
      'ALTER TABLE public.work_stash_entries DROP CONSTRAINT %I',
      v_constraint_name
    );
  END IF;
END;
$$;

ALTER TABLE public.work_stash_entries
  ADD CONSTRAINT work_stash_entries_entry_key_format_check
  CHECK (
    length(entry_key) BETWEEN 1 AND 256
    AND entry_key ~ '^[A-Za-z0-9_.:-]+$'
  );

INSERT INTO app.schema_migrations (migration_id)
VALUES ('010_workstash_entry_key_check')
ON CONFLICT (migration_id) DO NOTHING;

COMMIT;
