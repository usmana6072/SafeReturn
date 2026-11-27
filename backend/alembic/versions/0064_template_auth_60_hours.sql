-- Keep each function's owner, ACL, search_path, and all role/session guards.
-- Replace only the existing template-action signed-AMR window.
DO $migration$
DECLARE target regprocedure; source text; updated text;
BEGIN
 FOREACH target IN ARRAY ARRAY[
  'public.sr_template_draft_service_v33(uuid,bigint,text,jsonb)'::regprocedure,
  'public.sr_template_preview_admit(uuid,bigint,text,text)'::regprocedure,
  'public.sr_template_lifecycle(uuid,bigint,text,jsonb)'::regprocedure
 ] LOOP
  source := pg_get_functiondef(target);
  updated := replace(replace(source, '-amr>1200', '-amr>216000'), '-amr>300', '-amr>216000');
  IF position('sr_is_staff' IN source)=0
     OR position('sr_account_session_state' IN source)=0
     OR position('-amr>216000' IN replace(updated,' ',''))=0 THEN
   RAISE EXCEPTION 'Unexpected template authentication policy for %; review before changing', target;
  END IF;
  IF updated<>source THEN EXECUTE updated; END IF;
 END LOOP;
END $migration$;
