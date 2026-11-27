-- Keep the lifecycle function's owner, ACL, search_path, and all role/session guards.
-- Replace only its existing 20-minute signed-AMR window for template actions.
DO $migration$
DECLARE source text; updated text;
BEGIN
 source := pg_get_functiondef('public.sr_template_lifecycle(uuid,bigint,text,jsonb)'::regprocedure);
 updated := replace(source, '-amr>1200', '-amr>216000');
 IF position('sr_template_registry_gate' IN source)=0
    OR position('sr_account_session_state' IN source)=0
    OR position('-amr>216000' IN replace(updated,' ',''))=0 THEN
  RAISE EXCEPTION 'Unexpected template lifecycle authentication policy; review before changing';
 END IF;
 IF updated<>source THEN EXECUTE updated; END IF;
END $migration$;
