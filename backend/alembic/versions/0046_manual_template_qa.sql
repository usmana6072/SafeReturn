-- Manual QA attestation is separate from signed publication evidence.
-- No staff enrollment, role/grant/RLS change or publication eligibility change.
ALTER TABLE public.template_qa_reviews
 ADD COLUMN evidence_kind text NOT NULL DEFAULT 'signed_evidence' CHECK(evidence_kind IN('signed_evidence','manual_print')),
 ADD COLUMN preview_fingerprint char(64) CHECK(preview_fingerprint IS NULL OR preview_fingerprint ~ '^[a-f0-9]{64}$'),
 ALTER COLUMN reviewer_human_id DROP NOT NULL;
DO $$
DECLARE old_check text;
BEGIN
 SELECT conname INTO STRICT old_check FROM pg_constraint
 WHERE conrelid='public.template_qa_reviews'::regclass AND contype='c'
 AND pg_get_constraintdef(oid) LIKE '%decision%approval_id%';
 EXECUTE format('ALTER TABLE public.template_qa_reviews DROP CONSTRAINT %I',old_check);
END $$;
ALTER TABLE public.template_qa_reviews ADD CONSTRAINT sr_template_review_evidence_kind CHECK(
 (evidence_kind='manual_print' AND approval_id IS NULL AND preview_fingerprint IS NOT NULL)
 OR (evidence_kind='signed_evidence' AND reviewer_human_id IS NOT NULL AND ((decision='approved')=(approval_id IS NOT NULL)))
);
DO $migration$
DECLARE source text; anchor text := ' IF action IN (''review_status'',''review_decide'') THEN'; injected text;
BEGIN
 source:=pg_get_functiondef('public.sr_template_lifecycle(uuid,bigint,text,jsonb)'::regprocedure);
 IF position(anchor IN source)=0 OR position('manual_review_decide' IN source)>0 THEN RAISE EXCEPTION 'Unexpected QA function source'; END IF;
 injected := $body$
 IF action IN ('manual_review_status','manual_review_decide') THEN
  IF NOT EXISTS(SELECT 1 FROM public.sr_account_session_state(sid) s WHERE s.email_verified AND s.mfa_active)
   OR public.sr_is_staff(ARRAY['operations','security_admin','superadmin']) IS NOT TRUE
   OR amr IS NULL OR amr<0 OR amr>extract(epoch FROM clock_timestamp()) OR extract(epoch FROM clock_timestamp())-amr>1200 THEN RETURN NULL; END IF;
  PERFORM public.sr_template_registry_gate(action='manual_review_decide');
  SELECT * INTO r FROM public.print_template_revisions WHERE revision_id=(payload->>'revision_id')::uuid AND template_id=(payload->>'template_id')::uuid;
  IF NOT FOUND THEN RETURN jsonb_build_object('error','NOT_FOUND'); END IF;
  IF action='manual_review_decide' THEN
   IF public.sr_is_staff(ARRAY['operations']) IS NOT TRUE THEN RETURN NULL; END IF;
   SELECT * INTO r FROM public.print_template_revisions WHERE revision_id=r.revision_id FOR UPDATE;
   IF r.status<>'pending_qa' OR (payload->>'expected') IS NULL OR r.row_version<>(payload->>'expected')::bigint OR r.fingerprint_sha256 IS NULL OR r.fingerprint_sha256 IS DISTINCT FROM payload->>'preview_fingerprint' THEN RETURN jsonb_build_object('error','VERSION_MISMATCH'); END IF;
   IF (payload->>'expected_review_version') IS NULL OR COALESCE((SELECT max(q.review_version) FROM public.template_qa_reviews q WHERE q.revision_id=r.revision_id),0)<>(payload->>'expected_review_version')::bigint THEN RETURN jsonb_build_object('error','VERSION_MISMATCH'); END IF;
   IF payload->>'decision' IS NULL OR payload->>'decision' NOT IN('approved','rejected') OR payload->>'reason' IS NULL OR length(btrim(payload->>'reason')) NOT BETWEEN 4 AND 500 OR payload->>'confirmed' IS DISTINCT FROM 'true' THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
   IF EXISTS(SELECT 1 FROM public.template_qa_reviews q WHERE q.revision_id=r.revision_id AND q.decision='rejected') THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
   IF payload->>'decision'='rejected' THEN
    UPDATE public.template_qa_approvals SET revoked_at=COALESCE(revoked_at,clock_timestamp()),authority_version=authority_version+1 WHERE revision_id=r.revision_id AND consumed_at IS NULL AND revoked_at IS NULL;
   END IF;
   INSERT INTO public.template_qa_reviews(revision_id,revision_row_version,review_version,decision,review_note,reviewer_user_id,reviewer_human_id,approval_id,evidence_kind,preview_fingerprint)
    VALUES(r.revision_id,r.row_version,(payload->>'expected_review_version')::bigint+1,payload->>'decision',payload->>'reason',public.sr_actor_id(),NULL,NULL,'manual_print',r.fingerprint_sha256);
  END IF;
  SELECT COALESCE(jsonb_agg(to_jsonb(q) ORDER BY q.review_version DESC),'[]'::jsonb) INTO rows FROM (SELECT * FROM public.template_qa_reviews WHERE revision_id=r.revision_id ORDER BY review_version DESC LIMIT 20) q;
  RETURN jsonb_build_object('revision_id',r.revision_id,'revision_row_version',r.row_version,'review_version',COALESCE((rows->0->>'review_version')::bigint,0),'status',COALESCE(rows->0->>'decision','pending'),'history',rows,
   'can_review',public.sr_is_staff(ARRAY['operations']) IS TRUE AND r.status='pending_qa' AND r.fingerprint_sha256 IS NOT NULL AND COALESCE(rows->0->>'decision','pending')<>'rejected');
 END IF;
$body$;
 source:=replace(source,anchor,injected||anchor);
 EXECUTE source;
END $migration$;
