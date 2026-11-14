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
 IF NOT is_read AND (amr IS NULL OR amr<0 OR amr>extract(epoch FROM clock_timestamp()) OR extract(epoch FROM clock_timestamp())-amr>1200) THEN RETURN NULL; END IF;
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
 OR amr IS NULL OR amr<0 OR amr>extract(epoch FROM clock_timestamp()) OR extract(epoch FROM clock_timestamp())-amr>1200 THEN RETURN 'FORBIDDEN'; END IF;
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
CREATE OR REPLACE FUNCTION public.sr_template_lifecycle(sid uuid,amr bigint,action text,payload jsonb) RETURNS jsonb
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE h uuid; assignment uuid; r public.print_template_revisions; t public.print_templates; e public.template_qa_approvals;
 b public.print_template_variant_bindings; v public.product_variants; ctx jsonb; aid uuid; k public.template_issuer_keys; rows jsonb;
BEGIN
 IF NOT EXISTS(SELECT 1 FROM public.sr_account_session_state(sid) s WHERE s.email_verified AND s.mfa_active) THEN RETURN NULL; END IF;
 IF action IN('context_import','import','revoke','custody_check') THEN
  IF public.sr_is_staff(ARRAY['security_admin']) IS NOT TRUE THEN RETURN NULL; END IF;
 ELSIF action='bindings' THEN
  IF public.sr_is_staff(ARRAY['operations','security_admin','superadmin']) IS NOT TRUE THEN RETURN NULL; END IF;
 ELSE IF public.sr_is_staff(ARRAY['operations']) IS NOT TRUE THEN RETURN NULL; END IF; END IF;
 IF action<>'bindings' AND (amr IS NULL OR amr<0 OR amr>extract(epoch FROM clock_timestamp()) OR extract(epoch FROM clock_timestamp())-amr>1200) THEN RETURN NULL; END IF;
 IF action<>'bindings' AND NOT EXISTS(SELECT 1 FROM public.template_people) THEN RETURN jsonb_build_object('error','PROVIDER_UNAVAILABLE'); END IF;
 h:=public.sr_template_human();
 IF h IS NULL AND action NOT IN('bindings','bind') THEN RETURN NULL; END IF;
 IF action IN('context_import','import','revoke','custody_check') THEN assignment:=public.sr_template_assignment(h,'custody');
 ELSIF action IN('context_publish','publish','retire','publisher_check','approval_input') THEN assignment:=public.sr_template_assignment(h,'publish'); END IF;
 IF action NOT IN('bind','bindings') AND assignment IS NULL THEN RETURN NULL; END IF;
 IF action IN('publisher_check','custody_check') THEN RETURN jsonb_build_object('human_id',h); END IF;
 IF action IN('context_import','context_publish') THEN
  RETURN public.sr_template_evidence_context((payload->>'revision_id')::uuid,(payload->>'policy_id')::uuid,(payload->>'policy_version')::integer,
  CASE WHEN action='context_import' THEN 'import' ELSE 'publish' END,(payload->>'importer_human')::uuid);
 END IF;
 IF action='approval_input' THEN
  SELECT * INTO e FROM public.template_qa_approvals WHERE approval_id=(payload->>'approval_id')::uuid;
  IF NOT FOUND THEN RETURN jsonb_build_object('error','NOT_FOUND'); END IF;
  RETURN jsonb_build_object('approval_id',e.approval_id,'ciphertext',encode(e.ciphertext,'hex'),'key_version',e.key_version,'importer_human',e.importer_human,'evidence_sha256',e.evidence_sha256);
 END IF;
 IF action='bindings' THEN
  SELECT COALESCE(jsonb_agg(to_jsonb(x) ORDER BY binding_id),'[]'::jsonb) INTO rows FROM (
   SELECT * FROM public.print_template_variant_bindings WHERE ((payload->>'after') IS NULL OR binding_id>(payload->>'after')::uuid)
   AND ((payload->>'variant_id') IS NULL OR variant_id=(payload->>'variant_id')::uuid)
   AND ((payload->>'tag_type') IS NULL OR tag_type=payload->>'tag_type') AND ((payload->>'active') IS NULL OR is_active=(payload->>'active')::boolean)
   ORDER BY binding_id LIMIT LEAST(COALESCE((payload->>'limit')::integer,20),50)+1) x;
  RETURN jsonb_build_object('items',rows,'next_cursor',NULL,'as_of',clock_timestamp());
 END IF;
 PERFORM public.sr_template_registry_gate(true);
 IF action='import' THEN
  SELECT * INTO r FROM public.print_template_revisions WHERE revision_id=(payload->'summary'->>'revision_id')::uuid FOR UPDATE;
  IF r.status<>'pending_qa' OR NOT r.provenance_complete OR r.row_version<>(payload->'summary'->>'revision_row_version')::bigint OR r.fingerprint_sha256<>payload->'summary'->>'revision_fingerprint_sha256' THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
  IF (payload->'summary'->>'expires_at')::timestamptz<=clock_timestamp() THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
  SELECT * INTO e FROM public.template_qa_approvals WHERE evidence_id=(payload->'summary'->>'evidence_id')::uuid;
  IF FOUND THEN
   IF e.evidence_sha256<>payload->'summary'->>'evidence_sha256' THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
  ELSE
   INSERT INTO public.template_qa_approvals(approval_id,evidence_id,revision_id,revision_row_version,revision_fingerprint_sha256,evidence_sha256,policy_id,policy_version,summary,ciphertext,key_version,importer_human,expires_at)
   VALUES((payload->>'approval_id')::uuid,(payload->'summary'->>'evidence_id')::uuid,r.revision_id,r.row_version,r.fingerprint_sha256,payload->'summary'->>'evidence_sha256',
   (payload->'summary'->>'policy_id')::uuid,(payload->'summary'->>'policy_version')::integer,payload->'summary',decode(payload->>'ciphertext','hex'),(payload->>'key_version')::smallint,h,(payload->'summary'->>'expires_at')::timestamptz) RETURNING * INTO e;
  END IF;
  RETURN jsonb_build_object('approval_id',e.approval_id,'revision_id',r.revision_id,'revision_row_version',e.revision_row_version,'revision_fingerprint_sha256',e.revision_fingerprint_sha256,'evidence_sha256',e.evidence_sha256,'state','eligible','expires_at',e.expires_at);
 END IF;
 IF action='revoke' THEN
  IF (payload->>'key_id' IS NULL)=(payload->>'evidence_id' IS NULL) THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
  IF payload->>'key_id' IS NOT NULL THEN
   SELECT * INTO k FROM public.template_issuer_keys WHERE key_id=(payload->>'key_id')::uuid FOR UPDATE;
   IF NOT FOUND THEN RETURN jsonb_build_object('error','NOT_FOUND'); END IF;
   IF k.authority_version<>(payload->>'expected_authority_version')::bigint THEN RETURN jsonb_build_object('error','VERSION_MISMATCH'); END IF;
   UPDATE public.template_issuer_keys SET revoked_at=COALESCE(revoked_at,clock_timestamp()),authority_version=authority_version+1 WHERE key_id=k.key_id;
   aid:=k.key_id;
  ELSE
   SELECT * INTO e FROM public.template_qa_approvals WHERE evidence_id=(payload->>'evidence_id')::uuid FOR UPDATE;
   IF NOT FOUND THEN RETURN jsonb_build_object('error','NOT_FOUND'); END IF;
   IF e.authority_version<>(payload->>'expected_authority_version')::bigint THEN RETURN jsonb_build_object('error','VERSION_MISMATCH'); END IF;
   UPDATE public.template_qa_approvals SET revoked_at=COALESCE(revoked_at,clock_timestamp()),authority_version=authority_version+1 WHERE approval_id=e.approval_id;
   aid:=e.evidence_id;
  END IF;
  INSERT INTO public.template_authority_withdrawals(target_kind,target_id,authority_version,reason_code,actor_id) VALUES(CASE WHEN payload->>'key_id' IS NOT NULL THEN 'key' ELSE 'evidence' END,aid,(payload->>'expected_authority_version')::bigint+1,payload->>'reason_code',public.sr_actor_id()) RETURNING revocation_id INTO assignment;
  RETURN jsonb_build_object('revocation_id',assignment,'target_kind',CASE WHEN payload->>'key_id' IS NOT NULL THEN 'key' ELSE 'evidence' END,'target_id',aid,'authority_version',(payload->>'expected_authority_version')::bigint+1,'state','withdrawn');
 END IF;
 IF action='bind' THEN
  IF payload->>'revision_id' IS NULL THEN
   SELECT r0.template_id INTO aid FROM public.print_template_variant_bindings b0 JOIN public.print_template_revisions r0 ON r0.revision_id=b0.revision_id
   WHERE b0.variant_id=(payload->>'variant_id')::uuid AND b0.tag_type=payload->>'tag_type' AND b0.is_active AND b0.binding_id=(payload->>'expected_binding_id')::uuid;
   SELECT * INTO b FROM public.print_template_variant_bindings WHERE binding_id=(payload->>'expected_binding_id')::uuid;
  ELSE SELECT template_id INTO aid FROM public.print_template_revisions WHERE revision_id=(payload->>'revision_id')::uuid; END IF;
 ELSE aid:=(payload->>'template_id')::uuid; END IF;
 SELECT * INTO t FROM public.print_templates WHERE template_id=aid FOR UPDATE;
 SELECT * INTO r FROM public.print_template_revisions WHERE revision_id=COALESCE((payload->>'revision_id')::uuid,b.revision_id) AND template_id=t.template_id FOR UPDATE;
 IF t.template_id IS NULL OR r.revision_id IS NULL THEN RETURN jsonb_build_object('error','NOT_FOUND'); END IF;
 IF action='publish' THEN
  IF (payload->>'expected')::bigint<>r.row_version THEN RETURN jsonb_build_object('error','VERSION_MISMATCH'); END IF;
  SELECT * INTO e FROM public.template_qa_approvals WHERE approval_id=(payload->>'approval_id')::uuid AND revision_id=r.revision_id FOR UPDATE;
  IF NOT FOUND OR e.revoked_at IS NOT NULL OR e.consumed_at IS NOT NULL OR e.expires_at<=clock_timestamp() OR e.revision_row_version<>r.row_version OR e.evidence_sha256<>payload->>'verified_evidence_sha256'
  OR r.status<>'pending_qa' OR NOT r.provenance_complete OR t.lifecycle_status='retired' THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
  IF EXISTS(SELECT 1 FROM public.template_revision_contributors c LEFT JOIN public.template_people m ON m.user_id=c.actor_id AND m.revoked_at IS NULL WHERE c.revision_id=r.revision_id AND (m.human_id IS NULL OR m.human_id=h))
  OR EXISTS(SELECT 1 FROM jsonb_array_elements(e.summary->'attestations') x JOIN public.template_issuer_keys k ON k.key_id=(x->>'key_id')::uuid JOIN public.template_authorities a ON a.authority_id=k.authority_id
   WHERE k.revoked_at IS NOT NULL OR k.expires_at<=clock_timestamp() OR a.revoked_at IS NOT NULL OR a.expires_at<=clock_timestamp() OR a.human_id=h)
  OR ((e.summary->>'allow_importer_publisher')::boolean IS NOT TRUE AND e.importer_human=h) THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
  UPDATE public.template_qa_approvals SET consumed_at=clock_timestamp(),consumed_by=h,publisher_authority_id=assignment,authority_version=authority_version+1 WHERE approval_id=e.approval_id;
  UPDATE public.print_template_revisions SET status='published',published_at=clock_timestamp(),approval_id=e.approval_id,row_version=row_version+1 WHERE revision_id=r.revision_id RETURNING * INTO r;
  UPDATE public.print_templates SET lifecycle_status='active',row_version=row_version+1 WHERE template_id=t.template_id;
  RETURN jsonb_build_object('revision',public.sr_template_revision_view(r),'approval_id',e.approval_id);
 ELSIF action='bind' THEN
  SELECT * INTO v FROM public.product_variants WHERE id=(payload->>'variant_id')::uuid FOR UPDATE;
  IF NOT FOUND THEN RETURN jsonb_build_object('error','NOT_FOUND'); END IF;
  IF v.catalog_version<>(payload->>'expected')::bigint OR v.catalog_version<>(payload->>'expected_variant_version')::bigint THEN RETURN jsonb_build_object('error','VERSION_MISMATCH'); END IF;
  IF payload->>'revision_id' IS NULL THEN
   IF v.is_active OR b.binding_id IS NULL OR NOT b.is_active OR b.variant_id<>v.id OR b.tag_type<>payload->>'tag_type' THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
   UPDATE public.print_template_variant_bindings SET is_active=false,row_version=row_version+1 WHERE binding_id=b.binding_id RETURNING * INTO b;
   UPDATE public.template_registry_sources SET generation=generation+1 WHERE variant_id=v.id;
   UPDATE public.product_variants SET catalog_version=catalog_version+1 WHERE id=v.id RETURNING * INTO v;
   RETURN jsonb_build_object('binding',to_jsonb(b),'variant_row_version',v.catalog_version);
  END IF;
  IF NOT public.sr_template_revision_clear(r.revision_id,false) THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
  IF v.template_key IS DISTINCT FROM t.key OR v.template_version IS DISTINCT FROM r.version OR v.fulfillment_method IS DISTINCT FROM 'pdf_label' OR v.size_mm IS DISTINCT FROM (r.content->>'symbol_mm')::numeric OR t.purpose IS DISTINCT FROM payload->>'tag_type'
  OR NOT COALESCE((r.content->'material_codes') ? v.material,false) THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
  SELECT * INTO b FROM public.print_template_variant_bindings WHERE variant_id=v.id AND tag_type=payload->>'tag_type' AND is_active FOR UPDATE;
  IF b.binding_id IS DISTINCT FROM (payload->>'expected_binding_id')::uuid THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
  UPDATE public.print_template_variant_bindings SET is_active=false,row_version=row_version+1 WHERE binding_id=b.binding_id;
  INSERT INTO public.print_template_variant_bindings(variant_id,tag_type,revision_id) VALUES(v.id,t.purpose,r.revision_id) RETURNING * INTO b;
  INSERT INTO public.template_registry_sources(variant_id) VALUES(v.id) ON CONFLICT(variant_id) DO UPDATE SET generation=public.template_registry_sources.generation+1;
  UPDATE public.product_variants SET catalog_version=catalog_version+1 WHERE id=v.id RETURNING * INTO v;
  RETURN jsonb_build_object('binding',to_jsonb(b),'variant_row_version',v.catalog_version);
 ELSIF action='retire' THEN
  IF (payload->>'expected')::bigint<>r.row_version THEN RETURN jsonb_build_object('error','VERSION_MISMATCH'); END IF;
  IF r.status<>'published' OR EXISTS(SELECT 1 FROM public.print_template_variant_bindings WHERE revision_id=r.revision_id AND is_active) THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
  UPDATE public.print_template_revisions SET status='retired',row_version=row_version+1 WHERE revision_id=r.revision_id RETURNING * INTO r;
  UPDATE public.print_templates SET lifecycle_status=CASE WHEN NOT EXISTS(SELECT 1 FROM public.print_template_revisions WHERE template_id=t.template_id AND status<>'retired') THEN 'retired' ELSE lifecycle_status END,row_version=row_version+1 WHERE template_id=t.template_id RETURNING * INTO t;
  RETURN jsonb_build_object('revision',public.sr_template_revision_view(r),'template',to_jsonb(t)-'created_by');
 END IF;
 RETURN jsonb_build_object('error','CONFLICT');
END $$;
COMMIT;
