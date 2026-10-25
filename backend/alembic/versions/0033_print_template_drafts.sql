-- Offline-only additive draft registry. No published templates, asset enrollment,
-- QA authority or checkout bindings can be created by this revision.
CREATE TABLE public.print_templates (
 template_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 key text NOT NULL UNIQUE CHECK (key ~ '^[A-Za-z0-9._-]{3,80}$'),
 name text NOT NULL CHECK (char_length(name) BETWEEN 1 AND 100),
 purpose text NOT NULL CHECK (purpose IN ('lost','ice')),
 lifecycle_status text NOT NULL DEFAULT 'draft' CHECK (lifecycle_status='draft'),
 row_version bigint NOT NULL DEFAULT 1 CHECK (row_version>0),
 created_by uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE public.print_template_revisions (
 revision_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 template_id uuid NOT NULL REFERENCES public.print_templates(template_id) ON DELETE RESTRICT,
 version integer NOT NULL CHECK (version BETWEEN 1 AND 100000),
 status text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','pending_qa')),
 row_version bigint NOT NULL DEFAULT 1 CHECK (row_version>0),
 content jsonb NOT NULL CHECK (jsonb_typeof(content)='object' AND octet_length(content::text)<=32768),
 version_note text NOT NULL CHECK (char_length(version_note) BETWEEN 4 AND 500),
 fingerprint_sha256 char(64) CHECK (fingerprint_sha256 ~ '^[0-9a-f]{64}$'),
 published_at timestamptz CHECK (published_at IS NULL),
 created_by uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
 updated_by uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
 created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(template_id,version),
 CHECK ((status='draft' AND fingerprint_sha256 IS NULL) OR (status='pending_qa' AND fingerprint_sha256 IS NOT NULL))
);
CREATE UNIQUE INDEX uq_print_template_editable_draft ON public.print_template_revisions(template_id) WHERE status='draft';
-- Enrollment has no runtime writer. Actual approved asset provenance is still required.
CREATE TABLE public.print_template_asset_sets (
 asset_set_id uuid PRIMARY KEY,
 font_path text NOT NULL CHECK (char_length(font_path) BETWEEN 1 AND 2048),
 font_sha256 char(64) NOT NULL CHECK (font_sha256 ~ '^[0-9a-f]{64}$'),
 logo_path text NOT NULL CHECK (char_length(logo_path) BETWEEN 1 AND 2048),
 logo_sha256 char(64) NOT NULL CHECK (logo_sha256 ~ '^[0-9a-f]{64}$'),
 review_reference text NOT NULL CHECK (char_length(review_reference) BETWEEN 4 AND 160),
 reviewed_at timestamptz NOT NULL,
 withdrawn_at timestamptz
);
CREATE TABLE public.print_template_preview_commands (
 actor_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
 key_hash char(64) NOT NULL CHECK (key_hash ~ '^[0-9a-f]{64}$'),
 request_hash char(64) NOT NULL CHECK (request_hash ~ '^[0-9a-f]{64}$'),
 PRIMARY KEY(actor_id,key_hash)
);
CREATE TABLE public.print_template_preview_attempts (
 attempt_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 actor_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
 admitted_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX ix_template_preview_rate ON public.print_template_preview_attempts(actor_id,admitted_at);
ALTER TABLE public.print_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.print_template_revisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.print_template_asset_sets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.print_template_preview_commands ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.print_template_preview_attempts ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.print_templates,public.print_template_revisions,public.print_template_asset_sets,public.print_template_preview_commands,public.print_template_preview_attempts FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;

CREATE FUNCTION public.sr_template_content_valid(c jsonb) RETURNS boolean
LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
DECLARE field text; n numeric; item jsonb; expected text[]:=ARRAY[
 'schema_version','renderer','preset','symbol_mm','width_mm','height_mm','qr_x_mm','qr_y_mm',
 'logo_mm','min_pitch_mm','font_pt','header','english_lines','urdu_lines','asset_set_id','material_codes'];
BEGIN
 IF c IS NULL OR jsonb_typeof(c)<>'object' OR (SELECT count(*) FROM jsonb_object_keys(c))<>cardinality(expected)
 OR EXISTS(SELECT 1 FROM jsonb_object_keys(c) k WHERE NOT k=ANY(expected))
 OR c->'schema_version' IS DISTINCT FROM '1'::jsonb OR c->>'renderer' IS DISTINCT FROM 'safereturn-vector-v1' OR c->>'preset' IS DISTINCT FROM 'fixed-footer-v1' THEN RETURN false; END IF;
 FOREACH field IN ARRAY ARRAY['symbol_mm','width_mm','height_mm','qr_x_mm','qr_y_mm','logo_mm','min_pitch_mm','font_pt'] LOOP
  IF jsonb_typeof(c->field)<>'string' OR (c->>field)!~'^[0-9]{1,3}\.[0-9]{2}$' THEN RETURN false; END IF;
  n:=(c->>field)::numeric; IF n<=0 OR n>270 THEN RETURN false; END IF;
 END LOOP;
 IF (c->>'symbol_mm')::numeric NOT BETWEEN 30 AND 100 OR (c->>'width_mm')::numeric NOT BETWEEN 40 AND 190
 OR (c->>'height_mm')::numeric NOT BETWEEN 60 AND 270 OR (c->>'qr_x_mm')::numeric<4 OR (c->>'qr_y_mm')::numeric<18
 OR (c->>'logo_mm')::numeric>6 OR (c->>'logo_mm')::numeric>(c->>'symbol_mm')::numeric*0.15
 OR (c->>'min_pitch_mm')::numeric<0.3 OR (c->>'font_pt')::numeric NOT BETWEEN 8 AND 14
 OR (c->>'qr_x_mm')::numeric+(c->>'symbol_mm')::numeric>(c->>'width_mm')::numeric-4
 OR (c->>'qr_y_mm')::numeric+(c->>'symbol_mm')::numeric>(c->>'height_mm')::numeric-12 THEN RETURN false; END IF;
 IF jsonb_typeof(c->'header')<>'string' OR char_length(c->>'header') NOT BETWEEN 1 AND 50 THEN RETURN false; END IF;
 FOREACH field IN ARRAY ARRAY['english_lines','urdu_lines','material_codes'] LOOP
  IF jsonb_typeof(c->field)<>'array' OR jsonb_array_length(c->field) NOT BETWEEN 1 AND (CASE WHEN field='material_codes' THEN 10 ELSE 4 END) THEN RETURN false; END IF;
  FOR item IN SELECT value FROM jsonb_array_elements(c->field) LOOP
   IF jsonb_typeof(item)<>'string' OR char_length(item#>>'{}') NOT BETWEEN 1 AND 120 THEN RETURN false; END IF;
   IF field='material_codes' AND (item#>>'{}')!~'^[a-z0-9_-]{1,40}$' THEN RETURN false; END IF;
   IF field='urdu_lines' AND (item#>>'{}')~'[A-Za-z0-9]' THEN RETURN false; END IF;
  END LOOP;
 END LOOP;
 IF (c->>'qr_y_mm')::numeric-4-(c->>'font_pt')::numeric*1.5/2.8346456693*(jsonb_array_length(c->'english_lines')+jsonb_array_length(c->'urdu_lines')-1)<4 THEN RETURN false; END IF;
 IF c->'material_codes'<>(SELECT jsonb_agg(v ORDER BY v) FROM (SELECT DISTINCT value v FROM jsonb_array_elements(c->'material_codes')) x) THEN RETURN false; END IF;
 IF jsonb_typeof(c->'asset_set_id')<>'string' OR c->>'asset_set_id' IS NULL THEN RETURN false; END IF;
 PERFORM (c->>'asset_set_id')::uuid;
 -- The API also rejects markup/controls/URI schemes. The helper rejects them at storage.
 IF (c->>'header') ~ '[<>\\{}[:cntrl:]]' OR (c->>'header') ~* '[a-z][a-z0-9+.-]*[[:space:]]*:'
 OR EXISTS(SELECT 1 FROM jsonb_array_elements_text((c->'english_lines')||(c->'urdu_lines')) v WHERE v ~ '[<>\\{}[:cntrl:]]' OR v ~* '[a-z][a-z0-9+.-]*[[:space:]]*:') THEN RETURN false; END IF;
 RETURN true;
EXCEPTION WHEN invalid_text_representation OR numeric_value_out_of_range THEN RETURN false;
END $$;
ALTER TABLE public.print_template_revisions ADD CONSTRAINT ck_template_content CHECK (public.sr_template_content_valid(content));

CREATE FUNCTION public.sr_template_service(sid uuid,amr bigint,action text,payload jsonb) RETURNS jsonb
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE actor uuid:=public.sr_actor_id(); t public.print_templates; r public.print_template_revisions;
 result jsonb; rows jsonb; take integer; after_id uuid; next_id uuid; a public.print_template_asset_sets; is_read boolean:=action IN('list','detail');
BEGIN
 IF public.sr_is_staff(CASE WHEN is_read THEN ARRAY['operations','security_admin','superadmin'] ELSE ARRAY['operations'] END) IS NOT TRUE
 OR NOT EXISTS(SELECT 1 FROM public.sr_account_session_state(sid) s WHERE s.email_verified AND s.mfa_active) THEN RETURN NULL; END IF;
 IF NOT is_read AND (amr IS NULL OR amr<0 OR amr>extract(epoch FROM clock_timestamp()) OR extract(epoch FROM clock_timestamp())-amr>300) THEN RETURN NULL; END IF;
 IF action IS NULL OR action NOT IN('list','detail','create','revision','edit','preview_input','submit') THEN RETURN jsonb_build_object('error','PROVIDER_UNAVAILABLE'); END IF;
 IF payload IS NULL OR jsonb_typeof(payload)<>'object' OR octet_length(payload::text)>32768 THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
 IF action='preview_input' THEN
  -- Deliberately lock-free: no DB locks are held during external PDF processing.
  SELECT * INTO t FROM public.print_templates WHERE template_id=(payload->>'template_id')::uuid;
  SELECT * INTO r FROM public.print_template_revisions WHERE template_id=t.template_id AND revision_id=(payload->>'revision_id')::uuid;
  IF t.template_id IS NULL OR r.revision_id IS NULL THEN RETURN jsonb_build_object('error','NOT_FOUND'); END IF;
  IF payload->>'expected' IS NULL OR (payload->>'expected')::bigint<>r.row_version THEN RETURN jsonb_build_object('error','VERSION_MISMATCH'); END IF;
  SELECT * INTO a FROM public.print_template_asset_sets WHERE asset_set_id=(r.content->>'asset_set_id')::uuid AND withdrawn_at IS NULL;
  IF NOT FOUND THEN RETURN jsonb_build_object('error','PROVIDER_UNAVAILABLE'); END IF;
  RETURN jsonb_build_object('key',t.key,'version',r.version,'purpose',t.purpose,'content',r.content,
   'assets',jsonb_build_object('font',jsonb_build_object('path',a.font_path,'sha256',a.font_sha256),'logo',jsonb_build_object('path',a.logo_path,'sha256',a.logo_sha256)));
 END IF;
 IF action='list' THEN
  take:=COALESCE((payload->>'limit')::integer,20); after_id:=(payload->>'after')::uuid;
  IF take NOT BETWEEN 1 AND 50 THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
  SELECT jsonb_agg(to_jsonb(x)-'created_by' ORDER BY template_id) INTO rows FROM (
   SELECT * FROM public.print_templates WHERE (after_id IS NULL OR template_id>after_id)
   AND (payload->>'purpose' IS NULL OR purpose=payload->>'purpose') AND (payload->>'status' IS NULL OR lifecycle_status=payload->>'status')
   ORDER BY template_id LIMIT take+1) x;
  rows:=COALESCE(rows,'[]'::jsonb);
  IF jsonb_array_length(rows)>take THEN rows:=rows-take; next_id:=(rows->(take-1)->>'template_id')::uuid; END IF;
  RETURN jsonb_build_object('items',rows,'next_cursor',next_id,'as_of',clock_timestamp());
 END IF;
 IF action='create' THEN
  IF (SELECT count(*) FROM jsonb_object_keys(payload))<>3 OR NOT payload ?& ARRAY['key','name','purpose']
  OR payload->>'key' IS NULL OR payload->>'name' IS NULL OR payload->>'purpose' IS NULL
  OR btrim(payload->>'name')='' OR (payload->>'name') ~ '[<>\\{}[:cntrl:]]' THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
  INSERT INTO public.print_templates(key,name,purpose,created_by) VALUES(payload->>'key',payload->>'name',payload->>'purpose',actor) RETURNING * INTO t;
  RETURN to_jsonb(t)-'created_by';
 END IF;
 IF NOT is_read AND (payload->>'expected' IS NULL OR (payload->>'expected')::bigint<1) THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
 -- One parent lock serializes version allocation, editing and future transitions.
 SELECT * INTO t FROM public.print_templates WHERE template_id=(payload->>'template_id')::uuid FOR UPDATE;
 IF NOT FOUND THEN RETURN jsonb_build_object('error','NOT_FOUND'); END IF;
 IF action='detail' THEN
  take:=COALESCE((payload->>'limit')::integer,20); after_id:=(payload->>'after')::uuid;
  IF take NOT BETWEEN 1 AND 50 THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
  SELECT jsonb_agg(to_jsonb(x)-'created_by'-'updated_by'-'version_note' ORDER BY revision_id) INTO rows FROM (
   SELECT * FROM public.print_template_revisions WHERE template_id=t.template_id AND (after_id IS NULL OR revision_id>after_id) ORDER BY revision_id LIMIT take+1) x;
  rows:=COALESCE(rows,'[]'::jsonb);
  IF jsonb_array_length(rows)>take THEN rows:=rows-take; next_id:=(rows->(take-1)->>'revision_id')::uuid; END IF;
  RETURN jsonb_build_object('template',to_jsonb(t)-'created_by','revisions',rows,'next_cursor',next_id);
 END IF;
 IF action='revision' THEN
  IF (payload->>'expected')::bigint<>t.row_version THEN RETURN jsonb_build_object('error','VERSION_MISMATCH'); END IF;
  IF EXISTS(SELECT 1 FROM public.print_template_revisions WHERE template_id=t.template_id AND status='draft') THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
  IF EXISTS(SELECT 1 FROM public.print_template_revisions WHERE template_id=t.template_id) THEN
   IF NOT EXISTS(SELECT 1 FROM public.print_template_revisions WHERE template_id=t.template_id AND revision_id=(payload->>'base_revision_id')::uuid) THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
  ELSIF payload->>'base_revision_id' IS NOT NULL THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
  IF (SELECT count(*) FROM public.print_template_revisions WHERE template_id=t.template_id)>=100 THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
  INSERT INTO public.print_template_revisions(template_id,version,content,version_note,created_by,updated_by)
   SELECT t.template_id,COALESCE(max(version),0)+1,payload->'content',payload->>'version_note',actor,actor FROM public.print_template_revisions WHERE template_id=t.template_id RETURNING * INTO r;
  UPDATE public.print_templates SET row_version=row_version+1 WHERE template_id=t.template_id RETURNING * INTO t;
  RETURN jsonb_build_object('template',to_jsonb(t)-'created_by','revision',(to_jsonb(r)-'created_by'-'updated_by'-'version_note')||jsonb_build_object('fingerprint_sha256',NULL,'published_at',NULL));
 END IF;
 SELECT * INTO r FROM public.print_template_revisions WHERE template_id=t.template_id AND revision_id=(payload->>'revision_id')::uuid FOR UPDATE;
 IF NOT FOUND THEN RETURN jsonb_build_object('error','NOT_FOUND'); END IF;
 IF (payload->>'expected')::bigint<>r.row_version THEN RETURN jsonb_build_object('error','VERSION_MISMATCH'); END IF;
 IF r.status<>'draft' THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
 IF action='submit' THEN
  SELECT * INTO a FROM public.print_template_asset_sets WHERE asset_set_id=(r.content->>'asset_set_id')::uuid AND withdrawn_at IS NULL FOR SHARE;
  IF NOT FOUND THEN RETURN jsonb_build_object('error','PROVIDER_UNAVAILABLE'); END IF;
  IF payload->'proof_content' IS DISTINCT FROM r.content OR payload->>'proof_font' IS DISTINCT FROM a.font_sha256::text
  OR payload->>'proof_logo' IS DISTINCT FROM a.logo_sha256::text OR (payload->>'proof_fingerprint') IS NULL OR (payload->>'proof_fingerprint')!~'^[0-9a-f]{64}$' THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
  UPDATE public.print_template_revisions SET status='pending_qa',row_version=row_version+1,fingerprint_sha256=payload->>'proof_fingerprint',updated_by=actor WHERE revision_id=r.revision_id RETURNING * INTO r;
  UPDATE public.print_templates SET row_version=row_version+1 WHERE template_id=t.template_id;
  RETURN jsonb_build_object('revision',to_jsonb(r)-'created_by'-'updated_by'-'version_note','validation_status','needs_independent_physical_qa');
 END IF;
 UPDATE public.print_template_revisions SET content=payload->'content',version_note=payload->>'version_note',updated_by=actor,row_version=row_version+1 WHERE revision_id=r.revision_id RETURNING * INTO r;
 UPDATE public.print_templates SET row_version=row_version+1 WHERE template_id=t.template_id;
 RETURN (to_jsonb(r)-'created_by'-'updated_by'-'version_note')||jsonb_build_object('fingerprint_sha256',NULL,'published_at',NULL);
END $$;
REVOKE ALL ON FUNCTION public.sr_template_content_valid(jsonb) FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
REVOKE ALL ON FUNCTION public.sr_template_service(uuid,bigint,text,jsonb) FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
GRANT EXECUTE ON FUNCTION public.sr_template_service(uuid,bigint,text,jsonb) TO safereturn_api;

CREATE FUNCTION public.sr_template_preview_admit(sid uuid,amr bigint,k text,h text) RETURNS text
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE actor uuid:=public.sr_actor_id(); previous text;
BEGIN
 IF public.sr_is_staff(ARRAY['operations']) IS NOT TRUE OR NOT EXISTS(SELECT 1 FROM public.sr_account_session_state(sid) s WHERE s.email_verified AND s.mfa_active)
 OR amr IS NULL OR amr<0 OR amr>extract(epoch FROM clock_timestamp()) OR extract(epoch FROM clock_timestamp())-amr>300 THEN RETURN 'FORBIDDEN'; END IF;
 IF k IS NULL OR h IS NULL OR k!~'^[0-9a-f]{64}$' OR h!~'^[0-9a-f]{64}$' THEN RETURN 'CONFLICT'; END IF;
 PERFORM pg_advisory_xact_lock(hashtextextended('template-preview:'||actor::text,0));
 SELECT request_hash INTO previous FROM public.print_template_preview_commands WHERE actor_id=actor AND key_hash=k;
 IF FOUND AND previous<>h THEN RETURN 'IDEMPOTENCY_KEY_REUSED'; END IF;
 IF (SELECT count(*) FROM public.print_template_preview_attempts WHERE actor_id=actor AND admitted_at>clock_timestamp()-interval '60 seconds')>=5 THEN RETURN 'RATE_LIMITED'; END IF;
 INSERT INTO public.print_template_preview_commands(actor_id,key_hash,request_hash) VALUES(actor,k,h) ON CONFLICT DO NOTHING;
 INSERT INTO public.print_template_preview_attempts(actor_id) VALUES(actor);
 INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,target_id,reason,safe_details)
 VALUES(actor,'staff','template.preview_admitted','print_template_preview',actor,'synthetic private preview admission',jsonb_build_object('outcome','admitted'));
 RETURN 'ok';
END $$;
REVOKE ALL ON FUNCTION public.sr_template_preview_admit(uuid,bigint,text,text) FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
GRANT EXECUTE ON FUNCTION public.sr_template_preview_admit(uuid,bigint,text,text) TO safereturn_api;
