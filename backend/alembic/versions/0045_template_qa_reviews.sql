-- SOURCE ONLY. No grants, role changes, enrollment, seeds or migration execution.
CREATE TABLE public.template_qa_reviews (
 review_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 revision_id uuid NOT NULL REFERENCES public.print_template_revisions(revision_id) ON DELETE RESTRICT,
 revision_row_version bigint NOT NULL CHECK(revision_row_version>0),
 review_version bigint NOT NULL CHECK(review_version>0),
 decision text NOT NULL CHECK(decision IN ('approved','rejected')),
 review_note text NOT NULL CHECK(length(btrim(review_note)) BETWEEN 4 AND 500),
 reviewer_user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
 reviewer_human_id uuid NOT NULL,
 approval_id uuid REFERENCES public.template_qa_approvals(approval_id) ON DELETE RESTRICT,
 decided_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(revision_id,review_version),
 CHECK((decision='approved')=(approval_id IS NOT NULL))
);
ALTER TABLE public.template_qa_reviews ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.template_qa_reviews FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
-- Access only through the existing authenticated SECURITY DEFINER function.
CREATE TRIGGER sr_template_reviews_append BEFORE UPDATE OR DELETE ON public.template_qa_reviews
 FOR EACH ROW EXECUTE FUNCTION public.sr_template_no_rewrite();

-- Preserve the installed function's owner, ACL, search_path and 1200s recency.
-- Abort on unexpected source rather than replacing unrelated lifecycle behavior.
DO $migration$
DECLARE source text; anchor text := ' IF action=''import'' THEN'; injected text;
BEGIN
 source := pg_get_functiondef('public.sr_template_lifecycle(uuid,bigint,text,jsonb)'::regprocedure);
 -- Fresh migration chains carry the original 300s policy. Apply only the
 -- owner-approved template recency change; already-1200s installs stay intact.
 source := replace(source,'extract(epoch FROM clock_timestamp())-amr>300','extract(epoch FROM clock_timestamp())-amr>1200');
 IF position(anchor IN source)=0 OR position('>1200' IN replace(source,' ',''))=0
 OR position('sr_template_registry_gate(true)' IN source)=0 THEN
  RAISE EXCEPTION 'Template lifecycle source/20-minute policy requires review';
 END IF;
 injected := $body$
 IF action IN ('import','publish') AND EXISTS (
  SELECT 1 FROM public.template_qa_reviews q WHERE q.revision_id=COALESCE((payload->>'revision_id')::uuid,(payload->'summary'->>'revision_id')::uuid)
  AND q.decision='rejected' AND q.review_version=(SELECT max(q2.review_version) FROM public.template_qa_reviews q2 WHERE q2.revision_id=q.revision_id)
 ) THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
$body$;
 source := replace(source,anchor,injected||anchor);
 anchor := ' IF NOT EXISTS(SELECT 1 FROM public.sr_account_session_state(sid)';
 IF position(anchor IN source)=0 THEN RAISE EXCEPTION 'Unexpected lifecycle authentication source'; END IF;
 injected := $body$
 IF action IN ('review_status','review_decide') THEN
  IF NOT EXISTS(SELECT 1 FROM public.sr_account_session_state(sid) s WHERE s.email_verified AND s.mfa_active)
   OR public.sr_is_staff(ARRAY['operations','security_admin','superadmin']) IS NOT TRUE
   OR amr IS NULL OR amr<0 OR amr>extract(epoch FROM clock_timestamp()) OR extract(epoch FROM clock_timestamp())-amr>1200 THEN RETURN NULL; END IF;
  PERFORM public.sr_template_registry_gate(action='review_decide');
  SELECT * INTO r FROM public.print_template_revisions WHERE revision_id=(payload->>'revision_id')::uuid AND template_id=(payload->>'template_id')::uuid;
  IF NOT FOUND THEN RETURN jsonb_build_object('error','NOT_FOUND'); END IF;
  h:=public.sr_template_human();
  assignment:=public.sr_template_assignment(h,'custody');
  IF action='review_decide' THEN
   IF public.sr_is_staff(ARRAY['security_admin']) IS NOT TRUE OR assignment IS NULL OR h IS NULL THEN RETURN NULL; END IF;
   SELECT * INTO r FROM public.print_template_revisions WHERE revision_id=r.revision_id FOR UPDATE;
   IF r.status<>'pending_qa' OR NOT r.provenance_complete OR NOT EXISTS(SELECT 1 FROM public.template_revision_contributors c WHERE c.revision_id=r.revision_id) OR r.row_version<>(payload->>'expected')::bigint THEN RETURN jsonb_build_object('error','VERSION_MISMATCH'); END IF;
   IF EXISTS(SELECT 1 FROM public.template_revision_contributors c LEFT JOIN public.template_people m ON m.user_id=c.actor_id AND m.revoked_at IS NULL WHERE c.revision_id=r.revision_id AND (m.human_id IS NULL OR m.human_id=h)) THEN RETURN NULL; END IF;
   IF COALESCE((SELECT max(q.review_version) FROM public.template_qa_reviews q WHERE q.revision_id=r.revision_id),0)<>(payload->>'expected_review_version')::bigint THEN RETURN jsonb_build_object('error','VERSION_MISMATCH'); END IF;
   IF (payload->>'expected') IS NULL OR (payload->>'expected_review_version') IS NULL OR (payload->>'expected_review_version')::bigint<0 OR payload->>'decision' IS NULL OR payload->>'review_note' IS NULL OR payload->>'decision' NOT IN ('approved','rejected') OR length(btrim(payload->>'review_note')) NOT BETWEEN 4 AND 500 OR payload->>'confirmed' IS DISTINCT FROM 'true' THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
   IF EXISTS(SELECT 1 FROM public.template_qa_reviews q WHERE q.revision_id=r.revision_id AND q.decision='rejected') THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
   IF payload->>'decision'='approved' THEN
    SELECT * INTO e FROM public.template_qa_approvals WHERE approval_id=(payload->>'approval_id')::uuid AND revision_id=r.revision_id;
    IF NOT FOUND OR e.revoked_at IS NOT NULL OR e.consumed_at IS NOT NULL OR e.expires_at<=clock_timestamp() OR e.revision_row_version<>r.row_version OR e.revision_fingerprint_sha256<>r.fingerprint_sha256 OR e.evidence_sha256 IS DISTINCT FROM payload->>'verified_evidence_sha256' OR e.importer_human<>h THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
   ELSE
    UPDATE public.template_qa_approvals SET revoked_at=COALESCE(revoked_at,clock_timestamp()),authority_version=authority_version+1 WHERE revision_id=r.revision_id AND consumed_at IS NULL AND revoked_at IS NULL;
   END IF;
   INSERT INTO public.template_qa_reviews(revision_id,revision_row_version,review_version,decision,review_note,reviewer_user_id,reviewer_human_id,approval_id)
    VALUES(r.revision_id,r.row_version,(payload->>'expected_review_version')::bigint+1,payload->>'decision',payload->>'review_note',public.sr_actor_id(),h,CASE WHEN payload->>'decision'='approved' THEN e.approval_id ELSE NULL END);
  END IF;
  SELECT COALESCE(jsonb_agg(to_jsonb(q) ORDER BY q.review_version DESC),'[]'::jsonb) INTO rows FROM (SELECT * FROM public.template_qa_reviews WHERE revision_id=r.revision_id ORDER BY review_version DESC LIMIT 20) q;
  RETURN jsonb_build_object('revision_id',r.revision_id,'revision_row_version',r.row_version,'review_version',COALESCE((rows->0->>'review_version')::bigint,0),'status',COALESCE(rows->0->>'decision','pending'),'history',rows,
   'can_review',public.sr_is_staff(ARRAY['security_admin']) IS TRUE AND assignment IS NOT NULL AND h IS NOT NULL AND r.status='pending_qa' AND r.provenance_complete AND EXISTS(SELECT 1 FROM public.template_revision_contributors c WHERE c.revision_id=r.revision_id) AND COALESCE(rows->0->>'decision','pending')<>'rejected' AND NOT EXISTS(SELECT 1 FROM public.template_revision_contributors c LEFT JOIN public.template_people m ON m.user_id=c.actor_id AND m.revoked_at IS NULL WHERE c.revision_id=r.revision_id AND (m.human_id IS NULL OR m.human_id=h)));
 END IF;
$body$;
 source := replace(source,anchor,injected||anchor);
 EXECUTE source;
END $migration$;
