-- Manual approval is explicit, never masquerades as cryptographic evidence.
-- Existing order/snapshot approval FKs remain intact and point to a real record.
ALTER TABLE public.template_qa_approvals
 ADD COLUMN approval_kind text NOT NULL DEFAULT 'signed_evidence' CHECK(approval_kind IN('signed_evidence','manual_print')),
 ADD COLUMN manual_review_id uuid UNIQUE REFERENCES public.template_qa_reviews(review_id) ON DELETE RESTRICT,
 ALTER COLUMN ciphertext DROP NOT NULL, ALTER COLUMN key_version DROP NOT NULL,
 ALTER COLUMN importer_human DROP NOT NULL, ALTER COLUMN expires_at DROP NOT NULL;
ALTER TABLE public.template_qa_approvals ADD CONSTRAINT sr_template_approval_source CHECK(
 (approval_kind='signed_evidence' AND manual_review_id IS NULL AND ciphertext IS NOT NULL AND key_version IS NOT NULL AND importer_human IS NOT NULL AND expires_at IS NOT NULL)
 OR(approval_kind='manual_print' AND manual_review_id IS NOT NULL AND ciphertext IS NULL AND key_version IS NULL AND importer_human IS NULL AND expires_at IS NULL)
);
ALTER TABLE public.print_template_revisions DROP CONSTRAINT ck_template_revision_lifecycle;
ALTER TABLE public.print_template_revisions ADD CONSTRAINT ck_template_revision_lifecycle CHECK(
 (status='draft' AND fingerprint_sha256 IS NULL AND published_at IS NULL AND approval_id IS NULL AND manual_review_id IS NULL)
 OR(status='pending_qa' AND fingerprint_sha256 IS NOT NULL AND published_at IS NULL AND approval_id IS NULL AND manual_review_id IS NULL)
 OR(status IN('published','retired') AND fingerprint_sha256 IS NOT NULL AND published_at IS NOT NULL AND (approval_id IS NOT NULL OR manual_review_id IS NOT NULL))
);
DO $patch$
DECLARE source text; anchor text; injected text;
BEGIN
 source:=pg_get_functiondef('public.sr_template_manual_publication_guard()'::regprocedure);
 anchor:=' IF NEW.manual_review_id IS NOT NULL THEN';
 IF position(anchor IN source)=0 THEN RAISE EXCEPTION 'Review manual publication guard'; END IF;
 injected:=$body$
 IF NEW.manual_review_id IS NULL AND NEW.approval_id IS NOT NULL AND EXISTS(SELECT 1 FROM public.template_qa_approvals e WHERE e.approval_id=NEW.approval_id AND e.approval_kind='manual_print') THEN RAISE EXCEPTION 'Manual review provenance required' USING ERRCODE='23514'; END IF;
 IF NEW.manual_review_id IS NOT NULL AND NEW.approval_id IS NOT NULL AND NOT EXISTS(
  SELECT 1 FROM public.template_qa_approvals e WHERE e.approval_id=NEW.approval_id AND e.approval_kind='manual_print'
  AND e.manual_review_id=NEW.manual_review_id AND e.revision_id=NEW.revision_id AND e.revision_fingerprint_sha256=NEW.fingerprint_sha256
 ) THEN RAISE EXCEPTION 'Manual approval reference mismatch' USING ERRCODE='23514'; END IF;
$body$;
 EXECUTE replace(source,anchor,injected||anchor);
 source:=pg_get_functiondef('public.sr_template_revision_clear(uuid,boolean)'::regprocedure);
 anchor:=' SELECT * INTO e FROM public.template_qa_approvals WHERE approval_id=r.approval_id;';
 IF position(anchor IN source)=0 THEN RAISE EXCEPTION 'Review installed approval predicate'; END IF;
 injected:=$body$
 IF r.manual_review_id IS NOT NULL THEN
  RETURN EXISTS(SELECT 1 FROM public.template_qa_approvals a JOIN public.template_qa_reviews q ON q.review_id=a.manual_review_id
   JOIN public.template_production_policies p ON p.policy_id=a.policy_id AND p.version=a.policy_version
   JOIN public.print_template_asset_sets s ON s.asset_set_id=(r.content->>'asset_set_id')::uuid
   WHERE a.approval_id=r.approval_id AND a.approval_kind='manual_print' AND a.manual_review_id=r.manual_review_id
   AND a.revision_id=r.revision_id AND a.revision_fingerprint_sha256=r.fingerprint_sha256 AND a.revoked_at IS NULL AND a.consumed_at IS NOT NULL
   AND q.decision='approved' AND q.evidence_kind='manual_print' AND q.preview_fingerprint=r.fingerprint_sha256
   AND NOT EXISTS(SELECT 1 FROM public.template_qa_reviews newer WHERE newer.revision_id=r.revision_id AND newer.review_version>q.review_version)
   AND p.revoked_at IS NULL AND a.summary->>'policy_sha256'=p.sha256 AND p.body->>'approval_mode'='manual_print' AND p.body->>'renderer'='safereturn-vector-v1'
   AND s.withdrawn_at IS NULL);
 END IF;
$body$;
 EXECUTE replace(source,anchor,injected||anchor||E'\n IF e.approval_kind=''manual_print'' THEN RETURN false; END IF;');
 source:=pg_get_functiondef('public.sr_template_lifecycle(uuid,bigint,text,jsonb)'::regprocedure);
 anchor:=' IF action IN (''manual_review_status'',''manual_review_decide'') THEN';
 IF position(anchor IN source)=0 THEN RAISE EXCEPTION 'Review manual lifecycle integration'; END IF;
 injected:=$body$
 IF action='manual_variant_bind' THEN
  IF NOT EXISTS(SELECT 1 FROM public.sr_account_session_state(sid) s WHERE s.email_verified AND s.mfa_active)
   OR public.sr_is_staff(ARRAY['operations']) IS NOT TRUE OR amr IS NULL OR amr<0 OR amr>extract(epoch FROM clock_timestamp()) OR extract(epoch FROM clock_timestamp())-amr>1200 THEN RETURN NULL; END IF;
  PERFORM public.sr_template_registry_gate(true);
  SELECT * INTO v FROM public.product_variants WHERE id=(payload->>'variant_id')::uuid FOR UPDATE;
  IF NOT FOUND OR payload->>'expected' IS NULL OR v.catalog_version<>(payload->>'expected')::bigint THEN RETURN jsonb_build_object('error','VERSION_MISMATCH'); END IF;
  IF NOT EXISTS(SELECT 1 FROM public.products x WHERE x.id=v.product_id AND x.commerce_model='single_qr' AND x.qr_type IN('lost','ice') AND x.lifecycle_status<>'archived') THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
  SELECT r0.* INTO r FROM public.print_template_revisions r0 JOIN public.print_templates t0 ON t0.template_id=r0.template_id
   JOIN public.products x ON x.id=v.product_id WHERE t0.key=v.template_key AND r0.version=v.template_version AND r0.status='published' AND t0.lifecycle_status='active' AND t0.purpose=x.qr_type FOR UPDATE OF r0;
  IF NOT FOUND THEN RETURN jsonb_build_object('error','TEMPLATE_BINDING_UNAVAILABLE'); END IF;
  SELECT * INTO t FROM public.print_templates WHERE template_id=r.template_id;
  IF v.currency_code<>'PKR' OR v.fulfillment_method<>'pdf_label' OR v.size_mm IS DISTINCT FROM (r.content->>'symbol_mm')::numeric OR NOT COALESCE((r.content->'material_codes') ? v.material,false) THEN RETURN jsonb_build_object('error','TEMPLATE_VARIANT_MISMATCH'); END IF;
  SELECT * INTO b FROM public.print_template_variant_bindings WHERE variant_id=v.id AND tag_type=t.purpose AND is_active FOR UPDATE;
  IF r.manual_review_id IS NULL THEN
   RETURN public.sr_template_lifecycle(sid,amr,'bind',jsonb_build_object('variant_id',v.id,'tag_type',t.purpose,'revision_id',r.revision_id,'expected',v.catalog_version,'expected_variant_version',v.catalog_version,'expected_binding_id',b.binding_id,'confirmed',true));
  END IF;
  IF NOT EXISTS(SELECT 1 FROM public.print_template_asset_sets s WHERE s.asset_set_id=(r.content->>'asset_set_id')::uuid AND s.withdrawn_at IS NULL) THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
  SELECT to_jsonb(q) INTO ctx FROM public.template_qa_reviews q WHERE q.review_id=r.manual_review_id AND q.revision_id=r.revision_id AND q.decision='approved' AND q.evidence_kind='manual_print' AND q.preview_fingerprint=r.fingerprint_sha256;
  IF ctx IS NULL OR EXISTS(SELECT 1 FROM public.template_qa_reviews q WHERE q.revision_id=r.revision_id AND q.review_version>(ctx->>'review_version')::bigint) THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
  IF payload->>'policy_sha256' IS NULL OR payload->>'policy_id' IS NULL OR payload->'policy'->>'approval_mode' IS DISTINCT FROM 'manual_print' OR payload->'policy'->>'renderer' IS DISTINCT FROM 'safereturn-vector-v1' OR (payload->>'policy_sha256') !~ '^[a-f0-9]{64}$' THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
  IF NOT COALESCE((payload->'policy'->>'canonical_origin') ~ '^https://[A-Za-z0-9.-]+(:[0-9]{1,5})?$' OR (payload->'policy'->>'canonical_origin') ~ '^http://(127[.]0[.]0[.]1|localhost)(:[0-9]{1,5})?$',false) THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
  IF NOT EXISTS(SELECT 1 FROM public.template_production_policies p WHERE p.policy_id=(payload->>'policy_id')::uuid AND p.version=1) THEN
   INSERT INTO public.template_production_policies(policy_id,version,sha256,body,reviewed_by,archive_reference)
    VALUES((payload->>'policy_id')::uuid,1,payload->>'policy_sha256',payload->'policy',public.sr_actor_id(),'manual-print-binding-v1');
  END IF;
  IF NOT EXISTS(SELECT 1 FROM public.template_production_policies p WHERE p.policy_id=(payload->>'policy_id')::uuid AND p.version=1 AND p.sha256=payload->>'policy_sha256' AND p.body=payload->'policy' AND p.revoked_at IS NULL) THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
  SELECT * INTO e FROM public.template_qa_approvals WHERE manual_review_id=r.manual_review_id;
  IF NOT FOUND THEN
   ctx:=jsonb_build_object('approval_mode','manual_print','review_id',r.manual_review_id,'reviewer_user_id',ctx->>'reviewer_user_id','reviewed_at',ctx->>'decided_at','revision_fingerprint_sha256',r.fingerprint_sha256,'policy_sha256',payload->>'policy_sha256');
   INSERT INTO public.template_qa_approvals(approval_id,evidence_id,revision_id,revision_row_version,revision_fingerprint_sha256,evidence_sha256,policy_id,policy_version,summary,ciphertext,key_version,importer_human,expires_at,consumed_at,approval_kind,manual_review_id)
    VALUES(gen_random_uuid(),r.manual_review_id,r.revision_id,r.row_version,r.fingerprint_sha256,encode(sha256(convert_to(ctx::text,'UTF8')),'hex'),(payload->>'policy_id')::uuid,1,ctx,NULL,NULL,NULL,NULL,clock_timestamp(),'manual_print',r.manual_review_id) RETURNING * INTO e;
  END IF;
  IF e.approval_kind<>'manual_print' OR e.policy_id<>(payload->>'policy_id')::uuid OR e.revoked_at IS NOT NULL THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
  IF r.approval_id IS DISTINCT FROM e.approval_id THEN
   UPDATE public.print_template_revisions SET approval_id=e.approval_id,row_version=row_version+1 WHERE revision_id=r.revision_id;
  END IF;
  IF NOT public.sr_template_revision_clear(r.revision_id,false) THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
  IF b.revision_id=r.revision_id THEN RETURN jsonb_build_object('binding',to_jsonb(b),'variant_row_version',v.catalog_version); END IF;
  UPDATE public.print_template_variant_bindings SET is_active=false,row_version=row_version+1 WHERE variant_id=v.id AND tag_type=t.purpose AND is_active;
  INSERT INTO public.print_template_variant_bindings(variant_id,tag_type,revision_id) VALUES(v.id,t.purpose,r.revision_id) RETURNING * INTO b;
  INSERT INTO public.template_registry_sources(variant_id) VALUES(v.id) ON CONFLICT(variant_id) DO UPDATE SET generation=public.template_registry_sources.generation+1;
  UPDATE public.product_variants SET catalog_version=catalog_version+1 WHERE id=v.id RETURNING * INTO v;
  INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,target_id,reason,safe_details) VALUES(public.sr_actor_id(),'staff','template.variant.bound','print_template',r.template_id,'Published physical QA design selected for typed variant',jsonb_build_object('event_id',b.binding_id::text,'outcome','success'));
  RETURN jsonb_build_object('binding',to_jsonb(b),'variant_row_version',v.catalog_version);
 END IF;
$body$;
 source:=replace(source,anchor,injected||anchor);
 anchor:='  SELECT * INTO e FROM public.template_qa_approvals WHERE approval_id=(payload->>''approval_id'')::uuid;';
 IF position(anchor IN source)=0 THEN RAISE EXCEPTION 'Review signed evidence read boundary'; END IF;
 source:=replace(source,anchor,anchor||E'\n  IF FOUND AND e.approval_kind=''manual_print'' THEN RETURN jsonb_build_object(''error'',''CONFLICT''); END IF;');
 EXECUTE source;
END $patch$;
