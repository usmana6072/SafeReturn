-- Development-only reviewed policy update; no migration 0044 or table changes.
BEGIN;
SET LOCAL lock_timeout='5s';
CREATE OR REPLACE FUNCTION public.sr_template_draft_service_v33(sid uuid,amr bigint,action text,payload jsonb) RETURNS jsonb
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE actor uuid:=public.sr_actor_id(); t public.print_templates; r public.print_template_revisions;
 result jsonb; rows jsonb; take integer; after_id uuid; next_id uuid; a public.print_template_asset_sets; is_read boolean:=action IN('list','detail');
BEGIN
 IF public.sr_is_staff(CASE WHEN is_read THEN ARRAY['operations','security_admin','superadmin'] ELSE ARRAY['operations'] END) IS NOT TRUE
 OR NOT EXISTS(SELECT 1 FROM public.sr_account_session_state(sid) s WHERE s.email_verified AND s.mfa_active) THEN RETURN NULL; END IF;
 IF NOT is_read AND (amr IS NULL OR amr<0 OR amr>extract(epoch FROM clock_timestamp()) OR extract(epoch FROM clock_timestamp())-amr>CASE WHEN action IN('create','revision','edit','preview_input') THEN 900 ELSE 300 END) THEN RETURN NULL; END IF;
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
CREATE OR REPLACE FUNCTION public.sr_template_preview_admit(sid uuid,amr bigint,k text,h text) RETURNS text
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE actor uuid:=public.sr_actor_id(); previous text;
BEGIN
 IF public.sr_is_staff(ARRAY['operations']) IS NOT TRUE OR NOT EXISTS(SELECT 1 FROM public.sr_account_session_state(sid) s WHERE s.email_verified AND s.mfa_active)
 OR amr IS NULL OR amr<0 OR amr>extract(epoch FROM clock_timestamp()) OR extract(epoch FROM clock_timestamp())-amr>900 THEN RETURN 'FORBIDDEN'; END IF;
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
COMMIT;
